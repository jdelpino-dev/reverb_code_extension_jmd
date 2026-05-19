# Interview Meta-Skills Practice Guide

Separate from the 6 feature scenarios, these are the general skills to drill.
Practice these BEFORE doing the feature scenarios — they're the foundation.

______________________________________________________________________

## 1. Code Reading & Orientation (First 3 Minutes)

### What interviewers are watching for

- Do you panic or stay methodical?
- Do you start from the entry point or randomly open files?
- Can you trace a request end-to-end without running the app?

### Practice drill

Set a timer for 3 minutes. Open the repo cold. Narrate out loud:

1. "I'll start with the routes to see what endpoints exist"
2. "This route maps to this controller/handler"
3. "The controller calls a client class that wraps the external API"
4. "The response gets passed to a template/component that renders it"

### Things to name explicitly

- Framework being used and version signals (Rails 5, Flask, CRA)
- The data flow: HTTP request → route → controller → API client → response → template
- Test strategy: what's mocked, what's integrated
- What's intentionally missing (error handling, caching, auth)

______________________________________________________________________

## 2. Explaining Architecture Out Loud

### The "three sentence" pattern

Use this structure every time you explain a component:

1. **What it does** — "This class wraps the Reverb API and returns parsed JSON"
2. **How it does it** — "It uses HTTParty/requests/fetch with versioned headers"
3. **Why this way** — "Centralizing the client means tests can stub one place"

### Practice phrases for common observations

| Observation | How to say it |
| -- | -- |
| Missing error handling | "I notice there's no rescue/try-catch here — the happy path is clear, so that's probably where I'd start extending" |
| No caching | "Every page load hits the API. For an interview app that's fine, but in production I'd consider caching categories since they rarely change" |
| Tight coupling | "The controller instantiates the client directly — you could inject it, but for this scale it's fine" |
| No auth | "The public API doesn't require auth for read-only endpoints, which keeps this simple" |

### Anti-patterns to avoid

- Don't critique the code unprompted ("this should be refactored...")
- Don't over-explain basics ("so Rails is an MVC framework...")
- Don't stay silent while reading — narrate your thought process

______________________________________________________________________

## 3. Command Line & Tooling Fluency

### Before the interview, verify you can

```bash
# Navigate quickly
cd ruby && ls app/controllers/
grep -r "def " app/controllers/

# Run tests
bin/rspec                          # Ruby
pipenv run pytest -vs              # Python
yarn test                          # React

# Run single test file
bin/rspec spec/requests/listings_spec.rb
pipenv run pytest -vs tests/test_listings.py
yarn test --testPathPattern=ListingsPage

# Start server
rails s                            # Ruby
pipenv run flask run --reload      # Python
yarn start                         # React

# Quick API check (useful to explore available fields)
curl -s -H "Accept: application/json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/listings/all?per_page=1" | python3 -m json.tool | head -50

# Git workflow during interview
git checkout -b feature/detail-page
git add -p                         # stage hunks selectively
git commit -m "Add listing detail endpoint to client"
```

### Key shortcuts to have ready

- Jump to definition / find references in your editor
- Split panes: code + test side-by-side
- Terminal: run tests without leaving editor
- Quick file search by name

______________________________________________________________________

## 4. Testing Workflow

### The pattern the codebase uses

All three stacks follow the same testing philosophy:

1. **Mock the external HTTP call** (WebMock / unittest.mock.patch / jest.fn)
2. **Exercise the unit** (client method / route / component)
3. **Assert on the output** (parsed data / rendered HTML / DOM nodes)

### When you add a feature, test in this order

1. **Client test first** — stub HTTP, assert returned data shape
2. **Integration/request test** — stub the client class, assert rendered output
3. **Only then** worry about edge cases

### Phrases for discussing tests

- "I'll start with a test for the client method since that's the new IO boundary"
- "I'm stubbing at the client level here so the request spec focuses on rendering logic"
- "This test is fast because it never hits the network"
- "If I had more time I'd add a test for the 404 case"

### Quick patterns to memorize

**Ruby (RSpec + WebMock):**

```ruby
stub_request(:get, "https://api.reverb.com/api/listings/123")
  .to_return(status: 200, body: { listing: { title: 'Test' } }.to_json)
```

**Python (unittest.mock):**

```python
mock_get = patch('reverb_client.requests.get').start()
mock_get.return_value.json.return_value = {'listing': {'title': 'Test'}}
```

**React (Jest):**

