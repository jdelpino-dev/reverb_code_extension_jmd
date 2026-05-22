# Interview Conversation Questionnaire

Practice answering these out loud. Time yourself — each answer should be 30-90 seconds.
Check model answers in `QUESTIONNAIRE_ANSWERS.md` AFTER attempting each one.

______________________________________________________________________

## Part 1: Code Orientation & Architecture

### Q1. "Walk me through what happens when a user visits /categories and submits a search."

**Hints:**

- Start from the route, not the browser
- Name each layer: route → handler → client → API → response → template
- Mention what gets passed between layers

______________________________________________________________________

### Q2. "How is the ReverbClient class structured, and why would you design it this way?"

**Hints:**

- Three-sentence pattern: what / how / why
- Mention testability
- Note what it hides (HTTP details, headers, base URL)

______________________________________________________________________

### Q3. "What do you notice about how tests are organized in this codebase?"

**Hints:**

- Two levels: client unit tests vs. route/integration tests
- What's mocked at each level
- What the tests DON'T cover (useful observation)

______________________________________________________________________

### Q4. "If you were onboarding a new developer to this codebase, what would you point out first?"

**Hints:**

- Entry points (routes)
- External dependency (Reverb API)
- How to run tests
- What's intentionally simple

______________________________________________________________________

## Part 2: Implementation Decisions

### Q5. "You're about to add a new feature. Where do you start?"

**Hints:**

- Think about the order: API client → route → template → tests
- Why start at the data layer?
- Mention running tests early and often

______________________________________________________________________

### Q6. "Should filtering happen on the client or the server? How do you decide?"

**Hints:**

- Data size matters
- UX responsiveness matters
- What happens when the dataset grows?
- What does the API already support?

______________________________________________________________________

### Q7. "You need to add a new parameter to the API client method. How do you handle backward compatibility?"

**Hints:**

- Default arguments
- What happens to existing callers?
- Return type changes are different from parameter additions

______________________________________________________________________

### Q8. "The existing code uses `params={}` as a default argument in Python. What's the issue?"

**Hints:**

- Mutable default argument problem
- When does it actually bite you?
- Should you fix it during the interview? (careful)

______________________________________________________________________

## Part 3: Testing

### Q9. "Walk me through how you'd write a test for a new API client method."

**Hints:**

- What do you mock?
- What do you assert?
- How do you verify the correct URL/params were called?

______________________________________________________________________

### Q10. "Why are we mocking at the HTTP level in client tests but mocking the client class in route tests?"

**Hints:**

- What each test is trying to verify
- Speed / isolation
- If client changes, which tests break?

______________________________________________________________________

### Q11. "How would you test an error case?"

**Hints:**

- What does `pytest.raises` do?
- How do you make the mock return a failure?
- What's the assertion on the route level?

______________________________________________________________________

### Q12. "Your test passes but the feature is broken in the browser. What went wrong?"

**Hints:**

- Mock might not match real API response shape
- Template rendering might have a different data path
- Could be a missing field in the mock data

______________________________________________________________________

## Part 4: Trade-offs & Design

### Q13. "You just implemented the happy path. What would you add next with another 30 minutes?"

**Hints:**

- Error handling
- Edge cases (empty data, missing fields)
- Loading states
- URL state preservation

______________________________________________________________________

### Q14. "How would you handle the case where the external API is slow or down?"

**Hints:**

- Timeout
- Graceful degradation (show message, not 500)
- Where to catch the error (client vs. controller)
- Caching as a longer-term solution

______________________________________________________________________

### Q15. "We want to add pagination. What changes and what stays the same?"

**Hints:**

- Client method signature changes
- Return value changes (metadata needed)
- Template needs new controls
- URL needs to carry page state

______________________________________________________________________

### Q16. "If this app needed to scale to 50 routes, how would you restructure the Python code?"

**Hints:**

- Flask Blueprints
- Separate files per resource
- Factory pattern for app creation
- How Rails does it differently (built-in structure)

______________________________________________________________________

## Part 5: Cross-Language Awareness

### Q17. "How does this Flask app compare to the Rails version?"

**Hints:**

- Explicit vs. convention
- File organization
- Routing approach
- Template syntax similarities

______________________________________________________________________

### Q18. "What would be easier in Rails? What's easier in Flask?"

**Hints:**

- Rails: RESTful routes, resourceful controllers, generators
- Flask: explicitness, traceability, minimal magic
- Think about team size and app complexity

______________________________________________________________________

### Q19. "If Reverb asked you to switch to the Rails version mid-interview, what would transfer and what would you need to look up?"

**Hints:**

- Concepts that transfer: MVC pattern, testing strategy, API client pattern
- Need to look up: Rails-specific DSL, ERB syntax, RSpec matchers
- Be honest about what you know vs. don't

______________________________________________________________________

## Part 6: Collaboration & Communication

### Q20. "You've been coding for 10 minutes and realize your approach has a flaw. What do you do?"

**Hints:**

- Don't panic
- Name the flaw out loud
- Propose the pivot
- Ask if the interviewer agrees

______________________________________________________________________

### Q21. "The interviewer asks 'what if we wanted to do X instead?' How do you respond?"

**Hints:**

- Don't defend your current approach
- Acknowledge the alternative
- Discuss trade-offs
- Ask if they'd like you to switch

______________________________________________________________________

### Q22. "You don't know how a specific API works. What do you do during the interview?"

