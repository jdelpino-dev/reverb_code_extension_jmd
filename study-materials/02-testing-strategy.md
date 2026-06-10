# Chapter 2: Testing Strategy

## Test Architecture Summary

```text
test_categories.py ──┐
test_listings.py ────┼──→ patch('reverb_client.requests.get') → Mock
test_reverb_client.py┘
```

All tests mock at the same level: `requests.get` inside `reverb_client.py`.
Even the "unit" tests for `ReverbClient` exercise real parsing logic — they're
thin integration tests that stop at the HTTP boundary.

| File | Scope | What it proves |
| --- | --- | --- |
| `test_reverb_client.py` | Client class in isolation | JSON key extraction works |
| `test_listings.py` | Full route → client → template | Listing data renders in HTML |
| `test_categories.py` | Full route → service → client → template | Filter logic + rendering |
| `helpers.py` | Utility | `parse_html()` wraps BeautifulSoup |

---

## How the Mock Chain Works

```python
mock_get = patch('reverb_client.requests.get').start()
mock_get.return_value.json.return_value = {'categories': [...]}
```

Parse the chain:

1. `patch('reverb_client.requests.get')` — replaces `requests.get` *as imported in reverb_client module*
2. `.start()` — activates the patch, returns a `MagicMock`
3. `mock_get.return_value` — what `requests.get(...)` returns (a mock Response)
4. `.json.return_value` — what `response.json()` returns (your dict)

