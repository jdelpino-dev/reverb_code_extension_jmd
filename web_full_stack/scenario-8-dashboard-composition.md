# Scenario 8: Composing Multiple API Calls (Dashboard View)

## The Ask

> "Add a homepage dashboard that shows the top 5 categories and the 5 most recent listings together on one page."

This tests coordinating multiple data sources, handling partial failures, structuring service helpers, and rendering a composite view.

______________________________________________________________________

## Phase 1: Explain the Architecture (2-3 min)

**What to say:**

"Right now each route calls one API endpoint and renders one resource. A dashboard page needs data from two endpoints — categories and listings — rendered together. The key decisions are: do I fetch sequentially or in parallel? What if one call fails but the other succeeds — do I show partial data or a full error page? And how do I structure the service layer so this doesn't become a single bloated handler."

**Clarifying questions:**

- "Should both sections be required, or can the page render with just one if the other fails?"
- "Is there a priority — should categories load even if listings fail?"
- "Top 5 categories by what — alphabetical, most popular? (API supports any ordering?)"

______________________________________________________________________

## Phase 2: Implement

### 2a. Service Layer — Coordinating Multiple Calls

**Python** — `app.py`:

```python
@app.route('/')
@app.route('/dashboard')
def dashboard():
    categories, categories_error = _load_dashboard_categories()
    listings, listings_error = _load_dashboard_listings()

    return render_template('dashboard.html',
        categories=categories,
        listings=listings,
        categories_error=categories_error,
        listings_error=listings_error,
    )


def _load_dashboard_categories():
    try:
        categories = ReverbClient().categories()[:5]
        return categories, None
    except ApiError as e:
        return [], str(e)


def _load_dashboard_listings():
    try:
        listings = ReverbClient().listings(per_page=5)
        return listings, None
    except ApiError as e:
        return [], str(e)
```

**Ruby** — `app/controllers/dashboard_controller.rb`:

```ruby
class DashboardController < ApplicationController
  def index
    @categories, @categories_error = load_dashboard_categories
    @listings, @listings_error = load_dashboard_listings
  end

  private

  def load_dashboard_categories
    categories = ReverbClient.new.categories.first(5)
    [categories, nil]
  rescue ReverbClient::ApiError => e
    [[], e.message]
  end

  def load_dashboard_listings
    listings = ReverbClient.new.listings(per_page: 5)
    [listings, nil]
  rescue ReverbClient::ApiError => e
    [[], e.message]
  end
end
```

**Ruby** — `config/routes.rb`:

```ruby
root "dashboard#index"
resources :categories, only: [:index]
resources :listings, only: [:index, :show]
```

**React** — `DashboardPage.js`:

```jsx
import React, { useEffect, useState } from 'react';
import { fetchCategories, fetchListings } from './API';
import { Link } from 'react-router-dom';

export default function DashboardPage() {
  const [categories, setCategories] = useState([]);
  const [listings, setListings] = useState([]);
  const [categoriesError, setCategoriesError] = useState(null);
  const [listingsError, setListingsError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([fetchCategories(), fetchListings()])
      .then(([catResult, listResult]) => {
        if (catResult.status === 'fulfilled') {
          setCategories(catResult.value.categories.slice(0, 5));
        } else {
          setCategoriesError('Unable to load categories.');
        }

        if (listResult.status === 'fulfilled') {
          setListings(listResult.value.listings.slice(0, 5));
        } else {
          setListingsError('Unable to load listings.');
        }
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="loading">Loading dashboard...</p>;

  return (
    <div className="dashboard">
      <section className="dashboard__categories">
        <h2>Top Categories</h2>
        {categoriesError
          ? <p className="error">{categoriesError}</p>
          : <CategoryList categories={categories} />}
      </section>

      <section className="dashboard__listings">
        <h2>Recent Listings</h2>
        {listingsError
          ? <p className="error">{listingsError}</p>
          : <ListingList listings={listings} />}
      </section>
    </div>
  );
}
```

### 2b. Template — Partial Rendering with Graceful Degradation

**Python** — `templates/dashboard.html`:

```html
{% extends 'base.html' %}
{% block content %}
<h1>Dashboard</h1>

<section class="dashboard__categories">
  <h2>Top Categories</h2>
  {% if categories_error %}
    <p class="error">{{ categories_error }}</p>
  {% elif categories %}
    <ul class="list-group">
      {% for category in categories %}
        <li class="list-group-item">
          <a href="{{ url_for('listings', category=category['slug']) }}">
            {{ category['full_name'] }}
          </a>
        </li>
      {% endfor %}
    </ul>
  {% else %}
    <p>No categories available.</p>
  {% endif %}
</section>

<section class="dashboard__listings">
  <h2>Recent Listings</h2>
  {% if listings_error %}
    <p class="error">{{ listings_error }}</p>
  {% elif listings %}
    <ul class="list-group">
      {% for listing in listings %}
        <li class="list-group-item">
          <a href="{{ url_for('listing_detail', listing_id=listing['id']) }}">
            {{ listing['title'] }}
          </a>
          {% if listing.get('price') %}
            <span class="price">{{ listing['price']['display'] }}</span>
          {% endif %}
        </li>
      {% endfor %}
    </ul>
  {% else %}
    <p>No listings available.</p>
  {% endif %}
</section>
{% endblock %}
```

**Ruby** — `app/views/dashboard/index.html.erb`:

```erb
<h1>Dashboard</h1>

<section class="dashboard__categories">
  <h2>Top Categories</h2>
  <% if @categories_error %>
    <p class="error"><%= @categories_error %></p>
  <% elsif @categories.present? %>
    <ul class="list-group">
      <% @categories.each do |category| %>
        <li class="list-group-item">
          <%= link_to category['full_name'], listings_path(category: category['slug']) %>
        </li>
      <% end %>
    </ul>
  <% else %>
    <p>No categories available.</p>
  <% end %>
</section>

<section class="dashboard__listings">
  <h2>Recent Listings</h2>
  <% if @listings_error %>
    <p class="error"><%= @listings_error %></p>
  <% elsif @listings.present? %>
    <ul class="list-group">
      <% @listings.each do |listing| %>
        <li class="list-group-item">
          <%= link_to listing['title'], listing_path(listing['id']) %>
          <% if listing['price'] %>
            <span class="price"><%= listing['price']['display'] %></span>
          <% end %>
        </li>
      <% end %>
    </ul>
  <% else %>
    <p>No listings available.</p>
  <% end %>
</section>
```

### 2c. Key Patterns to Narrate

1. **Independent error handling:** Each API call is wrapped independently. If categories fail, listings still render. The page is always useful.
2. **Service helpers as coordination point:** `_load_dashboard_categories()` returns a tuple of (data, error). The route stays thin — it just passes results to the template.
3. **`Promise.allSettled` (React):** Unlike `Promise.all` which rejects on first failure, `allSettled` waits for all to complete and reports individual outcomes. Critical for partial rendering.
4. **Slicing at the service layer:** `[:5]` happens in the helper, not the template. The template should never contain business logic like "show only 5."

______________________________________________________________________

## Phase 3: Test

**Python** — `tests/test_dashboard.py`:

```python
def test_dashboard_renders_both_sections(client):
    with patch('reverb_client.requests.get') as mock_get:
        mock_get.return_value.json.side_effect = [
            {'categories': [{'full_name': 'Guitars', 'slug': 'guitars'}]},
            {'listings': [{'id': '1', 'title': 'Fender Tele', 'price': {'display': '$500'}}]},
        ]
        mock_get.return_value.ok = True
        res = client.get('/dashboard')

    html = parse_html(res)
    assert 'Guitars' in html.select_one('.dashboard__categories').text
    assert 'Fender Tele' in html.select_one('.dashboard__listings').text


def test_dashboard_shows_listings_when_categories_fail(client):
    with patch('app._load_dashboard_categories', return_value=([], 'API error')):
        with patch('app._load_dashboard_listings',
                   return_value=([{'id': '1', 'title': 'Working', 'price': {'display': '$100'}}], None)):
            res = client.get('/dashboard')

    html = parse_html(res)
    assert 'API error' in html.select_one('.dashboard__categories .error').text
    assert 'Working' in html.select_one('.dashboard__listings').text


def test_dashboard_shows_categories_when_listings_fail(client):
    with patch('app._load_dashboard_categories',
               return_value=([{'full_name': 'Guitars', 'slug': 'guitars'}], None)):
        with patch('app._load_dashboard_listings', return_value=([], 'Timeout')):
            res = client.get('/dashboard')

    html = parse_html(res)
    assert 'Guitars' in html.select_one('.dashboard__categories').text
    assert 'Timeout' in html.select_one('.dashboard__listings .error').text


def test_dashboard_limits_to_5_items(client):
    categories = [{'full_name': f'Cat {i}', 'slug': f'cat-{i}'} for i in range(20)]
    with patch('app._load_dashboard_categories',
               return_value=(categories[:5], None)):
        with patch('app._load_dashboard_listings',
                   return_value=([{'id': str(i), 'title': f'Item {i}'} for i in range(5)], None)):
            res = client.get('/dashboard')

    html = parse_html(res)
    category_items = html.select('.dashboard__categories .list-group-item')
    assert len(category_items) == 5
```

