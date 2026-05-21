# Code Reading Strategy — Python/Flask Stack

## Phase 1: Entry Points (30 seconds)

Start at `app.py`. There are only two routes — say them out loud:

| Route | What it does |
| -- | -- |
| `GET /` or `/categories` | Reads `?query=`, filters categories client-side, renders HTML |
| `GET /listings` | Fetches 10 listings, renders HTML |

Key observation: **no REST API is exposed** — Flask serves rendered HTML pages only. The JSON API lives at `api.reverb.com`, not here.

---

## Phase 2: The API Client (1 minute)

Open `reverb_client.py`. Trace the data flow:

```plaintext
ReverbClient()
  ._get(path, params)
    → requests.get(base_uri + path, headers=HEADERS, params=params)
    → .json()
```

Things to notice and articulate:

1. **No auth** -- only `Accept`, `Accept-Version`, `Content-Type` headers
2. **Hardcoded base URI** -- `https://api.reverb.com/api` (no env var override in production)
3. **Constructor allows injection** -- `base_uri` param enables testing against a different host
4. **Mutable default argument** -- `params={}` is a classic Python footgun (shared across calls)
5. **No error handling** -- `.json()` will throw on non-200 or malformed responses
6. **No timeout** -- `requests.get` will hang indefinitely on a stalled connection

---

## Phase 3: Categories Search Logic (1 minute)

In `app.py`, trace the search flow:

```plaintext
request.args.get('query')
  -> _search_categories(query)
    -> if not query: return []         # short-circuit: no query = no results
    -> _load_categories()              # fetches ALL categories from API
    -> filter(lambda c: query.lower() in c['full_name'].lower(), categories)
```

Things to articulate:

1. **Client-side filtering** -- always fetches the full category tree, then filters in Python
2. **Case-insensitive substring match** -- `in` operator on lowercased strings
3. **No caching** -- every search re-fetches the entire category list from Reverb
4. **`filter()` returns an iterator** -- works with Jinja2's `{% for %}`, but `len()` would fail on it

---

## Phase 4: Templates (30 seconds)

```plaintext
base.html          -> Bootstrap 4 layout, navbar with links to /categories and /listings
categories.html    -> Search form (GET /) + conditional list or "no results" message
listings.html      -> Iterates listings, renders thumbnail + title
```

Key observation in `listings.html`:

```jinja
{{ listing['photos'][0]['_links']['thumbnail']['href'] }}
```

This deeply nested access has **no safety** — a listing with no photos will crash the template with a `KeyError`/`IndexError`.

---

## Phase 5: Test Architecture (1 minute)

### Structure

```plaintext
tests/
  helpers.py              → parse_html() wraps BeautifulSoup
  test_reverb_client.py   → Unit tests for ReverbClient (mocks requests.get)
  test_categories.py      → Integration tests: Flask test client + mocked API
  test_listings.py        → Integration tests: Flask test client + mocked API
```

### Patterns to recognize

| Pattern | Where | Why it matters |
| -- | -- | -- |
| `patch('reverb_client.requests.get')` | All test files | Mocks at the boundary — no real HTTP calls |
| `mock_get.return_value.json.return_value = {...}` | Fixtures | Simulates the Reverb API response shape |
| `app.test_client()` | Integration tests | Flask's built-in test client, no server needed |
| `parse_html(res)` via BeautifulSoup | Integration tests | Asserts on rendered DOM, not raw strings |
| `html.body.select_one('ul.list-group').li.text` | Assertions | CSS-selector based, mirrors how a user would verify |

### What's NOT tested

- Error responses (500, timeout, malformed JSON)
- Empty listings (no photos)
- Pagination or `per_page` behavior
- The "no results" message path in categories (partially — checks `len == 0` but not the `<p>` text)

---

## Phase 6: Tradeoffs and Problems to Discuss

### Architecture

| Issue | Impact | What you'd improve |
| -- | -- | -- |
| No caching of categories | Every search = full round-trip to Reverb API | Add `functools.lru_cache` or Redis with TTL |
| Client-side filtering | Fetches entire category tree every time | Use Reverb's query param if available, or cache locally |
| No separation of concerns for listings | `listings()` route calls client directly -- no service layer | Extract `_load_listings()` for consistency with categories |
| Tight coupling to Reverb response shape | Template directly indexes `listing['photos'][0]['_links']['thumbnail']['href']` | Normalize in the client or a serializer |

### Resilience

| Issue | Impact | What you'd improve |
| -- | -- | -- |
| No timeout on `requests.get` | App hangs if Reverb is slow | Add `timeout=(3, 5)` -- 3s connect, 5s read |
| No error handling | 500 from Reverb -> unhandled exception -> Flask 500 | Try/except in service layer + user-friendly flash messages |
| No retries | Transient failures surface immediately | `requests.adapters.HTTPAdapter` with `Retry` |
| Mutable default `params={}` | Potential for params leaking between calls | Use `params=None`; `if params is None: params = {}` |

### Testing

| Issue | Impact | What you'd improve |
| -- | -- | -- |
| `patch().start()` without `stop()` | Mock leaks between tests | Use `@patch` decorator or `with patch(...)` context manager |
| No parametrized tests | Repetitive setup for edge cases | Use `@pytest.mark.parametrize` |
| No fixture teardown | `mock_get` lives beyond test scope | `addCleanup` or `yield` + `patch.stopall()` |
| DOM assertions are fragile | Changing a CSS class breaks tests | Consider testing the data passed to templates separately |

### Security / Best Practices

| Issue | Impact | What you'd improve |
| -- | -- | -- |
| No CSRF protection on form | GET form is fine, but if converted to POST it's vulnerable | Use `flask-wtf` for any state-changing forms |
| No input sanitization | `query` goes straight to filter — safe here but bad habit | Validate/strip input at boundary |
| CDN integrity hash for Bootstrap | Good — already present | Keep it |
| No `Content-Security-Policy` | XSS surface exists if user data is rendered | Add CSP headers |

---

## Verbal Walkthrough Script (Practice Out Loud)

> "The app has two pages -- categories and listings -- both served as server-rendered HTML via Flask and Jinja2.
>
> For categories: when a user submits the search form, Flask reads the `query` param, calls `_search_categories()` which delegates to `_load_categories()`, which calls the Reverb public API to fetch all categories. The service filters them in Python using a case-insensitive substring match. The results render as a `<ul>` list.
>
> For listings: Flask calls `ReverbClient().listings()` directly with a hardcoded `per_page=10`. There's no service helper for listings -- that's an inconsistency I'd fix.
>
> The API client is a thin wrapper around `requests` with no auth needed -- just accept headers and API versioning. Tests mock `requests.get` at the module boundary so nothing hits the network.
>
> If I were to improve this, the biggest wins would be: adding a timeout and error handling to the HTTP client, caching the category list since it changes rarely, fixing the mutable default argument in `_get()`, and adding `_load_listings()` for architectural consistency."
