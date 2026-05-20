# Scenario 5: Error Handling & Loading States

## The Ask

> "What happens if the API is slow or returns an error? Add loading and error states."

Tests defensive programming thinking and UX awareness. Very likely as a follow-up extension.

______________________________________________________________________

## Phase 1: Explain

"Right now if the API fails, Ruby/Python will raise an unhandled exception and show a 500 page. React will silently fail — the listings array stays empty with no feedback. There's also no loading indicator while the API request is in flight."

**Clarifying questions:**

- "Should I handle errors at the client level (retry, timeout) or the UI level (show message)?"
- "Is a simple 'Something went wrong' message sufficient, or should we distinguish between error types?"

______________________________________________________________________

## Phase 2: Implement

### 2a. API Client — Graceful Error Handling

**Ruby** — `lib/reverb_client.rb`:

```ruby
class ReverbClient
  class ApiError < StandardError; end

  # ... existing code ...

  private

  def get(path, params = {})
    response = HTTParty.get(base_uri + path, headers: HEADERS, query: params)

    unless response.success?
      raise ApiError, "API returned #{response.code}"
    end

    JSON.parse(response.body)
  end
end
```

**Python** — `reverb_client.py`:

```python
class ApiError(Exception):
    pass

class ReverbClient:
    # ... existing code ...

    def _get(self, path, params=None):
        response = requests.get(
            self._base_uri + path,
            headers=self.HEADERS,
            params=params
        )
        if not response.ok:
            raise ApiError(f"API returned {response.status_code}")
        return response.json()
```

**React** — `API.js`:

```javascript
async function getJSON(url) {
  const response = await fetch(url, { headers: HEADERS });
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }
  return await response.json();
}
```

### 2b. Controller/Component — Catch and Display

**Ruby** — `app/controllers/listings_controller.rb`:

```ruby
def index
  @listings = ReverbClient.new.listings
rescue ReverbClient::ApiError => e
  @error = "Unable to load listings. Please try again."
  @listings = []
end
```

**Python** — `app.py`:

```python
@app.route('/listings')
def listings():
    try:
        results = ReverbClient().listings()
    except ApiError:
        results = []
        flash("Unable to load listings. Please try again.")
    return render_template('listings.html', listings=results)
```

**React** — `ListingsPage.js`:

```jsx
export default function ListingsPage() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetchListings()
      .then((response) => {
        setListings(response.listings);
        setError(null);
      })
      .catch((err) => {
        setError('Unable to load listings. Please try again.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  if (loading) return <p className="loading">Loading listings...</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <ul className="listings__list">
      {listings.map((listing) => (
        // ... existing rendering
      ))}
    </ul>
  );
}
```

### 2c. View Updates

**Ruby** — `app/views/listings/index.html.erb`:

```erb
<% if @error %>
  <div class="alert alert-danger"><%= @error %></div>
<% elsif @listings.present? %>
  <ul class="list-group">
    <!-- existing list -->
  </ul>
<% else %>
  <p>No listings found.</p>
<% end %>
```

______________________________________________________________________

## Phase 3: Test

**Ruby** — `spec/lib/reverb_client_spec.rb`:

```ruby
it 'raises ApiError on non-success response' do
  stub_request(:get, "https://api.reverb.com/api/listings/all?per_page=10")
    .to_return(status: 500, body: 'Internal Server Error')

  expect { client.listings }.to raise_error(ReverbClient::ApiError)
end
```

**Ruby** — `spec/requests/listings_spec.rb`:

```ruby
context 'when API fails' do
  before do
    allow(ReverbClient).to receive(:new).and_raise(ReverbClient::ApiError.new("API returned 500"))
  end

  it "shows error message" do
    get listings_path
    assert_select ".alert-danger", /Unable to load/
  end
end
```

**Python**:

```python
def test_handles_api_error(client):
    with patch('reverb_client.requests.get') as mock_get:
        mock_get.return_value.ok = False
        mock_get.return_value.status_code = 500
        # assert ApiError raised or graceful fallback rendered
```

**React**:

