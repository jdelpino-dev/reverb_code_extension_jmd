# Scenario 3: Pagination

## The Ask

> "Right now we only show 10 listings. Add pagination so users can browse through more results."

Tests whether you can manage state across requests and understand API pagination patterns.

______________________________________________________________________

## Phase 1: Explain

"The client already passes `per_page: 10` to the API. The Reverb API likely returns pagination metadata (total count, next page link). I'll add page navigation that passes an offset or page param to the API and renders prev/next controls."

**Clarifying questions:**

- "Do you want numbered pages, or just Next/Previous?"
- "Should the page number be in the URL (bookmarkable) or just in-memory?"

______________________________________________________________________

## Phase 2: Implement

### 2a. Explore API pagination

The Reverb API returns HAL-style links:

```json
{
  "total": 2537869,
  "current_page": 1,
  "total_pages": 50,
  "per_page": 10,
  "listings": [...],
  "_links": {
    "next": { "href": "https://api.reverb.com/api/listings/all?page=2&per_page=10" }
  }
}
```

### CRITICAL GOTCHA: 50-Page Cap

Despite ~2.5M total listings, `total_pages` is **always capped at 50** regardless of `per_page`. This is intentional:

- Deep offset pagination is expensive and unstable on a live marketplace
- It prevents full-catalog scraping
- The cap applies per-query — narrower filters expose a *different* 50-page window

**Implications for your implementation:**

- Never show numbered page buttons 1–N assuming `total_pages` reflects the true dataset size
- The "total" field (2.5M) does NOT mean you can access all of them via pagination
- To reach more data, partition queries by category, condition, price range, etc.

### Pagination: Where Link-Following Genuinely Helps

Pagination is the strongest case for following `_links` rather than constructing URLs:

- `_links.next.href` gives you a full absolute URL — the server tells you exactly where the next page is
- `_links.prev.href` for the previous page
- **`_links.next` is absent on the last page** — this is the authoritative signal to hide "Next", more reliable than comparing `current_page >= total_pages` (which is capped at 50 anyway)
- The link encodes the correct `per_page` value, so you can't accidentally mismatch params

**Why this matters for the 50-page cap:** Since `total_pages` is artificially capped at 50, you cannot trust arithmetic like `current_page < total_pages` to mean "more data exists." But `_links.next` being present/absent is the server's definitive answer.

**Practical approach for the interview:** Construct URLs with `?page=N` for simplicity (it works), but store/use `_links.next` presence as the "has more pages" signal. Mention: "Following `_links.next` is more robust than page arithmetic because `total_pages` is capped."

### 2b. Extend the API Client

**Ruby** — `lib/reverb_client.rb`:

```ruby
def listings(per_page: 10, page: 1, query: nil)
  params = { per_page: per_page, page: page }
  params[:query] = query if query.present?
  get('/listings/all', params)
end
```

Note: now returns the full response (not just `['listings']`) so the controller can access pagination metadata.

**Ruby** — `app/controllers/listings_controller.rb`:

```ruby
def index
  response = ReverbClient.new.listings(page: page_param)
  @listings = response['listings']
  @current_page = response['current_page']
  @total_pages = response['total_pages']
end

private

def page_param
  (params[:page] || 1).to_i
end
```

**Python** — `reverb_client.py`:

```python
def listings(self, per_page=10, page=1, query=None):
    params = {'per_page': per_page, 'page': page}
    if query:
        params['query'] = query
    return self._get('/listings/all', params)
```

**Python** — `app.py`:

```python
@app.route('/listings')
def listings():
    page = request.args.get('page', 1, type=int)
    response = ReverbClient().listings(page=page)
    return render_template('listings.html',
                           listings=response['listings'],
                           current_page=response['current_page'],
                           total_pages=response['total_pages'])
```

**React** — `ListingsPage.js`:

```jsx
const [page, setPage] = useState(1);

useEffect(() => {
  fetchListings(page).then((response) => {
    setListings(response.listings);
    setTotalPages(response.total_pages);
  });
}, [page]);
```

### 2c. Pagination Controls

**Ruby** — `app/views/listings/index.html.erb` (below the list):

