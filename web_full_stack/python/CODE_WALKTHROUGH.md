# Code Walkthrough — Python/Flask Stack

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

**Partially — missing the M.** No Model layer (no data classes, no DB). Raw
dicts flow from API to template. Routes act as Controller, Jinja2 templates are
the View, and `_search_categories` absorbs Model-like business logic.

More precisely: this is a **layered architecture** (Route/Controller → Service → Client),
not MVC. The Rails version in this repo *is* MVC by convention.

Note: MVC is a presentation pattern for one application boundary — it doesn't
describe full-stack systems with network boundaries (SPA + API, microservices).
See [MVC_AND_ARCHITECTURE_PATTERNS.md](MVC_AND_ARCHITECTURE_PATTERNS.md) for
deeper analysis including the Next.js hybrid case.

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

**Categories path:** Route (Controller) → `_search_categories()` → `_load_categories()` → `ReverbClient()`

**Listings path:** Route (Controller) → `ReverbClient()` directly

This is the main architectural issue. The `_load_categories()` helper is a thin
wrapper now, but it represents the service boundary where pagination, caching,
and normalization belong. `listings` skips this layer entirely.

**Fix:** Add `_load_listings()` for consistency, establishing the service
boundary for both routes before adding features on top of it.

---

## File-by-File Breakdown

### app.py — Routes (Controller) + Service Layer

- `categories()`: Controller/route. Reads query param, delegates to service helper.
- `listings()`: Controller/route. Calls client directly (inconsistent).
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
level. This means the full path from route (controller) → service → client → (mocked) HTTP
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
| Input validation | Not implemented | Would go in routes/controller (validate query params) |

---

## Architecture Considerations per Interview Scenario

The architectural choices (and gaps) in this codebase have concrete consequences
for each feature you might be asked to implement. The central theme: **listings
skips the service layer**, and that debt compounds across scenarios.

### Scenario 1: Listing Detail Page

- **No service helper needed** — fetching a single listing by ID is a straight
  client→route pass-through (like current listings). No filtering/coordination.
- **But** if you skip adding `_load_listing(id)`, you perpetuate the
  inconsistency. Mention: "I'll add it for consistency," then keep it thin.
- **Raw dicts with no Model** — `listing['photos'][0]['_links']['large_crop']['href']`
  is deeply nested key access. One missing key = crash. The codebase has no error
  handling ("happy path only").

### Scenario 2: Search / Filter Listings

- **This is where you fix the inconsistency.** The main architectural issue is
  "listings skips the service layer." Adding `_search_listings(query)` mirrors
  `_search_categories(query)` — the architecture tells you exactly where it goes.
- **Decision point:** client-side filter (like categories does — fetch ALL, then
  filter in Python) vs. pass `query` to the API? The Reverb API supports `query`
  natively on `/listings/all` — architecturally cleaner to let the API filter
  rather than downloading everything.
- **Implication:** If you choose API-side filtering, `_search_listings` becomes a
  thin wrapper that passes the query through. If you choose client-side, it
  becomes a `_load_listings()` + filter pattern (matching categories).

### Scenario 3: Pagination

- **Explicitly belongs in the service layer** — the "What's Intentionally
  Missing" table above says so directly. This is the scenario that justifies
  `_load_listings()` existing as a service boundary.
- **Breaking change to the client:** Currently `listings()` returns
  `self._get(...)['listings']` (unwraps the response). Pagination needs metadata
  (`current_page`, `total_pages`). You must change the return type. The client's
  job (per the architecture table) is "headers, URLs, JSON parsing" — returning
  the full response is still within scope.
- **The mutable default arg becomes real:** `_get(self, path, params={})` is
  noted as "harmless since never mutated." But if you add `params['page'] = page`
  inside `_get` or in a caller that passes the same dict, the default persists
  across calls. This is the scenario where the gotcha stops being theoretical.

### Scenario 4: Category → Listings Navigation

- **Connects two parallel paths.** The architecture diagram shows categories and
  listings as independent vertical stacks. This scenario adds a horizontal link
  between them (category → filtered listings).
- **`base_uri` injectable via constructor** — the client is already designed for
  configurability. Adding a `category` param is trivial at the client level.
- **No input validation** (noted as "not implemented"). Category slugs from the
  API are safe, but if you accept user-typed slugs in the URL, you're passing
  untrusted input directly to the external API.

### Scenario 5: Error Handling

- **The codebase is most explicit about this gap:** "No error handling: no
  try/except, no status code checks. Happy path only." The architecture table
  tells you where it goes: "Service layer (try/except) + flash messages in
  templates."
- **`_get` has no status check** — `response.json()` will raise `JSONDecodeError`
  on non-JSON error responses (e.g., HTML error pages from a proxy).
- **Two failure modes in `_get`:**
  1. HTTP error status (4xx/5xx) — `response.ok` is `False`.
  2. Network failure — `requests.get` raises `ConnectionError`/`Timeout`.
  Both need handling, and both should surface as the same custom exception to the
  service/route layer.
- **The mutable default becomes dangerous** if you add retry logic that mutates
  the params dict between attempts.

### Scenario 6: Price Display + Sort

- **Sort is business logic → service layer.** But listings has no service layer.
  You either: (a) add `_sort_listings(listings, order)` first, or (b) inline it
  in the route and accept the architectural debt.
- **Raw dicts, no Model** — `listing['price']['amount']` requires nested keys to
  exist. Listings without prices (drafts, auction-style, "Call for price") will
  crash `float()`. No data class validates the shape before the template sees it.
- **No input validation** — the `sort` query param arrives as a raw string.
  `sort=evil` falls through to unsorted (safe by accident, not by design).
  Explicit validation would reject unknown sort values.

### The Compound Effect

The walkthrough's central insight — **"listings skips the service layer"** —
compounds across scenarios:

```text
Scenario 2: Sort logic goes... where? Inline in the route.
Scenario 3: Pagination coordination goes... inline in the route.
Scenario 5: Error handling wraps... the entire route body.
Scenario 6: Sort + pagination + error handling = 20 lines of logic in one route function.
```

If you fix it early (add `_load_listings()` in Scenario 1 or 2), every
subsequent scenario has a clean place to add logic. If you don't, the route
function grows into a god-function that's untestable in isolation:

```python
# Without service layer — everything in one route
@app.route('/listings')
def listings():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort')
    category = request.args.get('category')
    try:
        results = ReverbClient().listings(page=page, category=category)
        listings = results['listings']
        if sort == 'price_asc':
            listings.sort(key=lambda l: float(l['price']['amount']))
        elif sort == 'price_desc':
            listings.sort(key=lambda l: float(l['price']['amount']), reverse=True)
    except ApiError:
        listings = []
        flash("Unable to load listings.")
    return render_template('listings.html', listings=listings, ...)

# With service layer — route is thin, logic is testable
@app.route('/listings')
def listings():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort')
    category = request.args.get('category')
    try:
        listings, pagination = _load_listings(page=page, category=category)
        listings = _sort_listings(listings, sort)
    except ApiError:
        listings, pagination = [], {}
        flash("Unable to load listings.")
    return render_template('listings.html', listings=listings, **pagination)
```

**Interview signal:** Recognizing this early and saying "let me add the service
boundary first, then build the feature on top" shows architectural thinking —
the ability to identify structural debt before it causes pain.

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
