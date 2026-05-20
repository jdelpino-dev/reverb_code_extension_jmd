# Terminology Glossary — Reverb Engineer II (Activation & Retention)

Use these terms precisely during the interview. Main terms are language-agnostic; ecosystem equivalents are noted in descriptions.

---

## Architecture & Design Patterns

### Layered Architecture

A design where code is organized into horizontal layers with clear responsibilities. Each layer only communicates with adjacent layers. Keeps concerns separated and boundaries testable.

- **Python/Flask:** Route → Service helper (`_load_*`) → Client → External API
- **Ruby/Rails:** Controller → Private methods → Client lib → External API
- **React:** Component → API module → `fetch()` → External API

### MVC (Model-View-Controller)

Pattern separating data (Model), presentation (View), and request handling (Controller). The "Model" in this codebase is the API client + response data (no database).

- **Flask:** Route handler (Controller) + Jinja2 template (View) + ReverbClient (Model)
- **Rails:** Controller class + ERB template (View) + Client lib (Model)
- **React:** Component state (Model) + JSX (View) + event handlers (Controller)

### Service Layer

The middle layer between HTTP handling and data access. Coordinates business logic (filtering, pagination, caching) without knowing about HTTP or templates.

- **Flask:** `_load_categories()`, `_search_categories()` helper functions
- **Rails:** Private controller methods or dedicated service objects (`app/services/`)
- **React:** Custom hooks or utility functions that call the API module

### API Client / HTTP Wrapper

A class or module that encapsulates all HTTP concerns (base URL, headers, endpoint paths, response parsing). Provides a clean interface for the rest of the app.

- **Python:** `ReverbClient` class using `requests` library
- **Ruby:** `ReverbClient` class using `HTTParty` gem
- **JavaScript:** `API.js` module using `fetch()`

### Separation of Concerns

Each module/layer/function has one responsibility. HTTP routing does not contain business logic; templates do not call APIs directly.

### Single Responsibility Principle (SRP)

A class or function should have one reason to change. The API client changes only when the external API changes; the route handler changes only when URL structure changes.

### Dependency Injection

Passing dependencies (like an API client) into a function or constructor rather than hard-coding them. Enables testing with mocks.

- **Python:** `ReverbClient(base_uri='...')` — inject base URI; in tests, inject a mock
- **Ruby:** `ReverbClient.new(base_uri: '...')`
- **React:** Props or context for injecting API functions into components

---

## HTTP & Web Fundamentals

### Request/Response Cycle

The full path of a user interaction: browser sends HTTP request → server routes it → handler executes logic → response (HTML/JSON) returned to browser.

### Route / Endpoint

A URL pattern mapped to a handler function. Defines what code runs for a given URL + HTTP method.

- **Flask:** `@app.route('/listings')` decorator
- **Rails:** `resources :listings, only: [:index]` in `config/routes.rb`
- **React Router:** `<Route exact path="/listings" component={ListingsPage} />`
- **Express:** `app.get('/listings', handler)`

### Route Parameter / URL Parameter

A dynamic segment in the URL path, captured as a variable.

- **Flask:** `@app.route('/listings/<listing_id>')` → `def show(listing_id)`
- **Rails:** `/listings/:id` → `params[:id]`
- **Express:** `/listings/:id` → `req.params.id`

### Query Parameter / Query String

Key-value pairs after `?` in a URL (`?page=2&sort=price_asc`). Used for optional filters, pagination, and search.

- **Flask:** `request.args.get('page', 1, type=int)`
- **Rails:** `params[:page]`
- **React:** `useSearchParams()` or `URLSearchParams`
- **Express:** `req.query.page`

### URL-Based State

Encoding UI state (current page, active filters, sort order) in the URL so users can bookmark, share, and use the back button.

### RESTful Routing

Convention-based URL structure for CRUD resources: `GET /resources` (index), `GET /resources/:id` (show), `POST /resources` (create), etc.

