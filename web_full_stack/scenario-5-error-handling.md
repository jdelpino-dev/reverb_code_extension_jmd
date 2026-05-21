# Scenario 5: Error Handling & Loading States

## The Ask

> "What happens if the API is slow or returns an error? Add loading and error states."

Tests defensive programming thinking and UX awareness. Very likely as a follow-up extension.

______________________________________________________________________

## Phase 1: Explain

"Right now if the API fails, Python will raise an unhandled exception and show a 500 page. React will silently fail — the listings array stays empty with no feedback. There's also no loading indicator while the API request is in flight."

**Clarifying questions:**

- "Should I handle errors at the client level (retry, timeout) or the UI level (show message)?"
- "Is a simple 'Something went wrong' message sufficient, or should we distinguish between error types?"
- "Do we need loading states for the server-rendered Python app, or just for React?"

______________________________________________________________________

## Phase 2: The Four Failure Paths

Before writing code, understand the distinct ways a third-party API call can fail:

```plaintext
1. request could not complete
   -> requests.RequestException (transport: timeout, DNS, connection)

2. request completed, but HTTP status is bad
   -> response.raise_for_status()
   -> requests.HTTPError (subclass of RequestException)

3. HTTP status is OK, but body is malformed
   -> response.json() fails
   -> ValueError / JSONDecodeError

4. JSON is valid, but shape is wrong
   -> dict["expected_key"] fails
   -> KeyError
```

Each path has a different root cause and needs a different log message.

______________________________________________________________________

## Phase 3: Implemented Solution (Interview-Appropriate)

This is what I actually built — a practical tradeoff between correctness and
interview time constraints. No custom exception hierarchy. The client stays
thin, the service catches everything, the route flashes.

### 3a. Client: `reverb_client.py`

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
        if params is None:
            params = {}
        response = requests.get(
            self._base_uri + path,
            headers=self.HEADERS,
            params=params,
            timeout=(3, 5),  # (connect, read)
        )
        response.raise_for_status()  # HTTPError for 4xx/5xx → RequestException subclass
        return response.json()       # only reached on 2xx
```

**Key decisions:**

- `timeout=(3, 5)` — 3s connect, 5s read. A user-facing page can't wait longer.
- `raise_for_status()` — converts HTTP errors into exceptions before `.json()` is called.
  Without it, a 503 returning HTML reaches `.json()` and raises misleading `JSONDecodeError`.
- No custom exceptions in the client — raw `requests` exceptions propagate naturally.
  The service layer catches them by type.

### 3b. Service layer: `app.py` service helpers

```python
import logging
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


def _load_categories():
    try:
        categories = ReverbClient().categories()
        # Defensive normalization: drop items missing required fields
        return [c for c in categories if "full_name" in c]
    except RequestException:
        logger.exception("Network error fetching categories from Reverb API")
    except KeyError:
        logger.exception("Unexpected response shape from Reverb API /categories/flat")
    except ValueError:
        logger.exception("Invalid JSON response from Reverb API /categories/flat")


def _load_listings():
    try:
        return ReverbClient().listings()
    except RequestException:
        logger.exception("Network error fetching listings from Reverb API")
    except KeyError:
        logger.exception("Unexpected response shape from Reverb API /listings/all")
    except ValueError:
        logger.exception("Invalid JSON response from Reverb API /listings/all")


def _search_categories(query):
    if not query:
        return []
    categories = _load_categories()
    if categories is None:
        return None  # propagate load failure
    return list(filter(lambda c: query.lower() in c["full_name"].lower(), categories))
```

**Key decisions:**

- Three separate `except` clauses with distinct log messages — enables triage.
- Implicit `return None` on any failure — lets routes distinguish error from empty.
- `_search_categories` propagates `None` — prevents `TypeError` from filtering `None`.
- Defensive `"full_name" in c` check — normalizes item-level shape issues.

### 3c. Routes: `app.py` route handlers

```python
@app.route("/")
@app.route("/categories")
def categories():
    query = request.args.get("query")
    categories = _search_categories(query)
    if not query:
        flash("Search using a query string...", "warning")
    elif categories is None:
        flash("Could not load categories. Please try again.", "error")
        categories = []
    elif not categories:
        flash(f"No category results for: {query}.", "info")
    return render_template("categories.html", categories=categories)


@app.route("/listings")
def listings():
    results = _load_listings()
    if results is None:
        flash("Could not load listings. Please try again.", "error")
        results = []
    return render_template("listings.html", listings=results)
