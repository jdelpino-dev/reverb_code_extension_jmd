# ReverbClient — Improvements Report

**Date:** 2026-05-20
**File:** `web_full_stack/python/reverb_client.py`
**Context:** Code interview at Reverb — "What would you improve with 30 more minutes?" or "How would you make this production-ready?"

______________________________________________________________________

## Starting Point (Original Client)

```python
import requests

class ReverbClient:
    HEADERS = {
        "Accept": "application/hal+json",
        "Accept-Version": "3.0",
        "Content-Type": "application/hal+json",
    }

    def __init__(self, base_uri="https://api.reverb.com/api"):
        self._base_uri = base_uri

    def listings(self, per_page=10):
        return self._get("/listings/all", {"per_page": per_page})["listings"]

    def categories(self):
        return self._get("/categories/flat")["categories"]

    def _get(self, path, params=None):
        return requests.get(
            self._base_uri + path, headers=self.HEADERS, params=params
        ).json()
```

______________________________________________________________________

## Improvement 1 & 2: Persistent `requests.Session` with Shared Headers

### Original

```python
requests.get(self._base_uri + path, headers=self.HEADERS, params=params)
```

### Improved

```python
self._session = requests.Session()
self._session.headers.update(self.HEADERS)
# then:
self._session.get(...)
```

### Why sessions matter in this architecture

Your app is both a **server** (to the browser) and a **client** (to Reverb):

```plaintext
Browser → Your backend (server) → Reverb API (server)
```

`requests.Session` represents that long-lived client relationship. It has nothing to do with the browser/user session (cookies, login state). It is your backend's persistent connection to Reverb.

### What a Session provides

**1. Connection reuse** — Without a session, each `requests.get()` may open a new TCP/TLS connection:

```plaintext
DNS lookup → TCP handshake → TLS handshake → HTTP request → response → teardown
```

With a session, urllib3's connection pool reuses existing connections. For multiple Reverb calls per user request (categories + listings + detail), this matters.

**2. Shared default headers** — Every Reverb call needs the same baseline. The session stores them once:

```python
self._session.headers.update(self.HEADERS)
```

Without a session, every method must pass `headers=self.HEADERS`. That becomes brittle when you add `Authorization`, `User-Agent`, `X-Display-Currency`, or tracing headers.

**3. Auth belongs on the session** — The session represents "this Reverb API client, using this token, with these headers." Adding auth later is one line:

```python
self._session.headers["Authorization"] = f"Bearer {token}"
```

**4. Adapters mount on the session** — Retry policy, connection pooling, TLS config, and proxy settings all attach via `session.mount()`. The session owns the full transport policy.

**5. Throttling and caching are client-level state** — `_last_request_time`, `_cache`, retry config — all belong to the same long-lived object. The session is the foundation that ties them together.

### Important: do not create a new session per request

Bad (defeats connection reuse):

```python
ReverbClient().listings()
ReverbClient().categories()
```

Good (reuse the client):

```python
client = ReverbClient()
client.listings()
client.categories()
```

In a Flask app, create the client once per process or inject it as a service dependency.

### Browser session vs `requests.Session`

| Concept | What it is |
| -- | -- |
| Browser/user session | Logged-in user, cookies, frontend state |
| `requests.Session` | Persistent Python HTTP client: headers, connection pool, adapters, retry config |

They are unrelated. Your `requests.Session` is not the user's browser session — it is your backend's identity when talking to Reverb.

### Interview angle

> "A Session represents the long-lived server-to-server relationship with Reverb. It gives us connection reuse, header persistence, adapter mounting for retries, and a natural place for auth. Same pattern you'd use for Stripe, GitHub, or any external API client."

______________________________________________________________________

## Improvement 3: Avoid Mutable Default Arguments

### Original

```python
def _get(self, path, params={}):
```

### Improved

```python
def _get(self, path, params=None):
```

### Why

- Classic Python gotcha: default mutable objects are shared across all calls to the function.
- Even if `params` is never mutated here, `None` is the idiomatic and safer default.
- Interviewers specifically look for awareness of this pattern.

### Interview angle

> "Mutable defaults are evaluated once at function definition time. If anyone later mutates `params` inside `_get`, all subsequent calls see the mutation. `None` is the safe convention."

______________________________________________________________________

## Improvement 4: Request Timeout

### Original

