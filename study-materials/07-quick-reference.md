# Chapter 7: Quick Reference

## Commands

```bash
# Run server
pipenv run flask run --reload

# Run all tests (verbose, show prints)
pipenv run pytest -vs

# Run single file
pipenv run pytest -vs tests/test_listings.py

# Run single test
pipenv run pytest -vs tests/test_categories.py::test_displays_full_name_of_matching_categories

# Keyword match
pipenv run pytest -k "categories"

# Stop on first failure + verbose + prints
pipenv run pytest -vxs

# Last failed only
pipenv run pytest --lf

# Drop into debugger on failure
pipenv run pytest --pdb

# Quick API check
curl -s -H "Accept: application/json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/listings/all?per_page=1" | python3 -m json.tool | head -50

# Categories API
curl -s -H "Accept: application/json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/categories/flat" | python3 -m json.tool | head -30
```

---

## Flask Patterns

```python
# Route with URL param
@app.route('/listings/<listing_id>')
def listing_detail(listing_id):
    ...

# Query string (safe — returns default on invalid)
request.args.get('page', 1, type=int)
request.args.get('query')  # None if absent

# Render template
return render_template('listings.html', listings=results, page=page)

# Redirect
return redirect(url_for('listings', category='guitars'))

# Flash message
flash("Something went wrong")
```

---

## Jinja2 Patterns

```html
<!-- Variable (auto-escaped) -->
{{ listing['title'] }}

<!-- Loop -->
{% for item in listings %}
  <li>{{ item['title'] }}</li>
{% endfor %}

<!-- Conditional -->
{% if listings %}...{% elif query %}...{% else %}...{% endif %}

<!-- Inheritance -->
{% extends 'base.html' %}
{% block content %}...{% endblock %}

<!-- URL generation -->
{{ url_for('listings', page=2) }}

<!-- Flash messages -->
{% for msg in get_flashed_messages() %}
  <div class="alert alert-danger">{{ msg }}</div>
{% endfor %}
```

---

## Mock Patterns

```python
from unittest.mock import patch

# Basic mock setup
mock_get = patch('reverb_client.requests.get').start()
mock_get.return_value.json.return_value = {'listings': [...]}

# Decorator (auto-cleanup)
@patch('reverb_client.requests.get')
def test_something(mock_get):
    mock_get.return_value.json.return_value = {...}

# Context manager (auto-cleanup)
with patch('reverb_client.requests.get') as mock_get:
    mock_get.return_value.json.return_value = {...}

# Assert what was called
mock_get.assert_called_once_with(
    'https://api.reverb.com/api/listings/all',
    headers=ReverbClient.HEADERS,
    params={'per_page': 10},
)

# Mock an error
mock_get.return_value.ok = False
mock_get.return_value.status_code = 500

# Mock a network error
mock_get.side_effect = ConnectionError("Connection refused")
```

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

When implementing a feature, consider:

- [ ] **Where does it go?** Client → Service → Route → Template
- [ ] **Does it break existing callers?** Default args preserve compatibility
- [ ] **Is the return type changing?** Update all callers + tests
- [ ] **Do I need a service boundary?** If there's business logic, yes
- [ ] **Error path?** What happens when the API fails?
- [ ] **Empty state?** What renders when there's no data?
- [ ] **URL state?** Should filters/pages be in the URL?
- [ ] **Test?** At minimum: one happy path integration test

---

## Implementation Order (For Any Feature)

```text
1. API Client method (new endpoint access)
2. Service helper (business logic)
3. Route handler (wire up)
4. Template (render)
5. Test (verify)
```

---

## Common Trade-off Answers

### "Client-side vs server-side filtering?"

> "For small datasets (categories), client-side is fine — instant response.
> For large datasets (listings), server-side using the API's query param — scales
> and has better relevance ranking."

### "What if the API is slow?"

> "Three layers: timeout on requests.get (fail fast), try/except with graceful
> degradation (show error message), and long-term caching for rarely-changing data."

### "Should you fix the mutable default?"

> "It's not causing bugs today since the dict is never mutated. I'd fix it if I'm
> adding code that modifies params, but I won't refactor mid-interview unprompted."

### "How would you add pagination?"

> "Client method takes a page param, returns full response (not just listings list)
> for metadata. Service helper extracts page info. Template gets prev/next controls.
> URL carries page state for shareable links."

### "What would you do with more time?"

> "Error handling first (biggest user impact), then empty states (UX), then
> caching for categories (performance). I wouldn't touch architectural refactoring
> unless the feature demanded it."

---

## Reverb API Reference

### Endpoints Used

```text
GET /api/categories/flat
  → { "categories": [{ "full_name": "Guitars", "slug": "guitars", ... }] }

GET /api/listings/all?per_page=10&query=fender&page=2
  → { "listings": [{ "id": "123", "title": "...", "price": {...}, "photos": [...] }],
      "current_page": 2, "total_pages": 50, "total": 1000 }

GET /api/listings/{id}
  → { "listing": { "id": "123", "title": "...", "description": "...",
                    "price": { "amount": "1500.00", "display": "$1,500" },
                    "photos": [{ "_links": { "thumbnail": { "href": "..." },
                                             "large_crop": { "href": "..." } } }] } }
```