```erb
<nav>
  <ul class="pagination">
    <% if @current_page > 1 %>
      <li class="page-item">
        <%= link_to 'Previous', listings_path(page: @current_page - 1), class: 'page-link' %>
      </li>
    <% end %>
    <li class="page-item disabled">
      <span class="page-link"><%= @current_page %> / <%= @total_pages %></span>
    </li>
    <% if @current_page < @total_pages %>
      <li class="page-item">
        <%= link_to 'Next', listings_path(page: @current_page + 1), class: 'page-link' %>
      </li>
    <% end %>
  </ul>
</nav>
```

**React**:

```jsx
<div className="pagination">
  <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</button>
  <span>{page} / {totalPages}</span>
  <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
</div>
```

______________________________________________________________________

## Phase 3: Test

**Ruby** — `spec/lib/reverb_client_spec.rb`:

```ruby
it 'fetches listings with page param' do
  stub_request(:get, "https://api.reverb.com/api/listings/all?per_page=10&page=2")
    .to_return(status: 200, body: {
      listings: [{ title: 'Page 2 Item' }],
      current_page: 2,
      total_pages: 5
    }.to_json)

  response = client.listings(page: 2)
  expect(response['current_page']).to eq(2)
  expect(response['listings'].length).to eq(1)
end
```

**Ruby** — `spec/requests/listings_spec.rb`:

```ruby
context 'with pagination' do
  let(:response) { { 'listings' => listings, 'current_page' => 2, 'total_pages' => 5 } }

  before { allow(ReverbClient).to receive(:new) { instance_double(ReverbClient, listings: response) } }

  it "shows pagination controls" do
    get listings_path(page: 2)
    assert_select ".pagination"
    assert_select "a", "Previous"
    assert_select "a", "Next"
  end
end
```

**React**:

```jsx
it('advances to next page when Next is clicked', async () => {
  // mock page 1 response, mount, await
  // click Next button
  // verify fetchListings called with page 2
});
```

______________________________________________________________________

## Phase 4: Trade-off Discussion

| Topic | What to say |
| -- | -- |
| Offset vs cursor pagination | "Offset (page number) is simple but can miss items if data changes between pages. Cursor-based is more reliable for feeds." |
| **50-page cap** | "Reverb caps `total_pages` at 50 per query. This is a platform constraint — to access more data, partition queries by category/condition/price rather than paginating deeper." |
| URL state | "Page in the URL means refresh stays on the same page, and you can share links to specific pages" |
| Link-following vs URL construction | \"For pagination, `_links.next` is genuinely useful \u2014 it's the server's authoritative signal that more data exists (more reliable than `current_page < total_pages` since that's capped at 50). I construct the initial URL but use `_links.next` presence to control the Next button.\" |
| Pre-fetching | "Could pre-fetch the next page for instant transitions, but adds complexity" |
| Infinite scroll vs pages | "Infinite scroll feels better for browsing but is harder to implement (intersection observer, append state). Pages are simpler and give positional context." |
| API contract change | "I changed the client to return the full response object instead of just listings — this is a breaking change to discuss." |

______________________________________________________________________

## Python Implementation — Full Walkthrough

### Step 1: Extend `reverb_client.py`

```python
def listings(self, per_page=10, page=1):
    params = {'per_page': per_page, 'page': page}
    return self._get('/listings/all', params)
```

**What to say:** "I'm changing the return value — instead of returning just `response['listings']`, I return the full response dict so the caller can access pagination metadata. This is a breaking change to the existing `listings()` call in `app.py`, so I'll update that too."

**Important:** The existing code returns `self._get(...)['listings']`. You're removing the `['listings']` unwrap. Mention this explicitly during the interview — it shows you're thinking about backward compatibility.

### Step 2: Update route in `app.py`

```python
@app.route('/listings')
def listings():
    page = request.args.get('page', 1, type=int)
    response = ReverbClient().listings(page=page)
    return render_template(
        'listings.html',
        listings=response['listings'],
        current_page=response['current_page'],
        total_pages=response['total_pages']
    )
```

