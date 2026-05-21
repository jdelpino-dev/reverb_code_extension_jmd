# Questionnaire — Model Answers

______________________________________________________________________

## Q1. "Walk me through what happens when a user visits /categories and submits a search."

"When a user hits `/categories?query=guitar`, Flask matches it to the `categories` route function in `app.py`. That function reads `query` from `request.args`, then calls `_search_categories(query)`. That helper calls `_load_categories()`, which instantiates `ReverbClient` and calls `.categories()`. The client makes a GET to `https://api.reverb.com/api/categories/flat` with JSON headers. The response comes back as a list of category dicts. We filter them in Python using a lambda that checks if the query string appears in each category's `full_name` (case-insensitive). The filtered list gets passed to `render_template('categories.html', categories=...)`, which iterates over them in Jinja2 and renders each as a list item. If no matches, the template shows a 'no results' message."

**Key points hit:** route -> service -> client -> HTTP call -> filter logic -> template render -> conditional display.

______________________________________________________________________

## Q2. "How is the ReverbClient class structured, and why would you design it this way?"

"It's a thin wrapper around the Reverb public API. It knows the base URL, the required headers (Accept, Accept-Version, Content-Type), and exposes one method per resource -- `categories()` and `listings()`. Internally it has a `_get` helper that builds the full URL, makes the HTTP request via the `requests` library, and parses JSON.

The design isolates all HTTP concerns in one place. If the API changes its headers or versioning, there's one file to update. For testing, I can mock `requests.get` in a single location and all route tests get predictable data without hitting the network."

______________________________________________________________________

## Q3. "What do you notice about how tests are organized in this codebase?"

"There are two test levels. First, `test_reverb_client.py` tests the client class directly — it mocks `requests.get` at the HTTP level and verifies the client returns correctly shaped data. Second, `test_categories.py` and `test_listings.py` are integration-level — they use Flask's test client to hit routes and assert on rendered HTML using BeautifulSoup.

The integration tests also mock `requests.get`, so they're still fast and offline. What they DON'T test: error paths, edge cases (empty photos array, missing fields), or what happens when the API is slow. That's where I'd extend."

______________________________________________________________________

## Q4. "If you were onboarding a new developer to this codebase, what would you point out first?"

"I'd start with `app.py` -- it's the entire application in one file. Two routes: `/categories` and `/listings`. Both follow the same pattern: read params, call `ReverbClient`, render a template.

Then I'd show `reverb_client.py` -- the only external dependency. Then the templates to see how data becomes HTML. Finally, I'd point them at the tests and show how to run them: `pipenv run pytest -vs`. The app is intentionally simple -- no database, no auth, no ORM. All data comes from the Reverb public API."

______________________________________________________________________

## Q5. "You're about to add a new feature. Where do you start?"

"I start at the data layer — the API client. That's the foundation everything else depends on. I add the method, write a quick test for it to verify I'm getting the right response shape. Then I add the route that calls it. Then the template that renders the data. Finally I write the integration test.

This order means I'm never writing UI code against imaginary data. Each step builds on a working layer below it. I also run tests after each step so I catch issues immediately rather than debugging a full stack of new code."

______________________________________________________________________

## Q6. "Should filtering happen on the client or the server? How do you decide?"

"It depends on the data volume and UX requirements. For categories — there are maybe a few hundred — client-side filtering is fine. You load them all once and filter is instant.

For listings — potentially thousands — server-side is better. The API supports a `query` param that does full-text search, which is more capable than substring matching on titles. The trade-off is latency per search. If it were as-you-type, I'd debounce at 300ms. Since this codebase uses a submit button, that's not an issue — each search is explicit.

I'd also consider URL state: putting the query in `?query=fender` means the search is shareable and survives page refresh."

______________________________________________________________________

## Q7. "You need to add a new parameter to the API client method. How do you handle backward compatibility?"

"I use a keyword argument with a default value. For example, changing `def listings(self, per_page=10)` to `def listings(self, per_page=10, query=None)`. Existing callers that don't pass `query` get the same behavior as before — `None` means the param isn't sent to the API.

The trickier case is changing the return type. If I need to return pagination metadata, the method currently returns just the listings list. Changing it to return the full response dict breaks every caller. In that case, I'd update all callers at the same time — in this small codebase that's just one route — and update the tests to match."

______________________________________________________________________

## Q8. "The existing code uses `params={}` as a default argument in Python. What's the issue?"

"Mutable default arguments in Python are evaluated once at function definition time, not at each call. If you ever mutated that dict (like `params['new_key'] = value`), the mutation persists across calls. It's a classic Python gotcha.