```

**Key decisions:**

- `None` = error, `[]` = valid empty, `[...]` = success. Three-way sentinel.
- Flash messages live in the route (presentation concern), not the service.
- `results = []` after flashing ensures the template always receives an iterable.

______________________________________________________________________

## Phase 4: Why This Design Works

### Exception hierarchy awareness

`requests` exception hierarchy (catch order matters — specific first):

```plaintext
RequestException
├── HTTPError          ← from raise_for_status()
├── ConnectionError    ← DNS, refused, network down
├── Timeout
│   ├── ConnectTimeout
│   └── ReadTimeout
├── TooManyRedirects
└── ...
```

`except RequestException` catches all of these, including `HTTPError`. Since we don't
need different user-facing behavior per subclass, one catch is sufficient at this scale.

### Why `raise_for_status()` lives in the client, not the service

The client is the HTTP boundary. It's the one that knows "a 503 is not data."
Converting HTTP errors into exceptions at the source prevents downstream code
from accidentally treating error responses as valid data.

### Why `ValueError` is needed alongside `RequestException`

`response.json()` can fail even after a 200 OK:

- CDN returning plain-text "OK"
- Proxy injecting HTML into the response
- API bug returning malformed JSON

In older `requests` versions, `JSONDecodeError` is not a `RequestException` subclass.
`ValueError` catches it safely regardless of version.

### Why not a custom `ApiError` at this scale

A single `ApiError` that wraps everything (timeout, 503, bad JSON) forces the caller
to inspect `.status_code` to decide what happened. That's worse than separate
exception types that the caller can match on directly — but for a small app with
two endpoints and one generic flash message, even that's overkill. The routes don't
care *why* it failed; they only care that it failed.

______________________________________________________________________

## Phase 5: Trade-off Discussion

| Topic | What to say |
|---|---|
| Where to handle errors | "The service catches all failures and returns None. The route decides what the user sees. Clean separation." |
| Why not custom exceptions | "At this scale I'm catching standard library exceptions directly. They already tell me what happened. I'd add custom exceptions when the caller needs semantic meaning beyond 'it failed.'" |
| Retry logic | "For transient 5xx errors I could add retry with backoff, but only after seeing real failure patterns in production." |
| Timeout value | "3s connect, 5s read. Categories are CDN-cached (~11ms). Listings hit origin (~600ms). 5s is generous for both." |
| 429 Rate Limiting | "429 is not a transient error — it's an instruction to slow down. Must back off (honor Retry-After), not retry immediately." |
| `None` vs empty list | "None means failure, empty list means valid empty response. This distinction lets the route flash the right message." |
| Logging | "logger.exception() captures the full traceback. When on-call, this is the difference between guessing and knowing." |
| Loading UX | "Server-rendered pages don't have loading states — the page is blank until the server responds. React needs explicit loading/error states in component state." |

______________________________________________________________________

## Phase 6: Ideal/Production Implementation (Can Hint At)

For a larger app or when the interviewer asks "how would you evolve this?", this is
the full pattern. Custom exception hierarchy in the client, semantic catches in the route.

### 6a. Custom exception hierarchy

```python
class ReverbClientError(Exception):
    """Base exception for all Reverb client errors."""


class ReverbTransportError(ReverbClientError):
    """Network, timeout, DNS, connection, or request-send failure."""


class ReverbHTTPError(ReverbClientError):
    """Reverb returned a 4xx or 5xx response."""
    def __init__(self, status_code: int, message: str, response_text: str = ""):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)


class ReverbResponseFormatError(ReverbClientError):
    """Reverb responded, but the body was not valid/expected JSON."""


class ReverbValidationError(ReverbClientError):
    """Reverb responded with JSON, but not the expected shape."""
```

### 6b. Client with exception translation

```python
class ReverbClient:
    HEADERS = {
        "Accept": "application/hal+json",
        "Accept-Version": "3.0",
        "Content-Type": "application/hal+json",
    }

    def __init__(self, base_uri="https://api.reverb.com/api", timeout=(3, 5)):
        self._base_uri = base_uri.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(self.HEADERS)

    def listings(self, per_page=10):
        data = self._get("/listings/all", {"per_page": per_page})
        try:
            return data["listings"]
        except KeyError as exc:
            raise ReverbValidationError("Missing expected 'listings' field") from exc

    def categories(self):
        data = self._get("/categories/flat")
        try:
            return data["categories"]
        except KeyError as exc:
            raise ReverbValidationError("Missing expected 'categories' field") from exc

    def _get(self, path, params=None):
        url = f"{self._base_uri}{path}"
        try:
            response = self._session.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
        except requests.HTTPError as exc:
            resp = exc.response
            status = resp.status_code if resp is not None else 0
            body = resp.text if resp is not None else ""
            raise ReverbHTTPError(
                status_code=status,
                message=f"Reverb API returned HTTP {status}",
                response_text=body,
            ) from exc
        except requests.RequestException as exc:
            raise ReverbTransportError("Could not reach Reverb API") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise ReverbResponseFormatError("Reverb returned invalid JSON") from exc
