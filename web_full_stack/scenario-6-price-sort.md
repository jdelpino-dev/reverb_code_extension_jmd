# Scenario 6: Price Display + Sort

## The Ask

> "Show the price for each listing, and let users sort listings by price."

Tests ability to work with nested data, add UI controls, and implement sorting logic.

______________________________________________________________________

## Phase 1: Explain

"Each listing from the API has a `price` object with fields like `amount` and `display` (formatted string). Currently we only show title and photo. I'll add the price to the display, then add a sort control."

**Clarifying questions:**

- "Should sorting happen client-side (re-order what we have) or should I pass a sort param to the API?"
- "Ascending, descending, or let the user toggle?"

______________________________________________________________________

## Phase 2: Implement

### 2a. Display Price (No API Change Needed)

The listing response already contains:

```json
{
  "title": "Fender Telecaster",
  "price": {
    "tax_included": false,
    "amount": "1200.00",
    "amount_cents": 120000,
    "currency": "USD",
    "symbol": "$",
    "display": "$1,200"
  }
}
```

### GOTCHA: `price.amount` is a STRING

`amount` is `"1200.00"` (string), not `1200.00` (number). Sorting directly without casting produces **lexicographic order** where `"95" > "450"`. You MUST cast to numeric for sorting.

### Better: Use `amount_cents` for Sorting

`price.amount_cents` is an **integer** (120000). Sorting by this avoids float precision issues entirely and is the most robust approach:

```python
# Preferred:
results.sort(key=lambda l: l['price']['amount_cents'])

# Also works but has float precision edge cases:
results.sort(key=lambda l: float(l['price']['amount']))
```

### `buyer_price` vs `price`

