# Test Walkthrough — Python/Flask Stack

## Test Architecture Summary

```text
test_categories.py ──┐
test_listings.py ────┼──→ patch('reverb_client.requests.get') → Mock
test_reverb_client.py┘
```

All tests mock at the same level: `requests.get` inside `reverb_client.py`.
This means even the "unit" tests for `ReverbClient` exercise the real parsing
logic — they're thin integration tests that stop at the HTTP boundary.

| File | Scope | What it proves |
| --- | --- | --- |
| `test_reverb_client.py` | Client class in isolation | JSON key extraction works |
| `test_listings.py` | Full route → client → template | Listing data renders in HTML |
| `test_categories.py` | Full route → service → client → template | Filter logic + rendering |
| `helpers.py` | Utility | `parse_html()` wraps BeautifulSoup |

---

## Architecture ↔ Testing Relationship

The test issues aren't just "bad test hygiene" — they mirror structural gaps in
the layered architecture itself. Understanding why requires looking at where the
tests mock relative to the layers.

### The Layers (from CODE_WALKTHROUGH.md)

```text
Route (Controller)  →  Service  →  Client  →  HTTP (requests.get)
      ↑                   ↑           ↑              ↑
  test_listings.py    (no tests)  test_reverb_client.py
  test_categories.py                               ↑
      └──────────────────────────────────────── mock here
```

Every test mocks at the same boundary: `requests.get`. This means:

- **Route tests are secretly integration tests.** They exercise
  Controller + Service + Client in one shot. If any layer breaks, the test fails
  — but the error message tells you nothing about *which* layer caused it.
- **There are no isolated service-layer tests.** `_search_categories()` is only
  tested as a side effect of hitting the `/categories` route. You can't verify
  filter logic without also exercising template rendering.
- **Client tests are redundant with route tests.** Both mock `requests.get` and
  assert on the return value. The client tests add almost no coverage that the
  route tests don't already provide.

### The Missing Service Boundary Problem

```python
# Categories: 3 layers, testable at each boundary
Route → _search_categories() → _load_categories() → ReverbClient().categories()

# Listings: 2 layers, no service boundary
Route → ReverbClient().listings()
```

For categories, you *could* mock `_load_categories()` to test filter logic
without hitting the client at all. For listings, there's no such seam — any test
must go through the full stack to the HTTP mock.

**Why this matters for each scenario:**

| Scenario | What you add | Where it belongs | Testing consequence |
| --- | --- | --- | --- |
| 2 (Search) | Filter/query logic | Service layer | Without `_load_listings()`, filter logic lives in the route. You can't test it without rendering a template. |
| 3 (Pagination) | Page param handling + metadata extraction | Service layer | Same: pagination logic tangled with route concerns. |
| 5 (Error handling) | try/except + flash | Route + Service | Error paths need different mock responses per layer. With one mock point, you can't distinguish "client raised" from "service caught and handled." |
| 6 (Sort) | Sorting logic | Service layer | Sort is pure business logic — it should be testable without HTTP or templates. But without a service function, it lives inline in the route. |

### What Ideal Layer-Aware Testing Looks Like

```python
# Layer 1: Client tests — mock requests.get, verify URL/params/headers
@patch('reverb_client.requests.get')
def test_client_calls_correct_url(mock_get):
    mock_get.return_value.json.return_value = {'listings': []}
    ReverbClient().listings(page=2, query='fender')
    mock_get.assert_called_once_with(
        'https://api.reverb.com/api/listings/all',
        headers=ReverbClient.HEADERS,
        params={'per_page': 10, 'page': 2, 'query': 'fender'},
    )

# Layer 2: Service tests — mock the CLIENT, verify business logic
@patch('app.ReverbClient')
def test_search_categories_filters_by_name(mock_client_class):
    mock_client_class.return_value.categories.return_value = [
        {'full_name': 'Guitars'}, {'full_name': 'Drums'}
    ]
    result = _search_categories('guitar')
    assert result == [{'full_name': 'Guitars'}]

# Layer 3: Route tests — mock the SERVICE, verify HTTP + template
@patch('app._load_listings')
def test_listings_route_renders_template(mock_load):
    mock_load.return_value = [{'title': 'Guitar', ...}]
    res = client.get('/listings')
    assert res.status_code == 200
    assert 'Guitar' in parse_html(res).body.text
```