**What to say:** "`request.args.get('page', 1, type=int)` does three things: gets the param, defaults to 1, and coerces to int. Flask's `type` parameter handles the conversion and returns the default if conversion fails — so `/listings?page=abc` gives page 1, not an error."

**Python idiom:** This is a great Flask feature to highlight. In Rails you'd do `(params[:page] || 1).to_i` which doesn't validate.

### Step 3: Update template — `templates/listings.html`

```html
{% extends 'base.html' %}
{% block content %}

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

  <nav class="mt-3">
    <ul class="pagination">
      {% if current_page > 1 %}
        <li class="page-item">
          <a class="page-link" href="{{ url_for('listings', page=current_page - 1) }}">Previous</a>
        </li>
      {% endif %}
      <li class="page-item disabled">
        <span class="page-link">{{ current_page }} / {{ total_pages }}</span>
      </li>
      {% if current_page < total_pages %}
        <li class="page-item">
          <a class="page-link" href="{{ url_for('listings', page=current_page + 1) }}">Next</a>
        </li>
      {% endif %}
    </ul>
  </nav>
{% endif %}

{% endblock %}
```

**What to say:** "Jinja2 supports arithmetic in templates (`current_page - 1`). The `url_for` generates the correct URL with the page param. I'm using Bootstrap's pagination classes since the project already uses Bootstrap."

### Step 4: Tests — `tests/test_listings.py`

```python
@pytest.fixture
def paginated_client():
    app.config['TESTING'] = True

    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'listings': [
            {
                'title': 'Page 2 Item',
                'photos': [{'_links': {'thumbnail': {'href': 'https://img.com/p2.jpg'}}}]
            }
        ],
        'current_page': 2,
        'total_pages': 5
    }

    with app.test_client() as client:
        yield client

def test_displays_pagination_controls(paginated_client):
    res = paginated_client.get('/listings', query_string={'page': 2})
    html = parse_html(res)
    pagination = html.body.select_one('.pagination')
    assert pagination is not None
    assert 'Previous' in pagination.text
    assert 'Next' in pagination.text

def test_previous_link_goes_to_previous_page(paginated_client):
    res = paginated_client.get('/listings', query_string={'page': 2})
    html = parse_html(res)
    prev_link = html.body.select_one('.pagination a')
    assert 'page=1' in prev_link['href']

def test_shows_current_page_indicator(paginated_client):
    res = paginated_client.get('/listings', query_string={'page': 2})
    html = parse_html(res)
    assert '2 / 5' in html.body.select_one('.pagination').text

def test_no_previous_on_first_page():
    app.config['TESTING'] = True
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'listings': [{'title': 'Item', 'photos': [{'_links': {'thumbnail': {'href': 'x'}}}]}],
        'current_page': 1,
        'total_pages': 5
    }

    with app.test_client() as client:
        res = client.get('/listings')
        html = parse_html(res)
        assert 'Previous' not in html.body.text
```

### Step 5: Client unit test

```python
def test_listings_with_page():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'listings': [{'title': 'Page 2 Item'}],
        'current_page': 2,
        'total_pages': 5
    }

    response = ReverbClient().listings(page=2)

    assert response['current_page'] == 2
    assert response['total_pages'] == 5
    assert len(response['listings']) == 1

    call_kwargs = mock_get.call_args[1]
    assert call_kwargs['params']['page'] == 2
```

### Rails comparison notes

| Aspect | Rails approach | Flask approach |
| -- | -- | -- |
| Page param coercion | `(params[:page] \|\| 1).to_i` | `request.args.get('page', 1, type=int)` — cleaner |
| Link generation | `link_to 'Next', listings_path(page: n)` | `<a href="{{ url_for('listings', page=n) }}">` |
| Pagination gem | `kaminari` or `will_paginate` | Manual (no standard Flask paginator for API data) |
| Template math | Not idiomatic in ERB (do in controller) | `{{ current_page - 1 }}` — Jinja2 allows it |
| Breaking client change | Would update controller + specs | Same — update `app.py` + tests |

**Key insight:** "Rails devs would reach for kaminari, but that's for ActiveRecord. Since we're wrapping an external API that already paginates, we just pass through the metadata. Same applies here in Flask — no library needed, just forward the API's pagination fields."
