# Scenario 9: Reverb API Client Improvements

## The Ask

> "You have 30 more minutes. What would you improve about the API client?"

or

> "How would you make this client production-ready?"

This tests whether you can identify reliability, resilience, and operational concerns in an HTTP client — and implement them cleanly without over-engineering.

______________________________________________________________________

## Phase 1: Explain Your Priorities (2-3 min)

**What to say:**

"The current client works but has no safety net. Three things I'd add immediately: a timeout so we never hang, `raise_for_status()` so errors don't silently return garbage, and a Session for connection reuse and as a foundation for everything else. If I have more time, I'd add retries for 5xx, throttling to avoid 429, and a cache for stable endpoints like categories."

**Priority order to communicate:**

1. Timeout — prevents indefinite hangs
2. `raise_for_status()` — prevents silent failures
3. Session — foundation for headers, retries, auth
4. Retries — survive transient 5xx errors
5. ETag/conditional GET — leverage server's built-in cache validation (categories return `304` with zero body)
6. Throttling — proactively avoid rate limits
7. TTL Caching — eliminate redundant calls (complement ETags for full round-trip avoidance)

______________________________________________________________________

## Phase 2: Implement (Incremental)

### Step 1: Session + Timeout + Error Handling (5 min)

```python
import requests


class ReverbClient:
    HEADERS = {
        "Accept": "application/hal+json",
        "Accept-Version": "3.0",
        "Content-Type": "application/hal+json",
    }

    def __init__(self, base_uri="https://api.reverb.com/api", timeout=20):
        self._base_uri = base_uri.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(self.HEADERS)

    def listings(self, per_page=10):
        data = self._get("/listings/all", {"per_page": per_page})
        return data["listings"]

    def categories(self):
        data = self._get("/categories/flat")
        return data["categories"]

    def _get(self, path, params=None):
        response = self._session.get(
            self._base_uri + path, params=params, timeout=self._timeout
        )
        response.raise_for_status()
        return response.json()
```

**Narrate:** "Session gives us connection reuse and a place to mount adapters. Timeout prevents hangs. `raise_for_status()` turns 4xx/5xx into exceptions before we try to parse garbage JSON."

______________________________________________________________________