In this codebase, the `_get` method uses `params={}` but passes it directly to `requests.get` without mutating it, so it's not causing bugs right now. The safer pattern is `params=None` then `if params is None: params = {}` inside the body.

Would I fix it during the interview? Yes -- it's a one-line change that eliminates a latent bug. I'd say: 'This is a classic Python gotcha -- let me fix it now since I'm about to add code that passes params through this method.'"

______________________________________________________________________

## Q9. "Walk me through how you'd write a test for a new API client method."

"Say I'm adding `listing(self, listing_id)`. My test:

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

I mock `requests.get` at the module level where it's imported. I set up the return value to match the real API shape. Then I call the method and assert two things: the returned data is correct, and the right URL was called. This gives me confidence the method works without hitting the network."

______________________________________________________________________

## Q10. "Why are we mocking at the HTTP level in client tests but mocking the client class in route tests?"

"Actually, both levels currently mock at the same point: `reverb_client.requests.get`. This means route tests are really integration tests -- they exercise the full path from route through service through client. That's fine for this scope since it catches real integration bugs like template/dict key mismatches.

Ideally, client tests would mock `requests.get` while route tests mock the client class. That way API URL changes only break client tests, and template changes only break route tests. They don't cascade. With 5 tests and 2 routes, the current shared approach is pragmatic -- but it would need to change for error handling tests where you need different mock behaviors at different layers."

______________________________________________________________________

## Q11. "How would you test an error case?"

"Two levels. At the client level:

```python
def test_raises_on_500():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.ok = False
    mock_get.return_value.status_code = 500

    with pytest.raises(ApiError):
        ReverbClient().listings()
```

I set `response.ok = False` on the mock, then assert the exception is raised.

At the route level, I'd mock the client to raise and verify the page still renders with an error message:

```python
def test_shows_error_on_failure():
    # mock that raises ApiError
    res = client.get('/listings')
    assert res.status_code == 200  # page renders, not a 500
    assert 'Unable to load' in parse_html(res).body.text
```

The key insight: the route test verifies graceful degradation, not the error-raising logic."

______________________________________________________________________

## Q12. "Your test passes but the feature is broken in the browser. What went wrong?"

"Most likely my mock data doesn't match the real API response shape. For example, if the real API returns `listing.photos[0]._links.large_crop.href` but my mock only has `thumbnail`, the test passes against my simplified mock but the template crashes on real data.

To catch this: I'd do a real `curl` against the API, look at the actual response shape, and make my mock match it exactly. The existing tests in this codebase are a bit loose — they only include the fields they assert on. In production, I'd use recorded API responses (fixtures) or add integration tests that hit the real API in a CI environment."

______________________________________________________________________

## Q13. "You just implemented the happy path. What would you add next with another 30 minutes?"

**Context:** This is a portable follow-up question — the interviewer asks it *after* you finish implementing any feature (listing detail page, search, pagination, etc.). "The happy path" refers to whatever you just built working correctly with ideal inputs. The question tests whether you can prioritize incremental robustness improvements beyond the success case.

"Assuming I just got the feature working end-to-end with valid data, here's what I'd add in order of impact:

1. **Error handling** — what if the API returns 500? Show a user-friendly message, not an unhandled exception. This means adding `try/except` around the client call in the route handler and rendering the page with an error banner.
2. **Empty state** — what if there are zero results? Don't show a blank page. Add a conditional in the template: 'No listings found' or 'Try a different search.'
3. **Loading feedback** — not relevant for server-rendered (the page loads synchronously), but for the React version I'd add a spinner or skeleton while the fetch is in flight.
4. **URL state** — make sure filters/pages are in the URL so back button and sharing work. For Flask this is already natural (`request.args`), but I'd verify the form preserves query params on submission.

I wouldn't touch caching, retries, or architectural refactoring — those are valuable conversations but not 30-minute implementations."

**Side note — relationship to scenarios and tests:**

- This question is the *conceptual prelude* to Scenario 5 (`scenario-5-error-handling.md`), which asks you to actually implement error handling and loading states. If you get Q13 in conversation, Scenario 5 is what doing it looks like in code.
- The existing tests (`test_categories.py`, `test_listings.py`) only cover the happy path — successful API responses with valid data. Q13 is essentially asking: "What's missing from those tests?" The answer maps directly to tests you'd write: mock a 500 response and assert the page still renders (see Q11's code example), mock an empty list and assert the 'no results' message appears.
- Items 1–2 from this answer connect to Q11 (testing error cases) and Q14 (handling slow/down APIs). The questionnaire is designed so these questions build on each other.

______________________________________________________________________

## Q14. "How would you handle the case where the external API is slow or down?"

"Three layers of defense:

1. **Timeout** — `requests.get(..., timeout=5)`. Don't let a slow API hang the user's request indefinitely.
2. **Exception handling** — Catch `requests.Timeout` and `ConnectionError` in the client, raise a domain-specific `ApiError`.
3. **Graceful UI** — In the route handler, catch `ApiError`, show a user-friendly message, render the page with empty data.

Longer-term: cache responses for endpoints that rarely change (categories). Use a circuit breaker if failures are sustained — that's a pattern where after N consecutive failures, you stop calling the API entirely for a cooldown period (e.g., 30 seconds) and return a cached/fallback response immediately. This prevents hammering a struggling service and lets it recover. After the cooldown, you let one request through to test if the service is back ('half-open' state). But those are 'with more time' answers, not interview-scope implementations."

______________________________________________________________________

## Q15. "We want to add pagination. What changes and what stays the same?"

"**Changes:**

- Client method adds a `page` parameter
- Client return value changes from `response['listings']` to the full response (need metadata)
- Route handler reads `page` from query params, passes it to client, extracts metadata
- Template gets pagination controls (prev/next links with page param in URL)
- Tests need updated mocks with pagination fields

**Stays the same:**

- The `_get` helper method
- Template rendering of individual listing items
- Test structure and mocking approach
- URL scheme (`/listings?page=2`)

The biggest design decision is changing the client's return type — that's a breaking change that requires updating all callers."

______________________________________________________________________

## Q16. "If this app needed to scale to 50 routes, how would you restructure the Python code?"

"Flask Blueprints. I'd split routes by resource:

```plaintext
app/
  __init__.py          # create_app factory
  categories/
    routes.py          # Blueprint with /categories routes
  listings/
    routes.py          # Blueprint with /listings routes
  clients/
    reverb_client.py   # Shared API client
  templates/
    categories/
    listings/
```

Each Blueprint is like a mini-app that gets registered on the main app. This is analogous to Rails' `app/controllers/` directory — each controller file handles one resource. Flask doesn't give you this structure for free like Rails does, but it scales fine once you set it up."

______________________________________________________________________

## Q17. "How does this Flask app compare to the Rails version?"

"Same architecture, different idioms:

- **Routing**: Rails has a DSL (`resources :listings`) that generates 7 RESTful routes. Flask uses explicit `@app.route` decorators — one per endpoint.
- **Controllers**: Rails separates controllers into classes with action methods. Flask keeps route functions flat in `app.py`.
- **Templates**: ERB (`<%= %>`) vs Jinja2 (`{{ }}`). Inheritance is `yield` in Rails vs `{% block %}` in Jinja2. Very similar otherwise.
- **Data passing**: Rails uses instance variables (`@listings`) that are implicitly available in templates. Flask explicitly passes kwargs to `render_template`.
- **Testing**: RSpec + WebMock vs pytest + unittest.mock. Same mock-the-HTTP pattern.

The Rails version has more files but less explicit wiring. The Flask version is more traceable but more verbose."

______________________________________________________________________

## Q18. "What would be easier in Rails? What's easier in Flask?"

"**Easier in Rails:**

- Adding RESTful routes — `resources :listings` gives you index, show, create, etc. automatically
- File organization at scale — conventions tell you where everything goes
- View helpers like `link_to`, `form_tag` — less raw HTML to write
- Adding a new resource follows a pattern: `rails generate controller`

**Easier in Flask:**

- Understanding the full request flow — no magic, every step is explicit
- Single-file apps — for this scope, having everything in `app.py` is actually nice
- Testing — `unittest.mock` is stdlib, no extra gems. Flask test client is simple.
- Debugging — fewer layers of indirection to trace through

For a 3-route app like this, Flask is arguably simpler. For a 50-route production app, Rails' conventions pay off."

______________________________________________________________________

## Q19. "If Reverb asked you to switch to the Rails version mid-interview, what would transfer and what would you need to look up?"

"**Transfers directly:**

- The architecture: client wrapper → controller → template pattern
- Testing philosophy: mock HTTP in client tests, mock client in controller tests
- The Reverb API knowledge — same endpoints regardless of language
- Problem-solving approach: start at data layer, build up

**Would need to look up:**

- RSpec syntax (matchers like `expect(x).to eq(y)`, `assert_select`)
- ERB template syntax (mostly minor: `<%= %>` vs `{{ }}`)
- Rails routing DSL details
- WebMock syntax for stubbing

**Would say to interviewer:** 'I'm more fluent in Python, but the patterns are the same. I might need a moment to check syntax, but the approach and architecture translate directly.'"

______________________________________________________________________

## Q20. "You've been coding for 10 minutes and realize your approach has a flaw. What do you do?"

"I say it out loud immediately: 'Actually, I just realized this won't work because (specific reason).' Then I propose the correction: 'I think the better approach is (alternative). Let me refactor this.'

