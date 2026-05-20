# Chapter 3: Flask & Python Patterns

## Flask Mental Model

"Flask is a micro-framework. Unlike Django or Rails which give you a full MVC
stack with ORM and admin panel, Flask provides a request dispatcher and a
template engine. Everything else — ORM, forms, auth — you add explicitly. This
app uses just the core: route decorators, `render_template`, and `request` for params."

---

## Key Flask Patterns (Know Cold)

### Route Definitions

```python
# Basic route
@app.route('/listings')
def listings():
    ...

# Route with URL parameter
@app.route('/listings/<listing_id>')
def listing_detail(listing_id):
    ...

# Multiple routes to same handler
@app.route('/')
@app.route('/categories')
def categories():
    ...
```

### Query String Access

```python
# Returns None if absent
request.args.get('query')

# With default + type coercion (safe — returns default on invalid input)
request.args.get('page', 1, type=int)

# Why type=int is safer than int(request.args.get('page', 1)):
# - ?page=abc → returns 1 (default) with type=int
# - ?page=abc → raises ValueError with int() cast
```

### Rendering Templates

```python
return render_template('listings.html', listings=results, page=page)
```

### Flash Messages (For Errors)

```python
from flask import flash
flash("Something went wrong")
# In template: {% for msg in get_flashed_messages() %} ... {% endfor %}
```

### Redirects

```python
from flask import redirect, url_for
return redirect(url_for('listings', category='guitars'))
```

### URL Generation

```python
# In Python code
url_for('listings', page=2)  # → /listings?page=2

# In Jinja2 templates
{{ url_for('listings', page=2) }}
```

---

## Jinja2 Template Essentials

```html
{# Variable output (auto-escaped for XSS safety) #}
{{ listing['title'] }}

{# Loop #}
{% for item in listings %}
  <li>{{ item['title'] }}</li>
{% endfor %}

{# Conditional #}
{% if listings %}
  ...
{% elif query %}
  <p>No results found.</p>
{% endif %}

{# Template inheritance #}
{% extends 'base.html' %}
{% block content %}...{% endblock %}

{# URL generation #}
<a href="{{ url_for('listings', page=2) }}">Next</a>

{# Flash messages #}
{% for msg in get_flashed_messages() %}
  <div class="alert alert-danger">{{ msg }}</div>
{% endfor %}

{# Safe filter (disable auto-escaping — use with caution) #}
{{ html_content | safe }}
```

---

## Python Gotchas in This Codebase

### 1. Mutable Default Argument

```python
# In reverb_client.py:
def _get(self, path, params={}):
```

Default `{}` is evaluated once at definition time. If anyone mutates it
(`params['key'] = value`), the mutation persists across calls.

**Safe pattern:**

```python
def _get(self, path, params=None):
    params = params or {}
```

**Interview stance:** Note it but don't refactor mid-interview unless you're
adding code that would mutate the params.

### 2. `filter()` Returns an Iterator

```python
return filter(lambda c: query.lower() in c['full_name'].lower(), categories)
```

This returns a lazy iterator, not a list. Works with Jinja2's `{% for %}`, but
`len()` would fail. If you need a list, wrap: `list(filter(...))`.

### 3. No `self` Mistakes

Common in interviews: forgetting `self` in method definitions or calls.

```python
# Wrong
def listings(per_page=10):  # missing self

# Right
def listings(self, per_page=10):
```

### 4. Import Paths for Mocking

```python
# Mock where it's USED, not where it's DEFINED
patch('reverb_client.requests.get')  # correct
patch('requests.get')                # wrong — doesn't affect reverb_client
```

---

## Python 3.8 Constraints

This codebase targets Python 3.8. Features NOT available:

| Feature | Added in | Workaround |
| --- | --- | --- |
| `dict \| dict` merge | 3.9 | `{**a, **b}` |
| `list[int]` in annotations | 3.9 | `from typing import List` |
| `str.removeprefix()` | 3.9 | `s[len(prefix):]` |
| `match` / `case` | 3.10 | `if/elif` chains |

