# Scenario 4: Category → Listings Navigation

## The Ask

> "When a user finds a category, they should be able to click it to see listings in that category."

Tests whether you can connect two existing features together — navigating from one resource to another with a parameter.

______________________________________________________________________

## Phase 1: Explain

"Right now categories and listings are completely independent pages. The Reverb API supports filtering listings by category — I'll make each category name a link that takes you to the listings page filtered by that category's UUID or slug."

**Clarifying questions:**

- "Should clicking a category go to a filtered listings page, or a new 'category detail' page?"
- "Does the API accept a `category` param on the listings endpoint?"

______________________________________________________________________

## Phase 2: Implement

### 2a. API Discovery

The Reverb API: `GET /api/listings/all?category=electric-guitars` or `?category_uuid=XXX`

The categories response includes `uuid` and `slug` fields per category.

### 2b. Extend the API Client

**Ruby** — `lib/reverb_client.rb`:

```ruby
def listings(per_page: 10, category: nil)
  params = { per_page: per_page }
  params[:category] = category if category.present?
  get('/listings/all', params)['listings']
end
```

**Python** — `reverb_client.py`:

```python
def listings(self, per_page=10, category=None):
    params = {'per_page': per_page}
    if category:
        params['category'] = category
    return self._get('/listings/all', params)['listings']
```

**React** — `API.js`:

```javascript
export async function fetchListings(category = null) {
  const params = category ? `?category=${category}` : '';
  return getJSON(`${LISTINGS_URL}/all${params}`);
}
```

### 2c. Update Controllers/Routes

**Ruby** — `app/controllers/listings_controller.rb`:

```ruby
def index
  @listings = ReverbClient.new.listings(category: params[:category])
  @category_name = params[:category]
end
```

**Python** — `app.py`:

```python
@app.route('/listings')
def listings():
    category = request.args.get('category')
    results = ReverbClient().listings(category=category)
    return render_template('listings.html', listings=results, category=category)
```

### 2d. Make Categories Clickable

**Ruby** — `app/views/categories/index.html.erb`:

```erb
<li class="list-group-item">
  <%= link_to category['full_name'], listings_path(category: category['slug']) %>
</li>
```

**Python** — `templates/categories.html`:

```html
<li class="list-group-item">
  <a href="{{ url_for('listings', category=category['slug']) }}">
    {{ category['full_name'] }}
  </a>
</li>
```

**React** — `CategoriesPage.js`:

```jsx
import { Link } from 'react-router-dom';

// In the map:
<li key={category.uuid} className="categories__list-item">
  <Link to={`/listings?category=${category.slug}`}>
    {category.full_name}
  </Link>
</li>
```

**React** — `ListingsPage.js` (read category from URL):

```jsx
import { useLocation } from 'react-router-dom';

function useQuery() {
  return new URLSearchParams(useLocation().search);
}

export default function ListingsPage() {
  const query = useQuery();
  const category = query.get('category');
  const [listings, setListings] = useState([]);

  useEffect(() => {
    fetchListings(category).then(res => setListings(res.listings));
  }, [category]);

  // ... render
}
```

### 2e. Show Active Category Context

Add a heading when filtered:

**Ruby**:

```erb
<% if @category_name %>
  <h2>Listings in: <%= @category_name.titleize %></h2>
  <%= link_to 'Show all listings', listings_path %>
<% end %>
```

**React**:

```jsx
{category && (
  <div>
    <h2>Listings in: {category}</h2>
    <Link to="/listings">Show all listings</Link>
  </div>
)}
```

______________________________________________________________________

## Phase 3: Test

**Ruby** — `spec/lib/reverb_client_spec.rb`:

```ruby
it 'fetches listings filtered by category' do
  stub_request(:get, "https://api.reverb.com/api/listings/all?per_page=10&category=electric-guitars")
    .to_return(status: 200, body: { listings: [{ title: 'A Guitar' }] }.to_json)

  listings = client.listings(category: 'electric-guitars')
  expect(listings.first['title']).to eq('A Guitar')
end
```

**Ruby** — `spec/requests/categories_spec.rb`:

```ruby
it "links categories to filtered listings" do
  get categories_path(query: 'guitar')
  assert_select "a[href=?]", listings_path(category: 'guitars')
end
```

**React**:

```jsx
it('passes category param to API when present in URL', async () => {
  // render with route ?category=guitars
  // verify fetchListings called with 'guitars'
});
```

______________________________________________________________________

## Phase 4: Trade-off Discussion

| Topic | What to say |
| -- | -- |
| Slug vs UUID | "Slug is human-readable in URLs. UUID is guaranteed unique. I used slug since the API supports it and it's better UX." |
| Coupling pages | "Now listings depends on knowing about categories. That's fine for navigation but I'd avoid deeper coupling." |
| Breadcrumbs | "With more time I'd add a breadcrumb: Home > Guitars > Listings" |
| Back button | "Since category is in the URL params, browser back works naturally" |
| Empty results | "Should handle the case where a category has zero listings" |

______________________________________________________________________

## Python Implementation — Full Walkthrough

### Step 1: Extend `reverb_client.py`

