# Chapter 16: New Codebase Stack Guide

The AI-generated hiring codebase uses a more modern, production-aligned stack than
the original friend-written version. This chapter covers everything that is new or
different so your existing prep transfers cleanly.

---

## What Changed at a Glance

| Concern | Old codebase | New codebase |
|---|---|---|
| App structure | Single `app.py` | App factory + Blueprints |
| HTTP client | `requests` (class) | `httpx` (module functions) |
| CSS framework | Bootstrap 4 (CDN) | Pico CSS v2 (CDN) + custom CSS |
| JS enhancement | None | HTMX 2 (CDN, optional) |
| Package manager | `pipenv` / `Pipfile` | `uv` / `pyproject.toml` |
| Linter | None | `ruff` |
| Service layer | Explicit (`_load_*` helpers) | Collapsed into routes |
| Query param name | `?query=` | `?search=` |
| Test fixture scope | Module-level `.start()` (leaky) | Scoped `with patch(...)` |
| `conftest.py` | None | Shared `client` fixture via factory |

---

## Flask Application Factory Pattern

### What it is

Instead of creating `app = Flask(__name__)` at module level (global), you wrap it
in a factory function. Every caller gets a fresh instance.

```python
# app/__init__.py
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)

    from app.routes.categories import categories_bp
    from app.routes.listings import listings_bp

    app.register_blueprint(categories_bp)
    app.register_blueprint(listings_bp)

    return app
```

### Why it matters

- **Testability:** `conftest.py` calls `create_app()` — each test gets a clean,
  independent app instance. No shared state leaking between tests.
- **Configuration injection:** You can pass a config object or environment name
  (`create_app('testing')`) to switch settings per environment.
- **Circular import prevention:** Blueprints are imported *inside* the factory,
  after `app` exists, so `from app import app` chains that cause circular imports
  are avoided.

### Interview script

> "The factory pattern wraps app creation in a function. The main benefit is
> testability — `conftest.py` calls `create_app()` directly, so each test gets a
> fresh instance with no shared state. It also makes configuration injection
> straightforward if we need to support multiple environments."

---

## Flask Blueprints

### What they are

A `Blueprint` is a collection of routes (and optionally static files / templates)
that you register onto an app. Think of it as a sub-router.

```python
# app/routes/categories.py
from flask import Blueprint, render_template, request
from app.clients import reverb

categories_bp = Blueprint("categories", __name__)

@categories_bp.route("/")
@categories_bp.route("/categories")
def index():
    search_term = request.args.get("search", "").strip()
    ...
    return render_template("categories/index.html", ...)
```

```python
# app/__init__.py — registration
app.register_blueprint(categories_bp)
app.register_blueprint(listings_bp)
```

### Key differences from the old codebase

| Old | New |
|---|---|
| `@app.route(...)` — routes on the global `app` | `@categories_bp.route(...)` — routes on the blueprint |
| `url_for('categories')` | `url_for('categories.index')` — **blueprint name + function name** |
| All routes in one file | Each resource in its own file under `app/routes/` |

### `url_for` with blueprints

```jinja2
{# Template: must prefix with blueprint name #}
{{ url_for('categories.index') }}
{{ url_for('listings.index') }}
```

```python
# Python code: same rule
from flask import url_for
url_for('categories.index', search='guitar')
```

Forgetting the blueprint prefix is a common bug — `url_for('index')` will raise
`BuildError` at runtime.

### Interview script

> "Blueprints let you split routes into separate modules and register them onto the
> app. The main practical difference I notice is `url_for` — you need to prefix the
> endpoint name with the blueprint name, like `categories.index`. The split also
> makes it natural to group templates by resource under `templates/categories/` and
> `templates/listings/`."

---

## `httpx` vs `requests`

The new client module (`app/clients/reverb.py`) uses `httpx` instead of `requests`.

### Side-by-side

```python
# Old — requests, class-based
import requests

class ReverbClient:
    HEADERS = {"Accept": "application/hal+json", "Accept-Version": "3.0"}

    def _get(self, path, params=None):
        if params is None:
            params = {}
        return requests.get(self._base_uri + path, headers=self.HEADERS, params=params).json()
```

```python
# New — httpx, module functions
import os
import httpx

HEADERS = {"Accept": "application/json", "Accept-Version": "3.0"}

def _get(path, params=None):
    host = os.environ["REVERB_HOST"]
    response = httpx.get(f"{host}/api/{path}", params=params or {}, headers=HEADERS)
    response.raise_for_status()   # ← raises on 4xx/5xx
    return response.json()
```