What IS available:

- f-strings (3.6+)
- `dataclasses` (3.7+)
- Walrus operator `:=` (3.8+)
- `typing.TypedDict`, `typing.Protocol` (3.8+)

---

## Common Implementation Patterns

### Adding a New Client Method

```python
# reverb_client.py
def listing(self, listing_id):
    return self._get(f'/listings/{listing_id}')['listing']
```

### Adding a New Route

```python
# app.py
@app.route('/listings/<listing_id>')
def listing_detail(listing_id):
    listing = _load_listing(listing_id)
    return render_template('listing_detail.html', listing=listing)

def _load_listing(listing_id):
    return ReverbClient().listing(listing_id)
```

### Adding a Service Helper with Filtering

```python
def _search_listings(query):
    if not query:
        return _load_listings()
    return ReverbClient().listings(query=query)
```

### Adding Error Handling

```python
from reverb_client import ReverbClient, ApiError

@app.route('/listings')
def listings():
    try:
        results = _load_listings()
    except ApiError:
        results = []
        flash("Unable to load listings. Please try again.")
    return render_template('listings.html', listings=results)
```

### Adding Pagination

```python
@app.route('/listings')
def listings():
    page = request.args.get('page', 1, type=int)
    results, pagination = _load_listings(page=page)
    return render_template('listings.html', listings=results, **pagination)

def _load_listings(page=1):
    response = ReverbClient().listings_with_metadata(page=page)
    return response['listings'], {
        'current_page': response.get('current_page', 1),
        'total_pages': response.get('total_pages', 1),
    }
```

---

## Flask Test Client Patterns

```python
# GET with query params
res = client.get('/categories', query_string={'query': 'guitar'})

# GET with URL param (no special syntax — it's in the URL)
res = client.get('/listings/123')

# Access response
res.status_code      # 200, 404, 500...
res.data             # bytes
res.data.decode()    # string (HTML)

# Parse HTML for assertions
from tests.helpers import parse_html
html = parse_html(res)
html.body.select_one('ul.list-group').li.text
html.body.find_all('li')
html.body.h1.text
```

---

## BeautifulSoup Quick Reference (For Test Assertions)

```python
from bs4 import BeautifulSoup

html = BeautifulSoup(res.data.decode(), 'html.parser')

# CSS selector (returns first match)
html.body.select_one('ul.list-group')
html.body.select_one('li.list-group-item h2')

# CSS selector (returns all matches)
html.body.select('li.list-group-item')

# Find by tag
html.body.find_all('li')

# Get attribute
img = html.body.select_one('img')
img['src']  # → 'https://image.com'

# Get text content
html.body.select_one('h2').text  # → 'Some Cool Instrument'
```

---

## File Layout (This Repo)

```text
app.py              ← All routes + service helpers
reverb_client.py    ← API wrapper
templates/
  base.html         ← Layout (Bootstrap navbar + content block)
  categories.html   ← Search form + category list
  listings.html     ← Listing cards (thumbnail + title)
static/
  style.css         ← Custom styles
tests/
  __init__.py
  helpers.py        ← parse_html() utility
  test_categories.py
  test_listings.py
  test_reverb_client.py
Pipfile             ← Dependencies (Flask 2.2.2, requests, pytest)
```

---

## Scaling Flask (If Asked "What About 50 Routes?")

```python
# Use Blueprints
# app/categories/routes.py
from flask import Blueprint
categories_bp = Blueprint('categories', __name__)

@categories_bp.route('/categories')
def index():
    ...

# app/__init__.py
def create_app():
    app = Flask(__name__)
    app.register_blueprint(categories_bp)
    app.register_blueprint(listings_bp)
    return app
```

> "Flask doesn't give you Rails' file structure for free, but Blueprints achieve
> the same organization. Each Blueprint is a mini-app with its own routes,
> templates, and static files."