**Benefits:**

- Each layer can break independently — the test that fails tells you exactly
  which layer is broken.
- Service logic (filter, sort, pagination math) is tested with plain Python
  asserts — no HTML parsing, no HTTP mocking.
- Route tests become thin: "given this data from the service, does the template
  render correctly?"
- Client tests focus on one thing: "are we calling the right URL with the right
  params?"

### Why the Current Approach Is Still Defensible

For 5 tests and 2 routes, layer-aware testing is over-engineering. The current
"mock at HTTP, test the full stack" approach:

- Is fast to write (one mock point serves all tests).
- Catches real integration bugs (e.g., template references wrong dict key).
- Matches the codebase complexity (no DI, no interfaces, no abstractions).

**The pivot point** is when you add Scenario 5 (error handling). At that point
you need to test "client raises → service catches → route renders flash" — a
multi-layer interaction that's nearly impossible to verify with a single
`requests.get` mock unless you're very careful about what the mock returns.

### Interview Talking Points

- "The tests mock at the HTTP boundary, which makes them integration tests in
  disguise. That's fine for this scope."
- "If I were adding error handling, I'd mock at the client boundary instead — so
  I can verify the service catches the exception without caring about HTTP
  details."
- "The missing `_load_listings()` is both an architecture issue and a testing
  issue — it means I can't inject test data without going through the full HTTP
  mock."
- "I'd add the service helper first, which gives me a clean test seam, then
  implement the feature on top of it."

---

## Issues Worth Discussing

### 1. `patch().start()` Without `stop()` — Mock Leakage

**Where:** Every test file.

```python
# test_categories.py (and others)
mock_get = patch('reverb_client.requests.get').start()
```

`patch().start()` begins monkey-patching but requires an explicit `.stop()` call
to undo it. None of these tests ever call `stop()`.

**Why it works anyway:**

- The test suite is tiny (5 tests across 3 files).
- Every test patches the *same* target, so the leaked patch just gets
  overwritten by the next `start()`.
- pytest may run `patch.stopall()` between sessions depending on plugin config,
  but that's not guaranteed.

**Why it's still a problem:**

- If you add a test that does NOT mock `requests.get`, it will unexpectedly hit
  a stale mock from a prior test.
- Test ordering becomes fragile — reordering or running a subset can produce
  different results.
- It violates the principle that each test should set up and tear down its own
  state.

**Correct patterns:**

```python
# Option A: Context manager (auto-stops)
def test_fetches_categories():
    with patch('reverb_client.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {...}
        categories = ReverbClient().categories()
        assert len(categories) == 2

# Option B: Decorator (auto-stops)
@patch('reverb_client.requests.get')
def test_fetches_categories(mock_get):
    mock_get.return_value.json.return_value = {...}
    ...

# Option C: Fixture with proper teardown
@pytest.fixture
def client():
    app.config['TESTING'] = True
    patcher = patch('reverb_client.requests.get')
    mock_get = patcher.start()
    mock_get.return_value.json.return_value = {...}

    with app.test_client() as client:
        yield client

    patcher.stop()  # ← This is what's missing

# Option D: Blanket cleanup (less precise but safe)
@pytest.fixture(autouse=True)
def cleanup_mocks():
    yield
    patch.stopall()
```

---

### 2. Fixture Doesn't Expose the Mock — Tests Can't Customize

**Where:** `test_categories.py` and `test_listings.py` fixtures.

```python
@pytest.fixture
def client():
    # mock is created here...
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = { 'categories': [...] }

    with app.test_client() as client:
        yield client  # ← only the Flask client is yielded
```

