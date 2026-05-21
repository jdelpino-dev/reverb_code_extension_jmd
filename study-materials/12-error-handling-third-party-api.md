# 12 - Error Handling for Third-Party API Calls

## The Problem

When a Flask app calls an external API, failures can happen at multiple layers.
Each layer has a different failure mode, a different exception type, and a different owner.
Without explicit handling at each layer, failures become silent 500s or — worse — misleading
empty pages with no user feedback.

---

## The Four Failure Paths

### Path 1: Transport failure — no response at all

**What:** DNS failure, connection refused, network timeout, SSL error.

**Raised by:** `requests.get()` automatically.

**Exception:** `requests.exceptions.RequestException` (base class for all `requests` errors).

**Who catches it:** the service layer.

```python
except RequestException:
    logger.exception("Network error fetching listings from Reverb API")
```

---

### Path 2: HTTP error status — server responded with 4xx or 5xx

**What:** the server responded but said it can't fulfill the request:
`401 Unauthorized`, `429 Rate Limited`, `503 Service Unavailable`, etc.

**Raised by:** `requests` does NOT raise automatically for HTTP error codes.
You must call `response.raise_for_status()` explicitly in the client.

**Exception:** `requests.exceptions.HTTPError` — a subclass of `RequestException`,
so it is caught by the same `except RequestException` clause in the service.

**Where to add it:** in the client's `_get()` method, before calling `.json()`:

```python
response = requests.get(...)
response.raise_for_status()   # raises HTTPError for 4xx/5xx
return response.json()        # only reached on 2xx
```

**Why it matters:** without this, a 503 returning an HTML error page silently
reaches `.json()` and raises `JSONDecodeError` instead of a meaningful HTTP error.

---

### Path 3: Invalid JSON body — 2xx with non-JSON response

**What:** the server returns HTTP 200 but the body is not valid JSON
(e.g., a CDN returning `"OK"` as plain text, or a misconfigured proxy).

**Raised by:** `response.json()` in the client.

**Exception:** `json.JSONDecodeError`, which is a subclass of `ValueError`.
In `requests >= 2.28`, it is also a subclass of `RequestException` — but in older
versions it is only a `ValueError`. To be safe, always catch `ValueError` explicitly.

**Who catches it:** the service layer.

```python
except ValueError:
    logger.exception("Invalid JSON response from Reverb API /listings/all")
```

---

### Path 4: Unexpected JSON shape — valid JSON, wrong structure

**What:** the server returns HTTP 200 with valid JSON, but the expected key is missing:

```json
{"message": "Unauthorized"}   // ← no "listings" key
{"error": "Too many requests"} // ← no "categories" key
```

**Raised by:** the key access in the client (`["listings"]`, `["categories"]`).

**Exception:** `KeyError`.

**Who catches it:** the service layer.

```python
except KeyError:
    logger.exception("Unexpected response shape from Reverb API /listings/all")
```

**Note:** this is distinct from item-level key errors (see Path 4b below).

---

### Path 4b: Item-level key missing — valid list, malformed items

**What:** the top-level key exists and the value is a list, but individual items
in the list are missing expected fields (e.g., a category dict without `"full_name"`).

**Raised by:** business logic that accesses item fields (e.g., inside a `filter` lambda).

**Exception:** `KeyError` — but raised *after* the service helper has already returned
successfully, so it is NOT caught by the service's `except KeyError`.

**Who handles it:** defensive normalization in the service, before returning:

```python
def _load_categories():
    try:
        categories = ReverbClient().categories()
        return [c for c in categories if "full_name" in c]  # drop malformed items
    except ...
```

This is **response normalization**, not exception handling. The service guarantees
a clean list to its callers — any item missing required fields is silently dropped.

---

## Complete Exception Coverage per Service Helper

```python
def _load_listings():
    try:
        return ReverbClient().listings()
    except RequestException:        # Path 1 + Path 2 (HTTPError is a subclass)
        logger.exception("Network error fetching listings from Reverb API")
    except KeyError:                # Path 4
        logger.exception("Unexpected response shape from Reverb API /listings/all")
    except ValueError:              # Path 3
        logger.exception("Invalid JSON response from Reverb API /listings/all")
```

All three `except` clauses are needed. `RequestException` does not cover `KeyError`
or `ValueError`. They are orthogonal failure modes.

---

## Where Each Concern Lives

| Concern | Layer | Mechanism |
|---|---|---|
| Transport failures | Service catches | `except RequestException` |
| HTTP 4xx/5xx | Client raises explicitly | `response.raise_for_status()` |
| Non-JSON body | Service catches | `except ValueError` |
| Wrong JSON shape (top-level) | Service catches | `except KeyError` |
| Malformed items (item-level) | Service normalizes | defensive list comprehension |
| Logging failures | Service | `logger.exception(...)` |
| User feedback (flash) | Route | `if results is None: flash(...)` |
| Error pages (500, 503) | Flask error handlers | `@app.errorhandler(N)` |

---

## The `None` Sentinel Pattern

Service helpers return `None` on any failure (all three `except` branches fall through
to an implicit `return None`). This lets the route distinguish:

- `None` → something went wrong → flash an error, render with empty data
- `[]` → valid empty result → flash "no results" or render empty state
- `[...]` → success → render normally

```python
# route
results = _load_listings()
if results is None:
    flash("Could not load listings. Please try again.", "error")
    results = []
return render_template("listings.html", listings=results)
```

Without this distinction, a network failure and a genuine empty result look identical
to the route, producing either a silent empty page or a misleading "no results" message.

---

## The `raise_for_status()` Gotcha

`requests` does **not** raise on HTTP error codes by default. This is intentional —
`requests` treats "got a response" as success regardless of the status code.

Without `raise_for_status()`, a 503 with an HTML body reaches `.json()` and raises
`JSONDecodeError` — which tells you nothing about the actual HTTP status code.

With `raise_for_status()`, the same 503 raises `HTTPError` immediately, which:

1. Contains the actual status code and response
2. Is a `RequestException` subclass — caught by existing service handlers
3. Never reaches `.json()` — no misleading `JSONDecodeError`

Always call `raise_for_status()` before `.json()` in any HTTP client.

---

## The `abort()` Inside `try` Gotcha

`abort()` raises `werkzeug.exceptions.HTTPException`. If your `except` clause is
`except Exception`, it will catch and swallow the `abort()`:

```python
try:
    abort(404)          # raises HTTPException
except Exception:       # ← catches it! abort never fires
    pass
```

Fix: catch specific exceptions (`RequestException`, `KeyError`, `ValueError`) rather
than `Exception`. Or re-raise `HTTPException` explicitly:

```python
from werkzeug.exceptions import HTTPException

except Exception as e:
    if isinstance(e, HTTPException):
        raise
    logger.exception(...)
```

Catching `Exception` is almost always wrong in service helpers.

---

## The `flash()` in Service Gotcha

`flash()` writes to the Flask session. Calling it inside a service helper requires
an active request context. If the helper is ever called outside a request
(CLI script, background job, test without app context), it raises:

```plaintext
RuntimeError: working outside of request context
```

Flash belongs in the route, not the service. The service returns data or `None`.
The route decides what the user sees.

---

## Summary: The Rule

> Every spontaneous failure must be caught by the service first.
> The service decides: recover silently, return `None`, or escalate.
> The route owns user-facing communication: flash messages, error pages, status codes.
> The client's job is to make HTTP errors visible by calling `raise_for_status()`.
