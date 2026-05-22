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

**Detail endpoint returns 47 fields** (vs. 26 in the collection view). The 21 detail-only fields break down as follows:

**Worth rendering on the detail page (user-facing value):**

| Field | Type | Why it matters |
| -- | -- | -- |
| `accepted_payment_methods` | array | Buyer needs to know how to pay |
| `location` | object | Where the item ships from |
| `shipping_policy` | string | Shipping terms and timeframes |
| `payment_policy` | string | Payment terms |
| `return_policy` | object | Refund/return conditions — critical for buyer trust |
| `videos` | array | Additional media (demo videos, etc.) |
| `stats` | object | Views, watchers — social proof |
| `offer_count` | number | Shows demand/activity |
| `handmade` | boolean | Product characteristic worth highlighting |
| `sold_as_is` | boolean | Important buyer disclosure (no warranty) |
| `local_pickup_only` | boolean | Critical — changes shipping expectations entirely |

**Internal/administrative (not worth rendering):**

| Field | Type | Why skip |
| -- | -- | -- |
| `in_watchlist` | boolean | Requires auth — not for public detail page |
| `draft` | boolean | Seller admin state |
| `live` | boolean | Seller admin state |
| `cloudinary_photos` | array | Duplicate of `photos` in different CDN format |
| `upc_does_not_apply` | boolean | Seller metadata, irrelevant to buyers |
| `origin_country_code` | string | Redundant — `location` already covers this |
| `same_day_shipping_ineligible` | boolean | Minor detail, `shipping_policy` covers this |
| `has_offer_for_buyer` | boolean | Requires auth |
| `is_my_listing` | boolean | Requires auth |
| `comparison_shopping_page_id` | string | Internal Reverb routing |

**Photos:** The detail endpoint returns **all photos** (e.g., 3+) vs. only 1 in the collection view. Plan to iterate/display multiple images.

### URL Construction vs. Link-Following (HATEOAS trade-off)

**Context:** this is about how your *server* calls the Reverb API — not browser navigation. The user always lands on your own Flask-rendered detail page.

The collection response includes `_links.self.href` for each listing (e.g., `https://api.reverb.com/api/listings/97305295-fender-telecaster-...`). In theory, your client could follow that URL directly instead of constructing `/listings/{id}` manually.

**Recommendation: construct URLs manually.** Here's why:

1. **You need construction anyway** — direct-access routes (bookmarks, shared links) only have the ID. You'd need two code paths if you also supported link-following.
2. **Security (SSRF risk)** — blindly following URLs from an external API response means your server will request whatever URL that response contains. An attacker who compromises the upstream API (or injects into the response) could redirect your server to internal services. Constructing from a known base URL + ID eliminates this.
3. **Single code path** — one `_get(f'/listings/{id}')` method works for every access pattern. No conditional logic, no "did we come from the collection view?" checks.
4. **Stable API** — Reverb's URL structure is versioned. It won't change without a major version bump. The HATEOAS benefit of "the server can change URLs and clients adapt" doesn't apply to a third-party API you don't control the versioning of.

**When link-following *would* make sense:** if you controlled both the API and the client (internal microservices), or if the API used opaque URLs that couldn't be constructed from known patterns.

**Interview framing:** "The collection response gives me `_links.self.href` which I *could* follow, but I construct the URL manually because: I need it for direct-access routes anyway, I avoid SSRF by not following external URLs blindly, and one code path is simpler than two. If this were an internal API I controlled, I might follow links to decouple from URL structure — but for a third-party API with stable versioning, explicit construction is safer and simpler."

**"But we use image URLs from the API in `<img>` tags — isn't that the same risk?"** No. The critical distinction is **who fetches the URL**:

| URL usage | Who fetches | SSRF risk? | Why |
| -- | -- | -- | -- |
| `_links.self.href` → server calls Reverb API | Your server | **Yes** | Server has access to internal network (cloud metadata, internal services) |
| `_links.large_crop.href` → rendered in `<img src>` | User's browser | **No** | Browser is sandboxed on the user's machine, cannot reach your internal infrastructure |

