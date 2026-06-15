# Code Walkthrough — Python/Flask Stack (2026)

This walkthrough describes the **upstream codebase** as the interviewer presents
it: [app/](app/), [tests/](tests/), [pyproject.toml](pyproject.toml). It maps
the file layout, traces requests end-to-end, and calls out observations
worth discussing — especially the ones that compound across the
[scenario docs](../scenario-1-detail-page.md).

The companion file is [TEST_WALKTHROUGH.md](TEST_WALKTHROUGH.md).

---

## Architecture Overview

This app is a **flat layered architecture** with Flask blueprints and a stateless
HTTP client module:

```text
Browser HTTP Request -> Blueprint (Route) -> Client (module functions) -> httpx -> Reverb API
                       |                                                        |
                       <- <- <- <- <- <- <- <- <- <- <- <- <- <- <- JSON response
                       |
                 View (Jinja2)
                       |
                  HTML Response
```

| Layer | File(s) | Responsibility |
| --- | --- | --- |
| App factory | [app/\_\_init\_\_.py](app/__init__.py) | Build `Flask`, load `.env`, register blueprints |
| Route (Controller) | [app/routes/categories.py](app/routes/categories.py), [app/routes/listings.py](app/routes/listings.py) | Parse query string, call client, render template |
| Client | [app/clients/reverb.py](app/clients/reverb.py) | Module-level functions that wrap Reverb endpoints |
| View | [app/templates/](app/templates/) | Jinja2 templates (layout + per-feature dirs) |
| Static | [app/static/css/app.css](app/static/css/app.css) | Pico CSS overrides + project styles |

