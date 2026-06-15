# Test Walkthrough — Python/Flask Stack (2026)

This walkthrough is the companion to [CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md).
It maps every test file in [tests/](tests/), explains where the mocks live and
*why*, and flags the issues worth bringing up in an interview.

The big architectural shift vs. the old codebase: **tests now mock at the
client function boundary**, not at `httpx.get`. That's a real improvement.
What's left is a smaller, more focused list of issues — mostly around
isolation, gaps in coverage, and one fixture that doesn't yet earn its keep.

---

## Test Architecture Summary

```text
tests/test_categories.py ──→ patch('app.routes.categories.reverb.categories')
tests/test_listings.py   ──→ patch('app.routes.listings.reverb.listings')
tests/clients/test_reverb.py ──→ patch('httpx.get') + monkeypatch.setenv('REVERB_HOST', ...)
tests/conftest.py        ──→ Flask app + test_client fixture (no mocks)
```

Two distinct mock boundaries, picked deliberately:

| Test file | Mock target | Scope |
| --- | --- | --- |
| [tests/clients/test_reverb.py](tests/clients/test_reverb.py) | `httpx.get` | Client functions in isolation (URL, params, headers, JSON unwrap) |
| [tests/test_categories.py](tests/test_categories.py) | `app.routes.categories.reverb.categories` | Route + template (filter logic + rendering) |
| [tests/test_listings.py](tests/test_listings.py) | `app.routes.listings.reverb.listings` | Route + template (listing rendering) |
| [tests/conftest.py](tests/conftest.py) | None | `client` fixture: fresh `create_app()` per test, `TESTING=True` |

The route tests no longer secretly exercise the client. The client tests no
longer secretly exercise routes or templates. **Each test fails for one
reason** — that's the whole point of choosing boundaries deliberately.

---

## Architecture ↔ Testing Relationship

### The Layers (from CODE_WALKTHROUGH.md)

```text
Blueprint (Route)  →  Client (reverb.*)  →  httpx.get  →  Reverb API
        ↑                    ↑                  ↑
    route tests        client tests        (no test goes here)
    mock here          mock here
```

Two mock boundaries, one per concern:

- **Client tests** mock `httpx.get` — verify the *transport* concern: correct
  URL, headers, params, JSON unwrap. Pure unit tests with `monkeypatch.setenv`
  to isolate from real `REVERB_HOST` config.
- **Route tests** mock `reverb.categories` / `reverb.listings` — verify the
  *route + template* concern: filter logic, query string handling, HTML output.
  They take the client's contract as a given (`returns a list of dicts`) and
  don't care how that contract is implemented.

