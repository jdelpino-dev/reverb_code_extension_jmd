# Scenario 1: Listing Detail Page

## The Ask

> "When a user clicks on a listing, they should see a detail page with more information."

This is the most classic interview extension — add a second route for an existing resource.

______________________________________________________________________

## Phase 1: Explain the Architecture (2-3 min)

**What to say:**

"The app currently fetches all listings from `/api/listings/all` and renders them as a flat list. Each listing has a title and thumbnail. There's no way to drill into a single listing. The `ReverbClient` only knows two endpoints — categories and listings. I'd extend it to fetch a single listing by ID, add a new route, and render the detail."

______________________________________________________________________

## Phase 2: Implement

### 2a. Discover the API

Reverb's public API exposes: `GET /api/listings/{id}` → returns a single listing object with fields like:

- `title`, `description`, `price`, `condition`, `shipping`, `photos[]`, `shop` info

**Detail endpoint returns 46 fields** (vs. ~28 in the collection view). Additional fields include: `accepted_payment_methods`, `return_policy`, `shipping_policy`, `location`, `videos`, `stats`, `offer_count`, and more.

**Photos:** The detail endpoint returns **all photos** (e.g., 3+) vs. only 1 in the collection view. Plan to iterate/display multiple images.

### URL Construction vs. Link-Following

Each listing in the collection view includes `_links.self.href` (e.g., `https://api.reverb.com/api/listings/97305295-fender-telecaster-...`).

**When link-following helps here:** If the user navigates from the listings page (where you already have the listing object in memory), you can pass `_links.self.href` to the detail page and use it directly — no URL construction needed.

**When URL construction is necessary:** When a user bookmarks or directly visits `/listings/123`, your route receives only the ID — you *must* construct the API URL. There's no `_links` to follow because you don't have a listing object yet.

**Interview framing:** "I construct the URL from the ID because the route only has an ID. If I were navigating from the collection view, I could pass the `_links.self.href` through — but for direct-access routes, URL construction is unavoidable."

### 2b. Extend the API Client

**Ruby** (`lib/reverb_client.rb`):

```ruby
def listing(id)
  get("/listings/#{id}")
end
```

**Python** (`reverb_client.py`):

```python
def listing(self, listing_id):
    return self._get(f'/listings/{listing_id}')
```

**React** (`API.js`):

```javascript
export async function fetchListing(id) {
  return getJSON(`${LISTINGS_URL}/${id}`);
}
```

**Note:** Unlike the collection endpoint (which wraps results in `{"listings": [...]}`) the detail endpoint returns the listing object **directly at the top level** with 46 keys. No `['listing']` unwrap needed.

### 2c. Add Route + Controller/Component

**Ruby** — `config/routes.rb`:

```ruby
resources :listings, only: [:index, :show]
```

**Ruby** — `app/controllers/listings_controller.rb`:

```ruby
def show
  @listing = ReverbClient.new.listing(params[:id])
end
```

**Python** — `app.py`:

```python
@app.route('/listings/<listing_id>')
def listing_detail(listing_id):
    listing = ReverbClient().listing(listing_id)
    return render_template('listing_detail.html', listing=listing)
```

**React** — New `ListingDetailPage.js`:

```jsx
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchListing } from './API';

export default function ListingDetailPage() {
  const { id } = useParams();
  const [listing, setListing] = useState(null);

  useEffect(() => {
    fetchListing(id).then(res => setListing(res.listing));
  }, [id]);

  if (!listing) return <p>Loading...</p>;

  return (
    <div className="listing-detail">
      <h1>{listing.title}</h1>
      <img src={listing.photos[0]._links.large_crop.href} alt={listing.title} />
      <p>{listing.description}</p>
      <p className="listing-detail__price">{listing.price.display}</p>
    </div>
  );
}
```

### 2d. Link from Listings Page

**Ruby** — `app/views/listings/index.html.erb`: Wrap title in a `link_to`:

```erb
<%= link_to listing['title'], listing_path(listing['id']) %>
```

**React** — `ListingsPage.js`: Wrap in `<Link>`:

```jsx
import { Link } from 'react-router-dom';
// ...
<Link to={`/listings/${listing.id}`}>{listing.title}</Link>
```

