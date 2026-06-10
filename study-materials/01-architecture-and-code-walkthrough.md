# Chapter 1: Architecture and Code Walkthrough

## Architecture Overview

This app uses a **layered architecture**:

```text
HTTP Request → Route (Controller) → Service → Client → Reverb API
                      ↑                ↑        ↑          ↓
                      ← ← ← ← ← ← ← ← ← ← ← ← JSON response
                      ↓
                    View (Jinja2) → HTML Response
```

| Layer | File(s) | Responsibility |
| --- | --- | --- |
| Route (Controller) | `app.py` (decorated functions) | Parse HTTP params, call service, render template |
| Service | `app.py` (`_load_*`, `_search_*` helpers) | App logic: filtering, coordination |
| Client | `reverb_client.py` (`ReverbClient`) | Wraps Reverb API: headers, URLs, JSON parsing |
| View | `templates/` (Jinja2) | HTML rendering only |

---

## Why "Layered Architecture" (Not MVC)

**Missing the M.** There's no Model layer — no data classes, no database, no ORM.
Raw dicts flow from API response directly into templates. Routes act as Controller,
Jinja2 templates are the View, and `_search_categories` absorbs what would be
Model-like business logic.

If asked "Is this MVC?":

> "Partially — it's missing the M. There's no domain model or persistence. I'd
> describe it as a layered architecture: Route → Service → Client. The service
> helpers absorb the business logic that a Model layer would normally hold."

---

## File-by-File Breakdown

### `app.py` — Routes + Service Layer

```python
@app.route('/')
@app.route('/categories')
def categories():
    categories = _search_categories(request.args.get('query'))
    return render_template('categories.html', categories=categories)

@app.route('/listings')
def listings():
    return render_template('listings.html', listings=ReverbClient().listings())

def _search_categories(query):
    if not query: return []
    categories = _load_categories()
    return filter(lambda c: query.lower() in c['full_name'].lower(), categories)

def _load_categories():
    return ReverbClient().categories()
```

**Key observations:**

- `categories()` route reads query param, delegates to service helper
- `listings()` route calls client directly — **inconsistency** (no service helper)
- `_search_categories(query)` is the service layer — contains business logic (filtering)
- `_load_categories()` is a thin wrapper (service boundary for future caching/pagination)

### `reverb_client.py` — External API Client

```python
class ReverbClient:
    HEADERS = {
        'Accept': 'application/json',
        'Accept-Version': '3.0',
        'Content-Type': 'application/hal+json'
    }

    def __init__(self, base_uri='https://api.reverb.com/api'):
        self._base_uri = base_uri

    def listings(self, per_page=10):
        return self._get('/listings/all', {'per_page': per_page})['listings']

    def categories(self):
        return self._get('/categories/flat')['categories']

    def _get(self, path, params={}):
        return requests.get(
            self._base_uri + path, headers=self.HEADERS, params=params
        ).json()
```

**Things to articulate:**

1. No auth — only Accept/Version/Content-Type headers
2. Constructor allows base URI injection — enables testing
3. Mutable default argument `params={}` — Python gotcha (harmless here, would bite with mutation)
4. No error handling — `.json()` will throw on non-200 or malformed responses
5. No timeout — `requests.get` will hang indefinitely on a stalled connection

### `templates/` — Jinja2 Views

- `base.html`: Bootstrap 4 layout, navbar with links, `{% block content %}` slot
- `categories.html`: Search form (GET `/`) + conditional list or "no results" message
- `listings.html`: Iterates listings, renders thumbnail + title

**Critical template observation:**

```jinja
{{ listing['photos'][0]['_links']['thumbnail']['href'] }}
```

Deeply nested dict access with **no safety** — a listing without photos crashes the template.

---

## Request Flow (End-to-End Trace)

### GET /categories?query=guitar

```text
1. Flask routes to categories() (matches both / and /categories)
2. Route reads request.args.get('query') → "guitar"
3. Calls _search_categories("guitar")
4. _search_categories calls _load_categories() → ReverbClient().categories()
5. ReverbClient._get('/categories/flat') → requests.get(...) → Reverb API
6. API returns { "categories": [...] }
7. ReverbClient extracts ['categories'] key → list of dicts
8. _search_categories filters: keeps items where query.lower() in full_name.lower()
9. Route passes filtered list to render_template('categories.html', ...)
10. Jinja2 renders base.html layout + categories.html block
```

### GET /listings

```text
1. Flask routes to listings()
2. Route calls ReverbClient().listings() DIRECTLY (no service helper)
3. ReverbClient._get('/listings/all', {'per_page': 10}) → Reverb API
4. API returns { "listings": [...] }
5. ReverbClient extracts ['listings'] key → list of dicts
6. Route passes list to render_template('listings.html', ...)
```

---

## The Central Architectural Issue: Service Layer Inconsistency

**Categories path:** Route → `_search_categories()` → `_load_categories()` → `ReverbClient()`

**Listings path:** Route → `ReverbClient()` directly

This inconsistency is the main structural discussion point. The `_load_categories()`
helper is thin now, but represents the service boundary where pagination, caching,
and normalization belong. Listings skips this layer entirely.

### Why It Matters for Each Scenario