The mock object is trapped inside the fixture. Individual tests cannot:

- Change the response for a specific scenario (e.g., empty list, 500 error).
- Assert how many times the API was called.
- Verify request parameters passed to `requests.get`.

**Better pattern — yield a tuple or use a separate fixture:**

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
    # Set a default response; tests can override via mock_api
    mock_api.return_value.json.return_value = { 'categories': [...] }
    with app.test_client() as client:
        yield client

def test_empty_categories(client, mock_api):
    mock_api.return_value.json.return_value = { 'categories': [] }
    res = client.get('/categories', query_string={'query': 'guitar'})
    # Now we can test the empty state
```

---

### 3. No Assertion on HTTP Status Code

**Where:** All route tests (`test_listings.py`, `test_categories.py`).

```python
def test_displays_listings(client):
    res = client.get('/listings')
    html = parse_html(res)
    # jumps straight to HTML assertions — never checks res.status_code
```

**Why it matters:**

- If the route raises an exception, Flask in testing mode returns a 500 with a
  traceback page. The test would "pass" because the asserted string isn't found,
  leading to a confusing `AttributeError` or `None` from BeautifulSoup — not a
  clear "this route is broken" signal.
- A simple `assert res.status_code == 200` at the top makes failures
  immediately obvious.

**Minimal fix:**

```python
def test_displays_listings(client):
    res = client.get('/listings')
    assert res.status_code == 200  # ← fail fast with a clear message
    html = parse_html(res)
    ...
```

---

### 4. Testing Absence vs. Testing the Empty State

**Where:** `test_categories.py`

```python
def test_displays_nothing_if_no_matching_categories(client):
    res = client.get('/categories', query_string={'query': 'didgeridoo'})
    html = parse_html(res)
    assert len(html.body.find_all('ul.list-group')) == 0
```

This verifies that no list is rendered, but doesn't verify what IS rendered.
From a UX perspective, showing nothing at all is arguably worse than showing a
"No results found" message.

**Two-level improvement:**

1. **Test the current behavior accurately** — assert both the absence of results
   AND the presence of whatever empty-state UI exists (even if it's just a blank
   page today).
2. **Drive new behavior via TDD** — write a test that asserts a "No results"
   message, watch it fail, then implement the empty state in the template.

```python
def test_displays_no_results_message_when_filter_matches_nothing(client):
    res = client.get('/categories', query_string={'query': 'didgeridoo'})
    html = parse_html(res)

    assert len(html.body.find_all('ul.list-group')) == 0
    assert 'No matching categories' in html.body.text  # drives UX implementation
```

---

### 5. `test_reverb_client.py` — No Fixture, No Cleanup

**Where:** Both tests in `test_reverb_client.py`.

```python
def test_fetches_categories():
    mock_get = patch('reverb_client.requests.get').start()
    ...

def test_fetches_listings():
    mock_get = patch('reverb_client.requests.get').start()
    ...
```

These are plain functions (no fixture, no context manager). Each `.start()` call
layers another active patch. Since they all target the same object it's harmless
here, but this is the pattern most likely to cause issues as the suite grows.

Additionally, these tests don't verify:

- That `_get` was called with the correct URL path (`/categories/flat`,
  `/listings/all`).
- That headers were sent correctly.
- That query params (like `per_page`) were passed through.

```python
# More thorough client test
@patch('reverb_client.requests.get')
def test_fetches_listings_with_correct_params(mock_get):
    mock_get.return_value.json.return_value = {
        'listings': [{'title': 'Guitar'}],
    }

    listings = ReverbClient().listings(per_page=5)

    mock_get.assert_called_once_with(
        'https://api.reverb.com/api/listings/all',
        headers=ReverbClient.HEADERS,
        params={'per_page': 5},
    )
    assert listings[0]['title'] == 'Guitar'