```python
def listings(self, per_page=10, category=None):
    params = {'per_page': per_page}
    if category:
        params['category'] = category
    return self._get('/listings/all', params)['listings']
```

**What to say:** "Adding an optional `category` keyword argument. When present, it filters the API response server-side. The API accepts a category slug."

### Step 2: Update route in `app.py`

```python
@app.route('/listings')
def listings():
    category = request.args.get('category')
    results = ReverbClient().listings(category=category)
    return render_template('listings.html', listings=results, category=category)
```

**What to say:** "I'm reading the category from query params and passing it through. Also forwarding it to the template so I can show context about what's being filtered."

### Step 3: Make categories clickable — `templates/categories.html`

```html
{% extends 'base.html' %}
{% block content %}

<form action="{{ url_for('categories') }}" method="get">
  <div class="form-group">
    <label for="query">Category Search</label>
    <input class="form-control" type="text" name="query" placeholder="Enter Category Name">
  </div>
  <div class="form-group">
    <button type="submit" class="btn btn-primary">Submit</button>
  </div>
</form>

{% if categories %}
  <ul class="list-group">
    {% for category in categories %}
      <li class="list-group-item">
        <a href="{{ url_for('listings', category=category['slug']) }}">
          {{ category['full_name'] }}
        </a>
      </li>
    {% endfor %}
  </ul>
{% elif request.args.get('query') %}
  <p>Sorry. No results were found for your search.</p>
{% endif %}

{% endblock %}
```

**What to say:** "Each category name becomes a link to the listings page with the category slug as a query parameter. `url_for('listings', category=...)` generates `/listings?category=electric-guitars`."

**Python note:** `url_for` automatically URL-encodes the parameter value, so slugs with special characters are safe.

### Step 4: Show context on listings page — `templates/listings.html`

```html
{% extends 'base.html' %}
{% block content %}

{% if category %}
  <div class="mb-3">
    <h2>Listings in: {{ category | replace('-', ' ') | title }}</h2>
    <a href="{{ url_for('listings') }}" class="btn btn-outline-secondary btn-sm">
      ← Show all listings
    </a>
  </div>
{% endif %}

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
{% elif category %}
  <p>No listings found in this category.</p>
{% endif %}

{% endblock %}
```

**What to say:** "I'm using Jinja2 filters to make the slug human-readable: `replace('-', ' ')` turns hyphens to spaces, and `title` capitalizes. There's also a 'back to all' link and an empty-state message."

### Step 5: Tests

**`tests/test_categories.py`** (add navigation test):

```python
def test_categories_link_to_listings(client):
    """Each category should link to filtered listings page."""
    res = client.get('/categories', query_string={'query': 'guitar'})
    html = parse_html(res)
    links = html.body.select('a')
    listing_links = [a for a in links if '/listings?category=' in (a.get('href') or '')]
    assert len(listing_links) > 0
```

**`tests/test_listings.py`** (add category filter tests):

```python
@pytest.fixture
def category_client():
    app.config['TESTING'] = True

    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'listings': [{
            'title': 'Electric Guitar',
            'photos': [{'_links': {'thumbnail': {'href': 'https://img.com/eg.jpg'}}}]
        }]
    }

    with app.test_client() as client:
        yield client

def test_listings_filtered_by_category(category_client):
    res = category_client.get('/listings', query_string={'category': 'electric-guitars'})
    html = parse_html(res)
    assert 'Electric Guitar' in html.body.text

def test_shows_category_context(category_client):
    res = category_client.get('/listings', query_string={'category': 'electric-guitars'})
    html = parse_html(res)
    assert 'Electric Guitars' in html.body.h2.text

def test_shows_back_to_all_link(category_client):
    res = category_client.get('/listings', query_string={'category': 'electric-guitars'})
    html = parse_html(res)
    back_link = html.body.select_one('a[href="/listings"]')
    assert back_link is not None
```

**`tests/test_reverb_client.py`** (add category param test):

```python
def test_listings_with_category():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'listings': [{'title': 'A Guitar'}]
    }

    listings = ReverbClient().listings(category='electric-guitars')

    assert listings[0]['title'] == 'A Guitar'
    call_kwargs = mock_get.call_args[1]
    assert call_kwargs['params']['category'] == 'electric-guitars'

def test_listings_without_category_omits_param():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {'listings': []}

    ReverbClient().listings()

    call_kwargs = mock_get.call_args[1]
    assert 'category' not in call_kwargs['params']
```

### Rails comparison notes

| Aspect | Rails approach | Flask approach |
| -- | -- | -- |
| URL generation | `listings_path(category: slug)` | `url_for('listings', category=slug)` |
| Slug formatting | `@category_name.titleize` (ActiveSupport) | `category \| replace('-', ' ') \| title` (Jinja2 filters) |
| Link helper | `link_to text, path` | `<a href="{{ url_for(...) }}">text</a>` |
| Param forwarding | Implicit via `params` hash | Explicit via `request.args.get` + template var |

**Key insight:** "This scenario connects two existing features. The implementation is small — mostly template changes and one new client param. In Rails you'd use `link_to` helpers; in Flask it's explicit HTML with `url_for`. Both generate the same result but Flask makes the HTML structure more visible."