### 2e. Add View/Template

**Ruby** — `app/views/listings/show.html.erb`:

```erb
<h1><%= @listing['title'] %></h1>
<img src="<%= @listing['photos'].first['_links']['large_crop']['href'] %>" />
<p><%= @listing['description'] %></p>
<p><strong><%= @listing['price']['display'] %></strong></p>
```

**Python** — `templates/listing_detail.html`:

```html
{% extends 'base.html' %}
{% block content %}
<h1>{{ listing['title'] }}</h1>
<img src="{{ listing['photos'][0]['_links']['large_crop']['href'] }}" />
<p>{{ listing['description'] }}</p>
<p><strong>{{ listing['price']['display'] }}</strong></p>
{% endblock %}
```

______________________________________________________________________

## Phase 3: Test

**Ruby** — `spec/lib/reverb_client_spec.rb`:

```ruby
it 'fetches a single listing' do
  stub_request(:get, "https://api.reverb.com/api/listings/123")
    .to_return(status: 200, body: { title: 'Test', price: { display: '$500' } }.to_json)

  listing = client.listing('123')
  expect(listing['title']).to eq('Test')
end
```

**Ruby** — `spec/requests/listings_spec.rb`:

```ruby
describe "GET /listings/:id" do
  let(:listing) { { 'title' => 'Fender', 'description' => 'Nice', 'price' => { 'display' => '$500' }, 'photos' => [{ '_links' => { 'large_crop' => { 'href' => 'img.png' } } }] } }

  before { allow(ReverbClient).to receive(:new) { instance_double(ReverbClient, listing: listing) } }

  it "displays listing details" do
    get listing_path(id: '123')
    assert_select "h1", "Fender"
  end
end
```

**Python**:

```python
def test_displays_listing_detail(client):
    res = client.get('/listings/123')
    html = parse_html(res)
    assert 'Some Cool Instrument' in html.body.h1.text
```

**React**:

```jsx
it('displays listing detail', async () => {
  const response = Promise.resolve({ title: 'Test', photos: [{_links: {large_crop: {href: 'img.png'}}}], price: { display: '$100' } });
  jest.spyOn(API, 'fetchListing').mockImplementation(() => response);
  // mount, await, assert
});
```

______________________________________________________________________

## Phase 4: Trade-off Discussion Points

- **What if the listing doesn't exist?** → Handle 404 from the API gracefully
- **Would you cache the listing data?** → Could check if we already have it from the index fetch
- **What about the URL slug?** → Reverb uses slug-based URLs (`/item/fender-tele`), discuss RESTful vs. SEO-friendly
- **N+1 concern?** → Not here (single fetch), but mention awareness
- **What would you show while loading?** → Skeleton screen vs. spinner

______________________________________________________________________

## Python Implementation — Full Walkthrough

This is your primary interview stack. Here's the complete implementation with annotations.

### Step 1: Extend `reverb_client.py`

```python
def listing(self, listing_id):
    """Fetch a single listing by ID."""
    return self._get(f'/listings/{listing_id}')
```

**What to say:** "I'm adding a method that takes an ID and hits the individual listing endpoint. Unlike the collection endpoint which wraps in `{'listings': [...]}`, the detail endpoint returns the listing object directly — no unwrapping needed. I verified this from the API response structure (46 keys at the top level)."

### Step 2: Add route in `app.py`

```python
@app.route('/listings/<listing_id>')
def listing_detail(listing_id):
    listing = ReverbClient().listing(listing_id)
    return render_template('listing_detail.html', listing=listing)
```

**What to say:** "Flask's angle-bracket syntax captures the URL segment as a parameter. I'm passing it through to the client and rendering a new template."

**Note the difference from Rails:** In Rails you'd add `resources :listings, only: [:index, :show]` and a `show` action. Flask doesn't have resourceful routing — each route is explicit. This is actually an advantage for this interview: you can explain exactly what's happening.

### Step 3: Link from listings page — `templates/listings.html`