```

---

## Summary Table

| Issue | Severity | Impact | Fix Effort |
| --- | --- | --- | --- |
| Missing `patch.stop()` | Medium | Mock leakage between tests | Low — add context managers or `stopall()` |
| Mock not exposed from fixture | Low | Can't write edge-case tests easily | Low — yield tuple or split fixture |
| No status code assertion | Low | Confusing failures when route breaks | Trivial — one line per test |
| No empty-state UX test | Low | UX gap goes unnoticed | Low — one new assertion |
| No param/URL assertions on client | Low | Client could call wrong endpoint undetected | Low — add `assert_called_with` |

---

## Interview Framing

These issues are intentional teaching moments, not bugs to "fix" mid-interview.
When discussing them:

- **Show awareness** — mention mock lifecycle and test isolation unprompted.
- **Prioritize** — mock leakage is the most architecturally significant; status
  code checks are the cheapest win.
- **Don't over-engineer** — for a 5-test suite, these are fine. The point is
  knowing what would break at scale and being able to articulate *why*.
- **Connect to the service-layer gap** — the missing `_load_listings()` helper
  also means you can't unit-test listing logic in isolation from the route, which
  compounds the fixture rigidity problem.

---

## Concrete Future Failures If Tests Aren't Fixed

These aren't theoretical — each maps to a scenario you'd hit while implementing
the interview features below.

### Mock Leakage → False Greens

**Trigger:** You add a test for error handling (Scenario 5) that does NOT set up
a mock — expecting the real `requests.get` to be called against a test server or
expecting the code to raise when no mock provides a response.

**What happens:** The leaked mock from a previous test silently provides a "happy
path" response. Your error-handling test passes despite never actually exercising
the error path. You deploy, the API goes down, and the app crashes because your
"passing" test never validated the rescue logic.

```python
# Scenario 5: You write this test expecting it to test real error behavior
def test_handles_connection_error():
    # No mock set up — expects real behavior or a controlled raise
    with pytest.raises(ApiError):
        ReverbClient().listings()
    # BUG: The leaked mock from test_fetches_listings() answers this call!
    # No exception is raised. Test fails with "ApiError not raised" but
    # only sometimes — depends on test execution order.
