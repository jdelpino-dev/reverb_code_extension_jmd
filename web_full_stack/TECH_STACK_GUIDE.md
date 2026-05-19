# Tech Stack Guide — Python/Flask Web App

## Resolved Versions (from Pipfile.lock)

| Package | Version | Role |
| -- | -- | -- |
| Python | 3.8 | Runtime (EOL: Oct 2024) |
| Flask | 2.2.2 | Web framework |
| Werkzeug | 2.3.8 | WSGI toolkit (Flask's HTTP layer) |
| Jinja2 | 3.1.6 | Template engine |
| requests | 2.25.1 | HTTP client for Reverb API |
| urllib3 | 1.26.20 | Transport layer for requests |
| MarkupSafe | 2.1.5 | Jinja2 auto-escaping |
| click | 8.1.8 | Flask CLI |
| itsdangerous | 2.2.0 | Session signing |
| python-dotenv | 0.15.0 | `.env` file loading |
| BeautifulSoup4 | 4.14.3 | HTML parsing in tests |
| pytest | 8.3.5 | Test runner |

---

## Python 3.8 Gotchas

Python 3.8 reached **end-of-life in October 2024** — no security patches.

### Language features NOT available (added in 3.9+)

| Feature | Added in | What you can't do |
| -- | -- | -- |
| `dict \| dict` merge operator | 3.9 | Must use `{**a, **b}` |
| `list[int]`, `dict[str, int]` in annotations | 3.9 | Must use `from typing import List, Dict` |
| `str.removeprefix()` / `str.removesuffix()` | 3.9 | Must slice manually |
| `match` / `case` (structural pattern matching) | 3.10 | Use `if/elif` chains |
| `ExceptionGroup` / `except*` | 3.11 | Not available |
| `tomllib` (stdlib TOML parsing) | 3.11 | Need third-party `tomli` |
| `Self` type | 3.11 | Use string annotation `"ClassName"` |
| Type parameter syntax `def foo[T](...)` | 3.12 | Use `TypeVar` |

### What IS available in 3.8

- Walrus operator `:=` (3.8+)
- `f-strings` (3.6+)
- `dataclasses` (3.7+)
- `typing.TypedDict`, `typing.Protocol` (3.8+)
- `functools.cached_property` (3.8+)
- Positional-only parameters with `/` (3.8+)

### Practical impact for this codebase

```python
# Can't do this (3.9+):
params: dict[str, str] = {}

# Must do this:
from typing import Dict
params: Dict[str, str] = {}

# Can't do this (3.9+):
merged = defaults | overrides

# Must do this:
merged = {**defaults, **overrides}
```

---

## Flask 2.2.2 Gotchas

### Key differences from Flask 3.x

| Flask 2.2 behavior | Flask 3.x change |
| -- | -- |
| `app.run(debug=True)` or `FLASK_DEBUG=1` | Same, but 3.x removed `FLASK_ENV` |
| `@app.before_first_request` available | **Removed** in 3.0 |
| `flask.json.jsonify` | Still works, but 3.x prefers returning dicts directly |
| `app.config.from_envvar()` | Still works |
| Requires `FLASK_APP` env var for CLI | Same |

### Things to know

1. **`--reload` flag** — use `flask run --reload` (not `--debugger`); the Pipfile README uses this correctly
2. **No async views** — Flask 2.2 supports `async def` routes only with `pip install flask[async]` (not installed here)
3. **`url_for()` in templates** — requires active request context; works fine in Jinja2 but will fail if called outside a request (e.g., in CLI commands without `app.test_request_context()`)
4. **Test client** — `app.test_client()` returns responses with `.data` (bytes), not `.text`; hence the `res.data.decode()` in the test helper
5. **No built-in CORS** — need `flask-cors` if adding JSON API endpoints for a frontend

### `FLASK_APP` and `.env`

The `.env` file (loaded by `python-dotenv`) sets `FLASK_APP=app.py`. Without it, `flask run` won't know which module to load. This is why the server log shows "Loading .env environment variables..."

---

## Werkzeug 2.3.8 Gotchas

Werkzeug is Flask's WSGI layer — you interact with it indirectly.

| Gotcha | Detail |
| -- | -- |
| Pinned below 3.0 | The Pipfile has `werkzeug = "<3.0"` because Flask 2.2 is incompatible with Werkzeug 3.x |
| Debugger PIN | Shown on startup; required to use the interactive debugger in-browser |
| `request.args` returns `ImmutableMultiDict` | `.get()` returns `None` (not KeyError) for missing keys — safe |
| URL routing is strict on trailing slashes | `/categories` and `/categories/` are different routes by default |

---

## Jinja2 3.1.6 Gotchas

### Auto-escaping

Jinja2 **auto-escapes HTML by default** when used with Flask. This means `{{ user_input }}` is safe from XSS — the output is escaped. To render raw HTML, you'd need `{{ content | safe }}` (not used in this codebase).

### Template gotchas specific to this codebase

```jinja
{# This will crash if listing has no photos: #}
{{ listing['photos'][0]['_links']['thumbnail']['href'] }}

{# Safe alternative: #}
{{ listing.get('photos', [{}])[0].get('_links', {}).get('thumbnail', {}).get('href', '') }}

{# Or better — use a default filter: #}
{% set photo_url = listing['photos'][0]['_links']['thumbnail']['href'] if listing.get('photos') else '' %}
```

### Jinja2 filters available (useful for scenarios)

| Filter | Syntax | Example | Use case |
| -- | -- | -- | -- |
| `default` | `default('N/A')` | `{{ price \| default('N/A') }}` | Fallback for missing data |
| `truncate` | `truncate(50)` | `{{ title \| truncate(50) }}` | Long listing titles |
| `sort` | `sort(attribute='name')` | `{% for c in categories \| sort(attribute='full_name') %}` | Client-side sorting |
| `length` | `length` | `{{ items \| length }}` | Count items in template |
| `tojson` | `tojson` | `{{ data \| tojson }}` | Embed data as JSON in `<script>` |
| `urlencode` | `urlencode` | `{{ query \| urlencode }}` | Safe URL params |

### Template inheritance (used here)

```plaintext
base.html         → defines {% block content %}
categories.html   → {% extends 'base.html' %} + {% block content %}...{% endblock %}
listings.html     → same pattern
```

Only **one level** of inheritance is used. You can add more blocks (e.g., `{% block title %}`) to `base.html` if needed for a scenario.

---

## requests 2.25.1 Gotchas

### Key behaviors

| Behavior | Detail |
| -- | -- |
| No default timeout | `requests.get(url)` will block **forever** if the server doesn't respond |
| `.json()` raises `ValueError` on non-JSON | If Reverb returns HTML error page, `.json()` explodes |
| `.raise_for_status()` not called | 4xx/5xx responses are silently returned as normal Response objects |
| Connection pooling | `requests.get()` creates a new session each time; use `requests.Session()` for reuse |
| `params={}` mutable default | Shared dict across calls — can leak state (this bug exists in the codebase) |

### Common patterns for the interview scenarios

```python
# Adding timeout (Scenario 5: Error Handling)
requests.get(url, timeout=5)

# Checking status
response = requests.get(url, timeout=5)
response.raise_for_status()  # raises HTTPError on 4xx/5xx
return response.json()

# Retry with backoff
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503])
session.mount('https://', HTTPAdapter(max_retries=retry))
```

### Version-specific notes (2.25.1 vs current 2.32+)

| 2.25.1 behavior | Modern requests (2.28+) |
| -- | -- |
| Uses `chardet` for encoding detection | Switched to `charset-normalizer` |
| `urllib3` 1.x only | Supports `urllib3` 2.x |
| No `json` param validation | Stricter JSON serialization |

The `chardet` dependency in the lockfile confirms this is the older behavior.

---

## pytest 8.3.5 — Patterns Used

### How mocking works in this codebase

```python
from unittest.mock import patch

# Start a patch (returns the mock object)
mock_get = patch('reverb_client.requests.get').start()

# Configure what .json() returns
mock_get.return_value.json.return_value = {'categories': [...]}
```

**Important**: The patch target is `'reverb_client.requests.get'` — patching where the module is **looked up**, not where it's defined. This is the correct `unittest.mock` pattern.

### Gotcha: `patch().start()` without cleanup

The test files call `.start()` but never `.stop()`. This works because pytest creates a new module import context per test session, but it's fragile. Better patterns:

```python
# Option A: decorator (auto-stops after test)
@patch('reverb_client.requests.get')
def test_something(mock_get):
    ...

# Option B: context manager
with patch('reverb_client.requests.get') as mock_get:
    ...

# Option C: fixture with cleanup
@pytest.fixture(autouse=True)
def mock_api():
    with patch('reverb_client.requests.get') as mock_get:
        yield mock_get
```

### pytest features useful for scenarios

| Feature | Syntax | Use case |
| -- | -- | -- |
| Parametrize | `@pytest.mark.parametrize('query,expected', [...])` | Test multiple filter inputs |
| Fixtures with params | `@pytest.fixture(params=[...])` | Test against different API responses |
| `raises` context | `with pytest.raises(ConnectionError):` | Error handling tests |
| `tmp_path` fixture | Built-in | If you need temp files |
| `monkeypatch` | `monkeypatch.setenv('KEY', 'val')` | Override env vars |

---

## BeautifulSoup 4 — Test Assertions

The test helper:

```python
from bs4 import BeautifulSoup

def parse_html(res):
    return BeautifulSoup(res.data.decode(), 'html.parser')
```

### Useful selectors for writing new test assertions

```python
html = parse_html(res)

# CSS selectors
html.select('ul.list-group li')          # all list items
html.select_one('h2.title')              # first match
html.select('a[href*="listings"]')       # links containing "listings"

# Find methods
html.find('p', class_='error')           # by class
html.find('input', {'name': 'query'})    # by attribute
html.find_all('img')                     # all images

# Text content
element.text          # inner text (stripped of tags)
element.get_text(strip=True)  # same but trimmed
element['href']       # attribute access
element.get('src')    # safe attribute access (returns None)
```

---

## Bootstrap 4.1.1 — Frontend

The templates use Bootstrap 4 via CDN with an integrity hash. Key classes in use:

| Class | Where | Purpose |
| -- | -- | -- |
| `navbar`, `navbar-expand-lg` | `base.html` | Top navigation |
| `container` | `base.html` | Centered content column |
| `list-group`, `list-group-item` | Both templates | Styled lists |
| `d-flex`, `flex-row`, `align-items-center` | `listings.html` | Flexbox layout for listing cards |
| `form-group`, `form-control`, `btn-primary` | `categories.html` | Form styling |

### Bootstrap 4 vs 5 differences (in case you instinctively write BS5)

| Bootstrap 4 | Bootstrap 5 |
| -- | -- |
| `ml-3`, `mr-3` | `ms-3`, `me-3` |
| `float-left`, `float-right` | `float-start`, `float-end` |
| `data-toggle` | `data-bs-toggle` |
| jQuery required for JS components | No jQuery |
| `badge-pill` | `rounded-pill` |

---

## Quick Reference: What to Import

```python
# Flask
from flask import Flask, request, render_template, redirect, url_for, abort, jsonify

# HTTP client
import requests

# Testing
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from tests.helpers import parse_html

# Typing (3.8-compatible)
from typing import List, Dict, Optional, Any
```

---

## Environment Setup Summary

```sh
# Install dependencies
pipenv install

# Run server (with auto-reload)
pipenv run flask run --reload

# Run tests
pipenv run pytest -vs

# The .env file sets:
# FLASK_APP=app.py
# FLASK_DEBUG=1 (assumed)
```