```jsx
it('shows error message when API fails', async () => {
  jest.spyOn(API, 'fetchListings').mockImplementation(() =>
    Promise.reject(new Error('API returned 500'))
  );

  const page = mount(<ListingsPage />);
  await act(async () => { /* wait */ });
  page.update();

  expect(page.find('.error').text()).toContain('Unable to load');
});

it('shows loading state initially', () => {
  jest.spyOn(API, 'fetchListings').mockImplementation(() => new Promise(() => {}));
  const page = mount(<ListingsPage />);
  expect(page.find('.loading').exists()).toBe(true);
});
```

______________________________________________________________________

## Phase 4: Trade-off Discussion

| Topic | What to say |
| -- | -- |
| Where to handle errors | "I chose to catch at the controller level so the client stays pure — it either returns data or throws. The controller decides what to show the user." |
| Retry logic | "For transient errors I could add automatic retry with backoff, but that's complexity I'd only add after seeing real failure patterns." |
| Timeout | "I'd set a request timeout (e.g., 5 seconds) so slow APIs don't hang the page indefinitely." |
| **Differentiated failure profiles** | "Categories are CDN-cached (24h, ~11ms response). Failure is extremely rare — implies CDN-level outage. Listings always hit origin (~600ms, `Cache-Control: no-cache`). Failure is routine. Error handling should be more aggressive for listings." |
| **429 Rate Limiting** | "Reverb returns 429 for excessive volume with no published quotas. This is NOT a transient error like 5xx — it's an instruction to slow down. Must back off (honor `Retry-After` header), not retry immediately." |
| **Timeout calibration** | "API exploration shows: categories ~11ms from CDN edge, listings ~600ms from origin. A 5s timeout is generous for categories but reasonable for listings." |
| Loading UX | "A spinner or skeleton gives feedback. Without it, the page looks broken during the fetch." |
| Error granularity | "I'm showing a generic message. In production I'd maybe distinguish between 'not found' and 'server error' but not leak API details to users." |
| Global error boundary (React) | "Could wrap the app in an ErrorBoundary for unhandled crashes, but per-component error state is more granular." |

______________________________________________________________________

## Python Implementation — Full Walkthrough

### Step 1: Add custom exception to `reverb_client.py`

```python
import requests


class ApiError(Exception):
    """Raised when the Reverb API returns a non-success status."""
    def __init__(self, status_code, message=''):
        self.status_code = status_code
        super().__init__(f"API returned {status_code}: {message}")


class ReverbClient:
    HEADERS = {
        'Accept': 'application/hal+json',
        'Accept-Version': '3.0',
        'Content-Type': 'application/hal+json'
    }

    def __init__(self, base_uri='https://api.reverb.com/api'):
        self._base_uri = base_uri

    def listings(self, per_page=10):
        return self._get('/listings/all', {'per_page': per_page})['listings']

    def categories(self):
        return self._get('/categories/flat')['categories']

    def _get(self, path, params=None):
        response = requests.get(
            self._base_uri + path,
            headers=self.HEADERS,
            params=params
        )
        if not response.ok:
            raise ApiError(response.status_code, response.text)
        return response.json()
```

**What to say:** "I'm adding a check after the HTTP call. If the response status isn't 2xx, I raise a custom `ApiError` with the status code. This keeps the client honest — it either returns data or raises. The controller layer decides how to present the error to users."

**Python idiom:** `response.ok` is a `requests` library property that returns `True` for any 2xx status. More Pythonic than checking `response.status_code < 400`.

### Step 2: Handle errors in `app.py`

```python
from flask import Flask, request, render_template, flash
from reverb_client import ReverbClient, ApiError

app = Flask(__name__)
app.secret_key = 'dev'  # needed for flash messages

@app.route('/')
@app.route('/categories')
def categories():
    try:
        categories = _search_categories(request.args.get('query'))
    except ApiError:
        categories = []
        flash("Unable to load categories. Please try again.")
    return render_template('categories.html', categories=categories)

@app.route('/listings')
def listings():
    try:
        results = ReverbClient().listings()
    except ApiError:
        results = []
        flash("Unable to load listings. Please try again.")
    return render_template('listings.html', listings=results)

def _search_categories(query):
    if not query:
        return []
    categories = _load_categories()
    return list(filter(lambda c: query.lower() in c['full_name'].lower(), categories))

def _load_categories():
    return ReverbClient().categories()
```