- **Rails:** `resources :listings` generates all 7 REST routes automatically
- **Flask:** Manual route definitions following the pattern
- **Express:** Manual or via `express.Router()`

### HTTP Methods (Verbs)

- **GET:** Retrieve data (safe, idempotent)
- **POST:** Create/submit data (not idempotent)
- **PUT/PATCH:** Update existing resource
- **DELETE:** Remove resource

### HTTP Status Codes

- **2xx:** Success (200 OK, 201 Created, 204 No Content)
- **3xx:** Redirect (301 Permanent, 302 Found, 304 Not Modified)
- **4xx:** Client error (400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 422 Unprocessable Entity, 429 Too Many Requests)
- **5xx:** Server error (500 Internal Server Error, 502 Bad Gateway, 503 Service Unavailable)

### Headers

Metadata sent with HTTP requests/responses. Key headers for this codebase:

- `Accept: application/json` — client wants JSON
- `Accept-Version: 3.0` — API version negotiation
- `Content-Type: application/hal+json` — body format is HAL+JSON

### Idempotency

An operation that produces the same result when executed multiple times. GET and PUT are idempotent; POST is not. Important for retry logic.

### Content Negotiation

Client and server agreeing on response format via `Accept` and `Content-Type` headers.

---

## Rendering & Templates

### Server-Side Rendering (SSR)

HTML generated on the server before sending to the browser. Faster initial paint, better SEO, simpler mental model.

- **Flask:** `render_template('listings.html', listings=data)`
- **Rails:** Implicit render of `app/views/listings/index.html.erb`
- **Next.js:** `getServerSideProps()` or Server Components

### Client-Side Rendering (CSR)

Browser downloads JavaScript, then builds the DOM. Better for highly interactive UIs.

- **React:** Components render JSX → virtual DOM → actual DOM
- **Trade-off vs SSR:** Slower initial load, more complex state management, requires loading states

### Template Engine

Processes templates with placeholders, producing final HTML.

- **Flask/Python:** Jinja2 (`{{ variable }}`, `{% for %}`, `{% block %}`)
- **Rails/Ruby:** ERB (`<%= variable %>`, `<% code %>`)
- **React:** JSX (JavaScript XML — `{variable}`, `{items.map(...)}`)

### Template Inheritance / Layout

A base template defines the page shell (head, nav, footer); child templates fill in content blocks.

- **Jinja2:** `{% extends 'base.html' %}` + `{% block content %}`
- **ERB:** `<%= yield %>` in layout + view templates fill the yield
- **React:** Layout components wrapping children via `props.children`

### Auto-Escaping

Template engine automatically escapes HTML special characters (`<`, `>`, `&`, `"`) to prevent XSS. Enabled by default in Jinja2 and ERB.

### Context / Template Variables

Data passed from the handler to the template for rendering.

- **Flask:** `render_template('page.html', listings=data, page=1)`
- **Rails:** Instance variables (`@listings`) automatically available in view
- **React:** Props passed to components, or state from hooks

---

## Testing

### Unit Test

Tests a single function/method in isolation. External dependencies are mocked.

- **Example:** Test that `ReverbClient.listings()` calls the correct URL and returns parsed data

### Integration Test

Tests multiple components working together. In this codebase: a full HTTP request through the route, with the API client mocked.

- **Flask:** `client.get('/listings')` → assert on rendered HTML
- **Rails:** Request specs hitting controller actions
- **React:** `render(<ListingsPage />)` → assert on DOM output

### End-to-End (E2E) Test

Tests the entire system including real external services (or staging). Not practiced in this repo but relevant to discuss.

- **Tools:** Cypress, Playwright, Selenium

### Mock / Stub

Replacing a real dependency with a controlled fake for testing.

- **Python:** `unittest.mock.patch('reverb_client.requests.get')`
- **Ruby/RSpec:** `allow(HTTParty).to receive(:get).and_return(...)`
- **JavaScript/Jest:** `jest.mock('./API')` or `jest.spyOn()`