```

### Mock Leakage → Flaky Tests Under Parallelization

**Trigger:** You add `pytest-xdist` for parallel test execution (common in CI for
speed).

**What happens:** Tests run in random order across workers. Mock leaks from one
worker's test don't cross process boundaries, but within a single worker, test
ordering is shuffled. Tests that passed sequentially now intermittently fail
because they depend on a prior test's leaked mock having set up the "right"
response shape.

### Rigid Fixture → Copy-Paste Explosion

**Trigger:** Scenarios 3 (pagination) and 5 (error handling) need different API
response shapes — pagination metadata, error status codes, empty arrays.

**What happens:** Since the existing fixture bakes in one hardcoded response and
doesn't expose the mock, you end up creating a new fixture per response shape:
`paginated_client`, `error_client`, `empty_client`, `priced_client`. Each
duplicates the `app.config['TESTING'] = True` + `patch` + `test_client` setup.
Six fixtures doing 90% the same thing. When the setup needs to change (e.g., you
add auth headers), you update one fixture and forget the others.

### No Status Code Check → Silent Template Errors

**Trigger:** Scenario 1 (detail page) — you add a new template
`listing_detail.html` with a Jinja2 syntax error or reference to an undefined
variable.

**What happens:** Flask returns a 500 with a traceback. Your test does
`parse_html(res)` on the error page, calls `.h1.text`, gets `None`, and raises
`AttributeError: 'NoneType' object has no attribute 'text'`. You spend 10
minutes debugging why "h1 is None" instead of immediately seeing "my route
returned 500."

### No URL/Param Assertions → Silently Wrong API Calls

**Trigger:** Scenario 4 (category navigation) — you add a `category` param to
`ReverbClient.listings()`. You typo the param name as `categories` (plural).

**What happens:** The test still passes because it only checks the shape of the
*mocked* return value — it never verifies what URL or params were actually passed
to `requests.get`. The API ignores the unknown `categories` param and returns
unfiltered results. The test is green, the feature is broken, and you only
discover it during manual testing.

---

## Impact on Each Interview Scenario

### Scenario 1: Listing Detail Page

| Test Issue | Concrete Impact |
| --- | --- |
| No `patch.stop()` | You add `test_listing_detail.py` with its own fixture. The leaked mock from `test_listings.py` is still active. If your new fixture patches at a different path (e.g., you try `patch('app.ReverbClient')` instead), both patches are active simultaneously — the real `requests.get` never gets called, but neither does your intended mock. Confusing double-mock behavior. |
| Fixture rigidity | The detail page returns a different JSON shape (`{'listing': {...}}` vs `{'listings': [...]}`) . You can't reuse the existing fixture at all. You create a whole new one, duplicating 8 lines of boilerplate. |
| No status code check | The most likely failure: your new `listing_detail.html` template references `listing['photos'][0]` but the mock data doesn't include `photos`. Flask returns 500. Without `assert res.status_code == 200`, you get `AttributeError` deep in BeautifulSoup — not "template failed to render." |

**What to do in the interview:** Add `assert res.status_code == 200` as the
first assertion in every new test you write. Mention: "The existing tests don't
do this, but I'm adding it because it makes template errors immediately
visible."

### Scenario 2: Search / Filter Listings

| Test Issue | Concrete Impact |
| --- | --- |
| No param assertions | You add `query` as an optional param to `ReverbClient.listings()`. But without `assert_called_with`, you have no test proving the query actually gets forwarded to `requests.get`. The mock returns the same canned data regardless of what params you pass. You could forget the `params['query'] = query` line entirely and tests would still pass. |
| Fixture rigidity | You need to test both "search with results" and "search with no results" (empty state). With the fixed fixture, you need two separate fixtures or an awkward inline re-patch. |
| Mock leakage | If you write `test_empty_search_shows_message()` as a standalone function (like `test_reverb_client.py` does), the leaked mock from the fixture-based tests may interfere — it returns a non-empty list, so your "empty results" test fails intermittently. |

**What to do in the interview:** Write a client-level test that uses
`mock_get.assert_called_once_with(...)` to verify the `query` param lands in the
HTTP request. Say: "I want to verify the param actually reaches the API, not
just that the mock returns what I told it to."

### Scenario 3: Pagination

| Test Issue | Concrete Impact |
| --- | --- |
| No param assertions | Same as Scenario 2 — you add `page` param but have no proof it reaches `requests.get`. |
| Fixture rigidity | Pagination requires a different response shape: `{'listings': [...], 'current_page': 2, 'total_pages': 5}`. The existing fixture only returns `{'listings': [...]}`. You need to create `paginated_client` from scratch. |
| Breaking change undetected | You change `ReverbClient.listings()` to return the full response dict (not just `['listings']`). The existing `test_displays_listings` test still passes because the mock returns whatever shape you define — it doesn't validate the return type contract. The route `app.py` breaks at runtime because it expected a list but got a dict. No test catches this. |

**What to do in the interview:** When you change the client's return type,
immediately update the existing test to match the new contract. Say: "This is a
breaking change — let me update the existing tests first so they fail if I
revert."

### Scenario 4: Category → Listings Navigation

| Test Issue | Concrete Impact |
| --- | --- |
| No param assertions | You add `category` param. Without `assert_called_with`, a typo like `params['cat'] = category` goes undetected. |
| Cross-file mock leakage | You add a test in `test_categories.py` that checks links render with `href="/listings?category=guitars"`. The categories fixture mocks `requests.get` with a categories response. But the template's `url_for('listings', ...)` call doesn't hit the API — it's purely Flask routing. This works fine. However, if you add an integration test that clicks the link and follows to `/listings`, the leaked mock still returns category data, not listing data. The listings page renders wrong content. |
| No empty-state test | You navigate to `/listings?category=underwater-basket-weaving` which returns zero listings. Without an empty-state test, you won't notice the blank page UX. |

**What to do in the interview:** Add a test that verifies the category slug
appears in the generated link href. Then add a separate test proving the
listings route respects the category param.

### Scenario 5: Error Handling & Loading States

| Test Issue | Concrete Impact |
| --- | --- |
| Mock leakage (critical) | This is where mock leakage becomes a showstopper. You need to simulate API failures: `mock_get.return_value.ok = False` or `mock_get.side_effect = requests.Timeout()`. If a leaked happy-path mock from a previous test is still active, your error mock might not take effect — `patch().start()` on the same target replaces the previous patch, but if test ordering changes, you may hit the happy path first, then your error test inherits the error mock. Tests become order-dependent. |
| No status code check (critical) | You implement error handling with `try/except` and `flash()`. If you mess up the exception handling (e.g., catch wrong exception type), the route returns 500. Without `assert res.status_code == 200`, you can't distinguish "my error handling worked (page renders with flash)" from "my error handling failed (Flask 500 page)." |
| Fixture rigidity (critical) | You need at minimum 3 response states: success, HTTP error, timeout. With a rigid fixture, you create 3 fixtures. If you also combine with pagination (Scenario 3), you need success+paginated, error+paginated, timeout+paginated — combinatorial explosion. |

**What to do in the interview:** This is the scenario where you **should** fix
the test infrastructure first. Say: "Before implementing error handling, I'm
going to refactor the test setup so the mock is exposed and properly cleaned up.
Otherwise I can't reliably test failure modes." This shows senior-level thinking
— investing in test infrastructure when the feature demands it.

### Scenario 6: Price Display + Sort

| Test Issue | Concrete Impact |
| --- | --- |
| Fixture rigidity | The existing fixture returns listings without `price` data. Your sort test needs `{'price': {'amount': '900.00', 'display': '$900'}}` in each listing. You create yet another fixture (`priced_client`). At this point you have 4-5 fixtures across your test files, all doing the same setup dance with slight data variations. |
| No param assertions | Sort is implemented server-side in the route (not via API param), so this issue is less critical here. However, if you chose to use the API's `sort` param instead, the same "silently wrong param" bug applies. |
| No status code check | If `float(listing['price']['amount'])` raises `ValueError` for a malformed price (missing key, string like "Call for price"), the route crashes with 500. Without status code assertions, your test gives a confusing BeautifulSoup error instead of "route failed." |
| Test data brittleness | The sort tests need at least 2 listings with different prices to verify ordering. The existing fixture has exactly 1 listing. You can't extend it without affecting other tests (fixture is shared across the file). This forces the new fixture pattern. |

**What to do in the interview:** Write sort tests with 2+ listings at different
prices. Assert the rendered order of `<h2>` elements changes based on the `sort`
param. Mention: "I'm testing the ordering of HTML elements, which implicitly
tests the sort logic without needing a unit test for the sort function itself."

---

## The Compound Effect

Each issue is "low severity" in isolation. But as you work through multiple
scenarios, they compound:

```text
Scenario 1: Create 1 new fixture (detail page response)
Scenario 2: Create 2 new fixtures (search results, empty search)
Scenario 3: Create 1 new fixture (paginated response) + break existing
Scenario 5: Create 3 new fixtures (success, error, timeout)
Scenario 6: Create 1 new fixture (priced listings)

Total: 8 new fixtures, all doing identical setup with different data.
```

If you'd fixed the infrastructure in Scenario 1 (expose mock, add cleanup), all
subsequent scenarios would just override `mock_api.return_value.json.return_value`
inline — no new fixtures needed.

**Interview signal:** Recognizing this compound debt and choosing to fix it early
(rather than accumulating copy-paste fixtures) demonstrates the kind of
judgment that distinguishes a senior engineer from someone who "just makes it
work."