```

**Key improvements over the interview version:**

- `requests.Session()` — reuses TCP connections, faster for multiple calls.
- Exception translation at source — callers never see raw `requests` exceptions.
- Specific-first catch order: `HTTPError` before `RequestException`.
- `from exc` — preserves the original traceback for debugging.

### 6c. Route with semantic catches

```python
from flask import current_app

@app.route("/listings")
def listings():
    try:
        results = ReverbClient().listings()
    except ReverbHTTPError as exc:
        current_app.logger.warning(
            "Reverb HTTP error", extra={"status_code": exc.status_code}
        )
        flash("Unable to load listings. Please try again.", "error")
        results = []
    except ReverbTransportError:
        current_app.logger.exception("Reverb transport failure")
        flash("The listings service is temporarily unavailable.", "error")
        results = []
    except (ReverbResponseFormatError, ReverbValidationError):
        current_app.logger.exception("Unexpected Reverb response format")
        flash("Unable to process listings right now.", "error")
        results = []
    return render_template("listings.html", listings=results)
```

**Why this is better:**

- Different user messages per failure class.
- `ReverbHTTPError` gives access to `status_code` — could differentiate 429 vs 503.
- The route catches application-level exceptions, not raw library internals.
- Service layer is eliminated — the client itself is the service when it handles translation.

### 6d. Mental model

```plaintext
┌─────────────────────────────────────────────────────────────────┐
│ requests library (raw)                                          │
│                                                                 │
│  Timeout, ConnectionError, HTTPError, ...                       │
│  ValueError / JSONDecodeError                                   │
│  KeyError                                                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │ translated at the boundary
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ ReverbClient (application boundary)                             │
│                                                                 │
│  ReverbTransportError      ← network/timeout/DNS                │
│  ReverbHTTPError           ← 4xx/5xx via raise_for_status()     │
│  ReverbResponseFormatError ← valid HTTP, bad JSON               │
│  ReverbValidationError     ← valid JSON, wrong shape            │
└─────────────────────────┬───────────────────────────────────────┘
                          │ caught by route/controller
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Flask route                                                     │
│                                                                 │
│  except ReverbHTTPError       → flash specific message          │
│  except ReverbTransportError  → flash "unavailable"             │
│  except ReverbResponseFormat  → flash "can't process"           │
│  except ReverbValidation      → flash "can't process"           │
└─────────────────────────────────────────────────────────────────┘
```

______________________________________________________________________

## Phase 7: React — Loading & Error States

```jsx
export default function ListingsPage() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetchListings()
      .then((response) => {
        setListings(response.listings);
        setError(null);
      })
      .catch((err) => {
        setError("Unable to load listings. Please try again.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  if (loading) return <p className="loading">Loading listings...</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <ul className="listings__list">
      {listings.map((listing) => (
        // ... existing rendering
      ))}
    </ul>
  );
}
```

**What to say:** "Server-rendered apps don't need loading states — the page arrives
fully rendered or not at all. React SPAs need explicit loading/error/success states
because the fetch happens client-side after the shell renders."

______________________________________________________________________

## Phase 8: Tests

```python
from unittest.mock import patch
from requests.exceptions import ConnectionError, Timeout

def test_load_categories_returns_none_on_network_error():
    with patch("reverb_client.requests.get", side_effect=ConnectionError()):
        result = _load_categories()
    assert result is None

def test_load_categories_returns_none_on_timeout():
    with patch("reverb_client.requests.get", side_effect=Timeout()):
        result = _load_categories()
    assert result is None

def test_load_categories_returns_none_on_bad_json(mock_response_200_html):
    result = _load_categories()
    assert result is None

def test_load_categories_filters_malformed_items():
    fake_data = {"categories": [
        {"full_name": "Guitars"},
        {"id": 2},  # missing full_name
    ]}
    with patch("reverb_client.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = fake_data
        result = _load_categories()
    assert len(result) == 1
    assert result[0]["full_name"] == "Guitars"

def test_listings_route_flashes_on_failure(client):
    with patch("app._load_listings", return_value=None):
        res = client.get("/listings")
    assert res.status_code == 200
    assert b"Could not load listings" in res.data
```

______________________________________________________________________

## Key Principle

> In a timed interview, use the simple pattern (catch standard exceptions in the
> service, return `None`, let the route flash). Mention the ideal pattern (custom
> exception hierarchy, semantic catches) as something you'd build toward.
> Both demonstrate understanding — the difference is scope, not knowledge.