### Fixture

Reusable test data or setup. Different meaning per ecosystem:

- **pytest:** `@pytest.fixture` — function that provides test data or setup/teardown
- **Rails/RSpec:** `let(:listings) { [...] }` — lazy-evaluated test data
- **Jest:** Setup files or factory functions

### Assertion

A check that a condition is true; the test fails if it's not.

- **Python:** `assert response.status_code == 200`
- **RSpec:** `expect(response).to have_http_status(:ok)`
- **Jest:** `expect(element).toBeInTheDocument()`

### Test Isolation

Each test is independent — no shared mutable state. Tests can run in any order.

### Test Double

Generic term for any fake used in testing (mock, stub, spy, fake, dummy).

### Arrange-Act-Assert (AAA)

Test structure pattern: set up data (Arrange), execute the action (Act), verify results (Assert). In BDD: Given-When-Then.

### Code Coverage

Percentage of code exercised by tests. Useful metric but not a quality guarantee — 100% coverage with bad assertions is meaningless.

### Test-Driven Development (TDD)

Write a failing test first, then implement the minimum code to pass, then refactor. Red → Green → Refactor.

### CSS Selector (in tests)

Using CSS selectors to find elements in rendered HTML for assertions.

- **Python/BeautifulSoup:** `soup.select('.listing-title')`
- **React Testing Library:** `screen.getByRole('heading')`, `screen.getByText('...')`
- **Capybara (Rails):** `page.find('.listing-title')`

---

## Error Handling & Resilience

### Exception / Error

An abnormal condition that disrupts normal flow. Should be caught and handled gracefully.

- **Python:** `raise ApiError("Not found")` / `try: ... except ApiError as e:`
- **Ruby:** `raise ApiError, "Not found"` / `begin ... rescue ApiError => e`
- **JavaScript:** `throw new Error("Not found")` / `try { } catch (e) { }`

### Custom Exception Class

A domain-specific error type that distinguishes expected failures from unexpected crashes.

- **Python:** `class ApiError(Exception): pass`
- **Ruby:** `class ApiError < StandardError; end`
- **JavaScript:** `class ApiError extends Error { }`

### Timeout

Maximum time to wait for an external call before failing. Prevents resource exhaustion.

- **Python/requests:** `requests.get(url, timeout=5)`
- **Ruby/HTTParty:** `HTTParty.get(url, timeout: 5)`
- **JavaScript/fetch:** `AbortController` with `setTimeout`

### Retry with Exponential Backoff

Re-attempting a failed operation with increasing delays (1s → 2s → 4s → 8s) to avoid overwhelming a struggling service. Add random jitter to prevent synchronized retries.

### Circuit Breaker

A pattern that stops calling a failing service after repeated failures. States: Closed (normal) → Open (fail-fast) → Half-Open (test recovery). Prevents cascading failures.

### Graceful Degradation

Showing a useful (if reduced) experience when part of the system fails. E.g., show cached data or a friendly error message instead of a 500 page.

### Flash Message

A one-time UI notification shown after an action (usually on redirect). Used to communicate errors or success.

- **Flask:** `flash("Something went wrong")` + `get_flashed_messages()` in template
- **Rails:** `flash[:alert] = "Something went wrong"` → rendered in layout

### Loading State

UI feedback while waiting for async data. Prevents the user from seeing a blank page.

- **React:** `const [loading, setLoading] = useState(true)` → render spinner
- **SSR:** Not applicable (page loads fully rendered)

### Fail-Fast

Detecting errors early and stopping immediately rather than propagating corrupted state downstream.

---

## Security

### XSS (Cross-Site Scripting)

Attacker injects malicious JavaScript that executes in other users' browsers. Mitigated by output encoding / auto-escaping in templates.

### CSRF (Cross-Site Request Forgery)