**What to say:** "I wrap the API call in try/except and use Flask's `flash` for user messages. The page still renders with empty data rather than crashing with a 500. I need `app.secret_key` for flash to work since it uses the session."

### Step 3: Display flash messages in `templates/base.html`

```html
<div class="container">
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      {% for message in messages %}
        <div class="alert alert-danger alert-dismissible mt-3">
          {{ message }}
          <button type="button" class="close" data-dismiss="alert">&times;</button>
        </div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  {% block content %}{% endblock %}
</div>
```

**What to say:** "Flash messages are rendered in the base layout so they work on any page. Bootstrap's alert classes give us styled error display for free."

### Step 4: Add timeout to prevent hanging

```python
def _get(self, path, params=None):
    try:
        response = requests.get(
            self._base_uri + path,
            headers=self.HEADERS,
            params=params,
            timeout=5
        )
    except requests.Timeout:
        raise ApiError(408, 'Request timed out')
    except requests.ConnectionError:
        raise ApiError(503, 'Could not connect to API')

    if not response.ok:
        raise ApiError(response.status_code, response.text)
    return response.json()
```

**What to say:** "I'm setting a 5-second timeout so slow API responses don't hang the page. I also catch `ConnectionError` for when the API is completely unreachable. Both get converted to our `ApiError` so the handler logic stays the same."

### Step 5: Tests

**`tests/test_reverb_client.py`:**

```python
from reverb_client import ReverbClient, ApiError
import pytest
from unittest.mock import patch, MagicMock

def test_raises_api_error_on_500():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.ok = False
    mock_get.return_value.status_code = 500
    mock_get.return_value.text = 'Internal Server Error'

    with pytest.raises(ApiError) as exc_info:
        ReverbClient().listings()

    assert exc_info.value.status_code == 500

def test_raises_api_error_on_timeout():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.side_effect = requests.Timeout()

    with pytest.raises(ApiError) as exc_info:
        ReverbClient().listings()

    assert exc_info.value.status_code == 408

def test_raises_api_error_on_connection_error():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.side_effect = requests.ConnectionError()

    with pytest.raises(ApiError) as exc_info:
        ReverbClient().listings()

    assert exc_info.value.status_code == 503
```

**`tests/test_listings.py`:**

```python
def test_shows_error_message_on_api_failure():
    app.config['TESTING'] = True
    app.secret_key = 'test'

    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.ok = False
    mock_get.return_value.status_code = 500
    mock_get.return_value.text = 'Server Error'

    with app.test_client() as client:
        res = client.get('/listings')
        html = parse_html(res)
        assert 'Unable to load listings' in html.body.text

def test_page_renders_without_listings_on_error():
    app.config['TESTING'] = True
    app.secret_key = 'test'

    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.ok = False
    mock_get.return_value.status_code = 500
    mock_get.return_value.text = 'Server Error'

    with app.test_client() as client:
        res = client.get('/listings')
        assert res.status_code == 200  # page renders, not a 500
```

### Rails comparison notes

| Aspect | Rails approach | Flask approach |
| -- | -- | -- |
| Custom exception | `class ApiError < StandardError; end` | `class ApiError(Exception): pass` |
| Rescue | `rescue ReverbClient::ApiError => e` | `except ApiError:` |
| Flash messages | `flash[:alert]` (built-in) | `flash("message")` (needs `secret_key`) |
| Global error handler | `rescue_from` in ApplicationController | `@app.errorhandler(ApiError)` decorator |
| Timeout | HTTParty option or Faraday middleware | `requests.get(..., timeout=5)` |
| Response check | `response.success?` | `response.ok` |

**Key insight:** "Python's exception handling with `try/except` maps directly to Ruby's `begin/rescue`. The pattern is the same: client raises, controller catches, user sees a friendly message. Flask's `flash` is simpler than Rails' flash — it's just a list of strings stored in the session."

**Discussion point — mutable default args:**
"The original code had `def _get(self, path, params={})` which is a classic Python bug — the dict is shared across calls. We fixed it to `params=None` in the foundational improvements (Scenario 0). Always mention this if you spot it in an interview codebase."