```python
requests.get(...)  # no timeout — waits forever
```

### Improved

```python
self._session.get(..., timeout=20)
```

### Why

- Without a timeout, the program hangs indefinitely on network issues.
- Production services require bounded response times.
- 20 seconds is generous for an API client; a stricter service might use 5–10s.

### Interview angle

> "Never make an unbounded network call. A timeout is one of the first things I add to any HTTP client."

______________________________________________________________________

## Improvement 5: Explicit HTTP Error Checking

### Original

```python
return requests.get(...).json()
```

### Improved

```python
response = self._session.get(...)
response.raise_for_status()
return response.json()
```

### Why

- A 4xx/5xx response often has a different JSON shape (error payload, HTML page, empty body).
- Calling `.json()` on a 500 response may raise a confusing `JSONDecodeError`.
- `raise_for_status()` turns bad HTTP codes into clear `requests.HTTPError` exceptions.

### Interview angle

> "I always check status before parsing. A 403 or 502 should not silently return garbage data to the caller."

______________________________________________________________________

## Improvement 6: Separate Response Retrieval from JSON Parsing

### Original

```python
return requests.get(...).json()
```

### Improved

```python
response = self._session.get(...)
response.raise_for_status()
return response.json()
```

### Why

- Gives a clear place to inspect status, headers, rate-limit info, or log the response before parsing.
- Enables debugging without changing the data flow.
- Necessary foundation for adding retries, caching, or metrics.

______________________________________________________________________

## Improvement 7: Content-Type Sanity Check

### Improved

```python
content_type = response.headers.get("Content-Type", "")
if "json" not in content_type:
    raise ValueError(f"Expected JSON response, got {content_type!r}")
```

### Why

- Catches proxy pages, HTML error pages, or misconfigured upstreams before `json()` raises a confusing parse error.
- Broad check (`"json" in content_type`) correctly accepts `application/json`, `application/hal+json`, `application/problem+json`.

### When to mention

This is a "bonus polish" item. Mention it if asked about defensive coding or if you have extra time. It shows awareness of real-world failure modes.

______________________________________________________________________

## Improvement 8: Centralized `_get` as the Single Request Method

### Improved

```python
def listings(self, per_page=10):
    data = self._get("/listings/all", {"per_page": per_page})
    return data["listings"]

def categories(self):
    data = self._get("/categories/flat")
    return data["categories"]
```

### Why

- All HTTP behavior (timeout, headers, error handling, retries, logging) lives in one place.
- Adding new endpoints requires only a thin public method.
- Follows DRY and the Single Responsibility Principle.

### Interview angle

> "I centralize HTTP logic in one private method so every new endpoint method stays simple and consistent."

______________________________________________________________________

## Improvement 9: Authentication-Ready Design

### Why the session approach helps

```python
self._session.headers.update({
    "Authorization": f"Bearer {token}"
})
```

- Adding auth later is a one-line change.
- No need to thread a token through every method signature.
- Works naturally with OAuth refresh flows (update session headers on token refresh).

______________________________________________________________________

## Improvement 10: Production-Like Client Summary

The fully improved client adopts these production behaviors:

| Behavior | Mechanism |
| -- | -- |
| Connection reuse | `requests.Session` |
| Default headers | `session.headers.update(...)` |
| Safe defaults | `params=None` |
| Bounded network calls | `timeout=20` |
| HTTP error detection | `raise_for_status()` |
| Content-type guard | `"json" not in content_type` |
| Centralized HTTP logic | Single `_get` method |
| Auth-ready | Session header pattern |

______________________________________________________________________

## Improvement 11: Retries with Exponential Backoff

### Why retries matter for the Reverb API

A marketplace API experiences transient failures: rate limits (429), temporary server issues (500/502/503/504), network blips. A well-behaved client handles these gracefully without manual intervention.