The API returns both `price` (seller's asking price) and `buyer_price` (what the buyer pays after currency conversion). These can differ when currency conversion applies. Display/sort by `price` for consistency unless you're building a buyer-specific experience.

**Ruby** — `app/views/listings/index.html.erb`:

```erb
<li class="d-flex list-group-item flex-row align-items-center">
  <div class="p-2">
    <%= image_tag(listing['photos'].first['_links']['thumbnail']['href']) %>
  </div>
  <div class="p-2 flex-grow-1">
    <h2><%= listing['title'] %></h2>
    <p class="text-success font-weight-bold"><%= listing['price']['display'] %></p>
  </div>
</li>
```

**Python** — `templates/listings.html`:

```html
<li class="d-flex list-group-item flex-row align-items-center">
  <div class="p-2">
    <img src="{{ listing['photos'][0]['_links']['thumbnail']['href'] }}" />
  </div>
  <div class="p-2 flex-grow-1">
    <h2>{{ listing['title'] }}</h2>
    <p class="text-success font-weight-bold">{{ listing['price']['display'] }}</p>
  </div>
</li>
```

**React** — `ListingsPage.js`:

```jsx
<li key={listing.id} className="listings__list-item">
  <img alt={listing.title} src={listing.photos[0]._links.small_crop.href} />
  <div className="listings__list-title">{listing.title}</div>
  <div className="listings__list-price">{listing.price.display}</div>
</li>
```

### 2b. Add Sort Control

**Ruby** — `app/controllers/listings_controller.rb`:

```ruby
def index
  @listings = ReverbClient.new.listings
  @listings = sort_listings(@listings, params[:sort])
end

private

def sort_listings(listings, sort_param)
  case sort_param
  when 'price_asc'
    listings.sort_by { |l| l['price']['amount_cents'] }
  when 'price_desc'
    listings.sort_by { |l| -l['price']['amount_cents'] }
  else
    listings
  end
end
```

**Ruby** — `app/views/listings/index.html.erb` (above the list):

```erb
<div class="form-inline mb-3">
  <label class="mr-2">Sort by:</label>
  <%= link_to 'Price ↑', listings_path(sort: 'price_asc'), class: 'btn btn-sm btn-outline-secondary mr-1' %>
  <%= link_to 'Price ↓', listings_path(sort: 'price_desc'), class: 'btn btn-sm btn-outline-secondary' %>
</div>
```

**Python** — `app.py`:

```python
@app.route('/listings')
def listings():
    results = ReverbClient().listings()
    sort = request.args.get('sort')
    if sort == 'price_asc':
        results.sort(key=lambda l: l['price']['amount_cents'])
    elif sort == 'price_desc':
        results.sort(key=lambda l: l['price']['amount_cents'], reverse=True)
    return render_template('listings.html', listings=results, sort=sort)
```

**React** — `ListingsPage.js`:

```jsx
const [sortOrder, setSortOrder] = useState(null);

const sortedListings = useMemo(() => {
  if (!sortOrder) return listings;
  return [...listings].sort((a, b) => {
    const priceA = a.price.amount_cents;
    const priceB = b.price.amount_cents;
    return sortOrder === 'asc' ? priceA - priceB : priceB - priceA;
  });
}, [listings, sortOrder]);

// In JSX:
<div className="listings__sort">
  <button onClick={() => setSortOrder('asc')}>Price ↑</button>
  <button onClick={() => setSortOrder('desc')}>Price ↓</button>
</div>
```

______________________________________________________________________

## Phase 3: Test

**Ruby** — `spec/requests/listings_spec.rb`:

```ruby
let(:listings) do
  [
    { 'title' => 'Cheap', 'price' => { 'amount' => '100.00', 'amount_cents' => 10000, 'display' => '$100' }, 'photos' => [{ '_links' => { 'thumbnail' => { 'href' => 'img.png' } } }] },
    { 'title' => 'Expensive', 'price' => { 'amount' => '900.00', 'amount_cents' => 90000, 'display' => '$900' }, 'photos' => [{ '_links' => { 'thumbnail' => { 'href' => 'img.png' } } }] }
  ]
end

it "displays price" do
  get listings_path
  assert_select ".text-success", "$100"
end

it "sorts by price ascending" do
  get listings_path(sort: 'price_asc')
  titles = css_select("h2").map(&:text).map(&:strip)
  expect(titles).to eq(['Cheap', 'Expensive'])
end

it "sorts by price descending" do
  get listings_path(sort: 'price_desc')
  titles = css_select("h2").map(&:text).map(&:strip)
  expect(titles).to eq(['Expensive', 'Cheap'])
end
```

**React**:

```jsx
it('sorts listings by price ascending', async () => {
  // mount with two listings at different prices
  // click sort asc button
  // verify order of rendered items
});
```

______________________________________________________________________

## Phase 4: Trade-off Discussion

| Topic | What to say |
| -- | -- |
| Client vs server sort | "Sorting client-side is instant and works for the 10 items we have. If paginated, sorting must be server-side or you're only sorting one page." |
| Sort + pagination conflict | "If I sort 10 items client-side but there are 1000 total, the sort is misleading. The API's sort param would be needed." |
| **`amount` is a string** | "The API returns `amount` as a string (`\"450.00\"`). Sorting without casting gives lexicographic order where `\"95\" > \"450\"`. I cast to float, but `amount_cents` (integer) is even safer." |
| Number parsing | "Using `amount_cents` (integer) avoids float precision issues entirely. It's already in the response — no reason to parse strings when the API gives us an int." |
| Active state on sort buttons | "I'd visually indicate which sort is currently active" |
| Multi-field sort | "With more time, could sort by price, date listed, condition, etc. A dropdown would replace individual buttons." |

______________________________________________________________________

## Python Implementation — Full Walkthrough

### Step 1: Display price — `templates/listings.html`

No API client change needed — the price data is already in the listing response.

```html
{% extends 'base.html' %}
{% block content %}

<div class="mb-3">
  <span class="mr-2">Sort by:</span>
  <a href="{{ url_for('listings', sort='price_asc') }}"
     class="btn btn-sm btn-outline-secondary {% if sort == 'price_asc' %}active{% endif %}">
    Price ↑
  </a>
  <a href="{{ url_for('listings', sort='price_desc') }}"
     class="btn btn-sm btn-outline-secondary {% if sort == 'price_desc' %}active{% endif %}">
    Price ↓
  </a>
</div>

{% if listings %}
  <ul class="list-group">
    {% for listing in listings %}
      <li class="d-flex list-group-item flex-row align-items-center">
        <div class="p-2">
          <img src="{{ listing['photos'][0]['_links']['thumbnail']['href'] }}" />
        </div>
        <div class="p-2 flex-grow-1">
          <h2>{{ listing['title'] }}</h2>
          <p class="text-success font-weight-bold mb-0">
            {{ listing['price']['display'] }}
          </p>
        </div>
      </li>
    {% endfor %}
  </ul>
{% endif %}

{% endblock %}
```

**What to say:** "I'm adding the price display using `listing['price']['display']` — the API gives us a pre-formatted string so we don't need to handle currency formatting ourselves. The sort buttons use `url_for` with a `sort` param, and I add an `active` class to show which is currently selected."

### Step 2: Add sorting logic in `app.py`

```python
@app.route('/listings')
def listings():
    results = ReverbClient().listings()
    sort = request.args.get('sort')

    if sort == 'price_asc':
        results.sort(key=lambda l: l['price']['amount_cents'])
    elif sort == 'price_desc':
        results.sort(key=lambda l: l['price']['amount_cents'], reverse=True)

    return render_template('listings.html', listings=results, sort=sort)
```

**What to say:** "I'm sorting in Python after fetching. `list.sort()` is in-place and takes a `key` function. I use `amount_cents` (an integer) instead of parsing the string `amount` to float — this avoids both lexicographic sort bugs and floating-point precision issues. `reverse=True` handles descending. I pass `sort` to the template so it can highlight the active button."

**Python idiom:** `list.sort(key=...)` is more efficient than `sorted(...)` when you don't need to keep the original order — it sorts in-place without creating a new list.

### Step 3: Handle missing price data defensively

```python
def _sort_key(listing):
    """Extract price for sorting, defaulting to 0 for listings without price."""
    try:
        return listing['price']['amount_cents']
    except (KeyError, TypeError):
        return 0
```

Then use: `results.sort(key=_sort_key)`

**What to say:** "Some listings might not have price data (drafts, not-for-sale items). I'll use a helper that returns 0 for those, so they sort to the beginning rather than crashing the page."

### Step 4: Tests — `tests/test_listings.py`

```python
@pytest.fixture
def priced_client():
    app.config['TESTING'] = True

    mock_get = patch('reverb_client.requests.get').start()
    mock_get.return_value.json.return_value = {
        'listings': [
            {
                'title': 'Expensive Guitar',
                'price': {'amount': '900.00', 'amount_cents': 90000, 'display': '$900'},
                'photos': [{'_links': {'thumbnail': {'href': 'https://img.com/exp.jpg'}}}]
            },
            {
                'title': 'Cheap Guitar',
                'price': {'amount': '100.00', 'amount_cents': 10000, 'display': '$100'},
                'photos': [{'_links': {'thumbnail': {'href': 'https://img.com/cheap.jpg'}}}]
            }
        ]
    }

    with app.test_client() as client:
        yield client

def test_displays_price(priced_client):
    res = priced_client.get('/listings')
    html = parse_html(res)
    prices = html.body.select('.text-success')
    assert len(prices) == 2
    assert '$900' in prices[0].text
    assert '$100' in prices[1].text

def test_sorts_by_price_ascending(priced_client):
    res = priced_client.get('/listings', query_string={'sort': 'price_asc'})
    html = parse_html(res)
    titles = [h2.text.strip() for h2 in html.body.select('h2')]
    assert titles == ['Cheap Guitar', 'Expensive Guitar']

def test_sorts_by_price_descending(priced_client):
    res = priced_client.get('/listings', query_string={'sort': 'price_desc'})
    html = parse_html(res)
    titles = [h2.text.strip() for h2 in html.body.select('h2')]
    assert titles == ['Expensive Guitar', 'Cheap Guitar']

def test_no_sort_preserves_api_order(priced_client):
    res = priced_client.get('/listings')
    html = parse_html(res)
    titles = [h2.text.strip() for h2 in html.body.select('h2')]
    # API order: Expensive first
    assert titles == ['Expensive Guitar', 'Cheap Guitar']

def test_sort_buttons_present(priced_client):
    res = priced_client.get('/listings')
    html = parse_html(res)
    links = html.body.select('a.btn-outline-secondary')
    hrefs = [a['href'] for a in links]
    assert any('sort=price_asc' in h for h in hrefs)
    assert any('sort=price_desc' in h for h in hrefs)

def test_active_sort_button_highlighted(priced_client):
    res = priced_client.get('/listings', query_string={'sort': 'price_asc'})
    html = parse_html(res)
    active_btn = html.body.select_one('a.active')
    assert 'price_asc' in active_btn['href']
```

### Rails comparison notes

| Aspect | Rails approach | Flask approach |
| -- | -- | -- |
| Sort logic | `listings.sort_by { \|l\| l['price']['amount_cents'] }` | `results.sort(key=lambda l: l['price']['amount_cents'])` |
| Descending | `sort_by { \|l\| -amount_cents }` (negate) | `sort(..., reverse=True)` — more explicit |
| Active class in view | ERB conditional `<%= 'active' if ... %>` | `{% if sort == 'price_asc' %}active{% endif %}` |
| In-place sort | `sort_by!` mutates | `.sort()` mutates (or `sorted()` for new list) |
| Link helper | `link_to 'Price ↑', listings_path(sort: ...)` | `<a href="{{ url_for(...) }}">` |
| Float parsing | `.to_f` (returns 0.0 on failure) | `float(...)` (raises ValueError — need try/except) |

**Key insight:** "Ruby's `.to_f` silently returns 0 for non-numeric strings, which is forgiving but can mask bugs. Python's `float()` raises `ValueError`, which forces you to handle the edge case explicitly. In an interview, mention this difference — it shows you think about failure modes."

**Python-specific discussion point:** "I used `list.sort()` (in-place) rather than `sorted()` (returns new list). For 10 items it doesn't matter, but it signals awareness of memory allocation. If I needed the original order preserved for something else, I'd use `sorted()`."

______________________________________________________________________

## Combination Variant: Category Landing Page (S4 + S6)

The interviewer might combine this scenario with **Scenario 4** (category navigation)
by asking:

> "Build a category landing page that shows the category name, the first 5
> listings with prices, and a 'See all' link."

This reuses your price display template pattern from this scenario combined with
the category-filtered API call from S4. No new patterns — just composition into
a single route and template.

**What to say:** "I already have the price display pattern and the category filter
param. I'll combine them into a new route that shows a preview of the category."

See [scenario-4-category-nav.md](scenario-4-category-nav.md) for the full combined
implementation sketch.