### Key differences

| | `requests` (old) | `httpx` (new) |
|---|---|---|
| API | Nearly identical for simple GET | Nearly identical for simple GET |
| Error handling | Silent — bad status returns body | `raise_for_status()` raises `httpx.HTTPStatusError` |
| Async support | No | Yes (`httpx.AsyncClient`) — same lib, async-ready |
| Base URL config | Constructor arg (`base_uri`) | Env var read at call time (`REVERB_HOST`) |
| `Accept` header value | `application/hal+json` | `application/json` |

### `raise_for_status()` — the important addition

```python
response.raise_for_status()
# Raises httpx.HTTPStatusError if status >= 400
# Has .response attribute with status code and body
```

Without this, a 429 (rate limit) or 503 (API down) would silently return the error
JSON body, which likely lacks the keys your code expects — causing a `KeyError`
downstream instead of a meaningful error at the HTTP boundary.

### Mocking `httpx` in tests

```python
from unittest.mock import MagicMock, patch
from app.clients import reverb

def make_mock_response(data):
    mock = MagicMock()
    mock.json.return_value = data
    mock.raise_for_status.return_value = None   # ← must stub this too
    return mock

def test_categories_fetches_and_returns_list():
    data = {"categories": [{"full_name": "Guitars"}]}
    with patch("httpx.get", return_value=make_mock_response(data)) as mock_get:
        result = reverb.categories()

    assert result == [{"full_name": "Guitars"}]
    mock_get.assert_called_once_with(
        "https://api.reverb.test/api/categories/flat",
        params={},
        headers=reverb.HEADERS,
    )
```

**Critical:** stub `raise_for_status` or it will raise `AttributeError` when called
on the `MagicMock`. The pattern `mock.raise_for_status.return_value = None` is
correct — it makes the call a no-op.

**Patch path:** `"httpx.get"` — because `reverb.py` calls `httpx.get` directly
(not via an alias), you patch it at the source module.

### Interview script

> "The new client uses `httpx` instead of `requests`. The API is nearly the same
> for a synchronous GET, but `httpx` adds `raise_for_status()` which makes HTTP
> errors explicit at the boundary rather than silently returning bad JSON. It's also
> async-ready if we ever need concurrent API calls. When mocking in tests, I need to
> stub `raise_for_status` as a no-op alongside `json.return_value`, and I patch
> `httpx.get` directly."

---

## Pico CSS v2

### What it is

Pico CSS is a classless (or near-classless) semantic CSS framework. It styles native
HTML elements directly — you get a clean, responsive UI by writing semantic HTML,
with no utility classes like Bootstrap's `btn btn-primary`.

```html
<!-- layout.html — loaded from CDN -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
```

### Core concept: semantic HTML = styled HTML

```html
<!-- A button — no class needed -->
<button type="submit">Search</button>

<!-- A card — uses <article> -->
<article>
  <strong>Guitars</strong>
</article>

<!-- A grid layout — use CSS Grid in app.css, not framework classes -->
<div class="listings-grid">...</div>
```

### Pico CSS built-in behaviors

| HTML element / attribute | What Pico does |
|---|---|
| `<main class="container">` | Centers content with max-width and padding |
| `<header class="container">` | Same centering for the header |
| `<nav><ul><li>` | Horizontal navigation bar automatically |
| `<article>` | Card with border, padding, border-radius |
| `<input type="text">` | Styled text input, full-width by default |
| `<button type="submit">` | Primary button style (uses CSS custom property color) |
| `<form>` | Vertical stacking with spacing |

### Pico CSS v2 vs. Bootstrap (old codebase)

| | Bootstrap 4 (old) | Pico CSS v2 (new) |
|---|---|---|
| Mental model | Utility classes on every element | Style HTML elements directly |
| A button | `<button class="btn btn-primary">` | `<button>` |
| A list group | `<ul class="list-group"><li class="list-group-item">` | `<ul><li>` or `<article>` cards |
| A form input | `<input class="form-control">` | `<input>` |
| Grid system | `.col-md-4`, `.row` | CSS Grid in your own stylesheet |
| Custom overrides | Override `.btn`, `.card` etc. | Override CSS custom properties or add classes |
| Bundle size | Large (JS + CSS) | ~10KB CSS only |

### Custom CSS in `app.css`

The new codebase adds component-specific classes on top of Pico:

```css
/* Grid layout — Pico doesn't provide a card grid */
.categories-list,
.listings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
}

/* Centered search form */
.search-form {
    max-width: 600px;
    margin: 0 auto 2rem;
}
```

The pattern is: **Pico handles typography, spacing, and base elements; `app.css`
handles layout and component-specific overrides.**

### Interview script

> "The new codebase swaps Bootstrap for Pico CSS v2, which is classless — it styles
> semantic HTML elements directly. A `<button>` gets primary button styles without
> needing `class='btn btn-primary'`. For layout (the card grid), Pico doesn't help,
> so `app.css` adds a CSS Grid rule. The template tests assert on class names like
> `class='category-card'`, so those custom classes are load-bearing for the tests."

---

## HTMX

HTMX is included in `layout.html` but not actively used yet — it's an optional
enhancement. Knowing what it is matters for the "where would you take this next?"
discussion.

```html
<script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.10/dist/htmx.min.js"
  integrity="sha384-..."
  crossorigin="anonymous"></script>
```

### What HTMX does

HTMX lets you make AJAX requests and update parts of the page using HTML attributes
instead of writing JavaScript. You add attributes to existing HTML elements.

```html
<!-- Without HTMX: full page reload on form submit -->
<form method="GET" action="/categories">
  <input type="text" name="search">
  <button>Search</button>
</form>

<!-- With HTMX: partial update, no full reload -->
<form hx-get="/categories" hx-target="#results" hx-swap="innerHTML">
  <input type="text" name="search">
  <button>Search</button>
</form>
<div id="results"></div>
```

### Key HTMX attributes

| Attribute | Meaning |
|---|---|
| `hx-get="/path"` | Make a GET request to this URL on trigger |
| `hx-post="/path"` | Make a POST request |
| `hx-target="#id"` | Replace this element with the response HTML |
| `hx-swap="innerHTML"` | How to swap: `innerHTML`, `outerHTML`, `beforeend`, etc. |
| `hx-trigger="input delay:300ms"` | Trigger on input with 300ms debounce |
| `hx-push-url="true"` | Update the browser URL bar |

### Flask + HTMX pattern

For partial updates, the Flask route returns an HTML fragment (not a full page):

```python
@categories_bp.route("/categories/results")
def results():
    search_term = request.args.get("search", "").strip()
    matched = [c for c in reverb.categories() if search_term.lower() in c["full_name"].lower()]
    # Return a partial template, not the full layout
    return render_template("categories/_results.html", categories=matched)
```

The partial template (`_results.html`) has no `{% extends "layout.html" %}` — it's
just the fragment that HTMX will swap in.

### Interview script

> "HTMX is loaded but not wired up yet. It lets you add interactivity via HTML
> attributes instead of JavaScript — for example, a live-search input that updates
> just the results `<div>` without a full page reload. On the Flask side, you'd add
> a route that returns an HTML fragment (a partial template with no layout), and
> HTMX handles the swap. It's a good next step for the search form."

---

## `uv` Package Manager

The new codebase uses `uv` instead of `pipenv`. You'll run commands from the README.

### Common commands

```bash
# Install all dependencies (including dev)
uv sync --dev

# Run the Flask dev server
uv run flask --app app run --debug

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Format code
uv run ruff format .

# Add a dependency
uv add httpx

# Add a dev dependency
uv add --dev pytest
```

### `pyproject.toml` layout

```toml
[project]
name = "hiring-code-python"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "flask>=3.1",
    "httpx>=0.28",
    "python-dotenv>=1.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.3",
    "ruff>=0.8",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]    # ← makes `from app.clients import reverb` work in tests
```

**`pythonpath = ["."]`** is the key pytest config — it adds the project root to
`sys.path` so imports like `from app.clients import reverb` resolve in tests.

---

## `ruff` Linter

`ruff` is a fast Python linter and formatter (replaces `flake8` + `isort` + `black`).

```bash
uv run ruff check .          # lint
uv run ruff check . --fix    # auto-fix safe issues
uv run ruff format .         # format (like black)
```

The project enables rule sets `E`, `F`, `I`, `UP`:

| Set | What it checks |
|---|---|
| `E` | PEP 8 style (indentation, whitespace) |
| `F` | Pyflakes (undefined names, unused imports) |
| `I` | Import order (like isort) |
| `UP` | pyupgrade — modernize syntax (e.g., `Union[X, Y]` → `X \| Y`) |

In interviews, if asked to lint: `uv run ruff check .` — not `flake8`, not `pylint`.