Attacker tricks an authenticated user's browser into making unwanted requests. Mitigated by CSRF tokens on state-changing (POST/PUT/DELETE) forms.

- **Flask:** `flask-wtf` provides CSRF protection
- **Rails:** Built-in `authenticity_token` on forms
- **React:** Token in headers for API calls

### SSRF (Server-Side Request Forgery)

Attacker manipulates the server into making requests to unintended internal/external URLs. Mitigate by validating and allowlisting URL parameters.

### SQL Injection

Attacker manipulates database queries via unsanitized input. Mitigated by parameterized queries / ORM. Not directly applicable here (no DB) but relevant to discuss.

### Input Validation

Checking that user input conforms to expected format before processing. Prefer allowlists (known-good values) over blocklists (known-bad values).

- **Flask:** `request.args.get('page', 1, type=int)` — coerces type, ignores invalid
- **Rails:** Strong parameters (`params.permit(:query, :page)`)

### Output Encoding / Escaping

Converting special characters to safe representations before rendering. Prevents XSS.

- **Jinja2:** Auto-escapes `{{ variable }}` — `<script>` becomes `&lt;script&gt;`
- **ERB:** `<%= variable %>` auto-escapes; `<%== variable %>` or `raw()` bypasses (dangerous)
- **React:** JSX auto-escapes by default; `dangerouslySetInnerHTML` bypasses

### Open Redirect

Attacker crafts a URL that redirects users to a malicious site after login. Mitigate by validating redirect targets against an allowlist of internal paths.

### Rate Limiting

Restricting the number of requests a client can make in a time window. Prevents abuse, scraping, and brute-force attacks.

### Defense in Depth

Multiple overlapping security layers so that failure of one control doesn't compromise the system.

### Principle of Least Privilege

Granting only the minimum permissions needed. Applicable to API keys, service accounts, and user roles.

### ReDoS (Regular Expression Denial of Service)

Crafted input causing catastrophic regex backtracking. Mitigate with `re.escape()` on user input or avoiding vulnerable patterns.

---

## API & Data

### HAL (Hypertext Application Language)

A JSON-based hypermedia format. Responses include `_links` with URLs to related resources and navigation (next/prev pages).

### Pagination

Splitting large result sets into pages. Response metadata includes `current_page`, `total_pages`, `per_page`, `total`.

- **Offset-based:** `?page=3&per_page=20` — simple but inconsistent under writes
- **Cursor-based:** `?after=abc123` — stable ordering, better for real-time feeds
- **Keyset:** Use last-seen value as boundary — efficient for sorted data

### API Versioning

Strategies for evolving APIs without breaking existing clients:

- **Header-based:** `Accept-Version: 3.0` (used by Reverb)
- **URL-based:** `/api/v3/listings`
- **Query param:** `?version=3`

### JSON Response Shape

The structure/schema of a JSON response. Knowing field names, nesting, and types before coding prevents surprises.

### Nested Data / Compound Object

Data within data — e.g., `listing.price.display` contains a formatted string, `listing.price.amount` contains a numeric value.

### Deserialization / Parsing

Converting raw response data (JSON string) into native data structures (dict, hash, object).

- **Python:** `response.json()` returns a `dict`
- **Ruby:** `JSON.parse(body)` returns a `Hash`
- **JavaScript:** `response.json()` returns a plain object

### Full-Text Search

Server-side searching across multiple text fields (title, description, etc.) with fuzzy matching. Reverb's API supports `?query=` parameter.

---

## Performance & Scalability

### Caching

Storing computed results to avoid repeated expensive operations.

- **In-memory:** Python `functools.lru_cache`, Ruby `Rails.cache`, React `useMemo`
- **HTTP cache:** `Cache-Control`, `ETag`, `304 Not Modified`
- **External:** Redis, Memcached
- **TTL (Time-To-Live):** How long cached data remains valid

### Debouncing