SSRF is specifically about tricking your *server* into making requests to unintended destinations. Image URLs in HTML are fetched by the browser — which can't reach `http://169.254.169.254/metadata` on your cloud provider. Rendering external image URLs from a trusted API in `<img>` tags is standard practice.

**Optional UX enhancement:** include a "View on Reverb" external link inside your detail page using `_links.web.href` — but that's a secondary user action, not an API call pattern.

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

### What if the listing doesn't exist?

Handle 404 from the API gracefully. Show a user-friendly "Listing not found" page rather than crashing with a stack trace. In Flask, catch the `ReverbHTTPError` with status 404 and render a custom template.

### Would you cache the listing data?

The listings page already fetched ~28 fields per listing from the collection endpoint. When the user clicks through to a detail page, you could avoid a second API call by reusing that data.

**Why it's tempting:** less latency, one fewer API call, better UX for the click-through flow.

**Why you still need the API call:**

- The detail endpoint returns **47 fields** vs. 26 in the collection — 21 fields are detail-only. You'd be missing `shipping_policy`, `return_policy`, `accepted_payment_methods`, `stats`, `videos`, `location`, extra photos, etc. (Note: `description` is actually in both, but the collection version may be truncated.)
- Direct-access routes (bookmarks, shared links) have no cached data — you need the API call anyway.
- Stale data — the listing may have changed since the index was fetched (price drop, sold, etc.).

**What to say:** "I could skip the API call if coming from the listings page, but the detail endpoint returns 21 additional fields I don't have — including return policy, payment methods, shipping policy, videos, and stats. Plus direct-access routes need the call regardless. One code path that always fetches fresh data is simpler and more correct. If latency were a problem, I'd cache at the client level with a short TTL."

**Hybrid approach (if pressed):** render the page immediately with the 28 fields you have (title, thumbnail, price), then hydrate in the background with the full detail response. This is a progressive-enhancement pattern — fast first paint, then complete data. Worth mentioning but probably overkill for a 45-min interview.

**How this would work in Flask:**

Flask is server-rendered, so "hydrate in the background" requires a small client-side layer:

1. The listings page passes partial data (title, price, thumbnail) via a query param or stores it in the user's session.
2. The detail route renders immediately with that partial data + skeleton placeholders for missing fields (description, extra photos, shipping policy).
3. A small inline `<script>` on the detail page calls a JSON endpoint on your own backend (e.g., `GET /api/listings/123/full`) which fetches from Reverb and returns the complete object.
4. The script populates the placeholder elements with the full data.

```python
# Route 1: renders immediately with partial data
@app.route('/listings/<listing_id>')
def listing_detail(listing_id):
    # Partial data passed from collection (e.g., via session or query param)
    partial = session.pop(f'listing_{listing_id}', None)
    if partial:
        # Fast path: render immediately with what we have
        return render_template('listing_detail.html', listing=partial, partial=True)
    # Slow path (direct access): fetch everything synchronously
    listing = ReverbClient().listing(listing_id)
    return render_template('listing_detail.html', listing=listing, partial=False)

# Route 2: JSON endpoint for client-side hydration
@app.route('/api/listings/<listing_id>/full')
def listing_full_json(listing_id):
    listing = ReverbClient().listing(listing_id)
    return jsonify(listing)
```

```html
<!-- In listing_detail.html -->
{% if partial %}
<script>
  fetch('/api/listings/{{ listing["id"] }}/full')
    .then(r => r.json())
    .then(data => {
      document.querySelector('.listing-description').textContent = data.description || '';
      // ... populate other fields
    });
</script>
{% endif %}
```

**Why this is usually overkill:** the Reverb API responds in ~200-400ms. The user won't notice. The added complexity (two routes, client-side JS, partial rendering logic, session management) isn't justified unless you're seeing real latency problems. In a 45-min interview, just fetch synchronously and mention this as a future optimization.

### What about the URL slug?

Reverb's API accepts **both** the numeric ID alone and the full ID+slug form:

```bash
# Both resolve to the same listing:
GET /api/listings/64997892
GET /api/listings/64997892-positive-grid-bias-modulation-twin-effect-pedal
```