### Headers Required

```python
HEADERS = {
    'Accept': 'application/json',
    'Accept-Version': '3.0',
    'Content-Type': 'application/hal+json'
}
```

---

## File Layout

```text
app.py              ← Routes + service helpers (THE entry point)
reverb_client.py    ← API client (THE external boundary)
templates/
  base.html         ← Layout (navbar + block)
  categories.html   ← Search form + list
  listings.html     ← Listing cards
tests/
  helpers.py        ← parse_html()
  test_categories.py
  test_listings.py
  test_reverb_client.py
Pipfile             ← Dependencies
```

---

## BeautifulSoup Assertions

```python
html = parse_html(res)

# First match by CSS selector
html.body.select_one('ul.list-group').li.text

# All matches
html.body.select('li.list-group-item')

# Attribute access
html.body.select_one('img')['src']

# Check text content
assert 'Guitar' in html.body.h1.text

# Check absence
assert len(html.body.find_all('ul.list-group')) == 0
```

---

## New Codebase Quick Reference (June 2026)

Use these alongside the old-codebase commands above. Pick the right set
depending on which codebase the interview lands in.

### Commands

```bash
# Install dependencies (dev + prod)
uv sync --dev

# Run the dev server
uv run flask --app app run --debug

# Run all tests
uv run pytest

# Run one test
uv run pytest tests/test_categories.py::test_search_matching_categories_displays_them

# Lint / format
uv run ruff check .
uv run ruff check . --fix
uv run ruff format .

# Add a dependency
uv add httpx
uv add --dev pytest
```

### Flask Blueprint patterns

```python
# app/__init__.py
def create_app():
    app = Flask(__name__)
    from app.routes.categories import categories_bp
    app.register_blueprint(categories_bp)
    return app

# app/routes/categories.py
categories_bp = Blueprint("categories", __name__)

@categories_bp.route("/categories")
def index():
    return render_template("categories/index.html", ...)
```

### `url_for` with Blueprints

```jinja2
{{ url_for('categories.index') }}                 {# blueprint.function #}
{{ url_for('listings.index', page=2) }}
{{ url_for('static', filename='css/app.css') }}
```

### `httpx` client patterns

```python
import os, httpx

HEADERS = {"Accept": "application/json", "Accept-Version": "3.0"}

def _get(path, params=None):
    host = os.environ["REVERB_HOST"]
    response = httpx.get(f"{host}/api/{path}", params=params or {}, headers=HEADERS)
    response.raise_for_status()    # ← always
    return response.json()
```

### Mock patterns (new codebase)

```python
# Route-level test — patch at the route boundary
with patch("app.routes.categories.reverb.categories", return_value=CATEGORIES):
    response = client.get("/categories?search=guitar")

# Client-level test — patch httpx + stub raise_for_status
def make_mock_response(data):
    mock = MagicMock()
    mock.json.return_value = data
    mock.raise_for_status.return_value = None    # ← critical
    return mock

with patch("httpx.get", return_value=make_mock_response({"categories": [...]})) as mock_get:
    reverb.categories()
    mock_get.assert_called_once_with(
        "https://api.reverb.test/api/categories/flat",
        params={}, headers=reverb.HEADERS,
    )
```

### Test assertion style

```python
# New codebase — raw byte assertions on response.data
assert response.status_code == 200
assert b"Guitars" in response.data
assert b'class="category-card"' in response.data
assert b'value="guitar"' in response.data       # echoed search term
```

### Jinja2 patterns specific to the new templates

```jinja2
{# Template inheritance #}
{% extends "layout.html" %}
{% block title %}Category Search{% endblock %}
{% block content %}...{% endblock %}

{# Partial include #}
{% include "partials/navigation.html" %}

{# Safe nested dict access (listings template pattern) #}
{% set photo_url = listing.get("photos", [{}])[0].get("_links", {}).get("thumbnail", {}).get("href") %}
{% if photo_url %}
  <img src="{{ photo_url }}" alt="{{ listing['title'] }}">
{% endif %}
```

### Pico CSS one-liners

```html
<button aria-busy="true">Searching…</button>          <!-- spinner -->
<input aria-invalid="true">                            <!-- red validation -->
<button data-tooltip="Hint">?</button>                 <!-- tooltip -->
<fieldset role="group">                                <!-- joined input bar -->
<details><summary>Show more</summary>...</details>     <!-- disclosure -->
<details name="x">...</details>                        <!-- accordion (1 open) -->
<details class="dropdown"><summary>Sort</summary><ul>...</ul></details>
<nav aria-label="breadcrumb">                          <!-- breadcrumb styling -->
```

### `data-*` / `.dataset` quick patterns

```html
<details data-disclosure data-label-closed="More" data-label-open="Less">
```

```javascript
document.querySelectorAll("[data-disclosure]").forEach(d => {
  const open = d.dataset.labelOpen;
  const closed = d.dataset.labelClosed;
  d.addEventListener("toggle", () => {
    d.querySelector("summary").textContent = d.open ? open : closed;
  });
});
```

See Chapters [16](16-new-codebase-stack-guide.md) (full stack guide),
[18](18-pico-css-guide.md) (Pico toolkit), and
[19](19-data-attributes-and-dataset.md) (data-attributes deep dive).