```javascript
jest.spyOn(API, 'fetchListing').mockImplementation(() =>
  Promise.resolve({ listing: { title: 'Test' } })
);
```

______________________________________________________________________

## 5. Trade-off Discussions

### Framework: ALWAYS use this structure

1. **State what you chose** — "I put the filter on the server side"
2. **Name the alternative** — "You could also filter client-side"
3. **Explain your reasoning** — "Server-side means less data over the wire for large sets"
4. **Acknowledge the downside** — "But it means a round-trip for every keystroke unless we debounce"

### Common trade-offs they'll probe

| Decision | Pro | Con |
| -- | -- | -- |
| Client-side filtering | Instant UI response, no extra requests | Needs all data loaded upfront, heavy on large sets |
| Server-side filtering | Works at any scale | Latency per query, need debounce/submit |
| Separate API client class | Testable, single responsibility | Extra abstraction for small apps |
| Inline fetch in component | Simple, fewer files | Harder to test, can't reuse |
| Loading spinner | Clear feedback | Can flash if response is fast |
| Skeleton screen | Feels faster | More complex to implement |
| Caching API responses | Faster repeat visits | Stale data, invalidation complexity |
| URL-based state (query params) | Shareable, back-button works | More wiring |

### Phrases that show maturity

- "For this scope it's fine, but at scale I'd..."
- "The trade-off here is between `X` and `Y` — I chose `X` because..."
- "I'm keeping it simple now but the interface is open for extension"
- "I'd want to understand the usage pattern before optimizing this"

______________________________________________________________________

## 6. Asking Good Questions Back

Interviewers want dialogue, not just execution. Ask things like:

- "Should the search be instant (as-you-type) or on submit?"
- "Do we care about the URL reflecting filter state?"
- "Is there a specific listing field you'd like displayed, or should I pick a reasonable set?"
- "Should I handle the empty state, or focus on the happy path first?"
- "Do you want me to write the test first or implement then test?"

______________________________________________________________________

## 7. Pacing & Time Management

Typical 45-minute interview breakdown:

| Phase | Time | What to do |
| -- | -- | -- |
| Intro/orientation | 0-5 min | Read code, ask clarifying questions |
| Explain architecture | 5-10 min | Walk through the request flow |
| Implement feature | 10-35 min | Code iteratively, talk while coding |
| Test | 35-42 min | Add at least one meaningful test |
| Wrap-up discussion | 42-45 min | Trade-offs, what you'd do next |

### If you get stuck

1. Say "Let me think about this for a moment" (silence is fine for 10-15 seconds)
2. Re-read the relevant code — don't guess
3. State your hypothesis: "I think the issue is X, let me verify"
4. Ask the interviewer: "Can I check — does this API return nested or flat?"

### If you finish early

Don't gold-plate. Instead:

- Add a test for an edge case
- Mention what you'd add next
- Clean up any TODO comments you left

______________________________________________________________________

## 8. Pre-Interview Checklist

- [ ] Editor configured: can open files, navigate, split panes
- [ ] Terminal accessible within editor
- [ ] Can run tests for your chosen stack without Googling the command
- [ ] Familiar with the Reverb API response shapes (do a live curl)
- [ ] Practiced explaining the architecture flow out loud (record yourself)
- [ ] Have 2-3 clarifying questions ready for any feature ask
- [ ] Know the mock/stub pattern cold for your stack

______________________________________________________________________

## 9. Python/Flask Deep Dive (Your Interview Stack)

### Flask mental model — what to say when explaining

"Flask is a micro-framework. Unlike Rails which is convention-over-configuration with a full MVC stack, Flask gives you a request dispatcher and a template engine. Everything else — ORM, forms, auth — you add explicitly. This app uses just the core: route decorators, `render_template`, and `request` for params."

### Python file layout (this repo)

```plaintext
app.py              ← All routes (equivalent to routes.rb + controllers)
reverb_client.py    ← API wrapper (equivalent to lib/reverb_client.rb)
templates/          ← Jinja2 templates (equivalent to app/views/)
  base.html         ← Layout
  categories.html   ← Category page
  listings.html     ← Listings page
tests/
  helpers.py        ← Test utilities (parse_html)
  test_categories.py
  test_listings.py
  test_reverb_client.py
```

### Key Flask patterns to know cold