That's the **right** split for a layered app with no service layer. If a
service layer is added (see [The Missing Service Layer](CODE_WALKTHROUGH.md#the-missing-service-layer)),
add a third mock boundary: route tests patch the service, service tests patch
the client, client tests patch `httpx.get`. Three layers, three mock points,
each isolated.

### What This Buys You

Each scenario in [the scenario docs](../scenario-1-detail-page.md) gets a
clean home for its tests:

| Scenario | What you add | Test target | Mock target |
| --- | --- | --- | --- |
| 1 (Detail page) | `reverb.listing(id)` + template | client + route | `httpx.get` + `app.routes.listings.reverb.listing` |
| 2 (Search listings) | `query` param on `reverb.listings` | client + route | `httpx.get` (assert `params`) + `reverb.listings` |
| 3 (Pagination) | Return-shape change in `reverb.listings` | client + route | Same as above |
| 5 (Error handling) | `ReverbError`, try/except in service | **new service test** + route | `reverb.*` in service test; `app.services.*` in route test |
| 6 (Price sort) | Sort logic | service (or route if no service yet) | Whatever houses the sort |

Notice that Scenario 5 is the one that justifies the third mock layer. Until
then, two layers are enough.

### What's Still NOT Covered

- **Error paths.** No test simulates `httpx.HTTPStatusError`,
  `httpx.TimeoutException`, or `httpx.ConnectError`. The first thing
  Scenario 5 demands.
- **Empty-list listings.** `test_listings.py` only has the happy path. The
  template handles `{% if listings %}...{% else %}No listings available
  {% endif %}`, but no test covers the `else` branch.
- **Photo-safety edge cases.** A listing with `photos: []` (explicit empty
  list, not missing) will currently `IndexError` the template — see
  [CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md#apptemplates--jinja2-views).
  No test catches this.
- **`per_page` clamping.** The proposed clamp in the client improvements
  isn't tested because it doesn't exist yet.
- **Root route's empty state.** `test_root_route_renders_categories` only
  checks the form renders. Doesn't verify "no search → no result list /
  no empty-state message" (the route's intended behavior).

---

## File-by-File Test Breakdown

### `tests/conftest.py` — The `client` Fixture

```python
import pytest
from app import create_app

@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
```

What's good:

- **Fresh app per test.** `create_app()` is called inside the fixture, not at
  module import. Each test gets isolated state.
- **No leaked patches.** No `patch().start()` here — that whole class of bug
  from the old codebase is gone.
- **Context-managed `test_client`.** The `with` block ensures cleanup if a
  test raises.

What's missing (worth raising in the interview):

- **No env-var isolation.** `create_app()` calls `load_dotenv()` at module
  import (in `app/__init__.py`). If `REVERB_HOST` is set in the shell, it
  bleeds into tests. The client tests handle this with `monkeypatch.setenv`,
  but the route tests don't — they rely on the client being mocked, so the
  env var is never read.
- **No autouse safety net.** If a developer forgets to patch
  `reverb.categories` in a new route test, `httpx.get` will fire against
  whatever `REVERB_HOST` resolves to. An `autouse` fixture that patches both
  client functions with sensible defaults would prevent accidental
  network I/O during tests.

A small addition that pays for itself:

```python
@pytest.fixture(autouse=True)
def no_real_reverb_calls(monkeypatch):
    """Belt-and-braces: any unpatched call to httpx.get during tests fails loud."""
    def _boom(*args, **kwargs):
        raise RuntimeError(f"Unmocked httpx.get({args[0]!r})")
    monkeypatch.setattr("httpx.get", _boom)
```

Then individual tests opt back in by patching the higher-level
`reverb.categories` / `reverb.listings`. Forgetting to patch becomes a
loud `RuntimeError`, not a silent network call.

### `tests/clients/test_reverb.py` — Client Unit Tests

```python
@pytest.fixture(autouse=True)
def set_reverb_host(monkeypatch):
    monkeypatch.setenv("REVERB_HOST", "https://api.reverb.test")
```

What's good:

- **`monkeypatch.setenv` is the right tool.** It's autouse, scoped to the
  test, automatically reverted on teardown. No leaked env vars between tests.
- **`patch("httpx.get")` is the correct boundary.** Mocks the transport, not
  the client function — the test exercises real `_get`, real JSON unwrap,
  real param construction.
- **`assert_called_once_with(...)` everywhere.** Every test verifies the URL,
  params, and headers — not just the return value. This is what makes the
  test useful: if you typo `per_page` as `perpage`, the test fails. The old
  codebase's tests would have passed.

What's worth noting:

- **`make_mock_response` is a tiny factory.** Five lines, used by every test.
  Promoting this to `conftest.py` or a fixture would let you write
  `mock_get(data=...)` instead of `make_mock_response(...)` plus the
  `patch("httpx.get", return_value=...)` boilerplate. Optional polish.
- **No error-path tests.** Three obvious gaps that would justify adding
  before Scenario 5:

  ```python
  def test_get_raises_on_http_error():
      mock = MagicMock()
      mock.raise_for_status.side_effect = httpx.HTTPStatusError(
          "500", request=MagicMock(), response=MagicMock(status_code=500)
      )
      with patch("httpx.get", return_value=mock):
          with pytest.raises(httpx.HTTPStatusError):
              reverb.categories()

  def test_get_raises_on_timeout():
      with patch("httpx.get", side_effect=httpx.TimeoutException("slow")):
          with pytest.raises(httpx.TimeoutException):
              reverb.categories()

  def test_get_raises_on_connect_error():
      with patch("httpx.get", side_effect=httpx.ConnectError("nope")):
          with pytest.raises(httpx.ConnectError):
              reverb.categories()
  ```

  These tests are also the **TDD foundation** for `ReverbError` (item 8 in
  the client improvements): once they pass with `httpx.*` exceptions, change
  them to `pytest.raises(ReverbError)` and the client implementation
  follows.

- **No `per_page` clamping test.** Doesn't exist yet because the clamp
  doesn't exist yet. Mention it in the interview as "I'd write the test
  first: `assert reverb.listings(per_page=99999)` calls `httpx.get` with
  `params={'per_page': 50}` — that's the contract."

- **`REVERB_HOST` missing isn't tested.** `os.environ["REVERB_HOST"]` raises
  `KeyError` if unset. A test that asserts that failure mode (or, better,
  one that confirms a clean `ReverbError("REVERB_HOST not configured")`
  after the boundary is in place) would close that hole.

### `tests/test_categories.py` — Route + Template Tests

```python
def test_search_matching_categories_displays_them(client):
    with patch("app.routes.categories.reverb.categories", return_value=CATEGORIES):
        response = client.get("/categories?search=guitar")

    assert response.status_code == 200
    assert b"Guitars" in response.data
    assert b"Drums" not in response.data
    assert b'value="guitar"' in response.data
```

What's good:

- **`patch("app.routes.categories.reverb.categories")` is the correct
  boundary.** This is "patch where it's looked up," the canonical Python
  mocking rule. The route module imports `reverb` and calls
  `reverb.categories()` — that's the binding to patch, not
  `app.clients.reverb.categories`.
- **`with patch(...)` context manager.** Auto-stops on exit. No leakage.
- **`assert response.status_code == 200`.** The old codebase's tests
  *didn't* have this. The 2026 ones do. Template errors now fail with
  "AssertionError: 500 != 200" instead of a confusing
  `AttributeError: 'NoneType' object has no attribute 'text'`.
- **Both positive and negative assertions.** `Guitars` in, `Drums` out.
  Verifies the filter actually filtered, not just that it returned
  something.
- **`test_no_matching_categories_shows_empty_state`** covers an empty-state
  UX assertion — the old codebase only tested *absence* of the result list;
  the 2026 version tests both absence and the presence of the "No
  categories found" message + the user's search term echoed back. That's a
  real upgrade.

What's worth noting:

- **`test_no_search_term_shows_form_and_no_categories` doesn't mock
  `reverb.categories`.** It's relying on the route's `if search_term:`
  guard to skip the client call entirely. That works *because the guard is
  correct* — but if a refactor accidentally moves the `reverb.categories()`
  call outside the guard, the test will hit `httpx.get` against
  `REVERB_HOST` and either fail with a real network error or, worse, pass
  by accident. The autouse `no_real_reverb_calls` fixture above would catch
  this immediately.

- **No assertion that the form is *prefilled*** on a no-result search. The
  test checks `b"violin" in response.data`, which matches the empty-state
  message — but it doesn't distinguish "echoed in the message" from "echoed
  in the input field". Two separate assertions
  (`b'value="violin"'` and `b'No categories found' in response.data`)
  would be clearer.

- **No test for `full_name` being `None`.** The route has
  `(c.get("full_name") or "").lower()` — that's defensive code. Worth a
  test:

  ```python
  def test_filter_handles_null_full_name(client):
      data = [{"full_name": None}, {"full_name": "Guitars"}]
      with patch("app.routes.categories.reverb.categories", return_value=data):
          response = client.get("/categories?search=guitar")
      assert response.status_code == 200
      assert b"Guitars" in response.data
  ```

  Without this test, someone could "simplify" the `or ""` away and tests
  would still pass.

- **`b"Guitars"` is a substring check.** If the template ever rendered the
  literal string "Guitars" elsewhere (heading, breadcrumb, schema.org), the
  test would pass even with a broken filter. For a tiny suite this is fine.
  A `parse_html` helper (BeautifulSoup) would let you assert on
  `body.find_all(".category-card")` directly — more precise, more verbose.

### `tests/test_listings.py` — Route + Template Tests

```python
def test_listings_returns_200(client):
    with patch("app.routes.listings.reverb.listings", return_value=LISTINGS):
        response = client.get("/listings")
    assert response.status_code == 200

def test_listings_displays_photo_and_title(client):
    with patch("app.routes.listings.reverb.listings", return_value=LISTINGS):
        response = client.get("/listings")
    assert b'class="listings-grid"' in response.data
    ...
```

What's good:

- Same patch-where-it's-looked-up correctness as the categories tests.
- Photo URL is a `.test` TLD — explicit "this is fake data," no risk of
  accidental network image loads in CI.
- Both `listings-grid` (the container) and `listing-card` (the item) are
  asserted — verifies the template structure, not just the data.

What's worth noting:

- **Two tests, one mock setup, duplicated.** The first test sets up the
  mock just to get a 200, the second sets up the *same* mock to check
  rendering. A shared fixture would dedupe:

  ```python
  @pytest.fixture
  def mock_listings():
      with patch("app.routes.listings.reverb.listings", return_value=LISTINGS) as m:
          yield m

  def test_listings_returns_200(client, mock_listings):
      assert client.get("/listings").status_code == 200

  def test_listings_displays_photo_and_title(client, mock_listings):
      ...
  ```

  At two tests this is over-engineering. At five+ it's the right move. The
  pivot will be Scenario 1 or 3, when the suite doubles.

- **No empty-listings test.** `LISTINGS = [...]` always has data. The
  template's `{% else %}No listings available at this time.{% endelse %}`
  branch is **untested**:

  ```python
  def test_listings_empty_state(client):
      with patch("app.routes.listings.reverb.listings", return_value=[]):
          response = client.get("/listings")
      assert response.status_code == 200
      assert b"No listings available" in response.data
      assert b"listings-grid" not in response.data
  ```

- **No `photos: []` test.** Per
  [CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md#apptemplates--jinja2-views),
  an explicit empty `photos: []` will `IndexError` the current template.
  A test that proves either (a) the bug exists and we accept it, or (b)
  the template handles it safely, would close the ambiguity.

- **No `per_page` assertion.** The route calls `reverb.listings()` with
  no args. If a future change adds `request.args.get("per_page")`
  forwarding, a test that asserts
  `mock_listings.assert_called_once_with(per_page=expected)` is the only
  way to catch silent typos.

### What's NOT in the suite — and where it belongs

| Missing coverage | Where it would live | Scenario it unblocks |
| --- | --- | --- |
| Error-path tests (HTTP error, timeout, connect error) | `tests/clients/test_reverb.py` | 5 |
| `ReverbError` translation tests | `tests/clients/test_reverb.py` | 5 |
| `per_page` clamp tests | `tests/clients/test_reverb.py` | 9 (client improvements) |
| `REVERB_HOST` missing test | `tests/clients/test_reverb.py` | 9 |
| Empty listings test | `tests/test_listings.py` | 5 (empty/error UX shared) |
| Photo-safety with `photos: []` | `tests/test_listings.py` | Bug fix |
| Filter handles `null` full_name | `tests/test_categories.py` | Regression guard |
| Service-layer tests | `tests/services/` (new dir) | 5 |
| Route uses service, not client (mock target shifts) | Existing route tests | 5 |

---

## Issues Worth Discussing

The 2026 tests fixed most of what the old codebase had wrong (mock leakage,
status-code assertions, empty-state coverage, param-assertions on client).
What's left is a smaller, more focused list:

### 1. No Network-Safety Net

**Where:** [tests/conftest.py](tests/conftest.py).

If any test calls a route that ends up calling `reverb.*` without a patch in
place, `httpx.get` fires against whatever `REVERB_HOST` resolves to in the
environment. In CI with no `.env`, this is a clear failure. In local dev with
`.env` loaded, it silently hits the real Reverb API.

**Fix:** an autouse fixture that monkeypatches `httpx.get` to raise. Tests
opt back in by patching `reverb.categories` / `reverb.listings`. See the
`no_real_reverb_calls` snippet under
[tests/conftest.py](#testsconftestpy--the-client-fixture) above.

### 2. Two Mock Strategies Coexist (Slight Inconsistency)

**Where:** Route tests use `with patch(...)` context manager. Client tests
use `patch(...)` as a context manager *and* an autouse fixture for
`monkeypatch.setenv`. Both work, both are correct — but mixing styles in a
larger suite makes it harder to scan.

If a developer adds an autouse fixture (per issue 1), the natural follow-up
is to standardize on autouse fixtures everywhere with helpers like
`mock_categories(data=...)` and `mock_listings(data=...)`. Not worth doing
yet; flag it when the suite hits ~10 tests.

### 3. Coverage Gaps Are Worse Than Test Hygiene

The 2026 codebase has zero error-path tests, zero empty-listings test, zero
`per_page` clamping test. These aren't "tests we should add for tidiness" —
they're **tests that block real scenarios**. Scenario 5 (error handling)
literally cannot be TDD'd without first writing the
`httpx.HTTPStatusError` / `httpx.TimeoutException` tests in
[tests/clients/test_reverb.py](tests/clients/test_reverb.py).

This is the strongest version of the old walkthrough's
"compound effect" argument. Each scenario adds tests; if the foundations
(error paths, empty states) aren't in place, you'll either write them on
the fly (slow) or skip them (debt).

### 4. Substring Assertions Are Fragile, But Fine For Now

**Where:** all route tests, e.g. `assert b"Guitars" in response.data`.

`response.data` is the raw bytes of the HTML. A `b"Guitars"` match is true
if the string appears anywhere — heading, card, footer, schema.org markup.
For 5 tests this is fine. For 50+, swap to a `parse_html` helper:

```python
# tests/helpers.py
from bs4 import BeautifulSoup

def parse_html(response):
    return BeautifulSoup(response.data, "html.parser")
```

Then:

```python
html = parse_html(response)
assert len(html.select(".category-card")) == 1
assert "Guitars" in html.select_one(".category-card").get_text()
```

More precise; requires adding `beautifulsoup4` to `dev-dependencies`. Not
worth doing pre-emptively.

### 5. Test Data Is Module-Level Constants

**Where:** `CATEGORIES = [...]` at the top of
[tests/test_categories.py](tests/test_categories.py), `LISTINGS = [...]` at
the top of [tests/test_listings.py](tests/test_listings.py).

Both are fine for the current size. As soon as Scenario 3 (pagination)
requires multiple shapes, this becomes copy-paste. Factories beat constants:

```python
def make_listing(**overrides):
    return {
        "title": "Default Title",
        "photos": [{"_links": {"thumbnail": {"href": "https://example.test/p.jpg"}}}],
        **overrides,
    }

LISTINGS = [make_listing(title="Fender Stratocaster")]
```

Then tests that need a price (Scenario 6) do
`make_listing(price={"amount_cents": 90000})` without duplicating the
whole shape. Flag this as the right move once the third test file appears.

---

## Summary Table

| Issue | Severity | Impact | Fix Effort |
| --- | --- | --- | --- |
| No network-safety net (autouse `httpx.get` guard) | Medium | Silent real API calls in dev | Low — 5-line fixture |
| Missing error-path tests | High | Blocks Scenario 5 | Medium — 3 tests + plan |
| Missing empty-listings test | Low | Untested template branch | Trivial |
| Missing `photos: []` safety test | Low | Latent template bug | Trivial |
| Missing `null` `full_name` test | Low | Regression risk on the `or ""` guard | Trivial |
| Substring assertions (vs BeautifulSoup) | Low | Fragile at scale, fine now | Medium — adds dep |
| Test data as constants vs factories | Low | Copy-paste pain at Scenario 3+ | Low — refactor when needed |

---

## Interview Framing

These are intentional teaching moments, not bugs to fix mid-interview. When
discussing them:

- **Acknowledge what the codebase got right.** The mock boundaries are
  correct — `httpx.get` for the client, `reverb.*` for the route. That's a
  real architectural improvement over the old version. Say so. Then move to
  what's left.
- **Lead with coverage gaps, not hygiene.** Missing error-path tests are
  more important than "we should use BeautifulSoup." Show you can rank.
- **Tie tests to scenarios.** Don't say "we should add error tests."
  Say: "Before I implement Scenario 5, I'd add three tests in
  `tests/clients/test_reverb.py` for `HTTPStatusError`,
  `TimeoutException`, and `ConnectError` — that's my TDD foundation for the
  `ReverbError` boundary in [CODE_WALKTHROUGH.md item 8](CODE_WALKTHROUGH.md#8-exception-leakage--the-client-should-own-its-errors)."
- **Don't over-engineer.** At 5–6 tests, fixtures-for-everything,
  BeautifulSoup, and factory helpers are over-engineering. The interview
  signal is knowing *when* they earn their keep, not insisting on them now.

---

## Concrete Future Failures If Tests Aren't Strengthened

These map directly to the scenarios.

### No Network-Safety Net → Silent Real-API Hits

**Trigger:** Scenario 1 (detail page). You add `reverb.listing(id)` and a new
route `/listings/<id>`. You write a route test, forget to patch
`app.routes.listings.reverb.listing`, but the test asserts only
`response.status_code == 200`.

**What happens:** `httpx.get` fires against `https://api.reverb.com/api/listings/<id>`.
You get a real 200 with real data. The test passes — by accident. Six months
later, Reverb rate-limits CI, every test starts flaking, and you spend an
afternoon discovering tests have been hitting prod.

### No Error-Path Tests → Scenario 5 Has No Foundation

**Trigger:** Scenario 5 (error handling). You decide to add `ReverbError` and
translate `httpx.HTTPStatusError` at the client boundary.

**What happens:** No existing tests pin the current behavior. When you change
`_get` to catch `httpx.HTTPError` and raise `ReverbError`, you have nothing
that says "previously this raised `HTTPStatusError`, now it raises
`ReverbError`." You can't TDD; you can only write-and-hope. **The right move
is to write the three error-path tests against the *current* behavior first,
then refactor them to assert `ReverbError` once you make the change.**

### No Empty-Listings Test → Scenario 5 Empty/Error UX Conflated

**Trigger:** Scenario 5 again. You decide to render the same "No listings
available" message both when the list is genuinely empty *and* when the API
fails. Tests don't distinguish, so the two cases drift apart in the
template (different copy, different element).

**What happens:** Bug reports come in: "the error message looks like the
empty state, users think there's no inventory when actually the API is
down." Tests give you no leverage to fix it, because they never
distinguished the cases.

### No `photos: []` Test → Template Crash In Production

**Trigger:** Reverb returns a listing with `photos: []` (an explicit empty
list) — possible for draft listings or moderation states.

**What happens:** The template does `listing.get("photos", [{}])[0]`. The
`or` default isn't triggered (key is present), so we get `[][0]` →
`IndexError`. Flask returns 500. No test caught it. Tracking it down means
reading the template line-by-line, because the traceback points into
Jinja's compiled code.

### No `per_page` Clamp Tests → Scenario 9 Has No Spec

**Trigger:** You implement the proposed `per_page` clamp (item 7 in the
client improvements). You set `PER_PAGE_MAX = 50` and clamp silently.
Three months later, someone "fixes" it to raise `ValueError` instead.
No test enforces either behavior; the API contract drifts.

**What happens:** A downstream caller that was relying on the silent clamp
starts seeing 500s. Or vice versa. Tests should pin the *chosen* behavior,
not just verify it works once.

---

## Impact on Each Interview Scenario

### Scenario 1: Listing Detail Page

| Test Concern | Concrete Impact |
| --- | --- |
| No autouse `httpx.get` guard | Forgetting to patch `reverb.listing` silently calls the real API in your test (above). |
| Test data as constants | Detail page returns one listing dict, not a list. You can't reuse `LISTINGS`. A `make_listing(**overrides)` factory in `tests/helpers.py` solves this once. |
| Status code assertions | Already in place — good. Keep them in every new test. |

**What to do:** Add `assert response.status_code == 200` first in every new
test. Add the autouse network guard. Extract a `make_listing` helper.

### Scenario 2: Search / Filter Listings

| Test Concern | Concrete Impact |
| --- | --- |
| Param assertions on client | If `query` is forwarded to the API, the client test must `assert_called_once_with(..., params={"per_page": 10, "query": "fender"}, ...)`. The pattern is already established in `test_listings_forwards_per_page` — just extend it. |
| No empty-search test | The route already short-circuits on empty `search`. Mirror that for listings: if the form posts an empty query, what happens? Test it. |

### Scenario 3: Pagination

| Test Concern | Concrete Impact |
| --- | --- |
| Breaking change to client return type | `reverb.listings()` currently returns `response["listings"]`. Pagination needs the surrounding metadata. Update the existing `test_listings_fetches_and_returns_list` test *first* so it fails — that's the contract you're changing. |
| Test data as constants | Pagination needs `{"listings": [...], "total": N, "_links": {...}}`. Without factories, you copy-paste a new constant. With factories, `make_listings_page(items=[...], total=12, page=1)`. |

### Scenario 4: Category → Listings Navigation

| Test Concern | Concrete Impact |
| --- | --- |
| Substring assertions | A test like `b'href="/listings?category=guitars"' in response.data` works but is brittle to template whitespace. A `parse_html().select("a[href*='/listings']")` assertion is sturdier — finally justifies the BeautifulSoup helper. |
| No autouse network guard | Following a link in a multi-step integration test (`client.get` then follow the redirect) — second request calls the listings route, which calls `reverb.listings`. Easy to forget to patch. |

### Scenario 5: Error Handling

| Test Concern | Concrete Impact |
| --- | --- |
| No error-path tests (critical) | This is the scenario that *cannot* be TDD'd without first adding `httpx.HTTPStatusError` / `httpx.TimeoutException` / `httpx.ConnectError` tests to `tests/clients/test_reverb.py`. They're the foundation for the `ReverbError` boundary. |
| No service-layer tests | Once a service module exists, route tests should mock the service (not the client). That shift is invisible if there are no service tests pinning the contract. |
| No empty-listings test | Error UX and empty-state UX must be distinguishable. Without tests, they drift. |

**What to do in the interview:** This is the scenario where you **invest in
the test infrastructure first**. Say out loud:
"Before I implement `ReverbError`, I'm adding three client tests that pin
the current `httpx.*` exceptions. Then I refactor those tests to assert
`ReverbError`, then I make them pass." That's pure TDD. The interview
signal is showing you can sequence test-then-code, not test-after.

### Scenario 6: Price Display + Sort

| Test Concern | Concrete Impact |
| --- | --- |
| Test data as constants | Sort tests need ≥2 listings at different prices. Factory pattern earns its keep. |
| Substring assertions | Asserting `<h2>` order via `b"..." in response.data` doesn't verify *order*. `parse_html().select(".listing-card h2")` returns a list — `[card.get_text() for card in ...]` lets you assert ordering precisely. |
| No malformed-price test | `float(listing["price"]["amount"])` crashes on `None` or `"Call for price"`. Without a test, the bug surfaces in production. Mirror the `null full_name` pattern from categories. |

---

## The Compound Effect (Reframed)

The old walkthrough's compound-effect story was about fixture rigidity
spawning copy-paste fixtures. The 2026 codebase avoids that with `with
patch(...)` blocks inside individual tests. The new compound story is
different and arguably more important:

```text
Scenario 1: Add detail page tests. Factory pattern starts to earn keep.
Scenario 2: Add search tests. Param assertions on client — pattern already there.
Scenario 3: Breaking change to client. Existing test must be updated first.
Scenario 5: Three error tests + service tests + route refactor — all new boundaries.
Scenario 6: Sort tests + price-safety tests + order-of-elements assertions.
```

If you skip the foundational tests early (autouse network guard, error-path
tests, empty states, factories), each subsequent scenario pays a small tax:
a forgotten patch, an inability to TDD, a constant duplicated. Individually
trivial; in aggregate, the difference between "I added five features in
two hours" and "I added three features and one regression."

**Interview signal:** Naming this trade-off, then making the *defensible
choice not to add them all up front* (because the suite is small enough),
is the signal. Adding them all defensively would be over-engineering. Not
naming the trade-off at all would be the failure mode.

---

## Running the Tests

```bash
# Install dev deps
uv sync --dev

# Run all tests
uv run pytest -v

# Run a single file
uv run pytest -v tests/test_listings.py

# Run a single test
uv run pytest -v tests/test_categories.py::test_search_matching_categories_displays_them

# Run only client tests
uv run pytest -v tests/clients/

# Run with print output visible (useful when debugging mock calls)
uv run pytest -vs

# Show what was actually called on a mock (handy in pdb)
# (drop a `breakpoint()` then inspect `mock_get.call_args_list`)
```
