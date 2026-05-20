# Scenario 2: Search / Filter Listings

## The Ask

> "Users can search categories, but they can't search listings. Add a way to filter listings by keyword."

This mirrors the existing categories filter pattern — tests whether you can replicate and adapt existing code.

______________________________________________________________________

## Phase 1: Explain (What You Already See)

"Categories already has filtering — server-side in Ruby/Python (submit form, re-render), client-side in React (instant filter via state). Listings currently just dumps all results. I'll follow the same pattern the codebase already uses for categories."

**Clarifying questions to ask:**

- "Should this filter client-side over the already-loaded listings, or should I pass a query to the API?"
- "The Reverb API supports `query` as a param on `/listings/all` — should I use that?"

______________________________________________________________________

## Phase 2: Implement

### Option A: Server-side (Ruby/Python) — Use API's query param

The Reverb API supports: `GET /api/listings/all?query=fender&per_page=10`

### Additional Search Endpoints (Discovered via API Exploration)

The API also exposes two **autocomplete/suggest** endpoints useful for search UX:

- `GET /api/autocomplete?query=fender` → returns `{ "makes": [...], "models": [...] }` (brand/model name suggestions)
- `GET /api/autosuggest?query=fender` → returns rich suggestions grouped by section with full `_links` to listings and web pages

These are perfect for a follow-up "add typeahead" extension. Mention them to show API awareness.

**Ruby** — `lib/reverb_client.rb`:

```ruby
def listings(per_page: 10, query: nil)
  params = { per_page: per_page }
  params[:query] = query if query.present?
  get('/listings/all', params)['listings']
end
```

**Ruby** — `app/controllers/listings_controller.rb`:

```ruby
def index
  @listings = ReverbClient.new.listings(query: params[:query])
end
```

**Ruby** — `app/views/listings/index.html.erb` (add form above the list):

```erb
<%= form_tag(listings_path, method: :get) do -%>
  <div class="form-group">
    <label for="query">Search Listings</label>
    <input class="form-control" type="text" name="query"
           value="<%= params[:query] %>"
           placeholder="Search by keyword">
  </div>
  <div class="form-group">
    <button type="submit" class="btn btn-primary">Search</button>
  </div>
<% end %>
```

**Python** — `reverb_client.py`:

```python
def listings(self, per_page=10, query=None):
    params = {'per_page': per_page}
    if query:
        params['query'] = query
    return self._get('/listings/all', params)['listings']
```

**Python** — `app.py`:

```python
@app.route('/listings')
def listings():
    query = request.args.get('query')
    results = ReverbClient().listings(query=query)
    return render_template('listings.html', listings=results, query=query)
```

### Option B: Client-side (React) — Filter in-memory

```jsx
// In ListingsPage.js — add filter state, same pattern as CategoriesPage
const [query, setQuery] = useState('');

const filtered = query
  ? listings.filter(l => l.title.toLowerCase().includes(query.toLowerCase()))
  : listings;
```

Add input field above the list, render `filtered` instead of `listings`.

______________________________________________________________________

## Phase 3: Test

**Ruby** — `spec/lib/reverb_client_spec.rb`:

```ruby
it 'fetches listings with a query' do
  stub_request(:get, "https://api.reverb.com/api/listings/all?per_page=10&query=fender")
    .to_return(status: 200, body: { listings: [{ title: 'Fender Tele' }] }.to_json)

  listings = client.listings(query: 'fender')
  expect(listings.first['title']).to include('Fender')
end
```

**Ruby** — `spec/requests/listings_spec.rb`:

```ruby
it "displays search form and results" do
  get listings_path(query: 'fender')
  assert_select "input[name=query]"
  assert_select "li.list-group-item"
end
```

**React**:

```jsx
it('filters listings by title', async () => {
  // mount, await data, simulate input change to "fender"
  // expect only matching listings visible
});
```

______________________________________________________________________

## Phase 4: Trade-off Discussion

| Topic | What to say |
| -- | -- |
| Client vs server filter | "Server-side uses the API's full-text search (better relevance, handles large catalogs). Client-side is instant but only searches titles in the already-loaded page." |
| Debounce | "If I made this as-you-type server-side, I'd debounce 300ms to avoid hammering the API" |
| URL state | "I'm putting the query in the URL params so the search is shareable and back-button works" |
| Empty state | "If no results, show a message rather than a blank page" |

______________________________________________________________________

## Python Implementation — Full Walkthrough

### Step 1: Extend `reverb_client.py`

