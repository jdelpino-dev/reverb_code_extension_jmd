# Chapter 22: Quick Reference (2026 Codebase)

The 2026 reference for the Flask + `httpx` + `uv` codebase under
[web_full_stack/python_2026/](../web_full_stack/python_2026/). Mirrors
[07-quick-reference.md](07-quick-reference.md) but adapted to blueprints,
the module-level `reverb` client, and `pytest` against `app.test_client()`.

For the legacy `pipenv` + `requests` + `app.py` codebase, see
[07-quick-reference.md](07-quick-reference.md).

---

## Commands

```bash
# Install dependencies (dev + prod, creates .venv automatically)
uv sync --dev

# Run dev server (FLASK_APP=app from .devcontainer, otherwise pass --app)
uv run flask --app app run --debug

# Run all tests
uv run pytest

# Verbose + show prints + stop on first failure
uv run pytest -vxs

# Single file
uv run pytest tests/test_listings.py

# Single test
uv run pytest tests/test_categories.py::test_search_matching_categories_displays_them

# Keyword match (substring against test names)
uv run pytest -k "categories and not empty"

# Re-run only the last failures
uv run pytest --lf

# Drop into pdb on failure
uv run pytest --pdb

# Lint / format
uv run ruff check .
uv run ruff check . --fix
uv run ruff format .

# Add deps
uv add httpx
uv add --dev pytest-cov
```

---

## Live API Exploration (curl + jq)

`jq` ships on macOS via `brew install jq`. These are copy-paste ready snippets
for poking the live Reverb API during prep or mid-interview — useful for
sanity-checking response shapes before writing a client method.

Every command is split one flag per line so you can read each header,
URL, and pipe stage independently — and edit any single line without
breaking the rest.

```bash
# Categories — top-level shape
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
  | jq 'keys'
```

```bash
# First 5 category full_names + slugs
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
  | jq '.categories[:5] | map({full_name, slug})'
```

```bash
# Count categories returned
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
  | jq '.categories | length'
```

```bash
# Filter categories by substring (client-side, same logic as the route)
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
  | jq --arg q "guitar" \
      '.categories | map(select(.full_name | ascii_downcase | contains($q)))'
```

```bash
# Listings — top-level keys (pagination envelope lives here)
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=1" \
  | jq 'keys'
```

```bash
# Listing card fields (what the index template actually consumes)
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=3" \
  | jq '.listings
        | map({
            id,
            title,
            price: .price.display,
            thumb: .photos[0]._links.thumbnail.href
          })'
```

```bash
# Pagination metadata
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=10&query=fender" \
  | jq '{total, total_pages, current_page, per_page}'
```

```bash
# Search by query
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=3&query=stratocaster" \
  | jq '.listings | map(.title)'
```

```bash
# Single listing — full shape, paged through `less`
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/97706305" \
  | jq '.' \
  | less
```

```bash
# Just the photo URLs from a single listing
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/97706305" \
  | jq '.photos
        | map(._links | {
            thumbnail: .thumbnail.href,
            large: .large_crop.href
          })'
```

```bash
# Inspect HAL navigational links on a collection
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=10" \
  | jq '._links'
```

```bash
# Headers only (verify caching + Vary, sanity-check status)
curl -sI \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
  | head -20
```

```bash
# Pretty-print *and* save a snapshot for fixture-building
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
  | jq '.' \
  > /tmp/reverb-categories.json
```

Handy `jq` patterns for schema/edge-case discovery:

```bash
# Show all unique keys present across listings (catches schema drift)
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=20" \
  | jq '[.listings[] | keys[]] | unique'
```

```bash
# Count listings with empty photos arrays (edge case for the template)
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=50" \
  | jq '.listings | map(select(.photos | length == 0)) | length'
```

> Note: the in-repo client calls `/api/listings` (not `/api/listings/all`).
> Real-API exploration should use `/api/listings/all` — the endpoint
> documented by Reverb. The `/api/listings` discrepancy is worth flagging
> in [11-reverb-client-improvements-report.md](11-reverb-client-improvements-report.md).

---

## Flask Blueprint Patterns

```python
# app/__init__.py — factory + blueprint registration
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

```python
# app/routes/categories.py
from flask import Blueprint, render_template, request
from app.clients import reverb