---

## New Test Architecture

### `conftest.py` — shared `client` fixture

```python
# tests/conftest.py
import pytest
from app import create_app

@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
```

Every test file gets this fixture automatically. No import needed — pytest discovers
`conftest.py` fixtures by convention.

### Scoped mocking (not leaky `.start()`)

```python
# Old pattern — leaky: patch stays active after test if not stopped
mock_get = patch('reverb_client.requests.get').start()

# New pattern — scoped: patch is reverted when the `with` block exits
with patch("app.routes.categories.reverb.categories", return_value=CATEGORIES):
    response = client.get("/categories?search=guitar")
```

The new code patches at the route boundary (`app.routes.categories.reverb.categories`)
rather than deep inside the client. This is higher-level mocking — tests don't care
how `reverb.categories()` makes its HTTP call, only what it returns.

### What the new tests assert

The new tests check class names in the response HTML:

```python
assert b'class="category-card"' in response.data
assert b'class="listings-grid"' in response.data
assert b'class="listing-card"' in response.data
```

These CSS class names are therefore **test-coupled** — renaming them in the template
will break tests. This is intentional: the test asserts on rendered structure, not
just text content.

### Empty-state test (new, was missing before)

```python
def test_no_matching_categories_shows_empty_state(client):
    with patch("app.routes.categories.reverb.categories", return_value=CATEGORIES):
        response = client.get("/categories?search=violin")

    assert b"No categories found" in response.data
    assert b"violin" in response.data          # echo search term back
    assert b'class="category-card"' not in response.data
```

The template must render an empty-state message and echo the search term back. The
old codebase had no test for this behavior.

---

## Jinja2 Patterns in This Codebase

### Template directory layout

```text
Old:                    New:
templates/              templates/
  base.html               layout.html
  categories.html         partials/
  listings.html             navigation.html
                          categories/
                            index.html
                          listings/
                            index.html
```

Resources get their own subdirectory. This mirrors a Rails/Django convention and
makes it natural to add more views per resource (e.g., `categories/show.html`)
without a flat namespace collision.

---

### Pattern 1 — Template inheritance (`extends` + `block`)

```jinja2
{# Child template — categories/index.html #}
{% extends "layout.html" %}

{% block title %}Category Search{% endblock %}

{% block content %}
  ... page-specific HTML ...
{% endblock %}
```

```jinja2
{# Parent template — layout.html #}
<title>{% block title %}Gear Garage{% endblock %}</title>
...
<main class="container">
  {% block content %}{% endblock %}
</main>
```

`layout.html` defines the skeleton with named `{% block %}` slots. Child templates
fill those slots with `{% extends %}` + matching `{% block %}` names. The default
value inside the parent block (`Gear Garage`) is used if no child overrides it.

Both page templates override `title` and `content`. Neither uses `{{ super() }}`
to append to the parent block — they fully replace it.

---

### Pattern 2 — Partials (`{% include %}`)

```jinja2
{# layout.html #}
<header class="container">
  {% include "partials/navigation.html" %}
</header>
```

`{% include %}` injects another template's content inline at that position.
The included file (`navigation.html`) is **not** a child template — it has no
`{% extends %}` and no `{% block %}`. It is a raw HTML fragment with Jinja2
expressions.

#### Is `partials/` a Jinja2 pattern?

No — `partials/` is **a folder naming convention**, not a Jinja2 feature. Jinja2
`{% include %}` works with any path. The `partials/` name is borrowed from Rails
(which uses `_partial.html.erb` with underscore prefix) and is widely used in
Flask projects to signal "this file is not a full page, it is a reusable fragment."

#### What `{% include %}` gives you vs. `{% extends %}`

| | `{% extends %}` | `{% include %}` |
|---|---|---|
| Purpose | Whole-page composition | Inject a reusable fragment |
| Slots / overrides | Yes (`{% block %}`) | No — included as-is |
| Context access | Inherits full template context | Inherits full template context |
| Use case | Page layout | Nav, footer, shared widgets |

The included partial has full access to the same template context as the parent.
In this codebase `navigation.html` only uses `url_for` (a Flask global), not any
route-specific variables, so it works from any page.

#### When to use `{% include %}` vs. a macro

`{% include %}` is correct for static reusable fragments (nav, footer). Use
`{% macro %}` when the fragment needs parameters:

```jinja2
{# Macro — reusable with arguments #}
{% macro category_card(category) %}
  <article class="category-card">
    <strong>{{ category["full_name"] }}</strong>
  </article>
{% endmacro %}

{{ category_card(c) }}
```