| Scenario | What you'd add | Why the gap hurts |
| --- | --- | --- |
| Search | Filter logic | Lives inline in route without service boundary |
| Pagination | Page coordination + metadata | No place to extract pagination info |
| Error handling | try/except + graceful degradation | Must wrap the entire route body |
| Sort | Business logic | Pure logic forced into HTTP handler |

### The Fix (Say This Early)

> "Let me add the service boundary first — `_load_listings()` — then build the
> feature on top of it. This gives me a clean test seam and a consistent
> architecture."

```python
# Before: everything in route
@app.route('/listings')
def listings():
    return render_template('listings.html', listings=ReverbClient().listings())

# After: consistent service boundary
@app.route('/listings')
def listings():
    results = _load_listings()
    return render_template('listings.html', listings=results)

def _load_listings():
    return ReverbClient().listings()
```

---

## What's Intentionally Missing

| Feature | Where it would go | Why it matters |
| --- | --- | --- |
| Error handling | Service layer (try/except) + flash messages | API failures crash the page |
| Pagination | Service layer + query params + template controls | Only shows 10 listings |
| Caching | Service layer (`@lru_cache` on `_load_categories`) | Every request hits the API |
| Input validation | Routes (validate query params) | Raw user input passes through |
| Listing detail page | New route + client method + template | No drill-down capability |
| Timeout | Client (`timeout=5` on requests.get) | Slow API hangs Flask indefinitely |

---

## Verbal Walkthrough Script (Practice Out Loud)

> "The app has two pages — categories and listings — both server-rendered via
> Flask and Jinja2.
>
> For categories: when a user submits the search form, Flask reads the query
> param, calls the Reverb API to fetch all categories, then filters them in
> Python using a case-insensitive substring match. Results render as a list.
>
> For listings: Flask calls Reverb's `/listings/all` endpoint with a hardcoded
> `per_page=10`, and the template renders each listing's title and first photo.
>
> The API client is a thin wrapper around `requests` with no auth needed. Tests
> mock `requests.get` at the module boundary so nothing hits the network.
>
> The main architectural observation: categories has a service layer
> (`_search_categories` → `_load_categories`) but listings calls the client
> directly. If I were extending this, I'd add `_load_listings()` first for
> consistency."

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

---

## New Codebase Addendum (June 2026)

The interview now uses a refreshed, AI-generated codebase at
`tmp/reverb-hiring-code-python`. The **layered architecture above still
applies** — but the boundaries are drawn differently. See
[Chapter 16](16-new-codebase-stack-guide.md) for the full guide.

### Architecture diff vs the original

| Layer | Old codebase | New codebase |
|---|---|---|
| Entry point | `app.py` (module-level `app = Flask(__name__)`) | `app/__init__.py` with `create_app()` factory |
| Routes | All in `app.py` | `app/routes/categories.py` + `app/routes/listings.py` as **Blueprints** |
| Service helpers | `_load_categories()`, `_search_categories()` in `app.py` | **Collapsed** — routes call the client directly |
| Client | `reverb_client.py` — `ReverbClient` class | `app/clients/reverb.py` — module-level functions, uses `httpx`, calls `raise_for_status()` |
| Templates | `templates/categories.html`, `listings.html` | `templates/categories/index.html`, `listings/index.html`, `partials/navigation.html` |

### New request flow — GET /categories?search=guitar

```text
1. Flask matches the URL against the categories Blueprint
2. categories.index() reads request.args.get("search", "").strip()
3. Route calls reverb.categories() DIRECTLY — no service helper
4. Filtering happens inline in the route via list comprehension
5. Filtered list passed to render_template("categories/index.html", ...)
6. layout.html renders, includes partials/navigation.html, fills the content block
```

Note the query param name changed: **`query` → `search`**.

### The service layer is now "intentionally collapsed"

The original codebase's main architectural critique — inconsistent service
boundaries between `categories` and `listings` — has been resolved by **removing
the service layer entirely**. Both routes call the client directly. This is
simpler for the current scope but reintroduces the same critique under a different
name: if pagination, caching, or business rules get added, there is no service
seam to extend.

**A second consequence: data-shaping collapses too.** A service layer is also
where you would normalize raw API dicts into something the template can consume
cleanly. Without it, two things happen:

- **Routes grow inline logic.** The categories route already does filtering via
  list comprehension inline. Add sorting or field normalization and the route
  becomes a data-manipulation function, not a thin HTTP handler.
- **Templates navigate raw API structure.** The listings template accesses
  `listing["photos"][0]["_links"]["thumbnail"]["href"]` directly. That path
  reflects Reverb's internal JSON shape, not a clean view model. A missing photo
  key crashes the template. A service layer (or even a small helper function)
  would resolve the photo URL once, return `None` on failure, and hand the
  template a flat dict it can render safely.

The interview script becomes:

> "The service layer is collapsed in this version, which is fine for the current
> scope. But collapsing it also collapses the data-shaping layer — the template
> is navigating raw API structure directly, which makes it fragile. If I were
> extending this, I'd extract a `services/` module that normalizes each listing
> into a flat dict before passing it to the template. That keeps routes thin,
> templates simple, and the API structure isolated to one place."

See [Chapter 16 § Collapsed Service Layer](16-new-codebase-stack-guide.md) for
the full discussion.