categories_bp = Blueprint("categories", __name__)

@categories_bp.route("/")
@categories_bp.route("/categories")
def index():
    search_term = request.args.get("search", "").strip()
    matched = []
    if search_term:
        matched = [
            c for c in reverb.categories()
            if search_term.lower() in (c.get("full_name") or "").lower()
        ]
    return render_template(
        "categories/index.html",
        categories=matched,
        search_term=search_term,
    )
```

Common request helpers:

```python
request.args.get("search", "").strip()      # empty string default
request.args.get("page", 1, type=int)       # safe int coercion
request.args.getlist("category")            # repeated query params
```

---

## `httpx` Client Patterns

```python
# app/clients/reverb.py
import os
import httpx

HEADERS = {"Accept": "application/json", "Accept-Version": "3.0"}
CATEGORIES_FLAT_PATH = "categories/flat"
LISTINGS_PATH = "listings"

def _get(path, params=None):
    host = os.environ["REVERB_HOST"]
    response = httpx.get(
        f"{host}/api/{path}",
        params=params or {},
        headers=HEADERS,
    )
    response.raise_for_status()       # always — surfaces 4xx/5xx
    return response.json()

def categories():
    return _get(CATEGORIES_FLAT_PATH)["categories"]

def listings(per_page=10):
    return _get(LISTINGS_PATH, {"per_page": per_page})["listings"]