The codebase doesn't use macros — the card HTML is inlined in the `{% for %}` loop.
A macro would be the natural refactor if a card appeared in more than one template.

---

### Pattern 3 — Control flow (`if` / `elif` / `else` / `for`)

```jinja2
{# Nested if — categories page #}
{% if search_term %}
  {% if categories %}
    ...results...
  {% else %}
    ...empty state...
  {% endif %}
{% endif %}
```

```jinja2
{# Simple if — listings page #}
{% if listings %}
  ...grid...
{% else %}
  <p>No listings available at this time.</p>
{% endif %}
```

The categories template uses **nested `if`** to separate "no query entered" (show
nothing) from "query entered but no matches" (show empty state). The listings
template uses a flat `if/else` — listings are always fetched, no search involved.

Note: Jinja2 `if` tests are truthy — an empty list `[]` is falsy, so
`{% if categories %}` correctly skips the results block when the list is empty.

---

### Pattern 4 — `{% for %}` loop

```jinja2
{% for category in categories %}
  <article class="category-card">
    <strong>{{ category["full_name"] }}</strong>
  </article>
{% endfor %}
```

Standard iteration. Jinja2 also provides loop helpers that this codebase doesn't
use but are worth knowing for the interview:

| Variable | Value |
|---|---|
| `loop.index` | 1-based iteration counter |
| `loop.index0` | 0-based iteration counter |
| `loop.first` | `True` on first iteration |
| `loop.last` | `True` on last iteration |
| `loop.length` | Total number of items |

`{% for x in items %}{% else %}empty{% endfor %}` — Jinja2 `for` supports an
`{% else %}` clause that renders when the list is empty. The codebase doesn't use
this — instead it wraps the loop in `{% if categories %}`. Both are valid; the
`for/else` form is more compact.

---

### Pattern 5 — `{% set %}` local variable

```jinja2
{# listings/index.html — inside the for loop #}
{% set photo_url = listing.get("photos", [{}])[0].get("_links", {}).get("thumbnail", {}).get("href") %}
{% if photo_url %}
  <img src="{{ photo_url }}" alt="{{ listing['title'] }}">
{% endif %}
```

`{% set %}` assigns a local variable within the template. Here it's used to extract
a deeply nested value so the `{% if %}` line stays readable.

The value itself — `listing.get("photos", [{}])[0].get("_links", {}).get("thumbnail", {}).get("href")` — is significant logic: it handles the case where a listing has no photos without raising a `KeyError`. The chain works by defaulting to an empty dict `{}` at each level so `.get()` is always called on a dict, never on `None`.

**Interview flag:** This is the most logic-heavy line in any template. The
alternative would be to move this extraction to the route:

```python
# In listings.index() — cleaner template, testable logic
def index():
    raw = reverb.listings()
    listings = [
        {**l, "thumbnail": _extract_thumbnail(l)}
        for l in raw
    ]
    return render_template("listings/index.html", listings=listings)

def _extract_thumbnail(listing):
    return (listing.get("photos") or [{}])[0].get("_links", {}).get("thumbnail", {}).get("href")
```

Whether to do this in the template or the route is a good trade-off discussion.
The current approach (in template) keeps the route thin; the alternative makes
the logic testable in isolation.

---

### Pattern 6 — `{{ url_for() }}` in templates

```jinja2
{# Generating a URL for a blueprint endpoint #}
<form method="GET" action="{{ url_for('categories.index') }}">

{# Generating a URL for a static file #}
<link rel="stylesheet" href="{{ url_for('static', filename='css/app.css') }}">

{# Navigation links #}
<a href="{{ url_for('categories.index') }}">Categories</a>
<a href="{{ url_for('listings.index') }}">Listings</a>
```

`url_for` is a Flask function injected into every template context automatically —
no import or explicit passing needed. Key rules:

- Blueprint endpoints: `'blueprint_name.function_name'`
- Static files: `url_for('static', filename='path/relative/to/static/')`
- Query string params: `url_for('categories.index', search='guitar')` → `/categories?search=guitar`

---

### Pattern 7 — Variable output and dict access

Two syntaxes are used across the templates:

```jinja2
{# Bracket notation — raises UndefinedError if key missing #}
{{ category["full_name"] }}
{{ listing["title"] }}

{# Attribute/method notation — safe default via .get() #}
listing.get("photos", [{}])
(c.get("full_name") or "").lower()   {# ← in route, not template #}
```