Delaying execution until a pause in input (e.g., wait 300ms after the user stops typing before firing a search request). Reduces unnecessary API calls.

- **JavaScript:** `setTimeout` + clear on new keystroke, or lodash `_.debounce()`
- **Conceptual in SSR:** Not applicable (form submission is explicit)

### Throttling

Limiting how frequently a function can execute (e.g., max once per 200ms). Unlike debouncing, it fires at regular intervals during continuous activity.

### N+1 Query Problem

Making N additional queries for N items when one query would suffice. Classic ORM issue. Not directly applicable here but shows awareness.

- **Rails:** `includes(:association)` or `eager_load`
- **Python/SQLAlchemy:** `joinedload()` or `subqueryload()`

### Lazy Loading

Deferring data fetching or computation until actually needed. Reduces initial load time.

- **React:** `React.lazy()` + `Suspense` for code-splitting
- **Rails:** `lazy_load` associations
- **Images:** `loading="lazy"` attribute

### Prefetching / Eager Loading

Loading data before it's requested, anticipating the user's next action (e.g., fetch page 2 while viewing page 1).

### Thundering Herd

Many clients simultaneously retrying or requesting the same resource when a service recovers. Mitigated by jitter in backoff and request coalescing.

### Connection Pooling

Reusing existing connections instead of creating new ones per request. Reduces overhead for database and HTTP connections.

---

## State Management

### Component State

UI state local to a single component (loading, form input values, toggle states).

- **React:** `useState()`, `useReducer()`
- **SSR (Flask/Rails):** No client-side state — each page load is stateless

### Application State

State shared across multiple components or pages (authenticated user, cart, theme).

- **React:** Context API, Redux, Zustand
- **SSR:** Session cookies, server-side session store

### URL as State

Using query parameters and path segments as the source of truth for UI state. Enables deep-linking and browser navigation.

### Derived State

State computed from other state rather than stored independently. Avoids duplication and sync bugs.

- **React:** Compute in render, or `useMemo()` for expensive derivations
- **Python:** Computed in the route handler before passing to template

---

## Frontend-Specific Concepts

### Component

A reusable, self-contained UI building block that manages its own rendering and behavior.

- **React:** Function component returning JSX
- **Rails:** Partials (`render partial: 'listing'`)
- **Jinja2:** `{% include 'partial.html' %}` or macros

### Props vs State

- **Props:** Data passed into a component from its parent (read-only)
- **State:** Data managed internally by a component (mutable via setter)

### Hook

A function that lets React components use state and lifecycle features without classes.

- `useState` — local state
- `useEffect` — side effects (API calls, subscriptions)
- `useCallback` / `useMemo` — memoization

### Virtual DOM

React's in-memory representation of the UI. React diffs the virtual DOM against the previous version and applies minimal real DOM updates (reconciliation).

### Client-Side Routing

Navigation handled by JavaScript without full page reloads. The URL changes but the browser doesn't fetch a new HTML document.

- **React Router:** `<Route>`, `<Link>`, `useHistory()`
- **Next.js:** File-based routing with `next/router`

### Conditional Rendering

Showing different UI based on state (loading spinner, error message, empty state, data).

- **React:** `{loading ? <Spinner /> : <DataList />}`
- **Jinja2:** `{% if listings %} ... {% else %} No results {% endif %}`
- **ERB:** `<% if @listings.any? %> ... <% else %> ... <% end %>`

---

## Python / Flask Specifics

### Decorator

A function that wraps another function to extend its behavior. Flask uses decorators for routing.

- `@app.route('/path')` — registers a route
- `@pytest.fixture` — marks a test fixture
- `@functools.lru_cache` — adds memoization

### List Comprehension

Concise syntax for creating filtered/transformed lists: `[x for x in items if condition]`.

### Lambda

Anonymous function: `lambda x: x['price']`. Used for sort keys and filter predicates.

### Dictionary `.get()`