### Step 2: Add Retries for Transient Failures (+5 min)

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ReverbClient:
    TRANSIENT_STATUS_CODES = (500, 502, 503, 504)

    def __init__(self, ..., max_retries=3, backoff_factor=0.5):
        ...
        retry = Retry(
            total=max_retries,
            allowed_methods=frozenset({"GET"}),
            status_forcelist=self.TRANSIENT_STATUS_CODES,
            backoff_factor=backoff_factor,
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
```

**Key decisions to explain:**

- Only retry GET (safe/idempotent). POST/PUT/DELETE could duplicate side effects.
- Only retry 5xx (transient server issues). 4xx means our request is wrong.
- `raise_on_status=False` — let `_get` own error handling centrally.
- `respect_retry_after_header=True` — honor server's backoff instructions.

______________________________________________________________________

### Step 3: Client-Side Throttling + 429 Handling (+5 min)

```python
import time


class ReverbClient:
    def __init__(self, ..., min_interval_seconds=1.0, max_interval_seconds=30.0):
        self._min_interval_seconds = min_interval_seconds
        self._max_interval_seconds = max_interval_seconds
        self._last_request_time = 0.0

    def _get(self, path, params=None):
        response = self._request_with_throttle(path, params)
        if response.status_code == 429:
            self._handle_rate_limit(response)
            response = self._request_with_throttle(path, params)
        response.raise_for_status()
        return response.json()

    def _request_with_throttle(self, path, params=None):
        self._throttle()
        response = self._session.get(
            self._base_uri + path, params=params, timeout=self._timeout
        )
        self._last_request_time = time.monotonic()
        return response

    def _throttle(self):
        elapsed = time.monotonic() - self._last_request_time
        remaining = self._min_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _handle_rate_limit(self, response):
        retry_after = self._parse_retry_after(response)
        self._min_interval_seconds = min(
            self._min_interval_seconds * 2, self._max_interval_seconds
        )
        time.sleep(retry_after)

    @staticmethod
    def _parse_retry_after(response):
        value = response.headers.get("Retry-After")
        if value is None:
            return 60.0
        try:
            return float(value)
        except ValueError:
            return 60.0
```

**Narrate:** "Retries are reactive — they recover after failure. Throttling is proactive — it prevents 429 in the first place. I handle 429 separately from 5xx because it's an instruction to slow down, not a transient error. The client adaptively doubles its interval after each 429."

______________________________________________________________________

### Step 4: TTL Cache for Stable Endpoints (+5 min)

```python
class ReverbClient:
    CACHE_TTLS = {
        "/categories/flat": 24 * 60 * 60,  # 24h — metadata
        "/listings/all": 60,                # 1min — marketplace state
    }

    def __init__(self, ..., enable_cache=True):
        self._enable_cache = enable_cache
        self._cache = {}

    def _get(self, path, params=None, use_cache=True):
        params = params or {}
        cache_key = (path, tuple(sorted(params.items())))

        if self._enable_cache and use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        response = self._request_with_throttle(path, params)
        # ... error handling ...
        data = response.json()

        if self._enable_cache and use_cache:
            ttl = self.CACHE_TTLS.get(path, 60)
            self._cache[cache_key] = (time.monotonic() + ttl, data)

        return data

    def _get_cached(self, cache_key):
        entry = self._cache.get(cache_key)
        if entry is None:
            return None
        expires_at, data = entry
        if time.monotonic() >= expires_at:
            del self._cache[cache_key]
            return None
        return data

    def clear_cache(self):
        self._cache.clear()
```

**Narrate:** "Cache sits before throttle — a hit means zero network overhead. Different TTLs per endpoint because categories (24h) and listings (60s) have fundamentally different change rates."

______________________________________________________________________

### Step 5: ETag / Conditional GET for Categories (+5 min)

The Reverb API **already supports** ETag-based conditional GET for categories:

- `/api/categories/flat` returns `ETag: W/"27bca2a233cebe6f57204ebb2785c5b0"` and `Cache-Control: max-age=86400, public`
- Sending `If-None-Match: <stored-etag>` returns `304 Not Modified` (zero body transfer, saves ~312 KB)
- Cloudflare validates the ETag at the edge without hitting the origin

This is the **first-class caching mechanism** the server was built for — more correct than client-side TTL alone because the server tells you when data actually changed.

```python
class ReverbClient:
    def __init__(self, ...):
        ...
        self._etags = {}      # path -> etag string
        self._etag_data = {}  # path -> cached response data

    def _get(self, path, params=None, use_cache=True):
        params = params or {}
        cache_key = (path, tuple(sorted(params.items())))

        # Check TTL cache first (for any endpoint)
        if self._enable_cache and use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        # Build headers with ETag for conditional GET
        request_headers = {}
        if path in self._etags:
            request_headers["If-None-Match"] = self._etags[path]

        response = self._session.get(
            self._base_uri + path,
            params=params,
            timeout=self._timeout,
            headers=request_headers,
        )

        # 304 Not Modified — use cached ETag data
        if response.status_code == 304 and path in self._etag_data:
            return self._etag_data[path]

        response.raise_for_status()
        data = response.json()

        # Store ETag for future conditional requests
        etag = response.headers.get("ETag")
        if etag:
            self._etags[path] = etag
            self._etag_data[path] = data

        # Also store in TTL cache
        if self._enable_cache and use_cache:
            ttl = self.CACHE_TTLS.get(path, 60)
            self._cache[cache_key] = (time.monotonic() + ttl, data)

        return data
```

**Narrate:** "The server already supports conditional GET for categories — I'm leveraging the infrastructure they built rather than reimplementing staleness detection. TTL cache avoids the network round-trip entirely; ETag catches cases where the TTL expires but the data hasn't actually changed. They complement each other."

**Key insight from API exploration:**

- Categories: ETag supported, CDN-cached 24h, `304` possible → use both TTL + ETag
- Listings: No ETag, `Cache-Control: no-cache`, always MISS → TTL cache only (short)

______________________________________________________________________

## Phase 3: Test

### Testing the improved client

The retry/throttle/cache layers are transport concerns. Tests should mock at the session level:

```python
from unittest.mock import MagicMock, patch
from reverb_client import ReverbClient


def test_raises_on_http_error():
    client = ReverbClient()
    with patch.object(client._session, "get") as mock_get:
        mock_get.return_value.status_code = 500
        mock_get.return_value.raise_for_status.side_effect = Exception("Server Error")
        with pytest.raises(Exception, match="Server Error"):
            client.categories()


def test_timeout_is_passed():
    client = ReverbClient(timeout=5)
    with patch.object(client._session, "get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"categories": []}
        client.categories()
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 5


def test_cache_returns_stored_value():
    client = ReverbClient(enable_cache=True)
    with patch.object(client._session, "get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"categories": [{"full_name": "Guitars"}]}
        mock_get.return_value.headers = {"Content-Type": "application/hal+json"}

        first = client.categories()
        second = client.categories()

        assert mock_get.call_count == 1  # Second call served from cache
        assert first == second
```

______________________________________________________________________

## Phase 4: Trade-Off Discussion Points

### "Why not just use httpx?"

> "For a synchronous Flask app, `requests` with a Session is the simplest correct choice. The patterns transfer directly to httpx if we ever need async or HTTP/2."

### "Is the throttle blocking? Doesn't that hurt request latency?"

> "Yes, `time.sleep()` blocks the thread. In a multi-threaded server (Gunicorn with threads), each worker has its own client instance, so one worker sleeping doesn't block others. For async, I'd use `asyncio.sleep()` with httpx instead."

### "What about thread safety?"

> "The current client is not thread-safe — `_last_request_time` and `_cache` could race. For a threaded deployment, I'd add a `threading.Lock` around `_get`. For production, I'd use a process-per-request model (Gunicorn prefork) where each process owns its client."

### "What if the cache grows too large?"

> "For this client with two endpoints, the cache is bounded by the number of distinct query parameter combinations. For a general-purpose client, I'd add `maxsize` and LRU eviction, or use `cachetools.TTLCache`."

### "Why separate 429 from the retry adapter?"

> "429 is not a transient server error — it's an instruction to slow down. I want to log it, adapt my future request rate, and respect `Retry-After`. The retry adapter hides that signal."

______________________________________________________________________

## The Four-Layer Defense (Summary)

```plaintext
1. CACHE    → Already have the answer? Return immediately (TTL-based).
2. ETAG     → TTL expired? Ask server "did it change?" (304 = no body transfer).
3. THROTTLE → Space out requests to avoid 429.
4. 429 HANDLER → Rate-limited? Honor Retry-After, adapt interval.
5. RETRY    → 5xx transient failure? Exponential backoff.
```

### API-Verified Cache Behavior (from exploration)

```plaintext
Endpoint               ETag    304 possible   CDN cached    Cache-Control
/api/categories/flat   YES     YES            YES (24h)     max-age=86400, public
/api/listings/all      NO      NO             NO (MISS)     no-cache
```

**Practical implication:** Categories benefit from both TTL + ETag. Listings only benefit from short client-side TTL (the server never caches them).

### Header Notes

- `Accept: application/hal+json` — has **zero effect** on the response (server always returns HAL+JSON regardless). Include as documentation convention.
- `Content-Type: application/hal+json` on GET — semantically meaningless (GET has no body). Harmless but unnecessary for reads.
- `Accept-Version: 3.0` — **does matter**. Defaults to 1.0 without it.

______________________________________________________________________

## What to Skip in a 45-min Interview

Don't implement all of this. Pick based on time:

| Time remaining | What to implement |
|----------------|-------------------|
| 30 min | Session + timeout + raise_for_status + retries |
| 20 min | Session + timeout + raise_for_status |
| 10 min | timeout + raise_for_status only |
| 5 min | Just explain the plan verbally |

Always **narrate** what you would add even if you don't have time to code it. The interviewer cares that you know the concerns exist.
