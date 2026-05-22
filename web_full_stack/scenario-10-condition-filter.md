# Scenario 10: Condition Dropdown Filter

## The Ask

> "Let users filter listings by condition — show a dropdown with the condition options from the API."

Tests working with reference data endpoints, structured filter controls (`<select>` vs.
freeform `<input>`), and preserving form state across requests.

______________________________________________________________________

## Phase 1: Explain (2-3 min)

**What to say:**

"Right now listings can be searched by keyword (Scenario 2), but users can't filter by
condition — 'Brand New', 'Mint', 'Excellent', etc. Reverb has a dedicated endpoint
`/api/listing_conditions` that returns the 8 condition levels. I'll fetch those to populate
a `<select>` dropdown, pass the selected condition UUID to the listings endpoint, and
preserve the selection after the page reloads."

**Clarifying questions:**

- "Should the filter be a standalone control, or combinable with the keyword search?"
- "Should I show the count of results per condition, or just the names?"
- "Does the listings API accept `condition` as a param?" (It does — `?condition=mint`)

______________________________________________________________________

## Phase 2: Implement

### 2a. API Discovery

The Reverb API exposes:

```bash
GET /api/listing_conditions
```

**Response:**

```json
{
  "conditions": [
    { "uuid": "7c3f45de-...", "display_name": "Brand New", "slug": "brand-new", "description": "..." },
    { "uuid": "ac5b9c1e-...", "display_name": "Mint", "slug": "mint", "description": "..." },
    { "uuid": "df268ad1-...", "display_name": "Excellent", "slug": "excellent", "description": "..." },
    { "uuid": "ae4d9114-...", "display_name": "Very Good", "slug": "very-good", "description": "..." },
    { "uuid": "f7a3f48c-...", "display_name": "Good", "slug": "good", "description": "..." },
    { "uuid": "98777886-...", "display_name": "Fair", "slug": "fair", "description": "..." },
    { "uuid": "6a9dfcad-...", "display_name": "Poor", "slug": "poor", "description": "..." },
    { "uuid": "fbf35668-...", "display_name": "Non Functioning", "slug": "non-functioning", "description": "..." }
  ]
}
```

The listings endpoint accepts: `GET /api/listings/all?condition=mint&per_page=10`

**Key insight:** The param uses the **slug** (not the UUID) — `?condition=mint`, not
`?condition=ac5b9c1e-...`. Verify this during implementation.

### 2b. Extend the Client — `reverb_client.py`

```python
def listing_conditions(self):
    return self._get("/listing_conditions")["conditions"]

def listings(self, per_page=10, query=None, condition=None):
    params = {"per_page": per_page}
    if query:
        params["query"] = query
    if condition:
        params["condition"] = condition
    return self._get("/listings/all", params)["listings"]
```

**What to say:** "I'm adding a `listing_conditions()` method for the reference data, and
extending `listings()` with an optional `condition` param. Both are backward-compatible —
existing callers without `condition` won't break."

### 2c. Service Layer — `app.py`

```python
def _load_conditions():
    return ReverbClient().listing_conditions()


@app.route("/listings")
def listings():
    query = request.args.get("query")
    condition = request.args.get("condition")
    conditions = _load_conditions()
    results = _load_listings(query=query, condition=condition)
    return render_template(
        "listings.html",
        listings=results,
        conditions=conditions,
        query=query,
        selected_condition=condition,
    )
```

**What to say:** "I fetch conditions on every request so the dropdown is always populated.
In production I'd cache this — conditions change rarely and the endpoint is CDN-cached for
24 hours — but for the interview I'll keep it simple."

**Note:** `_load_listings()` needs updating to accept and forward `condition`:

```python
def _load_listings(query=None, condition=None):
    return ReverbClient().listings(query=query, condition=condition)
```

### 2d. Template — `templates/listings.html`

```html
<form method="GET" action="{{ url_for('listings') }}">
  <div class="form-group">
    <label for="query">Search</label>
    <input type="text" name="query" id="query"
           value="{{ query or '' }}" placeholder="Search by keyword">
  </div>

  <div class="form-group">
    <label for="condition">Condition</label>
    <select name="condition" id="condition">
      <option value="">All Conditions</option>
      {% for cond in conditions %}
        <option value="{{ cond.slug }}"
                {% if cond.slug == selected_condition %}selected{% endif %}>
          {{ cond.display_name }}
        </option>
      {% endfor %}
    </select>
  </div>

  <button type="submit">Filter</button>
</form>

{% if listings %}
  {% for listing in listings %}
    <div class="listing-card">
      <h3>{{ listing.title }}</h3>
      <span class="condition-badge">{{ listing.condition.display_name }}</span>
      <span class="price">{{ listing.price.display }}</span>
    </div>
  {% endfor %}
{% else %}
  <p class="empty-state">No listings found for this condition. Try a different filter.</p>
{% endif %}
```