```python
# 1. Route with URL param
@app.route('/listings/<listing_id>')
def listing_detail(listing_id):
    ...

# 2. Query string access
request.args.get('query')           # returns None if absent
request.args.get('page', 1, type=int)  # with default + type coercion

# 3. Render template with context
return render_template('listings.html', listings=results, page=page)

# 4. Redirect
from flask import redirect, url_for
return redirect(url_for('listings', category='guitars'))

# 5. Flash messages (for errors)
from flask import flash
flash("Something went wrong")
# In template: {% for msg in get_flashed_messages() %} ... {% endfor %}
```

### Jinja2 essentials

```html
{# Variable output #}
{{ listing['title'] }}

{# Loop #}
{% for item in listings %}...{% endfor %}

{# Conditional #}
{% if listings %}...{% elif query %}...{% endif %}

{# Template inheritance #}
{% extends 'base.html' %}
{% block content %}...{% endblock %}

{# URL generation #}
{{ url_for('listings', category='guitars') }}
```

### pytest patterns for this codebase

```python
# Fixture for test client + mocked API
@pytest.fixture
def client():
    app.config['TESTING'] = True
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = { ... }
    with app.test_client() as client:
        yield client

# Route test
def test_listings_page(client):
    res = client.get('/listings')
    html = parse_html(res)
    assert html.body.select_one('h2').text == 'Expected Title'

# Client unit test (no fixture needed)
def test_fetches_listing():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {'listing': {'title': 'Test'}}
    result = ReverbClient().listing('123')
    assert result['title'] == 'Test'

# Run one test
# pipenv run pytest -vs tests/test_listings.py::test_displays_listings
```

### Common Python interview mistakes to avoid

- Forgetting `self` in method definitions
- Using mutable default arg (`params={}`) — the codebase does this, note it but don't refactor mid-interview
- Forgetting to `.start()` the patch
- Not importing `patch` from `unittest.mock`
- Forgetting `type=int` on `request.args.get` for numeric params

______________________________________________________________________

## 10. Python vs Ruby/Rails — Side-by-Side Comparison

Since Reverb is a Rails shop and you're learning Ruby, use these comparisons to show cross-language awareness during discussion.

### Conceptual mapping

| Concept | Rails | Flask | Notes |
| -- | -- | -- | -- |
| Route definition | `routes.rb` DSL | `@app.route` decorator | Rails separates routing from handlers |
| Controller | `class FooController` | Function decorated with route | Flask has no controller class by default |
| Action | `def index` method | Route function | Same concept, different organization |
| View/Template | ERB (`<%= %>`) | Jinja2 (`{{ }}`) | Very similar syntax, different delimiters |
| Layout | `application.html.erb` + `yield` | `base.html` + `{% block %}` | Template inheritance vs yield |
| Params | `params[:key]` (HashWithIndifferentAccess) | `request.args.get('key')` | Rails merges all params; Flask separates query/form/url |
| URL helper | `listings_path(page: 2)` | `url_for('listings', page=2)` | Both generate URLs from route names |
| Test HTTP mock | WebMock `stub_request` | `unittest.mock.patch` | WebMock is HTTP-specific; mock is general-purpose |
| Test client | RSpec request spec `get path` | Flask `app.test_client().get(path)` | Similar API |
| Instance var to template | `@listings` | Passed as kwarg to `render_template` | Rails uses instance vars implicitly |
| Strong params | `params.require(:x).permit(:y)` | N/A (no ORM) | Only relevant with DB writes |
| Dependency | Gemfile + Bundler | Pipfile + pipenv | Same concept |

### Things to say that show cross-language awareness

- "In Rails this would be a `before_action` — in Flask I'd use a decorator or just call it at the top of the route function"
- "Rails would do `respond_to` for content negotiation — here I'd check the `Accept` header manually or use Flask's `jsonify`"
- "The Rails equivalent of this test fixture would be a `let` block in RSpec with `instance_double`"
- "Flask doesn't have Rails' magic — I have to explicitly pass variables to templates, which is actually nice for readability"

### Where Python/Flask shines vs Rails (good for trade-off discussions)

- **Explicitness**: No magic — you can trace every variable from route → template
- **Lightweight**: No ORM, migrations, or generators for this scope of app
- **Testing**: `unittest.mock` is powerful and built-in (no extra gems)
- **Learning curve**: Fewer conventions to memorize

### Where Rails would be better (acknowledge the trade-off)

- **Convention**: RESTful routes, resourceful controllers — less boilerplate for CRUD
- **Ecosystem**: ActiveRecord, Action Cable, ActiveJob — batteries included
- **Scaling the team**: Conventions mean everyone writes similar code
- **This codebase**: If it grew, Flask would need structure (Blueprints, factory pattern) that Rails gives you for free