```python
def listings(self, per_page=10, query=None):
    params = {'per_page': per_page}
    if query:
        params['query'] = query
    return self._get('/listings/all', params)['listings']
```

**What to say:** "I'm adding an optional `query` keyword argument. If provided, it gets passed to the API. If not, behavior is unchanged — existing code won't break."

**Python idiom note:** Using `if query:` handles both `None` and empty string `""`. This is intentional — we don't want to send an empty query to the API.

### Step 2: Update route in `app.py`

```python
@app.route('/listings')
def listings():
    query = request.args.get('query')
    results = ReverbClient().listings(query=query)
    return render_template('listings.html', listings=results, query=query)
```

**What to say:** "`request.args.get('query')` returns `None` if the param isn't in the URL. I pass it to the client which ignores `None`, and also to the template so I can show the current search term in the input."

### Step 3: Update template — `templates/listings.html`

```html
{% extends 'base.html' %}
{% block content %}

<form action="{{ url_for('listings') }}" method="get">
  <div class="form-group">
    <label for="query">Search Listings</label>
    <input class="form-control" type="text" name="query"
           value="{{ query or '' }}"
           placeholder="Search by keyword">
  </div>
  <div class="form-group">
    <button type="submit" class="btn btn-primary">Search</button>
  </div>
</form>

{% if listings %}
  <ul class="list-group">
    {% for listing in listings %}
      <li class="d-flex list-group-item flex-row align-items-center">
        <div class="p-2">
          <img src="{{ listing['photos'][0]['_links']['thumbnail']['href'] }}" />
        </div>
        <h2 class="p-2">{{ listing['title'] }}</h2>
      </li>
    {% endfor %}
  </ul>
{% elif query %}
  <p>No listings found for "{{ query }}".</p>
{% endif %}

{% endblock %}
```

**What to say:** "I'm preserving the query value in the input so users see what they searched for. The `{{ query or '' }}` Jinja2 syntax handles the `None` case. The empty state only shows when there was an active search."

### Step 4: Tests — `tests/test_listings.py` (extend existing)

```python
@pytest.fixture
def search_client():
    app.config['TESTING'] = True

    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'listings': [
            {
                'title': 'Fender Telecaster',
                'photos': [{'_links': {'thumbnail': {'href': 'https://img.com/tele.jpg'}}}]
            }
        ]
    }

    with app.test_client() as client:
        yield client

def test_search_form_present(search_client):
    res = search_client.get('/listings')
    html = parse_html(res)
    assert html.body.select_one('input[name="query"]') is not None

def test_search_passes_query_to_api(search_client):
    res = search_client.get('/listings', query_string={'query': 'fender'})
    html = parse_html(res)
    # Input should preserve the search term
    input_el = html.body.select_one('input[name="query"]')
    assert input_el['value'] == 'fender'

def test_search_shows_results(search_client):
    res = search_client.get('/listings', query_string={'query': 'fender'})
    html = parse_html(res)
    assert 'Fender Telecaster' in html.body.text

def test_empty_search_shows_message():
    app.config['TESTING'] = True
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {'listings': []}

    with app.test_client() as client:
        res = client.get('/listings', query_string={'query': 'didgeridoo'})
        html = parse_html(res)
        assert 'No listings found' in html.body.text
```

### Step 5: Client unit test — add to `tests/test_reverb_client.py`

```python
def test_listings_with_query():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'listings': [{'title': 'Fender Telecaster'}]
    }

    listings = ReverbClient().listings(query='fender')

    assert len(listings) == 1
    # Verify the query param was passed
    call_kwargs = mock_get.call_args[1]
    assert call_kwargs['params']['query'] == 'fender'

def test_listings_without_query_omits_param():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {'listings': []}

    ReverbClient().listings()

    call_kwargs = mock_get.call_args[1]
    assert 'query' not in call_kwargs['params']
```

### Rails comparison notes

| Aspect | Rails approach | Flask approach |
| -- | -- | -- |
| Form helper | `form_tag(path, method: :get)` generates CSRF token + form | Plain HTML `<form>` — Flask doesn't auto-add CSRF for GET |
| Param access | `params[:query]` — merged hash | `request.args.get('query')` — only query string |
| Preserve input value | `value="<%= params[:query] %>"` | `value="{{ query or '' }}"` |
| Blank check | `query.blank?` (Rails extension) | `if query:` (Python truthiness) |
| Strong params | Not needed (no DB write) | N/A |

**Key insight:** "The Flask version follows the same pattern as categories but is more explicit. In Rails, `params` merges query string and route params — in Flask they're separate (`request.args` vs URL captures), which is clearer."