The `_links.self.href` always returns the full slug form (`64997892-positive-grid-bias-modulation-twin-effect-pedal`).

**For our app's routes**, we have a choice:

| Route pattern | Example | Trade-off |
| -- | -- | -- |
| `/listings/<id>` (numeric) | `/listings/64997892` | Simple, stable, but ugly and not SEO-friendly |
| `/listings/<id>-<slug>` | `/listings/64997892-positive-grid-bias-modulation-twin-effect-pedal` | SEO-friendly, human-readable, matches Reverb's pattern |

**Recommendation for the interview:** use the numeric ID for routing (`/listings/<listing_id>`) and pass just the ID to the API. Reasons:

1. **Simplicity** — one URL segment, one parameter, no slug generation logic.
2. **API accepts it** — `GET /api/listings/64997892` works fine without the slug.
3. **No slug maintenance** — if a listing title changes, slug-based URLs break unless you implement redirects.
4. **Interview scope** — slug generation is tangential complexity that doesn't demonstrate core skills.

**What to say:** "Reverb's API accepts both the bare ID and the ID+slug. I'm using just the ID for simplicity — it works, it's stable, and I don't need to generate or maintain slugs. In production, I'd add the slug for SEO (better Google indexing, human-readable URLs) and implement a redirect from the bare ID to the canonical slug URL — same pattern as Stack Overflow or GitHub."

**If asked to implement the slug:** the slug already exists in the collection response — each listing's `id` field is the numeric ID, but `_links.self.href` contains the full `{id}-{slug}` form. You can extract the slug segment from the self link and use it in your app's URLs.

Full flow:

```python
# In reverb_client.py — helper to extract slug from self link
def _extract_slug(self, listing):
    """Extract '64997892-positive-grid-...' from the self link URL."""
    # _links.self.href = "https://api.reverb.com/api/listings/64997892-positive-grid-..."
    return listing['_links']['self']['href'].split('/listings/')[-1]
```

```html
<!-- In listings.html — link uses the slug form for SEO-friendly URLs -->
<a href="{{ url_for('listing_detail', listing_slug=listing['_links']['self']['href'].split('/listings/')[-1]) }}">
  {{ listing['title'] }}
</a>
```

```python
# In app.py — route accepts the full slug form
@app.route('/listings/<listing_slug>')
def listing_detail(listing_slug):
    # The API accepts both "64997892" and "64997892-positive-grid-bias-..."
    # so we pass the full slug directly — no parsing needed
    listing = ReverbClient().listing(listing_slug)
    return render_template('listing_detail.html', listing=listing)
```

This works because the API treats `64997892` and `64997892-positive-grid-bias-modulation-twin-effect-pedal` as equivalent — the slug suffix is ignored for lookup purposes, but returned in canonical form in responses. Your app gets SEO-friendly URLs (`/listings/64997892-positive-grid-bias-modulation-twin-effect-pedal`) without any slug generation logic — you just pass through what Reverb gives you.

### N+1 concern

**What N+1 means:** making N additional queries/API calls after an initial query — typically one per item in a list.

**Concrete example in this app:** imagine the listings index page needs to show each seller's average rating. The collection endpoint (`/listings/all`) doesn't include shop ratings. To get them, you'd need to:

1. Fetch 50 listings from `/listings/all` (1 call)
2. For each listing, call `/shops/{shop_id}` to get the rating (50 calls)

Total: 51 API calls to render one page. That's N+1.

**Why it doesn't apply to the detail page:** you make exactly **one** API call (`GET /listings/{id}`) that returns everything needed — title, description, price, photos, shop info — in a single response. No loop, no per-item fetching.

**How well-designed REST APIs prevent N+1:**

The solution depends on what the API offers:

1. **Embedded/sideloaded resources** — some APIs support query parameters like `?include=shop` or `?embed=shop_details` that inline related resources into the response. This is the ideal solution: one call, all data. Whether this exists depends entirely on the API designer. Reverb's collection endpoint already embeds a subset of shop info per listing (shop name, link) — so for basic shop data, N+1 is already avoided.