### Implementation

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry = Retry(
    total=max_retries,
    connect=max_retries,
    read=max_retries,
    status=max_retries,
    allowed_methods=frozenset({"GET"}),
    status_forcelist=(429, 500, 502, 503, 504),
    backoff_factor=0.5,
    respect_retry_after_header=True,
    raise_on_status=False,
)
adapter = HTTPAdapter(max_retries=retry)
self._session.mount("https://", adapter)
self._session.mount("http://", adapter)
```

### Key design decisions

#### Only retry GET requests

GET is safe (idempotent). Retrying POST/PUT/DELETE risks duplicating side effects unless the API supports idempotency keys.

#### Retry these status codes

| Status | Why retry? |
| -- | -- |
| 429 | Rate limited — retry after waiting |
| 500 | Temporary server failure |
| 502 | Bad gateway, proxy/upstream issue |
| 503 | Service unavailable |
| 504 | Gateway timeout |

#### Do NOT retry these

| Status | Why not? |
| -- | -- |
| 400 | Bad request — your parameters are wrong |
| 401 | Missing/invalid auth |
| 403 | Authenticated but not authorized |
| 404 | Resource does not exist |
| 422 | Validation/business-rule failure |

These require code or request changes, not another attempt.

#### `respect_retry_after_header=True`

For 429, the server may send `Retry-After: 10`. This tells urllib3 to honor that instruction instead of blindly retrying. Without it, aggressive retries become the exact crawler behavior that rate limits are designed to prevent.

#### `raise_on_status=False`

After retries are exhausted, return the final response to your code. Then `_get` calls `response.raise_for_status()` to handle the error consistently. This keeps error handling centralized rather than split between the adapter and the method.

### Conservative settings for a polite client

```python
max_retries=3
backoff_factor=0.5
timeout=20
allowed_methods={"GET"}
```

This produces roughly:

1. First attempt
2. Retry after ~0.5s
3. Retry after ~1s
4. Final attempt after ~2s

### Interview angle

> "I configure retries at the transport layer using urllib3's Retry with an HTTPAdapter. Only GET, only transient error codes, with exponential backoff and Retry-After respect. This keeps the client polite while handling real-world flakiness."

______________________________________________________________________

## Improvement 12: Logging

### Why

- In production, you need observability into API calls: what was requested, how long it took, what status came back.
- Helps debug issues without stepping through code.
- Critical for monitoring latency, error rates, and rate-limit patterns.

### Implementation sketch

```python
import logging

logger = logging.getLogger(__name__)

def _get(self, path, params=None):
    logger.debug("GET %s params=%s", self._base_uri + path, params)
    response = self._session.get(...)
    logger.debug("Response %s in %.2fs", response.status_code, response.elapsed.total_seconds())
    ...
```

### Interview angle

> "I would add structured logging to `_get` so we can monitor latency and error rates in production without modifying calling code."

______________________________________________________________________

## Improvement 13: Custom Exception Hierarchy

### Why

- Callers can distinguish between network errors, HTTP errors, and parsing errors.
- Enables fine-grained error handling upstream (retry network errors, show user-friendly messages for 404s).

### Implementation sketch

```python
class ReverbClientError(Exception):
    """Base exception for all client errors."""

class ReverbHTTPError(ReverbClientError):
    def __init__(self, status_code, message):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")

class ReverbParseError(ReverbClientError):
    """Response was not valid JSON or had unexpected content-type."""
```

### Interview angle

> "Custom exceptions give callers semantic meaning. The Flask layer can catch `ReverbHTTPError` and render a proper error page instead of showing a raw stack trace."

______________________________________________________________________

## Improvement 14: Pagination Support

### Why

- Reverb's API returns paginated results. The current client only fetches the first page.
- A production client needs to iterate over all pages or let the caller control pagination.

### Implementation sketch

```python
def listings_page(self, page=1, per_page=10):
    """Fetch a single page of listings."""
    data = self._get("/listings/all", {"page": page, "per_page": per_page})
    return data["listings"], data.get("total_pages", 1)

def all_listings(self, per_page=50):
    """Generator that yields all listings across pages."""
    page = 1
    while True:
        listings, total_pages = self.listings_page(page=page, per_page=per_page)
        yield from listings
        if page >= total_pages:
            break
        page += 1
```

### Interview angle

> "I would expose both a single-page method and a generator for full iteration. The generator lazily fetches pages, which keeps memory usage constant."

______________________________________________________________________

## Improvement 15: Response Caching (Short-Lived)

### Why

- Categories rarely change. Fetching them on every request wastes time and API quota.
- A simple TTL cache reduces redundant calls.

### Implementation sketch

```python
from functools import lru_cache
import time

def categories(self):
    return self._cached_categories()

@lru_cache(maxsize=1)
def _cached_categories(self):
    data = self._get("/categories/flat")
    return data["categories"]
```

Or with time-based expiry:

```python
_categories_cache = None
_categories_ts = 0