There is **no explicit service layer**. Filtering and any other business logic
currently lives inline in the route. Whether that is a gap or a deliberate
simplification is discussed in [The Missing Service Layer](#the-missing-service-layer)
below.

### Why this shape (and not something heavier)?

| Pattern | Why not (for this scope) |
| --- | --- |
| Repository | No DB — one external API |
| Gateway/Adapter | `app/clients/reverb.py` already *is* the gateway |
| Hexagonal / Ports & Adapters | No DI container; 30 lines of Flask — pure ceremony |
| Service classes | Two stateless GET endpoints — module functions are idiomatic |
| Class-based client (`ReverbClient`) | No shared state (pool, auth, session) to encapsulate yet |

### Is this MVC?

Partially — **no Model layer**. Raw `dict`s flow from `httpx.get(...).json()`
through the route into the Jinja template. The route is Controller, Jinja is
View, the "Model" is just whatever JSON shape Reverb returns. More precisely:
this is a **layered architecture** (Blueprint -> Client). The Ruby/Rails
version in this repo is MVC by convention; this Python version intentionally
isn't.

See [MVC_AND_ARCHITECTURE_PATTERNS.md](../MVC_AND_ARCHITECTURE_PATTERNS.md) for
the broader discussion.

---

## Request Flow (End-to-End Trace)

### GET /categories?search=guitar

```text
1. Flask routes to categories.index() in app/routes/categories.py
   (matches both `/` and `/categories`)
2. Route reads request.args.get("search", "").strip() -> "guitar"
3. Route calls reverb.categories() -> _get("categories/flat") -> httpx.get(...)
4. Reverb API returns { "categories": [...] }
5. _get unwraps response.json(); categories() extracts the "categories" key
6. Route filters in Python: substring match on full_name, case-insensitive
7. Route renders templates/categories/index.html with `categories` + `search_term`
8. Template renders search form + result cards (or empty-state message)
```

### GET /listings

```text
1. Flask routes to listings.index() in app/routes/listings.py
2. Route calls reverb.listings() directly (per_page defaults to 10)
3. _get("listings", {"per_page": 10}) -> httpx.get(...)
4. API returns { "listings": [...] }
5. listings() extracts the "listings" key, returns the list
6. Route renders templates/listings/index.html with `listings`
```

Both routes call the client **directly**. This is the symmetric version of the
old codebase's "listings skips the service layer" — now neither route has one.

---

## The Missing Service Layer

The old Python codebase had a half-implemented service layer (`_load_categories`,
`_search_categories` helpers in `app.py`) that listings ignored. The new
codebase has removed that asymmetry by deleting the helpers entirely:

```python
# app/routes/categories.py
matched_categories = [
    c for c in reverb.categories()
    if search_term.lower() in (c.get("full_name") or "").lower()
]
```

The filter — the only real business logic in either route — is **inline**.

### Two defensible framings

**(a) Intentional simplicity.** For two stateless GET endpoints with ~5 lines
of logic each, a service layer is pure ceremony. Modules and functions are
cheap in Python; promoting a one-line list comprehension into
`_search_categories()` adds an indirection without a payoff. **You shouldn't
introduce abstractions before they have a second caller.**

**(b) A real gap that compounds.** The walkthroughs for scenarios 2, 3, 5, 6
all add logic that *belongs* in a service layer (search forwarding, pagination
metadata, error translation, sort). Without a seam, that logic accretes inside
the route function and becomes hard to test in isolation. The cost of adding
the seam later is one rename + one new file; the cost of not having it
multiplies per scenario.

### Recommended posture for the interview

**Lazy introduction.** Don't add a `app/services/` module on day one. Do say
out loud, *unprompted*, something like:

> "Today these routes are thin enough that I'd keep the filter inline. The
> moment I need pagination metadata or error translation across multiple
> endpoints, I'd promote that into `app/services/listings.py` so the route
> stays a thin Controller and the logic becomes unit-testable without going
> through `app.test_client()`."

This shows architectural judgment in both directions: you know the pattern,
you also know when invoking it is over-engineering. The actual pivot point is
**Scenario 5 (error handling)** — once you need typed exceptions translated to
flash messages, the service layer earns its keep.

If you do introduce it, the shape is small:

```python
# app/services/listings.py
from app.clients import reverb

def load_listings(per_page=10):
    return reverb.listings(per_page=per_page)

def sort_listings(listings, order):
    ...
```

Routes import from `app.services.listings` instead of `app.clients.reverb`.
The client stays a transport-only concern.

---

## File-by-File Breakdown

### `app/__init__.py` — App Factory

```python
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

def create_app():
    app = Flask(__name__)

    from app.routes.categories import categories_bp
    from app.routes.listings import listings_bp

    app.register_blueprint(categories_bp)
    app.register_blueprint(listings_bp)
    return app
```

Things worth noting:

- **App factory pattern.** `create_app()` returns a fresh `Flask` per call —
  necessary for clean test isolation (`tests/conftest.py` builds a new app
  per fixture invocation) and standard practice for any non-trivial Flask app.
- **`load_dotenv()` at module import.** Runs once at import. Fine for dev/test;
  in production, env should already be set by the platform (Docker, systemd,
  etc.) and `.env` should not exist there.
- **Local imports inside `create_app()`.** Importing blueprints inside the
  factory avoids circular-import problems when the blueprint modules import
  back from `app.*`.
- **No config object, no logging setup, no error handlers.** All defensible
  for this scope; all would be the first things to add in a real codebase.
  Error handlers in particular tie into Scenario 5.

### `app/clients/reverb.py` — External API Client

```python
import os
import httpx

HEADERS = {"Accept": "application/json", "Accept-Version": "3.0"}
CATEGORIES_FLAT_PATH = "categories/flat"
LISTINGS_PATH = "listings"

def _get(path, params=None):
    host = os.environ["REVERB_HOST"]
    response = httpx.get(f"{host}/api/{path}", params=params or {}, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def categories():
    return _get(CATEGORIES_FLAT_PATH)["categories"]

def listings(per_page=10):
    return _get(LISTINGS_PATH, {"per_page": per_page})["listings"]
```

#### 1. `Accept` header was downgraded — note it

```python
HEADERS = {"Accept": "application/json", "Accept-Version": "3.0"}
```

The old Python and Ruby versions sent `Accept: application/hal+json`. This one
sends plain `application/json`. Reverb's API returns
[HAL](https://stateless.group/hal_specification.html) (Hypertext Application
Language) — JSON with a `_links` convention for embedded resources and
pagination. The templates still consume that shape
(`listing.photos[0]._links.thumbnail.href`), so the response is still HAL in
practice — but we're no longer *asking* for it. **Worth restoring** to make
the contract explicit:

```python
HEADERS = {"Accept": "application/hal+json", "Accept-Version": "3.0"}
```

`Accept-Version: 3.0` pins the API version — without it, Reverb could roll us
forward to a breaking version silently. This is correct.

#### 2. Mutable module-level dict

`HEADERS` is mutable. Anyone doing
`from app.clients.reverb import HEADERS; HEADERS["X"] = "Y"` mutates it for
every subsequent request — process-wide. Lock it with `MappingProxyType` for a
read-only view:

```python
from types import MappingProxyType

HEADERS = MappingProxyType({
    "Accept": "application/hal+json",
    "Accept-Version": "3.0",
})
```

Same ergonomics for the consumer; accidental mutation now fails loudly.

#### 3. `os.environ` read should stay lazy *and* centralized

```python
host = os.environ["REVERB_HOST"]
```

This is inconsistent with the other module-level constants — but **promoting
it to a constant would be worse**: it would be evaluated at import time, which
breaks test fixtures that set env vars, breaks `.env` loaders that haven't run
yet, and turns "missing config" into an opaque `ImportError` at boot.

The right move is a helper that keeps the read lazy and folds in the
hardcoded `/api/` prefix (which is part of the API contract, not config):

```python
def _base_url():
    return f"{os.environ['REVERB_HOST']}/api"

def _get(path, params=None):
    response = httpx.get(f"{_base_url()}/{path}", ...)
```

`/api/` stays in code, not in env — it doesn't vary by deploy. The host does.
If we ever needed path-rewriting proxies, we'd switch to a single
`REVERB_API_URL` env var.

#### 4. `params or {}` is dead code

`httpx.get` accepts `params=None` directly. Drop the `or {}`:

```python
response = httpx.get(..., params=params, ...)
```

The classic "mutable default argument" footgun — `def _get(path, params={})` —
doesn't apply here. The default is already `None`. The `or {}` builds a fresh
dict each call, so there's no aliasing bug. It's just noise.

#### 5. Timeout — never call an external API without one

```python
response = httpx.get(..., headers=HEADERS)
```

`httpx` defaults to a 5-second timeout, which is reasonable but **implicit**.
For a service we don't control, state it in code so the next reader doesn't
have to know httpx's defaults:

```python
response = httpx.get(..., headers=HEADERS, timeout=5.0)
```

For production, `httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=2.0)` —
each phase fails fast independently, so connect timeouts don't share a budget
with slow reads.

#### 6. Retries — flag the gap, don't over-engineer

There is no retry logic. For a take-home this is fine. Note that httpx's
built-in `HTTPTransport(retries=N)` only retries `ConnectError` — not
timeouts, not 5xx, not 429. So real retry behavior needs
[`tenacity`](https://tenacity.readthedocs.io/) or
[`stamina`](https://stamina.hynek.me/):

```python
from stamina import retry

@retry(on=httpx.HTTPError, attempts=3)
def _get(path, params=None):
    ...
```

Exponential backoff + jitter, idempotent GETs only. Worth mentioning as
"I'd add this when we see real flakiness, not pre-emptively — reflexive
retries mask transient bugs."

#### 7. `per_page` is unbounded — clamp at the boundary

```python
def listings(per_page=10):
    return _get(LISTINGS_PATH, {"per_page": per_page})["listings"]
```

Anything goes in. Reverb has a documented max (commonly 50); pass
`per_page=10000` and we get either a 4xx or a silently capped response that
surprises the caller. Also: `10` is a magic number.

```python
PER_PAGE_DEFAULT = 10
PER_PAGE_MAX = 50

def listings(per_page=PER_PAGE_DEFAULT):
    per_page = min(max(per_page, 1), PER_PAGE_MAX)
    return _get(LISTINGS_PATH, {"per_page": per_page})["listings"]
```

**Clamp silently** vs. **raise** is a defensible call either way. Clamp keeps
this a forgiving transport that documents Reverb's contract; raise would push
validation back to the route. Pick one and say why — don't waffle.

#### 8. Exception leakage — the client should own its errors

```python
response.raise_for_status()
```

When this fires, routes see `httpx.HTTPStatusError`. That's bad coupling:

- Routes now need to `import httpx` to catch errors from this client.
- Swapping `httpx` for `aiohttp` later breaks every route that catches it.
- No way to distinguish "Reverb failed" from any other httpx-based client.

Translate at the transport boundary:

```python
class ReverbError(Exception):
    """Raised for any failure talking to the Reverb API."""

def _get(path, params=None):
    try:
        response = httpx.get(...)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        raise ReverbError(f"Reverb request failed: {e}") from e
```

Routes catch `ReverbError`. The transport library becomes an implementation
detail. `from e` preserves the original traceback. **This is Scenario 5's
foundation.**

#### 9. Observability — we're blind right now

No logging. If Reverb starts returning 502s in production, we have no record
of which calls failed, how often, or how long they took. Minimum bar:

```python
import logging
log = logging.getLogger(__name__)

def _get(path, params=None):
    log.info("reverb.request", extra={"path": path, "params": params})
    try:
        response = httpx.get(...)
        response.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("reverb.error", extra={"path": path, "error": str(e)})
        raise ReverbError(...) from e
    log.info("reverb.response", extra={"path": path, "status": response.status_code})
    return response.json()
```

In production: structured logging (`structlog`) + timing metrics — request
count, latency histogram, error rate by status.

#### What we *didn't* propose, and why

- **No class.** Two stateless functions don't need encapsulation. A class
  would earn its keep if we wanted to share an `httpx.Client` (connection
  pooling, base URL config) or inject auth.
- **No async.** Routes are sync. Going async is a whole-stack decision.
- **No typed response models.** `dict` is fine for two endpoints. If this
  grew, `TypedDict` or `pydantic` would stop callers from passing dict keys
  around as strings.

### `app/routes/*.py` — Blueprints

Two blueprints, both thin Controllers. Things worth noticing:

- **Both routes call the client directly.** No service layer — see
  [above](#the-missing-service-layer).
- **`categories.index()` filters in Python.** Substring match, lowercased on
  both sides. `c.get("full_name") or ""` is a small but meaningful defense —
  if Reverb returns a category with `null` `full_name`, the filter survives.
  This pattern is missing from `_get` itself (where it matters more).
- **No input validation.** `search` is taken as-is. Harmless here (Python
  string handling is safe; the value never reaches a shell or SQL), but in a
  scenario where this becomes a URL param to the Reverb API (Scenario 2), you
  should think about length limits and stripping at minimum.
- **No error handling.** If `reverb.categories()` raises (any
  `httpx.HTTPError`), Flask returns the default 500 page. This is Scenario 5.
- **`listings.index()` is even thinner.** No filtering, no params. Just
  `render_template("listings/index.html", listings=reverb.listings())`. The
  template is doing the work.

### `app/templates/` — Jinja2 Views

```plaintext
templates/
├── layout.html
├── partials/
│   └── navigation.html
├── categories/
│   └── index.html
└── listings/
    └── index.html
```

- **`layout.html`** — base layout. Pico CSS v2 + custom CSS + HTMX 2.0 from
  CDN. HTMX is loaded but **not used yet** — it's a hook for partial-update
  scenarios (e.g., live-filter categories without a full page reload).
- **`partials/navigation.html`** — uses `url_for('categories.index')` and
  `url_for('listings.index')` (the `{blueprint}.{endpoint}` form is
  load-bearing — these break silently as text links would, but `url_for`
  raises `BuildError` immediately, which is the right failure mode).
- **`categories/index.html`** — search form (GET), conditional result list,
  explicit empty-state copy ("No categories found matching ..."). Notable:
  the search form is rendered on both empty and matched states. The list and
  empty-state are mutually exclusive and only shown after a search.
- **`listings/index.html`** — uses `{% set photo_url = listing.get("photos",
  [{}])[0].get("_links", {}).get("thumbnail", {}).get("href") %}`. This is
  **safe deep navigation** in Jinja — no `KeyError` if a listing has no
  photos. The old Python codebase crashed on missing photos; this one
  doesn't. Worth pointing out as a thing the new code got right.

Two photo-safety nuances to raise in the interview:

1. `listing.get("photos", [{}])` returns `[{}]` if `photos` is missing — but
   `[{}][0]` is `{}`, not an error. Good.
2. `listing.get("photos", [{}])[0]` will still index out of bounds if
   `photos` is an explicit `[]` (empty list). That's a real bug:
   `[].get(...)` on the result of `[][0]` → `IndexError`. Fix:

   ```jinja
   {% set photos = listing.get("photos") or [{}] %}
   {% set photo_url = photos[0].get("_links", {}).get("thumbnail", {}).get("href") %}
   ```

   `or [{}]` handles both `None` and `[]`. Tiny, but the kind of thing a
   senior dev catches at a glance.

### `app/static/css/app.css`

- Pico CSS v2 base, custom classes for `.search-hero`, `.category-card`,
  `.listing-card`, `.empty-state`, `.nav-logo-link`.
- Single grid (`auto-fill, minmax(250px, 1fr)`) → 3-column at `min-width:
  600px`. Mobile-first, no JS for layout.

### `tests/` — Test Strategy

See [TEST_WALKTHROUGH.md](TEST_WALKTHROUGH.md) for the full breakdown. The
big architectural shift vs. the old codebase: **tests now mock at the client
function boundary**, not at `httpx.get`. Route tests no longer secretly
exercise the client; client tests are now real unit tests.

---

## What's Intentionally Missing (Feature Gaps to Discuss)

| Feature | Where it would go | Priority |
| --- | --- | --- |
| `ReverbError` boundary | `app/clients/reverb.py` | High — Scenario 5 foundation |
| Explicit `timeout=` | `app/clients/reverb.py` `_get` | High — one line |
| `MappingProxyType` on `HEADERS` | `app/clients/reverb.py` | Low — defensive |
| `_base_url()` helper | `app/clients/reverb.py` | Low — consistency |
| Drop `params or {}` | `app/clients/reverb.py` | Low — cleanup |
| `per_page` clamping + constants | `app/clients/reverb.py` | Medium |
| Retry logic | `app/clients/reverb.py` (via `stamina`) | Low for take-home |
| Structured logging | `app/clients/reverb.py` | High for prod |
| Restore `application/hal+json` | `app/clients/reverb.py` `HEADERS` | Low — contract clarity |
| Service layer (`app/services/`) | New module | Medium — earns it at Scenario 5 |
| Pagination | Client + service + template | Medium |
| Listing detail page | New blueprint + client method + template | Medium |
| Input validation | Routes | Low (this app); High (if user input reaches API) |
| Photo-safety on empty `[]` | `listings/index.html` | Low — bug |
| Restore `Accept: hal+json` | `HEADERS` | Low |

---

## Architecture Considerations per Interview Scenario

The same compound-debt argument from the old walkthrough applies, just shifted.
The old version's central thesis was "listings skips the service layer." In
this version, **neither route has a service layer at all**, so every scenario
that adds business logic has the same question: do I add the helper now, or
inline it and pay the cost later?

The recommended posture is documented in
[The Missing Service Layer](#the-missing-service-layer): keep things inline
until Scenario 5 (error handling), then introduce `app/services/` to host
exception translation. The per-scenario notes below assume that posture.

### Scenario 1: Listing Detail Page

- Pure pass-through (fetch one listing by id). A `reverb.listing(id)` function
  in the client is the right shape; no service layer needed yet.
- **Template safety matters more here.** The list view has one access pattern
  (thumbnail); the detail view will deep-nav into `_links`, `condition`,
  `price`, `shop`, etc. The safe-`get` pattern from
  `templates/listings/index.html` should be the default; an unsafe
  `listing["price"]["amount"]` is a one-`KeyError` away from a 500.
- **No `ReverbError` boundary yet** — so a 404 from Reverb (listing id
  doesn't exist) currently surfaces as `httpx.HTTPStatusError`. Worth fixing
  here or in Scenario 5.

### Scenario 2: Search / Filter Listings

- This is where the **API-side vs. client-side filter** decision lives.
  Reverb's `/listings` accepts a `query` param natively. Pushing it to the
  API is architecturally cleaner and scales to large result sets; the
  client-side pattern (mirror of `categories`) only works because there are
  few categories total.
- Either way: `listings(per_page=..., query=...)` is the client signature.
  Stays in the client, no service layer needed for this alone.
- **Input validation:** if you forward `query` to the API, that's an
  untrusted string going to an external service. Length limit + strip is the
  bare minimum (the route already strips for `search` in categories).

### Scenario 3: Pagination

- **Breaking change to the client return type.** Today
  `reverb.listings()` returns just `response["listings"]`. Pagination needs
  the surrounding HAL `_links` and `total` metadata. Either return the full
  response dict and let the route extract, or return a tuple
  `(items, meta)`, or introduce a small dataclass.
- **This is also the scenario where a service helper starts paying off** —
  the route shouldn't be doing math on `current_page` / `total_pages`. Move
  pagination metadata extraction into `app/services/listings.py`.

### Scenario 4: Category -> Listings Navigation

- Connects two parallel paths. The category card becomes a link to
  `/listings?category=<slug>`. Trivial at the client level (add `category`
  param). The interesting part is the link generation in
  `templates/categories/index.html` and respecting the param in the listings
  route.
- **Input validation again** — `category` arrives in the URL and goes
  straight to the API. Same posture as Scenario 2's `query`.

### Scenario 5: Error Handling

- **The largest payoff scenario.** Three things land together:
  1. `ReverbError` in `app/clients/reverb.py` (item 8 above).
  2. `app/services/listings.py` and `app/services/categories.py` modules
     that catch `ReverbError`, log it, and return an empty result + an
     `Optional[str]` error message — or re-raise a domain exception that
     routes catch.
  3. Routes use `flask.flash()` (or a `error` template variable) to surface
     the failure in the UI.
- Templates need an error region (visible flash messages or a banner). The
  empty-state and the error-state are different UX — don't conflate them.

### Scenario 6: Price Display + Sort

- Sort is **pure business logic** — it belongs in the service layer the
  moment one exists. Inline in the route is the smell.
- Sort by `price.amount_cents` (integer), not `price.amount` (string) — avoids
  lexicographic ordering and float precision.
- Listings without prices (drafts, "Call for price") will crash `float()` /
  `int()`. The safe-`get` pattern from the template applies in the sort
  predicate too: `key=lambda l: l.get("price", {}).get("amount_cents") or 0`.

### Scenario 9: Reverb Client Improvements

This walkthrough's own [client section](#appclientsreverbpy--external-api-client)
is the canonical answer to Scenario 9. The nine items there
(`MappingProxyType`, `_base_url`, drop `params or {}`, explicit timeout,
retries gap, `per_page` clamp, `ReverbError` boundary, logging, restore
`hal+json`) are exactly what to walk through.

The interview-grade ordering:

1. **`ReverbError` + explicit timeout** — these change behavior at the
   boundary, which is where bugs and outages live.
2. **`per_page` clamp** — small, defensive, easy to demo.
3. **`_base_url()` and dropping `params or {}`** — mechanical cleanups.
4. **`MappingProxyType`, retries, logging, hal+json** — discuss as
   "in a production codebase I'd…", don't necessarily write code.

---

## Running the App

```bash
# Install dependencies (uv)
uv sync --dev

# Run server
uv run flask --app app run --debug

# Run all tests
uv run pytest -v

# Run single test file
uv run pytest -v tests/test_listings.py

# Run single test
uv run pytest -v tests/test_categories.py::test_search_matching_categories_displays_them

# Lint
uv run ruff check .
uv run ruff format .
```