```html
{% for listing in listings %}
  <li class="d-flex list-group-item flex-row align-items-center">
    <div class="p-2">
      <img src="{{ listing['photos'][0]['_links']['thumbnail']['href'] }}" />
    </div>
    <div class="p-2 flex-grow-1">
      <h2>
        <a href="{{ url_for('listing_detail', listing_id=listing['id']) }}">
          {{ listing['title'] }}
        </a>
      </h2>
    </div>
  </li>
{% endfor %}
```

**What to say:** "`url_for` generates the URL from the function name. This is like Rails' `listing_path` helper but explicit — you name the function, not the route."

### Step 4: New template — `templates/listing_detail.html`

```html
{% extends 'base.html' %}
{% block content %}
<div class="listing-detail">
  <h1>{{ listing['title'] }}</h1>

  {% if listing['photos'] %}
    <img src="{{ listing['photos'][0]['_links']['large_crop']['href'] }}"
         alt="{{ listing['title'] }}"
         class="img-fluid mb-3" />
  {% endif %}

  {% if listing.get('description') %}
    <p>{{ listing['description'] }}</p>
  {% endif %}

  {% if listing.get('price') %}
    <p class="h4 text-success">{{ listing['price']['display'] }}</p>
  {% endif %}

  <a href="{{ url_for('listings') }}" class="btn btn-outline-secondary">← Back to listings</a>
</div>
{% endblock %}
```

**What to say:** "I'm using `listing.get('description')` instead of `listing['description']` for optional fields — avoids a KeyError if the API doesn't include it. For `photos` I check the list isn't empty."

### Step 5: Full test file — `tests/test_listing_detail.py`

```python
from app import app

import pytest
from tests.helpers import parse_html
from unittest.mock import patch

@pytest.fixture
def client():
    app.config['TESTING'] = True

    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'id': '123',
        'title': 'Fender Telecaster',
        'description': 'A nice guitar',
        'price': {'amount': '1200.00', 'amount_cents': 120000, 'display': '$1,200'},
        'photos': [{
            '_links': {
                'large_crop': {'href': 'https://img.reverb.com/large.jpg'}
            }
        }]
    }

    with app.test_client() as client:
        yield client

def test_displays_listing_title(client):
    res = client.get('/listings/123')
    html = parse_html(res)
    assert 'Fender Telecaster' in html.body.h1.text

def test_displays_listing_price(client):
    res = client.get('/listings/123')
    html = parse_html(res)
    assert '$1,200' in html.body.text

def test_displays_listing_image(client):
    res = client.get('/listings/123')
    html = parse_html(res)
    img = html.body.select_one('img')
    assert img['src'] == 'https://img.reverb.com/large.jpg'

def test_has_back_link(client):
    res = client.get('/listings/123')
    html = parse_html(res)
    back_link = html.body.select_one('a[href="/listings"]')
    assert back_link is not None
```

**What to say:** "I'm testing four things independently: title renders, price renders, image src is correct, and there's a back link. Each test is focused on one assertion."

### Step 6: Client unit test — add to `tests/test_reverb_client.py`

```python
def test_fetches_single_listing():
    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'id': '123', 'title': 'Fender Telecaster'
    }

    listing = ReverbClient().listing('123')

    assert listing['title'] == 'Fender Telecaster'
    mock_get.assert_called_once()
    call_url = mock_get.call_args[0][0]
    assert '/listings/123' in call_url
```

### Rails comparison notes (for discussion)

| Aspect | Rails approach | Flask approach (what you did) |
| -- | -- | -- |
| Route | `resources :listings, only: [:index, :show]` — implicit `/listings/:id` | `@app.route('/listings/<listing_id>')` — explicit |
| Params | `params[:id]` via ActionDispatch | Function argument from URL capture |
| Template | `render` is implicit (convention: `show.html.erb`) | `render_template('listing_detail.html', ...)` — explicit |
| Link helper | `listing_path(listing)` (assumes `.id`) | `url_for('listing_detail', listing_id=...)` |
| Test double | `instance_double(ReverbClient)` | `patch('reverb_client.requests.get')` |

**Key insight to articulate:** "In Rails, convention means less code but more implicit behavior. Here I have to be explicit about template name and variable passing, which makes the code more traceable but slightly more verbose."