**Key template decisions:**

- `selected` attribute preserves the dropdown state after form submit
- Empty `value=""` on the first option means "no filter" — it won't send the param
- Both `query` and `condition` are in the same form — they combine naturally

______________________________________________________________________

## Phase 3: Test

### Client test — `tests/test_reverb_client.py`

```python
def test_listing_conditions_returns_conditions(self):
    mock_data = {
        "conditions": [
            {"uuid": "abc", "display_name": "Mint", "slug": "mint"},
            {"uuid": "def", "display_name": "Good", "slug": "good"},
        ]
    }
    self.mock_get.return_value.json.return_value = mock_data
    result = self.client.listing_conditions()
    self.assertEqual(len(result), 2)
    self.assertEqual(result[0]["display_name"], "Mint")


def test_listings_with_condition_passes_param(self):
    mock_data = {"listings": [{"title": "Test", "condition": {"slug": "mint"}}]}
    self.mock_get.return_value.json.return_value = mock_data
    self.client.listings(condition="mint")
    call_args = self.mock_get.call_args
    self.assertEqual(call_args[1]["params"]["condition"], "mint")
```

### Route test — `tests/test_listings.py`

```python
@patch("app.ReverbClient")
def test_listings_with_condition_filter(self, MockClient):
    mock_instance = MockClient.return_value
    mock_instance.listing_conditions.return_value = [
        {"slug": "mint", "display_name": "Mint"}
    ]
    mock_instance.listings.return_value = [
        {"title": "Fender Tele", "condition": {"display_name": "Mint"}, "price": {"display": "$800"}}
    ]

    response = self.client.get("/listings?condition=mint")
    self.assertEqual(response.status_code, 200)
    self.assertIn(b"Fender Tele", response.data)
    # Verify condition was passed through
    mock_instance.listings.assert_called_with(query=None, condition="mint")


@patch("app.ReverbClient")
def test_listings_dropdown_shows_conditions(self, MockClient):
    mock_instance = MockClient.return_value
    mock_instance.listing_conditions.return_value = [
        {"slug": "mint", "display_name": "Mint"},
        {"slug": "good", "display_name": "Good"},
    ]
    mock_instance.listings.return_value = []

    response = self.client.get("/listings")
    self.assertIn(b"Mint", response.data)
    self.assertIn(b"Good", response.data)
    self.assertIn(b'<select name="condition"', response.data)


@patch("app.ReverbClient")
def test_listings_preserves_selected_condition(self, MockClient):
    mock_instance = MockClient.return_value
    mock_instance.listing_conditions.return_value = [
        {"slug": "mint", "display_name": "Mint"}
    ]
    mock_instance.listings.return_value = []

    response = self.client.get("/listings?condition=mint")
    # The selected option should have the 'selected' attribute
    self.assertIn(b"selected", response.data)
```

______________________________________________________________________

## Phase 4: Trade-off Discussion

| Topic | What to say |
| --- | --- |
| Caching conditions | "Conditions are reference data — 8 values that rarely change. In production I'd cache this with a 1-hour TTL or fetch once at startup. The API already CDN-caches it for 24h." |
| Combinable filters | "Query + condition in the same form means they combine in the URL: `?query=fender&condition=mint`. The API handles the intersection." |
| `slug` vs `uuid` | "I'm using the slug because URLs are human-readable. If the API accepted both, slug is better for shareability — `?condition=mint` reads better than `?condition=ac5b9c1e-...`" |
| Empty results UX | "An empty result with a selected condition is still useful — it tells the user 'nothing in Mint right now, try Good'. I'd show the active filter clearly so they can clear it." |
| N+1 API calls | "Fetching conditions on every page load is fine for 8 items, but if this scaled to 50 filter options I'd consider loading them once on app init or caching per-session." |

______________________________________________________________________

## A&R Team Framing

- "Condition filters reduce friction for buyers with specific needs — someone looking for 'Brand New' doesn't want to scroll past 'Fair' and 'Poor' items. This directly reduces bounce."
- "For retention: if a user always filters by 'Mint', I'd consider persisting that preference in their session/profile so their next visit starts pre-filtered."
- "A condition dropdown is also a conversion signal — a user who selects 'Brand New' is signaling high purchase intent. Worth logging for funnel analytics."

______________________________________________________________________

## Complexity Self-Assessment

**Time to implement cold:** ~20 minutes (client + route + template + one test)

**New patterns vs. existing scenarios:**

- `<select>` with dynamic options from an API (new — S2 only used `<input>`)
- Fetching reference data to build the UI (new — no prior scenario fetches two endpoints)
- `selected` attribute preservation (new template pattern)
- Combining multiple filter params in one form (builds on S2)

**Why this is realistic for the interview:** It's a natural follow-up after "add search" —
the interviewer says "great, now let's add a structured filter too." It's 15-20 minutes of
work and tests whether you can fetch reference data and wire it into a form control.