**Ruby** — `spec/requests/dashboard_spec.rb`:

```ruby
describe "GET /" do
  let(:client) { instance_double(ReverbClient) }

  before { allow(ReverbClient).to receive(:new).and_return(client) }

  context "when both APIs succeed" do
    before do
      allow(client).to receive(:categories).and_return([{ 'full_name' => 'Guitars', 'slug' => 'guitars' }])
      allow(client).to receive(:listings).and_return([{ 'id' => '1', 'title' => 'Fender' }])
    end

    it "renders both sections" do
      get root_path
      assert_select ".dashboard__categories", /Guitars/
      assert_select ".dashboard__listings", /Fender/
    end
  end

  context "when categories API fails" do
    before do
      allow(client).to receive(:categories).and_raise(ReverbClient::ApiError, "timeout")
      allow(client).to receive(:listings).and_return([{ 'id' => '1', 'title' => 'Fender' }])
    end

    it "still shows listings" do
      get root_path
      assert_select ".dashboard__categories .error", /timeout/
      assert_select ".dashboard__listings", /Fender/
    end
  end
end
```

**React**:

```jsx
import { render, screen, waitFor } from '@testing-library/react';
import * as API from './API';
import DashboardPage from './DashboardPage';

it('renders both sections on success', async () => {
  jest.spyOn(API, 'fetchCategories').mockResolvedValue({
    categories: [{ full_name: 'Guitars', slug: 'guitars' }]
  });
  jest.spyOn(API, 'fetchListings').mockResolvedValue({
    listings: [{ id: '1', title: 'Fender Tele', price: { display: '$500' } }]
  });

  render(<DashboardPage />);

  await waitFor(() => {
    expect(screen.getByText('Guitars')).toBeInTheDocument();
    expect(screen.getByText('Fender Tele')).toBeInTheDocument();
  });
});

it('shows listings even when categories fail', async () => {
  jest.spyOn(API, 'fetchCategories').mockRejectedValue(new Error('timeout'));
  jest.spyOn(API, 'fetchListings').mockResolvedValue({
    listings: [{ id: '1', title: 'Fender Tele' }]
  });

  render(<DashboardPage />);

  await waitFor(() => {
    expect(screen.getByText(/unable to load categories/i)).toBeInTheDocument();
    expect(screen.getByText('Fender Tele')).toBeInTheDocument();
  });
});
```

______________________________________________________________________

## Phase 4: Trade-off Discussion Points

- **Sequential vs parallel fetching?** In Python/Ruby (synchronous), calls are sequential by default. Could use `concurrent.futures.ThreadPoolExecutor` (Python) or `Parallel` gem (Ruby) for true parallelism. In React, `Promise.allSettled` is naturally parallel. For two fast calls, sequential is fine — parallelism adds complexity.

- **`Promise.all` vs `Promise.allSettled`?** `.all` rejects on first failure — entire page breaks if one call fails. `.allSettled` gives you individual results — critical for partial rendering.

- **Why not one API call?** A backend-for-frontend (BFF) could aggregate both in one endpoint. But that's an architecture change beyond interview scope. Mention it: "In production, if latency matters, I'd consider a BFF layer or GraphQL to batch these."

- **What about caching?** Categories rarely change — could cache with a 5-minute TTL. Listings change frequently — cache briefly or not at all. `functools.lru_cache` for in-process, Redis for multi-process.

- **Service object vs helper functions?** For this scope, `_load_dashboard_*` functions are fine. At scale, a `DashboardService` class encapsulates the coordination and becomes individually testable.

- **What if both fail?** The page still renders — just with two error messages. You could add a threshold: "If everything fails, show a full error page instead of an empty shell." That's a UX decision to discuss with product.

- **N+1 concern?** Not applicable here (two calls total), but shows you're thinking about it. If the dashboard grew to "show 5 categories with their top listing each," that's 6 calls — time for a batch endpoint.

- **Testing strategy for composition?** Mock at the service helper level (`_load_dashboard_categories`), not at `requests.get`. This keeps dashboard tests focused on rendering logic, not HTTP details. Client tests already cover the HTTP layer.