def categories(self):
    if time.time() - self._categories_ts > 300:  # 5 min TTL
        self._categories_cache = self._get("/categories/flat")["categories"]
        self._categories_ts = time.time()
    return self._categories_cache
```

### Interview angle

> "Categories are nearly static. A 5-minute TTL cache eliminates redundant API calls without risking stale data for fast-changing resources like listings."

______________________________________________________________________

## Improvement 16: Rate-Limit Awareness

### Why

- Beyond retries, a production client should proactively respect rate limits.
- Reverb (like most APIs) returns rate-limit headers: `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

### Implementation sketch

```python
def _get(self, path, params=None):
    response = self._session.get(...)
    remaining = response.headers.get("X-RateLimit-Remaining")
    if remaining and int(remaining) < 5:
        logger.warning("Rate limit nearly exhausted: %s remaining", remaining)
    ...
```

### Interview angle

> "I would read rate-limit headers and log warnings when we approach the limit. In a high-throughput system, I would add preemptive throttling."

______________________________________________________________________

## Improvement 17: Configuration via Environment Variables

### Why

- Base URI, timeout, and retry settings should not be hardcoded for production.
- Enables different configurations for dev, staging, and production.

### Implementation sketch

```python
import os

class ReverbClient:
    def __init__(
        self,
        base_uri=None,
        timeout=None,
    ):
        self._base_uri = (base_uri or os.environ.get("REVERB_API_URL", "https://api.reverb.com/api")).rstrip("/")
        self._timeout = timeout or int(os.environ.get("REVERB_TIMEOUT", "20"))
```

### Interview angle

> "Hardcoding the base URI is fine for an exercise, but in production I would read it from the environment so we can point at staging or a mock server without code changes."

______________________________________________________________________

## Improvement 18: Type Hints

### Why

- Improves IDE support, documentation, and static analysis.
- Shows professionalism and attention to maintainability.

### Implementation sketch

```python
from typing import Any

class ReverbClient:
    def __init__(self, base_uri: str = "https://api.reverb.com/api", timeout: int = 20) -> None:
        ...

    def listings(self, per_page: int = 10) -> list[dict[str, Any]]:
        ...

    def categories(self) -> list[dict[str, Any]]:
        ...

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        ...
```

### Interview angle

> "Type hints cost nothing at runtime and make the client self-documenting. They also enable mypy to catch misuse."

______________________________________________________________________

## Improvement 19: Testability — Dependency Injection for the Session

### Why

- The current tests mock `requests.get` globally. This is brittle.
- Injecting the session (or a transport) makes testing cleaner and enables fakes.

### Implementation sketch

```python
class ReverbClient:
    def __init__(self, session=None, ...):
        self._session = session or requests.Session()
        ...
```

In tests:

```python
def test_categories(fake_session):
    client = ReverbClient(session=fake_session)
    ...
```

### Interview angle

> "Injecting the session lets tests provide a fake transport without patching module-level globals. It also enables integration tests with a recorded session (VCR/responses library)."

______________________________________________________________________

## Improvement 20: `__repr__` and `__str__`

### Why

- Useful for debugging: `print(client)` shows meaningful info.
- Small polish that shows attention to Python conventions.

### Implementation sketch

```python
def __repr__(self):
    return f"ReverbClient(base_uri={self._base_uri!r}, timeout={self._timeout})"
```

______________________________________________________________________

## Improvement 21: Context Manager Support

### Why

- Sessions should be closed when done to release connections.
- A context manager makes resource cleanup explicit.

### Implementation sketch

```python
class ReverbClient:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._session.close()

    def close(self):
        self._session.close()
```

Usage:

```python
with ReverbClient() as client:
    listings = client.listings()
```

### Interview angle

> "For long-running processes or CLI tools, I would add context manager support so connections are properly released."

______________________________________________________________________

## Deep Dive: Client-Side Throttling

### The relationship between retries and throttling

| Mechanism | Posture | Purpose |
| -- | -- | -- |
| Retries | Reactive | Recover after a failure |
| Throttling | Proactive | Prevent failures by spacing requests |

Retries alone mean: call too fast → get 429 → retry later. Throttling means: space out calls → avoid 429 in the first place.

### Why split 429 out of the retry adapter

In the basic retry version, `RETRY_STATUS_CODES = (429, 500, 502, 503, 504)`. For a serious client, handle 429 explicitly:

- **5xx → retry adapter** (transient server failures)
- **429 → explicit rate-limit handler** (instruction to slow down)

429 is not "server had a problem." It is an instruction. You may want to log it, reduce future request rate, or pause a queue.

### Implementation: simple throttle + adaptive 429 handling

```python
import time

class ReverbClient:
    TRANSIENT_STATUS_CODES = (500, 502, 503, 504)  # 429 handled separately

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
        ...

    def _request_with_throttle(self, path, params=None):
        self._throttle()
        response = self._session.get(self._base_uri + path, params=params, timeout=self._timeout)
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
            self._min_interval_seconds * 2,
            self._max_interval_seconds,
        )
        time.sleep(retry_after)

    @staticmethod
    def _parse_retry_after(response):
        retry_after = response.headers.get("Retry-After")
        if retry_after is None:
            return 60.0
        try:
            return float(retry_after)
        except ValueError:
            return 60.0
```

### Adaptive behavior

- Start at 1 req/sec
- On 429: double the interval (1s → 2s → 4s → ... capped at 30s)
- `Retry-After` header honored when present; defaults to 60s if absent

### Recommended configurations

| Use case | `min_interval_seconds` | Effective rate |
| -- | -- | -- |
| Interactive exploration | 1.5 | ~40 req/min |
| Broad listing crawls | 3.0 | ~20 req/min |
| Aggressive (with permission) | 0.5 | ~120 req/min |

### Interview angle

> "Retries are reactive — they recover after failure. Throttling is proactive — it prevents failure. I separate 429 from 5xx because rate limiting is an instruction, not a transient error. The client adaptively slows down after 429 and respects `Retry-After`."

______________________________________________________________________

## Deep Dive: Endpoint-Aware TTL Cache

### Relationship to throttling

```plaintext
throttling = control how fast you call the API
caching    = control whether you call it at all
retries    = recover from temporary failures
```

The fastest and safest request is the one you never send.

### Cache candidates in the Reverb API

| Endpoint | TTL | Reason |
| -- | -- | -- |
| `/categories/flat` | 24h | Metadata, rarely changes |
| `/listing_conditions` | 24h | Static reference data |
| `/currencies/display` | 24h | Static reference data |
| `/currencies/listing` | 24h | Static reference data |
| `/listings/all` | 60s | Marketplace state changes often |
| `/my/*` | No cache | Auth-specific, stale = operational bugs |

### Implementation: in-memory TTL cache

```python
class ReverbClient:
    DEFAULT_CACHE_TTL_SECONDS = 60
    CACHE_TTLS = {
        "/categories/flat": 24 * 60 * 60,
        "/listing_conditions": 24 * 60 * 60,
        "/currencies/display": 24 * 60 * 60,
        "/listings/all": 60,
    }

    def __init__(self, ..., enable_cache=True):
        self._enable_cache = enable_cache
        self._cache = {}

    def _get(self, path, params=None, use_cache=True):
        params = params or {}
        cache_key = self._make_cache_key(path, params)

        if self._should_use_cache(path, use_cache):
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached  # No network call, no throttle wait

        response = self._request_with_throttle(path, params=params)
        # ... error handling ...
        data = response.json()

        if self._should_use_cache(path, use_cache):
            self._set_cached(cache_key, path, data)
        return data

    @staticmethod
    def _make_cache_key(path, params):
        return (path, tuple(sorted(params.items())))

    def _get_cached(self, cache_key):
        entry = self._cache.get(cache_key)
        if entry is None:
            return None
        expires_at, data = entry
        if time.monotonic() >= expires_at:
            del self._cache[cache_key]
            return None
        return data

    def _set_cached(self, cache_key, path, data):
        ttl = self.CACHE_TTLS.get(path, self.DEFAULT_CACHE_TTL_SECONDS)
        self._cache[cache_key] = (time.monotonic() + ttl, data)

    def _should_use_cache(self, path, use_cache):
        return self._enable_cache and use_cache

    def clear_cache(self):
        self._cache.clear()

    def clear_cache_for_path(self, path):
        self._cache = {k: v for k, v in self._cache.items() if k[0] != path}
```

### Key design points

**Cache key normalization** — `{"page": 1, "per_page": 10}` and `{"per_page": 10, "page": 1}` produce the same key via `sorted(params.items())`.