**Hints:**

- State your assumption
- Ask if you can check (curl, docs)
- Write code against your assumption, note it's unverified
- Don't pretend to know

______________________________________________________________________

### Q23. "The interviewer is silent after you explain something. What does that mean?"

**Hints:**

- Might be waiting for you to continue
- Might be giving you space to self-correct
- Ask: "Does that make sense, or would you like me to elaborate on any part?"
- Don't over-explain to fill silence

______________________________________________________________________

## Part 7: Python-Specific

### Q24. "Explain how `unittest.mock.patch` works in this codebase."

**Hints:**

- What it replaces and where
- The path string (`'reverb_client.requests.get'`) — why this path?
- `.start()` vs context manager
- Return value chaining (`.return_value.json.return_value`)

______________________________________________________________________

### Q25. "What's the difference between `request.args.get('page', 1, type=int)` and just `int(request.args.get('page', 1))`?"

**Hints:**

- What happens with invalid input?
- Error handling built into Flask's version
- Type safety

______________________________________________________________________

### Q26. "How would you add a helper function that's used across multiple routes?"

**Hints:**

- Regular function in `app.py` (current pattern)
- Module import for larger apps
- Flask's `@app.before_request` for cross-cutting concerns
- Compare to Rails' `before_action`

______________________________________________________________________

### Q27. "Why does this app use BeautifulSoup in tests?"

**Hints:**

- What `parse_html` does
- Why not just check `response.data` as a string?
- Structural assertions vs. substring matching
- Compare to Rails' `assert_select`

______________________________________________________________________

## Part 8: "Do You Actually Read Code?" Probes

These are quick, pointed questions the interviewer might ask during the "explain the code" phase. They test whether you've truly read the code rather than skimmed it. Practice answering in 15-30 seconds each.

______________________________________________________________________

### Q28. "Why does the ReverbClient use `application/hal+json` as the Accept header?"

**Hints:**

- HAL = Hypertext Application Language — a JSON format that includes `_links`
- Reverb's API returns hypermedia links (`_links.self`, `_links.next`) in this format
- Without it, you'd get plain JSON without navigation metadata
- Useful for pagination (`_links.next`) and resource self-references

______________________________________________________________________

### Q29. "What happens if `_get` returns a response that has no `listings` key?"

**Hints:**

- `self._get(...)["listings"]` would raise a `KeyError`
- No defensive handling exists — the app would 500
- Is that acceptable? (Depends on trust in the API contract)
- What would you add? (`.get("listings", [])` or explicit error handling)

______________________________________________________________________

### Q30. "Why is `per_page` hardcoded to 10 in the client?"

**Hints:**

- Default argument — callers can override it
- But the route doesn't expose it to the user (no `?per_page=` param)
- Trade-off: simple UI vs. user control
- If you were adding pagination, this would need to change

______________________________________________________________________

### Q31. "Why does `_get` call `.json()` directly without checking the status code?"

**Hints:**

- If the API returns 404 or 500, `.json()` might still parse (error body) or raise
- `requests` doesn't raise on 4xx/5xx by default — you need `.raise_for_status()`
- The current code silently treats error responses as data
- Where would you add the check? (In `_get`, so all callers benefit)

______________________________________________________________________

### Q32. "What's the purpose of `Accept-Version: 3.0` in the headers?"

**Hints:**

- Pins the API to version 3 of Reverb's public API
- Without it, you might get a different response shape if they release v4
- Defensive coding — your parsing logic depends on a known schema
- Similar to specifying API version in a URL path (`/v3/listings`)

______________________________________________________________________

### Q33. "The categories route has two decorators: `@app.route('/')` and `@app.route('/categories')`. Why?"

**Hints:**

- Same handler serves both URLs — the homepage IS the categories page
- Flask allows multiple route decorators on one function
- Alternative: redirect `/` to `/categories` (different trade-off — extra HTTP round-trip)
- SEO consideration: which URL is canonical?

______________________________________________________________________

### Q34. "Why does `_search_categories` filter on the client side instead of passing a query param to the API?"

**Hints:**

- The Reverb categories endpoint (`/categories/flat`) doesn't support a `query` parameter
- Client-side filtering is the only option without a server-side search endpoint
- Trade-off: fine for ~50 categories, would break at 10,000 items
- The listings endpoint DOES support query — different API, different strategy

______________________________________________________________________

### Q35. "What does `load_dotenv()` do and why is it called before `Flask(__name__)`?"

**Hints:**

- Loads `.env` file variables into `os.environ`
- Must run before any `os.environ.get()` calls (like `FLASK_SECRET_KEY`)
- In production, environment variables are set by the platform — `.env` is dev-only
- If called after `app = Flask(...)`, the secret key lookup would fail

______________________________________________________________________

### Q36. "Why does the app set `app.secret_key`? What uses it?"

**Hints:**

- `flash()` messages require a session, sessions require a secret key
- Without it, Flask raises a RuntimeError when you call `flash()`
- The fallback `"dev-only-secret"` is insecure — fine for dev, not production
- In production: generate a random key, store in environment variable

______________________________________________________________________

### Q37. "The `flash()` call uses category `'warning'` and `'info'`. Where do those end up?"

**Hints:**

- In the template via `get_flashed_messages(with_categories=true)`
- The category string maps to a CSS class for styling
- It's a convention, not enforced — you could use any string
- Look at `base.html` to see how flash messages render