I don't try to make the flawed approach work. I don't pretend I didn't notice. The interviewer wants to see how I recover, not that I'm perfect. Pivoting cleanly shows maturity.

If it's a small issue (wrong variable name, missing param), I fix inline and mention it. If it's architectural (wrong level of abstraction, wrong return type), I pause, explain the change, and ask if the interviewer agrees before refactoring."

______________________________________________________________________

## Q21. "The interviewer asks 'what if we wanted to do X instead?' How do you respond?"

"I don't get defensive about my current approach. I say: 'That's a good alternative. The trade-off would be (comparison).' Then I ask: 'Would you like me to switch to that approach, or discuss it and continue with what I have?'

This shows I can hold multiple solutions in mind, evaluate trade-offs, and take direction. If they say 'switch,' I switch cleanly. If they say 'keep going,' I note the alternative as something I'd revisit with more time."

______________________________________________________________________

## Q22. "You don't know how a specific API works. What do you do during the interview?"

"I state my assumption: 'I expect this endpoint returns a listing object with title, price, and photos. Let me write code against that assumption.'

If the environment allows it: 'Can I do a quick curl to check the response shape?' This takes 10 seconds and prevents building on wrong assumptions.

If not: I code against my assumed shape, add a comment like `# assuming API returns {listing: {...}}`, and mention: 'I'd verify this against the real response before shipping. If the shape is different, the fix is just updating the key path here.'"

______________________________________________________________________

## Q23. "The interviewer is silent after you explain something. What does that mean?"

"Usually it means they're satisfied and waiting for me to continue. I pause briefly (3-5 seconds), then ask: 'Shall I move on to implementation?' or 'Does that answer your question, or would you like me to go deeper on any part?'

I don't fill silence with rambling. I don't repeat myself. I don't assume they're confused. Most likely they're taking notes or thinking about the next question.

If I'm genuinely unsure whether I answered correctly, I'll say: 'I want to make sure I addressed what you were asking — was that what you were looking for?'"

______________________________________________________________________

## Q24. "Explain how `unittest.mock.patch` works in this codebase."

"`patch('reverb_client.requests.get')` replaces the `requests.get` function *as seen from the `reverb_client` module*. The path string matters — it's not `'requests.get'` globally, it's the reference in the module where it's used.

When you call `.start()`, it activates the patch and returns a `MagicMock` object. You then set up the mock's return chain: `mock_get.return_value.json.return_value = {...}`. This means when code calls `requests.get(url).json()`, it gets your dict back.

The chain works because: `requests.get(...)` returns `mock_get.return_value` (a Mock), then calling `.json()` on that returns `mock_get.return_value.json.return_value` (your dict).

Important: `.start()` stays active until `.stop()` is called or the test ends. In these tests, pytest handles cleanup automatically."

______________________________________________________________________

## Q25. "What's the difference between `request.args.get('page', 1, type=int)` and just `int(request.args.get('page', 1))`?"

"Flask's `type=int` version is safer. If the query param is `?page=abc`:

- `request.args.get('page', 1, type=int)` → returns `1` (the default, because conversion failed)
- `int(request.args.get('page', 1))` → raises `ValueError` and crashes the request

Flask's version treats type conversion failure the same as a missing param — it returns the default. This gives you input validation for free without try/except. It's especially important since query params come from user input and can be anything."

______________________________________________________________________

## Q26. "How would you add a helper function that's used across multiple routes?"

"For this codebase, a plain function in `app.py` works — that's what `_search_categories` already is. The underscore convention signals 'private/internal.'

For cross-cutting concerns (like adding a header to every response, or logging), I'd use Flask's `@app.before_request` or `@app.after_request` decorators.

For larger apps, I'd extract helpers into a separate module: `helpers.py` or a utils package. Import where needed.

In Rails, the equivalent would be `before_action` for request-level hooks, or `ApplicationController` methods for shared logic. Flask doesn't have an ApplicationController, but `@app.before_request` serves the same purpose."

______________________________________________________________________

## Q27. "Why does this app use BeautifulSoup in tests?"

"The `parse_html` helper wraps responses in BeautifulSoup so tests can make structural assertions about the HTML — like 'there's a `ul.list-group` containing an `li` with this text.'

The alternative is substring matching: `assert 'Guitars' in response.data`. That's fragile — it passes even if 'Guitars' appears in the wrong place (a nav link, a title, an error message).

BeautifulSoup lets you assert on DOM structure: 'the first `h2` inside `ul.list-group > li` contains this text.' That's more precise and mirrors what the user actually sees.

This is analogous to Rails' `assert_select` helper, which does the same thing with CSS selectors. Both are more reliable than string matching for HTML output."
