# Code Walkthrough — Python/Flask Stack

## Architecture Overview

This app uses a **layered architecture**:

```text
HTTP Request → Route (HTTP layer) → Service (app logic) → Client (external IO) → Reverb API
```

| Layer | File(s) | Responsibility |
| --- | --- | --- |
| Route | `app.py` (decorated functions) | Parse HTTP params, call service, render template |
| Service | `app.py` (`_load_*`, `_search_*` helpers) | App logic: filtering, coordination, future pagination/caching |
| Client | `reverb_client.py` (`ReverbClient`) | Wraps Reverb API: headers, URLs, JSON parsing |
| View | `templates/` (Jinja2) | HTML rendering only |

**"Service layer"** names the middle layer specifically. The overall pattern is
just **layered architecture** — the simplest structure that gives testable
boundaries without over-engineering into ports/adapters/hexagonal.

### Why not something more complex?

| Pattern | Why not (for this scope) |
| --- | --- |
| Repository | No DB — data comes from one external API |
| Gateway/Adapter | `ReverbClient` already *is* the gateway |
| Hexagonal/Ports | No DI container, 20 lines of Flask — pure ceremony |
| Clean Architecture | Same: the layers exist conceptually but formalizing them adds nothing |

If the app grew (multiple data sources, caching, auth), you'd promote the
service helpers into a class and potentially introduce ports/adapters.

### Is this MVC?

**Sort of — but it's missing the M.**

| MVC Layer | Traditional role | This app | Present? |
| --- | --- | --- | --- |
| **Model** | Data representation, business logic, DB access | — | No. No DB, no data classes. Raw dicts flow from API to template. |
| **View** | Renders output for the user | `templates/` (Jinja2) | Yes |
| **Controller** | Receives request, coordinates, returns response | Route functions in `app.py` | Yes (but mixed with service logic) |

What you actually have is **VC + Client**:

```text
Controller (routes in app.py) → Client (ReverbClient) → External API
     ↓
View (Jinja2 templates)
```

There's no Model layer — no `Listing` class, no `Category` class, no data
validation or domain logic attached to the data. Just raw dicts passed from the
API response to the template. The "service helpers" (`_search_categories`)
contain business logic that would normally live in a Model in proper MVC.

Compare to the **Rails version** in this same repo — that one *is* MVC by
convention (`app/models/`, `app/views/`, `app/controllers/`). Flask doesn't
enforce this separation; you structure it yourself.

If we added Pydantic models to represent `Listing` and `Category`, *then* you
could call it MVC — with the model being a value object rather than an ORM entity.

---

## Request Flow (End-to-End Trace)

### GET /categories?query=guitar

```text
1. Flask routes to `categories()` in app.py (matches both `/` and `/categories`)
2. Route reads `request.args.get('query')` → "guitar"
3. Calls `_search_categories("guitar")` (service layer)
4. _search_categories calls `_load_categories()` → `ReverbClient().categories()`
5. ReverbClient._get('/categories/flat') → requests.get(...) → Reverb API
6. API returns { "categories": [...] }
7. ReverbClient extracts ['categories'] key, returns list of dicts
8. _search_categories filters: keeps items where query.lower() is in full_name.lower()
9. Route passes filtered list to render_template('categories.html', ...)
10. Jinja2 renders using base.html layout + categories.html block
```

### GET /listings

```text
1. Flask routes to `listings()` in app.py
2. Route calls ReverbClient().listings() DIRECTLY (no service helper — inconsistency)
3. ReverbClient._get('/listings/all', {'per_page': 10}) → Reverb API
4. API returns { "listings": [...] }
5. ReverbClient extracts ['listings'] key, returns list of dicts
6. Route passes list to render_template('listings.html', ...)
```

---

## Key Insight: Inconsistency in Service Layer

**Categories path:** Route → `_search_categories()` → `_load_categories()` → `ReverbClient()`

**Listings path:** Route → `ReverbClient()` directly

This is the main architectural issue. The `_load_categories()` helper is a thin
wrapper now, but it represents the service boundary where pagination, caching,
and normalization belong. `listings` skips this layer entirely.

**Fix:** Add `_load_listings()` for consistency, establishing the service
boundary for both routes before adding features on top of it.

---

## File-by-File Breakdown

### app.py — Routes + Service Layer

- `categories()`: Route handler. Reads query param, delegates to service helper.
- `listings()`: Route handler. Calls client directly (inconsistent).
- `_search_categories(query)`: Service logic — filters categories by name match.
- `_load_categories()`: Service boundary — wraps client call (thin now, will grow).

### reverb_client.py — External API Client

```python
class ReverbClient:
    HEADERS = { 'Accept': 'application/json', 'Accept-Version': '3.0', ... }

    def listings(self, per_page=10):  # GET /listings/all?per_page=10
    def categories(self):             # GET /categories/flat
    def _get(self, path, params={}):  # Shared HTTP logic
```

**Notes:**

- `_get` uses a mutable default arg (`params={}`) — known Python gotcha, but
  harmless here since the dict is never mutated. Don't refactor mid-interview.
- No error handling: no try/except, no status code checks. Happy path only.
- `base_uri` is injectable via constructor — enables testing with a fake server
  if needed (though tests mock at the `requests.get` level instead).

### templates/ — Jinja2 Views

- `base.html`: Layout with Bootstrap navbar, `{% block content %}` slot.
- `categories.html`: Renders filtered category list as `<ul class="list-group">`.
- `listings.html`: Renders listings with title + thumbnail image.

### tests/ — Test Strategy

**Mocking approach:** All tests patch `reverb_client.requests.get` at the HTTP
level. This means the full path from route → service → client → (mocked) HTTP
is exercised in integration tests.

| File | What it tests | Stub level |
| --- | --- | --- |
| `test_reverb_client.py` | Client parses API JSON correctly | `requests.get` |
| `test_listings.py` | Route renders listing title + image | `requests.get` |
| `test_categories.py` | Route filters and renders categories | `requests.get` |
| `helpers.py` | `parse_html()` — BeautifulSoup wrapper for response assertions | N/A |

**What's NOT tested:**

- Error cases (API down, 404, malformed JSON)
- Empty states (no listings returned)
- Pagination (not implemented)
- The `_search_categories` filter logic in isolation (only tested through route)

---

## What's Intentionally Missing

| Feature | Status | Where it would go |
| --- | --- | --- |
| Error handling | Not implemented | Service layer (try/except) + flash messages in templates |
| Pagination | Not implemented | Service layer (`_load_*` helpers) + query params |
| Caching | Not implemented | Service layer (e.g., `@lru_cache` on `_load_categories`) |
| Listing detail page | Not implemented | New route + client method + template |
| Auth | Not needed | Reverb public API is read-only without auth |
| Input validation | Not implemented | Would go in routes (validate query params) |

---

## Running the App

```bash
# Install dependencies
pipenv install

# Run server
pipenv run flask run --reload

# Run all tests
pipenv run pytest -vs

# Run single test file
pipenv run pytest -vs tests/test_listings.py

# Run single test
pipenv run pytest -vs tests/test_categories.py::test_displays_full_name_of_matching_categories
```