Safe key access with a default: `data.get('price', 0)`. Avoids `KeyError` on missing keys.

### Context Manager

`with` statement for resource management (auto-cleanup). Used in tests for `patch()`.

### F-String

Formatted string literal: `f"Page {page} of {total}"`. Available Python 3.6+.

### Mutable Default Argument (Footgun)

`def f(params={})` — the dict is shared across all calls. Fix: use `None` default and create inside.

### Type Hints

Optional annotations for function signatures: `def listings(per_page: int = 10) -> List[dict]`. In Python 3.8: `from typing import Dict, List` required (no built-in generics).

---

## Ruby / Rails Specifics

### Resourceful Routing

`resources :listings` generates all 7 RESTful routes with conventional controller actions (index, show, new, create, edit, update, destroy).

### Convention over Configuration

Rails philosophy: follow naming conventions and get automatic wiring (controller name → view folder → URL path).

### Instance Variables in Views

`@listings` set in controller is automatically available in the corresponding view template.

### Strong Parameters

`params.permit(:query, :page)` — allowlist of accepted parameters. Prevents mass-assignment vulnerabilities.

### Gems

Ruby packages managed by Bundler (`Gemfile`). Equivalent to Python's pip packages or npm packages.

### RSpec

BDD-style testing framework: `describe`, `context`, `it`, `expect(...).to`.

### Symbols

Lightweight immutable identifiers: `:index`, `:only`. Used extensively in Rails configuration.

---

## JavaScript / React Specifics

### Async/Await

Syntax for handling Promises: `const data = await fetch(url)`. Makes async code read synchronously.

### Promise

An object representing an eventual completion (or failure) of an async operation. States: pending → fulfilled / rejected.

### Destructuring

Extracting values from objects/arrays: `const { listings } = await response.json()`.

### Spread Operator

`...` for copying/merging: `{...obj, newKey: value}` or `[...array, newItem]`.

### JSX

JavaScript XML — HTML-like syntax in React components that compiles to `React.createElement()` calls.

### useEffect

Hook for side effects (data fetching, subscriptions). Runs after render. Dependency array controls when it re-runs.

### act() (in tests)

Wraps code that causes React state updates, ensuring all updates are processed before assertions.

---

## Git & Version Control

### Atomic Commit

A commit containing one logical change. Each commit should leave the codebase in a working state.

### Branch

An isolated line of development. Feature branches keep work-in-progress separate from main.

### Staging / Index

The intermediate area where changes are collected before committing. `git add -p` stages individual hunks.

### Diff

The difference between two versions of a file. Reviewing diffs ensures you commit only intended changes.

### Rebase vs Merge

Two strategies for integrating branches. Rebase creates linear history; merge preserves branch topology.

---

## Software Design Principles

### DRY (Don't Repeat Yourself)

Extract shared logic into a single source of truth. But avoid premature abstraction — duplication is better than the wrong abstraction.

### YAGNI (You Aren't Gonna Need It)

Don't build features until they're actually needed. In an interview context: acknowledge what you'd add in production without over-engineering the solution.

### KISS (Keep It Simple, Stupid)

Prefer the simplest solution that works. Complexity should be justified by requirements.

### Composition over Inheritance

Building complex behavior by combining simpler pieces rather than deep class hierarchies.

- **React:** Composing components via props/children
- **Python:** Mixins or dependency injection
- **Ruby:** Modules and `include`

### Backward Compatibility

New changes don't break existing callers. Add optional parameters with defaults; don't change return types without updating all consumers.

---

## Additional Scenarios (Beyond Practiced)

### Authentication & Authorization

- **Authentication (AuthN):** Verifying identity (login, tokens, sessions)
- **Authorization (AuthZ):** Verifying permissions (roles, policies, access control)
- **Session:** Server-side state tied to a cookie; tracks logged-in user
- **JWT (JSON Web Token):** Stateless auth token containing claims; used in APIs
- **OAuth:** Delegated authorization protocol (sign in with Google/GitHub)