**Cache sits before throttle** — the flow is:

```plaintext
method call → check cache → HIT: return immediately
                           → MISS: throttle → request → store → return
```

**Force refresh** — public methods accept `use_cache=False` for debugging freshness.

**Different TTLs per endpoint** — one TTL for everything is wrong. Categories (24h) vs. listings (60s) have fundamentally different change rates.

### Respecting HTTP `Cache-Control` headers

A more advanced version reads the server's caching instructions:

```python
@staticmethod
def _cache_ttl_from_response(response, fallback_ttl):
    cache_control = response.headers.get("Cache-Control", "")
    for part in cache_control.split(","):
        part = part.strip().lower()
        if part.startswith("max-age="):
            try:
                return int(part.removeprefix("max-age="))
            except ValueError:
                return fallback_ttl
    return fallback_ttl
```

This respects the server when it says `max-age=86400`, falling back to your configured TTLs otherwise.

### Authenticated cache safety

For authenticated endpoints, cache keys must include identity:

```python
import hashlib

def _auth_cache_fragment(self):
    auth = self._session.headers.get("Authorization")
    if not auth:
        return None
    return hashlib.sha256(auth.encode()).hexdigest()[:16]
```

Without this, token A's cached `/my/listings` could leak to token B. For public-only endpoints, this is not needed.

### Interview angle

> "Caching reduces rate-limit risk, latency, and API cost. I use per-endpoint TTLs because metadata (categories) and marketplace state (listings) have different change rates. Cache checks happen before throttling — a cache hit means zero network overhead."

______________________________________________________________________

## The Four-Layer Defense Strategy

The complete request lifecycle in order:

```plaintext
1. CACHE    → Already have the answer? Return immediately.
2. THROTTLE → Space out requests to avoid 429.
3. 429 HANDLER → If rate-limited, honor Retry-After and adapt.
4. RETRY    → For 5xx transient failures, exponential backoff.
```

This is the engineering posture for a polite, resilient API client:

- Cache eliminates unnecessary requests
- Throttle prevents triggering rate limits
- 429 handler adapts when limits are hit
- Retries survive transient infrastructure failures

______________________________________________________________________

## Full Improved Client (Reference Implementation)