**The path string matters:** It's `'reverb_client.requests.get'` (where it's used), not `'requests.get'` (where it's defined).

---

## Current Test Patterns

### Integration Test (Route Level)

```python
@pytest.fixture
def client():
    app.config['TESTING'] = True
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'categories': [
            {'full_name': 'Guitars'},
            {'full_name': 'Geetars'},
        ],
    }
    with app.test_client() as client:
        yield client

def test_displays_full_name_of_matching_categories(client):
    res = client.get('/categories', query_string={'query': 'guitar'})
    html = parse_html(res)
    assert 'Guitars' in html.body.select_one('ul.list-group').li.text
```

### Unit Test (Client Level)

```python
def test_fetches_categories():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'categories': [{'full_name': 'Guitars'}, {'full_name': 'Geetars'}],
    }
    categories = ReverbClient().categories()
    assert len(categories) == 2
```

---

## Issues Worth Knowing (Don't Fix Unprompted — Discuss If Asked)

### 1. `patch().start()` Without `stop()` — Mock Leakage

Every test file uses `.start()` but never calls `.stop()`. Works because tests
patch the same target, but would break if you add a test that doesn't mock.

**Correct patterns:**

```python
# Context manager (auto-stops)
with patch('reverb_client.requests.get') as mock_get:
    mock_get.return_value.json.return_value = {...}
    result = ReverbClient().categories()

# Decorator (auto-stops)
@patch('reverb_client.requests.get')
def test_fetches_categories(mock_get):
    mock_get.return_value.json.return_value = {...}

# Fixture with proper teardown
@pytest.fixture
def mock_api():
    patcher = patch('reverb_client.requests.get')
    mock_get = patcher.start()
    yield mock_get
    patcher.stop()
```

### 2. Fixture Doesn't Expose the Mock

The `client` fixture yields only the Flask test client. Individual tests cannot
customize the mock response for edge cases.

**Better pattern:**

```python
@pytest.fixture
def mock_api():
    patcher = patch('reverb_client.requests.get')
    mock_get = patcher.start()
    yield mock_get
    patcher.stop()

@pytest.fixture
def client(mock_api):
    app.config['TESTING'] = True
    mock_api.return_value.json.return_value = {'categories': [...]}
    with app.test_client() as client:
        yield client

def test_empty_categories(client, mock_api):
    mock_api.return_value.json.return_value = {'categories': []}
    res = client.get('/categories', query_string={'query': 'guitar'})
    # Now we can test the empty state
```

### 3. No Status Code Assertion

Tests jump straight to HTML assertions without checking `res.status_code == 200`.
If the route raises, Flask returns a 500 traceback — test fails with a confusing
BeautifulSoup error instead of a clear status assertion.

### 4. No Param/URL Assertions on Client Tests

`test_reverb_client.py` verifies returned data but not that the correct URL or
params were sent. Add `mock_get.assert_called_once_with(...)` for confidence.

---

## What's NOT Tested

- Error responses (API returns 500, timeout, malformed JSON)
- Empty states (no listings returned, no photos on a listing)
- Pagination behavior
- The `_search_categories` filter logic in isolation
- That correct URL/headers are sent to Reverb

---

## Architecture ↔ Testing Relationship

The testing issues mirror the structural gaps:

```text
Route (Controller)  →  Service  →  Client  →  HTTP (requests.get)
      ↑                   ↑           ↑              ↑
  test_listings.py    (no tests)  test_reverb_client.py
  test_categories.py                               ↑
      └──────────────────────────────────────── mock here
```

- **Route tests are secretly integration tests** — exercise Controller + Service + Client in one shot
- **No isolated service-layer tests** — `_search_categories()` only tested through route
- **Client tests are redundant with route tests** — both mock `requests.get`

### Ideal Layer-Aware Testing

```python
# Layer 1: Client — mock requests.get, verify URL/params/headers
@patch('reverb_client.requests.get')
def test_client_calls_correct_url(mock_get):
    mock_get.return_value.json.return_value = {'listings': []}
    ReverbClient().listings(page=2)
    mock_get.assert_called_once_with(
        'https://api.reverb.com/api/listings/all',
        headers=ReverbClient.HEADERS,
        params={'per_page': 10, 'page': 2},
    )

# Layer 2: Service — mock the CLIENT, verify business logic
@patch('app.ReverbClient')
def test_search_categories_filters_by_name(mock_client_class):
    mock_client_class.return_value.categories.return_value = [
        {'full_name': 'Guitars'}, {'full_name': 'Drums'}
    ]
    result = list(_search_categories('guitar'))
    assert result == [{'full_name': 'Guitars'}]

# Layer 3: Route — mock the SERVICE, verify HTTP + template
@patch('app._load_listings')
def test_listings_route_renders_template(mock_load):
    mock_load.return_value = [{'title': 'Guitar', 'photos': [...]}]
    res = client.get('/listings')
    assert res.status_code == 200
    assert 'Guitar' in parse_html(res).body.text
```

---

## pytest Mastery (Know These Cold)

### Running Tests

```bash
# All tests
pipenv run pytest -vs

# Single file
pipenv run pytest -vs tests/test_listings.py

# Single test by name
pipenv run pytest -vs tests/test_categories.py::test_displays_full_name_of_matching_categories

# Keyword match
pipenv run pytest -k "categories"

# Stop on first failure
pipenv run pytest -x

# Verbose + stop + show prints
pipenv run pytest -vxs

# Last failed only
pipenv run pytest --lf

# Show local variables in tracebacks
pipenv run pytest -l

# Drop into debugger on failure
pipenv run pytest --pdb
```

### Reading Test Output

```text
FAILED tests/test_listings.py::test_displays_listings - AssertionError: assert 'Guitar' in ''
```

Parse quickly:

- **File:** `test_listings.py`
- **Test:** `test_displays_listings`
- **What failed:** Expected 'Guitar' in the output, got empty string
- **Likely cause:** Mock data wrong or template not rendering

---

## Writing a New Test (Template)

### For a new API client method

```python
def test_fetches_single_listing():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'listing': {'id': '123', 'title': 'Fender Telecaster'}
    }

    result = ReverbClient().listing('123')

    assert result['title'] == 'Fender Telecaster'
    call_url = mock_get.call_args[0][0]
    assert '/listings/123' in call_url
```

### For a new route

```python
def test_listing_detail_page(client):
    res = client.get('/listings/123')
    assert res.status_code == 200
    html = parse_html(res)
    assert 'Fender Telecaster' in html.body.h1.text
```

### For an error case

```python
def test_handles_api_error(client, mock_api):
    mock_api.return_value.ok = False
    mock_api.return_value.status_code = 500
    mock_api.return_value.json.side_effect = ValueError("No JSON")

    res = client.get('/listings')
    assert res.status_code == 200  # page renders, not a 500
    html = parse_html(res)
    assert 'Unable to load' in html.body.text
```

---

## Interview Talking Points

- "The tests mock at the HTTP boundary, which makes them integration tests in
  disguise. That's fine for this scope."
- "If I were adding error handling, I'd mock at the client boundary instead — so
  I can verify the service catches the exception without caring about HTTP details."
- "The missing `_load_listings()` is both an architecture issue and a testing
  issue — it means I can't inject test data without going through the full HTTP mock."
- "I'd add the service helper first, which gives me a clean test seam, then
  implement the feature on top of it."

---

## New Codebase Addendum (June 2026)

The testing architecture in the new codebase is **stricter and better scoped**.
Most of the issues raised above have been fixed. The mocking philosophy has also
shifted: the new tests patch **at the route boundary** rather than at the
`requests.get` HTTP boundary.

### What changed

| Concern | Old codebase | New codebase |
|---|---|---|
| Test runner | `pipenv run pytest -vs` | `uv run pytest` |
| Shared fixture | None — each file defines its own `client` | `tests/conftest.py` exposes a `client` fixture built from `create_app()` |
| Patch lifecycle | `patch(...).start()` with no `.stop()` (leaky) | `with patch(...)` context manager (scoped) |
| Mock target | `reverb_client.requests.get` (HTTP boundary) | `app.routes.categories.reverb.categories` (route boundary) |
| HTML parsing | `BeautifulSoup` via `tests/helpers.py` | Raw byte assertions: `assert b'class="category-card"' in response.data` |
| Empty state coverage | Not tested | Has a dedicated test (`test_no_matching_categories_shows_empty_state`) |
| URL/param verification on client tests | Not done | `mock_get.assert_called_once_with(...)` verifies URL, params, and headers |
| `raise_for_status` stubbing | N/A (client used `requests`) | Must stub `mock.raise_for_status.return_value = None` |

### The new mock pattern — know this cold

```python
# tests/test_categories.py
from unittest.mock import patch

CATEGORIES = [{"full_name": "Guitars"}, {"full_name": "Drums"}]

def test_search_matching_categories_displays_them(client):
    with patch("app.routes.categories.reverb.categories", return_value=CATEGORIES):
        response = client.get("/categories?search=guitar")

    assert response.status_code == 200
    assert b"Guitars" in response.data
    assert b'value="guitar"' in response.data   # ← also verifies search term echo
```

Two important details:

- **Patch path is `app.routes.categories.reverb.categories`** — patched where the
  *route* imports the client, not where `httpx` lives. The test no longer cares
  *how* the client fetches data, only what it returns.
- **Tests assert on CSS class names** (`b'class="category-card"'`). Those class
  names are now **load-bearing** — renaming them in the template will break the
  test. This is intentional: the test asserts on rendered structure, not just text.

### Client-level tests now stub httpx and verify the call

```python
# tests/clients/test_reverb.py
from unittest.mock import MagicMock, patch
import pytest
from app.clients import reverb

@pytest.fixture(autouse=True)
def set_reverb_host(monkeypatch):
    monkeypatch.setenv("REVERB_HOST", "https://api.reverb.test")

def make_mock_response(data):
    mock = MagicMock()
    mock.json.return_value = data
    mock.raise_for_status.return_value = None   # ← critical: stub as a no-op
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

### Two-layer test mental model in the new codebase

```text
                            What you mock         What you verify
Route test  client.get(...)  reverb.<function>     status, HTML, classes
Client test reverb.<func>()  httpx.get              URL, params, headers
```

No middle layer (no service helper) means no middle-layer test — consistent with
the collapsed-service-layer architecture.

See [Chapter 16 § New Test Architecture](16-new-codebase-stack-guide.md) for
the full reference.