### Database & Persistence

- **ORM (Object-Relational Mapping):** Maps database rows to objects. SQLAlchemy (Python), ActiveRecord (Rails), Prisma/Sequelize (JS).
- **Migration:** Version-controlled database schema changes
- **Transaction:** Group of operations that succeed or fail together (ACID)
- **Index:** Database structure for fast lookups on specific columns
- **Foreign Key:** Column referencing another table's primary key — enforces relationships

### Background Jobs & Async Processing

- **Job Queue:** System for processing work asynchronously (Celery, Sidekiq, Bull)
- **Worker:** Process that picks up and executes queued jobs
- **Idempotent Job:** A job that can safely be retried without side effects
- **Dead Letter Queue (DLQ):** Where failed jobs go after max retries

### Observability

- **Logging:** Recording events for debugging (`logger.info`, `Rails.logger`)
- **Metrics:** Numeric measurements (request latency, error rate, throughput)
- **Tracing:** Following a request across services (distributed tracing)
- **Alerting:** Automated notifications when metrics cross thresholds
- **SLI/SLO/SLA:** Service Level Indicator / Objective / Agreement

### Deployment & Infrastructure

- **CI/CD:** Continuous Integration / Continuous Deployment — automated test + deploy pipeline
- **Blue-Green Deployment:** Two identical environments; switch traffic between them
- **Canary Release:** Rolling out to a small percentage of users first
- **Feature Flag:** Toggle features on/off without deploying new code
- **Container:** Isolated runtime environment (Docker). Image = blueprint; container = running instance
- **Environment Variables:** Configuration injected at runtime, not hard-coded (secrets, URLs, feature flags)

### Event-Driven Architecture

- **Event:** A record of something that happened (UserSignedUp, OrderPlaced)
- **Publisher/Subscriber (Pub/Sub):** Decoupled communication; publisher emits events, subscribers react
- **Webhook:** HTTP callback triggered by an event in another system
- **Event Sourcing:** Storing state as a sequence of events rather than current snapshot

### Microservices & API Design

- **Microservice:** Small, independently deployable service owning one domain
- **API Gateway:** Single entry point routing requests to appropriate services
- **Service Discovery:** How services find each other's network addresses
- **Contract Testing:** Verifying that two services agree on API shape (Pact)
- **GraphQL:** Query language for APIs — client specifies exactly what fields it needs

### Activation & Retention Domain Terms

- **Activation:** The moment a new user first experiences core product value (first purchase, first listing)
- **Retention:** Keeping users engaged and returning over time
- **Onboarding Flow:** Guided steps to get a new user to their "aha moment"
- **Funnel:** Sequence of steps users take toward a conversion (signup → browse → purchase)
- **Conversion Rate:** Percentage of users completing a desired action
- **Churn:** Users who stop using the product
- **Cohort Analysis:** Grouping users by sign-up date to compare retention curves
- **A/B Test (Experiment):** Showing different variants to different user groups to measure impact
- **Feature Adoption:** Percentage of users who use a specific feature
- **Time to Value (TTV):** How quickly a new user reaches meaningful value

---

## Communication & Process Terms

### Trade-Off

A design decision where improving one quality (simplicity, performance, flexibility) comes at the cost of another. Always name both sides: "I chose X because Y, acknowledging the downside is Z."

### Technical Debt

Shortcuts taken now that will cost more to fix later. Acceptable when intentional and documented.

### Refactoring

Changing code structure without changing behavior. Should be backed by tests that verify nothing breaks.

### Spike

A time-boxed exploration to reduce uncertainty before committing to an implementation.

### Iteration

Building incrementally — ship a working version, gather feedback, improve. Contrasted with "big bang" releases.

### Scope Creep

Uncontrolled expansion of requirements during implementation. In an interview: acknowledge future improvements without building them.