#### The inconsistency

Categories template uses `category["full_name"]` — bracket notation, which raises
`UndefinedError` if the key is absent. The route's filter uses
`(c.get("full_name") or "")` — safe `.get()`. These are inconsistent.

Listings template uses `listing["title"]` for the title but the chained `.get()`
for photos. Two styles within the same template.

In Jinja2, `category["full_name"]` and `category.full_name` are treated the same —
Jinja2 tries attribute access first, then item access. Both raise `Undefined` (which
renders as an empty string in non-strict mode, but raises in strict mode). The `.get()`
pattern is explicitly safe and is the better choice for external API data where key
presence can't be guaranteed.

#### Consistent safe access would look like

```jinja2
{# Consistent — safe for external API data #}
{{ category.get("full_name", "Unknown") }}
{{ listing.get("title", "Untitled") }}
```

---

### Inconsistencies Summary

| Location | Issue | Severity |
|---|---|---|
| `categories/index.html` | `category["full_name"]` — bracket notation, no safe default | Low (key is always present in practice, but risky for external API) |
| `listings/index.html` | `listing["title"]` bracket vs. `.get()` chain for photos — mixed in same file | Low |
| `listings/index.html` | `{% set %}` contains complex logic that belongs in the route | Medium — hard to test in isolation |
| `listings/index.html` | `<b>` instead of `<strong>` for the title | Low — semantic only |
| Both page templates | Two hero class names (`.search-hero`, `.examples-hero`) for identical styles | Low — AI generation artifact |
| `categories/index.html` | `<input type="submit">` instead of `<button type="submit">` | Low — legacy HTML pattern |

---

### Interview script

> "The templates follow Flask's standard inheritance model — `layout.html` defines
> the skeleton with `{% block %}` slots, page templates fill them with `{% extends %}`.
> The navigation is pulled in with `{% include %}` — the `partials/` folder is a
> naming convention borrowed from Rails, not a Jinja2 feature. The most interesting
> line is the photo URL extraction in the listings template: it chains `.get()` with
> empty-dict defaults to safely navigate the nested API structure without raising.
> That logic is arguably better placed in the route where it's testable, which is
> a clean refactor to offer. I'd also standardize dict access — `category["full_name"]`
> and `listing["title"]` use bracket notation while the photos use `.get()`, and for
> external API data I'd use `.get()` consistently."

---

## Collapsed Service Layer — Interview Discussion

The new codebase has **no service layer**. Routes call `reverb.categories()` directly.

```python
# New — route calls client directly
@categories_bp.route("/categories")
def index():
    search_term = request.args.get("search", "").strip()
    matched_categories = [
        c for c in reverb.categories()
        if search_term.lower() in (c.get("full_name") or "").lower()
    ]
    return render_template("categories/index.html", categories=matched_categories, ...)
```

### When to add the service layer back

The service layer becomes necessary when:

- **Pagination:** `reverb.listings(page=page, per_page=20)` — pagination logic
  doesn't belong in the route or client.
- **Caching:** Cache the categories response (they rarely change) — caching logic
  belongs in a service, not a route.
- **Combining data:** A dashboard route that calls `reverb.categories()` and
  `reverb.listings()` and assembles a combined result.
- **Business rules:** "Filter out categories with fewer than 5 listings" — that's
  app logic, not HTTP logic.

### Interview script

> "The service layer is collapsed in this version — the route does the filtering
> inline. That's fine for the current scope. If I were adding pagination or caching,
> I'd extract a `_load_categories()` helper in the route module, or a dedicated
> `services/categories.py` file, to keep the route thin and the logic testable in
> isolation."

---

## Pre-Interview Checklist (New Codebase)

- [ ] Can run `uv sync --dev` and `uv run pytest` without thinking
- [ ] Know the difference: `url_for('categories.index')` vs old `url_for('categories')`
- [ ] Can explain the factory pattern and why `conftest.py` uses `create_app()`
- [ ] Know why `raise_for_status()` is important and how to stub it in tests
- [ ] Can name what Pico CSS does vs. what `app.css` adds on top
- [ ] Can describe what HTMX does and where it would hook into this app
- [ ] Know the patch path: `"app.routes.categories.reverb.categories"` (not `"httpx.get"` for route tests)
- [ ] Know `pythonpath = ["."]` in `pyproject.toml` makes test imports work
- [ ] Can add a new Blueprint route + template + test from scratch