```python
import logging
import os
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ReverbClientError(Exception):
    """Base exception for ReverbClient errors."""


class ReverbHTTPError(ReverbClientError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class ReverbParseError(ReverbClientError):
    """Response was not valid JSON or had unexpected content-type."""


class ReverbClient:
    HEADERS = {
        "Accept": "application/hal+json",
        "Accept-Version": "3.0",
        "Content-Type": "application/hal+json",
    }
    TRANSIENT_STATUS_CODES = (500, 502, 503, 504)
    DEFAULT_CACHE_TTL_SECONDS = 60
    CACHE_TTLS = {
        "/categories/flat": 24 * 60 * 60,
        "/listing_conditions": 24 * 60 * 60,
        "/currencies/display": 24 * 60 * 60,
        "/listings/all": 60,
    }

    def __init__(
        self,
        base_uri: str | None = None,
        timeout: int = 20,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        min_interval_seconds: float = 1.0,
        max_interval_seconds: float = 30.0,
        enable_cache: bool = True,
        session: requests.Session | None = None,
    ):
        self._base_uri = (
            base_uri or os.environ.get("REVERB_API_URL", "https://api.reverb.com/api")
        ).rstrip("/")
        self._timeout = timeout
        self._min_interval_seconds = min_interval_seconds
        self._max_interval_seconds = max_interval_seconds
        self._last_request_time = 0.0
        self._enable_cache = enable_cache
        self._cache: dict = {}

        self._session = session or requests.Session()
        self._session.headers.update(self.HEADERS)

        retry = Retry(
            total=max_retries,
            connect=max_retries,
            read=max_retries,
            status=max_retries,
            allowed_methods=frozenset({"GET"}),
            status_forcelist=self.TRANSIENT_STATUS_CODES,
            backoff_factor=backoff_factor,
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __repr__(self):
        return f"ReverbClient(base_uri={self._base_uri!r}, timeout={self._timeout})"

    def close(self):
        self._session.close()

    def listings(self, per_page: int = 10, use_cache: bool = True) -> list[dict]:
        data = self._get("/listings/all", {"per_page": per_page}, use_cache=use_cache)
        return data["listings"]

    def categories(self, use_cache: bool = True) -> list[dict]:
        data = self._get("/categories/flat", use_cache=use_cache)
        return data["categories"]

    def clear_cache(self):
        self._cache.clear()

    def _get(self, path: str, params: dict | None = None, use_cache: bool = True) -> dict:
        params = params or {}
        cache_key = self._make_cache_key(path, params)

        if self._should_use_cache(path, use_cache):
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        url = self._base_uri + path
        logger.debug("GET %s params=%s", url, params)

        response = self._request_with_throttle(path, params)

        if response.status_code == 429:
            self._handle_rate_limit(response)
            response = self._request_with_throttle(path, params)

        logger.debug("Response %s in %.2fs", response.status_code, response.elapsed.total_seconds())

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise ReverbHTTPError(response.status_code, str(exc)) from exc

        content_type = response.headers.get("Content-Type", "")
        if "json" not in content_type:
            raise ReverbParseError(f"Expected JSON response, got {content_type!r}")

        data = response.json()

        if self._should_use_cache(path, use_cache):
            self._set_cached(cache_key, path, data)

        return data

    def _request_with_throttle(self, path: str, params: dict | None = None):
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

    def _should_use_cache(self, path: str, use_cache: bool) -> bool:
        return self._enable_cache and use_cache

    def _get_cached(self, cache_key):
        entry = self._cache.get(cache_key)
        if entry is None:
            return None
        expires_at, data = entry
        if time.monotonic() >= expires_at:
            del self._cache[cache_key]
            return None
        return data

    def _set_cached(self, cache_key, path: str, data):
        ttl = self.CACHE_TTLS.get(path, self.DEFAULT_CACHE_TTL_SECONDS)
        self._cache[cache_key] = (time.monotonic() + ttl, data)

    @staticmethod
    def _make_cache_key(path, params):
        return (path, tuple(sorted(params.items())))

    @staticmethod
    def _parse_retry_after(response):
        retry_after = response.headers.get("Retry-After")
        if retry_after is None:
            return 60.0
        try:
            return float(retry_after)
        except ValueError:
            return 60.0
```

______________________________________________________________________

## Priority Ranking for Interview Discussion

If asked "What would you improve next?" — order by impact:

| Priority | Improvement | Why first |
| -- | -- | -- |
| 1 | Timeout | Prevents hangs — fundamental reliability |
| 2 | `raise_for_status()` | Prevents silent failures |
| 3 | `params=None` | Fixes a known Python bug pattern |
| 4 | Session | Foundation for everything else |
| 5 | Retries (5xx) | Handles transient server errors |
| 6 | Throttling | Proactively avoids rate limits |
| 7 | 429 handling | Adapts speed when limits are hit |
| 8 | Caching (TTL) | Eliminates redundant requests entirely |
| 9 | Logging | Observability for production debugging |
| 10 | Custom exceptions | Enables proper error handling upstream |
| 11 | Pagination | Required for any real data usage |
| 12 | Content-type check | Defensive, prevents confusing parse errors |
| 13 | Type hints | Documentation and static analysis |
| 14 | Config from env | Deployment flexibility |
| 15 | DI for session | Testing ergonomics |
| 16 | Context manager | Resource cleanup |

______________________________________________________________________

## Design Decision: URL Construction vs. HATEOAS Link-Following

### What is HATEOAS?

**HATEOAS** (Hypermedia As The Engine Of Application State) is a REST constraint where API responses include links to related resources. Instead of the client knowing URL patterns in advance, it discovers them from the response.

Example — Reverb's collection response:

```json
{
  "listings": [
    {
      "id": 97305295,
      "title": "Fender Telecaster",
      "_links": {
        "self": { "href": "https://api.reverb.com/api/listings/97305295-fender-telecaster" },
        "web": { "href": "https://reverb.com/item/97305295-fender-telecaster" },
        "photo": { "href": "https://images.reverb.com/..." }
      }
    }
  ]
}
```

A pure HATEOAS client would follow `_links.self.href` to fetch the listing detail, rather than constructing `f"/listings/{id}"`.

### Why we construct URLs manually (and don't follow `_links`)