```

Worth knowing:

- `params={}` (not `None`) keeps the mock-assertion contract stable
  (`params={}` shows up explicitly in `assert_called_once_with`).
- `httpx.HTTPStatusError` (from `raise_for_status`),
  `httpx.TimeoutException`, and `httpx.ConnectError` are the three
  exceptions to catch in an error-translation layer.
- Add `timeout=5.0` to `httpx.get(...)` once a real timeout policy
  exists — `httpx` does not set one by default in this client.

---

## Jinja2 Patterns (Blueprints + Layout)

```jinja2
{# Inheritance #}
{% extends "layout.html" %}
{% block title %}Listings{% endblock %}
{% block content %}...{% endblock %}

{# Partial include #}
{% include "partials/navigation.html" %}

{# Blueprint-aware url_for (blueprint.function) #}
<a href="{{ url_for('categories.index') }}">Categories</a>
<a href="{{ url_for('listings.index') }}">Listings</a>
<link rel="stylesheet" href="{{ url_for('static', filename='css/app.css') }}">

{# Safe nested dict access — the listings card pattern #}
{% set photo_url = listing.get("photos", [{}])[0]
                          .get("_links", {})
                          .get("thumbnail", {})
                          .get("href") %}
{% if photo_url %}
  <img src="{{ photo_url }}" alt="{{ listing['title'] }}">
{% endif %}

{# Echo back search term + empty state #}
<input type="text" name="search" value="{{ search_term }}">
{% if search_term and not categories %}
  <p>No categories found matching "{{ search_term }}"</p>
{% endif %}
```

---

## Mock Patterns

```python
from unittest.mock import MagicMock, patch

# --- Route-level test: patch where the symbol is *looked up* -----------
with patch("app.routes.categories.reverb.categories", return_value=CATEGORIES):
    response = client.get("/categories?search=guitar")

# --- Client-level test: patch httpx + stub raise_for_status ------------
def make_mock_response(data, status=200):
    mock = MagicMock()
    mock.json.return_value = data
    mock.raise_for_status.return_value = None   # critical: else MagicMock raises
    mock.status_code = status
    return mock

with patch("httpx.get", return_value=make_mock_response({"categories": [...]})) as mock_get:
    reverb.categories()
    mock_get.assert_called_once_with(
        "https://api.reverb.test/api/categories/flat",
        params={},
        headers=reverb.HEADERS,
    )

# --- Error paths -------------------------------------------------------
import httpx

# 5xx upstream
with patch("httpx.get") as mock_get:
    mock_get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=MagicMock(status_code=500),
    )
    with pytest.raises(httpx.HTTPStatusError):
        reverb.categories()

# Network failure
with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
    with pytest.raises(httpx.ConnectError):
        reverb.categories()

# Timeout
with patch("httpx.get", side_effect=httpx.TimeoutException("slow")):
    with pytest.raises(httpx.TimeoutException):
        reverb.listings()
```

### `conftest.py` fixture

```python
import pytest
from app import create_app

@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

# Optional safety net — fail loud if a test forgets to patch the client
@pytest.fixture(autouse=True)
def no_real_reverb_calls(monkeypatch):
    def _boom(*a, **kw):
        raise RuntimeError(f"Unpatched httpx.get during test: {a}, {kw}")
    monkeypatch.setattr("httpx.get", _boom)

# Isolate env reads in client tests
@pytest.fixture(autouse=True)
def set_reverb_host(monkeypatch):
    monkeypatch.setenv("REVERB_HOST", "https://api.reverb.test")
```

---

## Test Assertion Style

```python
# Status first — catches template render errors
assert response.status_code == 200

# Raw byte assertions on response.data (no BeautifulSoup in this codebase)
assert b"Guitars" in response.data
assert b"Drums" not in response.data
assert b'class="category-card"' in response.data
assert b'value="guitar"' in response.data            # echoed search term
assert b"No categories found" in response.data       # empty state
```

When the byte-string approach starts to feel brittle (deep DOM checks,
multi-selector assertions), pull in BeautifulSoup as a focused helper in
`tests/helpers.py` — but do not introduce it until a test actually needs
structural querying.

---

## HTTP Status Codes

| Code | Name | When |
| --- | --- | --- |
| 200 | OK | Successful GET |
| 201 | Created | Successful POST |
| 301 | Moved Permanently | Resource relocated |
| 302 | Found | Temporary redirect |
| 400 | Bad Request | Malformed request |
| 401 | Unauthorized | Not authenticated |
| 403 | Forbidden | Authenticated but not allowed |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation failed |
| 429 | Too Many Requests | Rate limited |
| 500 | Internal Server Error | Server bug |
| 502 | Bad Gateway | Upstream failure |
| 503 | Service Unavailable | Overloaded |

---

## Architecture Decision Checklist

- [ ] **Where does it go?** Client → (Service if it earns its keep) → Route → Template
- [ ] **Two callers yet?** Don't promote to a service module until the second one appears
- [ ] **Does the client return shape change?** Update every caller + test
- [ ] **Default args** keep existing callers working (`per_page=10`)
- [ ] **Error path?** Translate `httpx` exceptions at one layer, render flash + 200/5xx
- [ ] **Empty state?** Template must handle `[]` and missing-key dict access
- [ ] **URL state?** Pagination, search, sort all belong in the query string
- [ ] **Test?** At minimum: one route happy path + one client transport assertion

---

## Implementation Order (For Any Feature)

```text
1. Client function     → app/clients/reverb.py  (transport-only)
2. Service helper      → app/services/*.py      (only when ≥2 callers / real logic)
3. Route handler       → app/routes/*.py        (parse + delegate + render)
4. Template            → app/templates/.../*.html
5. Tests               → tests/clients/ + tests/test_*.py (two mock boundaries)
```

See the "lazy introduction" framing in
[../web_full_stack/python_2026/CODE_WALKTHROUGH.md](../web_full_stack/python_2026/CODE_WALKTHROUGH.md)
for *when* a service layer earns its keep — Scenario 5 (error handling) is
the usual tipping point.

---

## Common Trade-off Answers

### "Client-side vs server-side filtering?"

> "Categories are a small, stable reference list (~hundreds of items, 24h
> CDN-cached). Fetching the full list once and filtering in Python is fine.
> For listings, server-side via the API's `query` param — pagination and
> ranking belong on the marketplace."

### "What if the API is slow?"

> "Three knobs: pass `timeout=5.0` to `httpx.get` so we fail fast; catch
> `httpx.TimeoutException` / `HTTPStatusError` / `ConnectError` in a thin
> error layer and flash a friendly message; cache the categories response
> for ~24h since it matches Reverb's own CDN policy."

### "Should you add a service layer now?"

> "Today both routes are five lines of code with no shared logic — a
> service layer would be ceremony. The moment Scenario 5 (error handling)
> or pagination metadata shows up, I'd promote the shape into
> `app/services/listings.py` so the route stays thin and the logic is
> unit-testable without going through `app.test_client()`."

### "Why patch `app.routes.categories.reverb.categories` instead of `app.clients.reverb.categories`?"

> "Patch where the symbol is looked up, not where it's defined. The route
> module imports `reverb` and resolves `reverb.categories` at call time
> against its own module namespace. Patching at the source would miss it."

### "What would you do with more time?"

> "Add `timeout=5.0`, restore `Accept: application/hal+json` to be explicit,
> introduce error translation + flash messaging, add the `autouse`
> `no_real_reverb_calls` safety net, write the three missing error-path
> tests on the client, and only then think about caching."

---

## Reverb API Reference

### Endpoints

```text
GET /api/categories/flat
  → { "categories": [{ "full_name": "Guitars", "slug": "guitars", ... }] }

GET /api/listings/all?per_page=10&query=fender&page=2
  → { "listings": [{ "id": "123", "title": "...", "price": {...}, "photos": [...] }],
      "total": 1000, "total_pages": 100, "current_page": 2, "per_page": 10,
      "_links": { "next": {...}, "prev": {...}, ... } }

GET /api/listings/{id}
  → { "id": "123", "title": "...", "description": "...",
      "price": { "amount": "1500.00", "display": "$1,500" },
      "photos": [{ "_links": { "thumbnail": {"href": "..."},
                                large_crop: {"href": "..."} } }],
      "_links": { "self": {...}, "web": {...}, ... } }
```

### Headers

```python
# In repo (note: downgraded from hal+json — see CODE_WALKTHROUGH)
HEADERS = {"Accept": "application/json", "Accept-Version": "3.0"}

# What the original Ruby/old-Python clients sent (worth restoring)
HEADERS = {
    "Accept": "application/hal+json",
    "Accept-Version": "3.0",
    "Content-Type": "application/hal+json",
}
```

`Accept` is *documentation* (Reverb ignores it and returns `hal+json`
either way), but `Accept-Version: 3.0` is load-bearing — without it the
API may roll the client to a different major version.

---

## File Layout (2026)

```text
web_full_stack/python_2026/
├── pyproject.toml             ← uv + ruff + pytest config
├── app/
│   ├── __init__.py            ← create_app() factory
│   ├── clients/
│   │   └── reverb.py          ← module-level httpx wrapper (transport only)
│   ├── routes/
│   │   ├── categories.py      ← categories_bp blueprint
│   │   └── listings.py        ← listings_bp blueprint
│   ├── templates/
│   │   ├── layout.html        ← extends-base
│   │   ├── partials/
│   │   │   └── navigation.html
│   │   ├── categories/index.html
│   │   └── listings/index.html
│   └── static/css/app.css     ← Pico CSS overrides
└── tests/
    ├── conftest.py            ← client fixture (create_app + TESTING=True)
    ├── test_categories.py     ← patches app.routes.categories.reverb.categories
    ├── test_listings.py       ← patches app.routes.listings.reverb.listings
    └── clients/
        └── test_reverb.py     ← patches httpx.get + monkeypatch.setenv
```

---

## What's Different vs the 2025 Codebase

| Concern | 2025 (`07-quick-reference.md`) | 2026 (this file) |
| --- | --- | --- |
| Dep manager | `pipenv` | `uv` |
| HTTP client | `requests` | `httpx` |
| Routes | `@app.route` in `app.py` | Blueprints in `app/routes/*.py` |
| Client | `ReverbClient` class | Module-level functions in `app/clients/reverb.py` |
| Service layer | Half-implemented helpers | Removed — inline in route (lazy intro) |
| Mock target (route) | `reverb_client.requests.get` | `app.routes.<bp>.reverb.<fn>` |
| Mock target (client) | `reverb_client.requests.get` | `httpx.get` |
| Test asserts | BeautifulSoup `parse_html(res)` | Raw `b"..." in response.data` |
| Templates | Flat `templates/*.html` | `templates/<feature>/*.html` + `partials/` |
| `url_for` | `url_for('listings')` | `url_for('listings.index')` (blueprint-qualified) |
| Lint | (none enforced) | `ruff check` + `ruff format` |
| Env loading | Manual `os.environ` | `python-dotenv` via `load_dotenv()` at import |

When the interview lands on the 2026 codebase, the muscle memory shifts are:
**`uv run` instead of `pipenv run`**, **blueprint-qualified `url_for`**,
**two mock boundaries instead of one**, and **byte-string asserts** instead
of DOM queries.