2. **Batch endpoints** — some APIs offer `/shops?ids=1,2,3` to fetch multiple resources in one call. If available, you collect all unique shop IDs from the listings response and make one batch call instead of N individual calls.

3. **GraphQL** — if the service exposes a GraphQL API (Reverb does not publicly, but some services do), you can request exactly the fields you need across related resources in a single query. This eliminates N+1 by design — the client specifies the shape of data it wants, and the server resolves it in one round-trip.

4. **Accept the N+1 with mitigation** — if none of the above are available, several strategies reduce the impact:

   - **Pagination** — reduce N itself. Instead of loading 50 listings with 50 shop calls, load 10 per page. N+1 becomes 10+1 — manageable latency. Pagination is the simplest mitigation and often sufficient.

   - **Prefetching next pages** — while the user views page 1, prefetch page 2's data (including the N additional calls) in the background. By the time they click "Next", the data is ready. In Flask, this would be a client-side `fetch()` triggered after the initial page renders.

   - **Server-side caching** — shop data changes infrequently. Cache shop responses with a TTL (e.g., 5 minutes) so repeated listings from the same shop don't trigger additional API calls. After the first page load, most shops are cached and subsequent pages are fast.

   - **Client-side caching** — in a React SPA, store fetched shop data in state/context. As the user navigates between pages, previously-seen shops don't need re-fetching. HTTP cache headers (`Cache-Control: max-age=300`) also prevent redundant browser-to-server calls.

   - **Concurrent requests** — if you must make N calls, make them in parallel (Python: `asyncio.gather()` or `concurrent.futures.ThreadPoolExecutor`; JS: `Promise.all()`). Latency becomes max(N calls) instead of sum(N calls).

   - **Progressive enhancement / hydration** — render the page immediately with the data you have (title, price, photo from the collection response), then hydrate missing fields (shop rating, detailed stats) asynchronously. The user sees a fast initial render and additional data fills in within milliseconds. This is the same pattern discussed in the caching section above — render what you have, fetch what you don't in the background.

   ```python
   # Example: render listings immediately, hydrate shop ratings async
   @app.route('/listings')
   def listings():
       listings = ReverbClient().listings()
       # Render page with what we have — no shop ratings yet
       return render_template('listings.html', listings=listings)

   @app.route('/api/shop-ratings')
   def shop_ratings():
       """JSON endpoint called by client-side JS after page load."""
       shop_ids = request.args.getlist('ids')
       # Batch fetch or cached lookup
       ratings = {sid: get_cached_shop_rating(sid) for sid in shop_ids}
       return jsonify(ratings)
   ```

   ```html
   <!-- Client-side hydration for shop ratings -->
   <script>
     const shopIds = [...document.querySelectorAll('[data-shop-id]')]
       .map(el => el.dataset.shopId);
     fetch(`/api/shop-ratings?${shopIds.map(id => `ids=${id}`).join('&')}`)
       .then(r => r.json())
       .then(ratings => {
         Object.entries(ratings).forEach(([id, rating]) => {
           document.querySelector(`[data-shop-id="${id}"] .rating`).textContent = `★ ${rating}`;
         });
       });
   </script>
   ```

   This combines several mitigations: the page renders fast (progressive enhancement), the ratings call is batched (one call for all shops, not N), and results can be cached server-side.

**What to say:** "No N+1 here — it's a single fetch for a single resource. But if the index page needed data the collection endpoint doesn't provide (like detailed shop ratings), I'd first check if the API supports embedding related resources via a query parameter like `?include=shop`. If not, I'd look for a batch endpoint. If neither exists and the service has a GraphQL API, that's the cleanest solution — one query, exact data shape. Failing all of that, concurrent requests with caching would be the pragmatic fallback."

### What would you show while loading?

- **Spinner** — simplest, signals "loading" but offers no layout stability
- **Skeleton screen** — shows the page structure (grey boxes for title, image, description) before data arrives. Feels faster, reduces layout shift. More work to implement but better UX.
- **Server-side rendering** — Flask already does this; the page arrives fully rendered. The "loading" concern applies more to the React version where `useEffect` fetches after mount.

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