| Reason | Explanation |
| -- | -- |
| **Direct access requires it** | Bookmarked/shared URLs only provide an ID — no `_links` object exists. You need URL construction anyway. |
| **Single code path** | One `_get(f'/listings/{id}')` works for every access pattern. No "did we come from a collection view?" branching. |
| **SSRF prevention** | Following URLs from external responses means your server requests whatever URL the response contains. A compromised upstream (or injected response) could point your server at internal services. Constructing from a known base URL + validated ID eliminates this. |
| **Stable API** | Reverb's URL structure is versioned (`Accept-Version: 3.0`). URL patterns won't change without a major version bump. The HATEOAS flexibility benefit doesn't materialize for a stable third-party API. |
| **Simpler client** | The client only needs to know `base_uri + path`. No link-extraction logic, no response-parsing before the actual request. |

### When HATEOAS link-following *would* make sense

- **Internal microservices** — you control both sides and want to change URL structure without updating all clients.
- **Opaque identifiers** — the API uses non-constructible URLs (e.g., signed URLs, UUIDs without a pattern).
- **Pagination** — following `_links.next.href` for cursor-based pagination is a legitimate use of link-following (you can't construct cursor URLs).

### The SSRF angle in detail

```python
# DANGEROUS: following a URL from an untrusted response
def listing_by_link(self, link_href):
    return self._session.get(link_href).json()  # What if link_href is http://169.254.169.254/metadata?
```

```python
# SAFE: constructing from known base + validated ID
def listing(self, listing_id):
    return self._get(f'/listings/{listing_id}')  # Always hits self._base_uri + known path
```

Even if the Reverb API is trusted today, defense-in-depth means not designing a client that could be exploited if the upstream is compromised.

### "But we render image URLs from the API — isn't that the same risk?"

No. The key is **who fetches the URL**:

| URL usage | Who fetches | SSRF risk? | Why |
| -- | -- | -- | -- |
| `_links.self.href` → your server calls Reverb API | **Your server** | Yes | Server sits inside your network — can reach cloud metadata, internal services, databases |
| `_links.large_crop.href` → rendered in `<img src="...">` | **User's browser** | No | Browser runs on user's machine, sandboxed, cannot reach your internal infrastructure |

SSRF (Server-Side Request Forgery) requires your *server* to be the one making the request. When the browser fetches an image URL, the request originates from the user's device — it has no access to `http://169.254.169.254/metadata`, your VPC, or internal services.

**Remaining (low-severity) risks of rendering external image URLs:**

- Tracking pixels — a malicious URL could log which users view which listings
- Mixed content — `http://` images on an `https://` page get blocked by browsers
- Availability — if the CDN restructures URLs, images break

**Not a risk:** `<img src="javascript:...">` does not execute — browsers do not run JS from img src attributes.

**Bottom line:** rendering image URLs from a trusted API in `<img>` tags is standard, safe practice. The SSRF concern applies exclusively to URLs your *server* would fetch via `requests.get()` or equivalent.

### Interview angle

> "The collection response provides `_links.self.href` per listing — that's HATEOAS. I could follow those links, but I construct URLs manually because: (1) I need construction for direct-access routes anyway, (2) one code path is simpler than two, and (3) following external URLs introduces SSRF risk. HATEOAS shines for internal APIs where you control URL evolution — for a stable third-party API, explicit construction is safer and simpler."

______________________________________________________________________

## How to Talk About This in an Interview

### "What would you do with 30 more minutes?"

> "First: timeout and `raise_for_status()` — those prevent silent failures. Then a Session with a retry adapter for 5xx. Then I would add client-side throttling with adaptive 429 handling, and a TTL cache for stable endpoints like categories. That gives you a polite, resilient client."

### "How would you make this production-ready?"

> "Four layers: cache to avoid unnecessary calls, throttle to stay under rate limits, explicit 429 handling with adaptive slowdown, and retries for transient 5xx. Plus structured logging, custom exceptions, environment config, and pagination guardrails."

### "Why not just let the retry adapter handle 429?"

> "429 is not a transient server error — it is an instruction to slow down. I want to log it, adapt my future request rate, and respect `Retry-After`. The retry adapter hides that signal. Splitting 429 from 5xx gives the client intentional, observable behavior."

### "Why not use httpx or aiohttp?"

> "For a synchronous Flask app, `requests` with a Session is the simplest correct choice. If we needed async or HTTP/2, I would reach for `httpx`. The architectural patterns (centralized `_get`, retries, error hierarchy) transfer directly to any HTTP library."
