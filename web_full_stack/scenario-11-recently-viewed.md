# Scenario 11: Recently Viewed Listings (Session State)

## The Ask

> "Show users their 3 most recently viewed listings when they return to the homepage."

Tests session/cookie usage in Flask, cross-route state management, and a retention-focused
product feature. This is the first scenario that introduces persistent user state.

______________________________________________________________________

## Phase 1: Explain (2-3 min)

**What to say:**

"Right now every page load is stateless — we fetch from the API and render, with no memory
of what the user did before. A 'recently viewed' feature needs server-side session storage:
when a user visits a listing detail page, I store that listing's ID in the session. On the
homepage, I read those IDs and fetch the listings to display them. Flask's session uses a
signed cookie by default, which is fine for a few IDs but has size limits (~4KB). For more
data or more items, I'd move to server-side sessions (Redis/database)."

**Clarifying questions:**

- "Should I store just the IDs and re-fetch, or cache the full listing data in the session?"
- "How many items — 3? 5? Should it cap?"
- "Where should 'recently viewed' appear — homepage only, or a sidebar on every page?"
- "Should it persist across browser sessions (database) or just during the current visit (cookie session)?"

______________________________________________________________________

## Phase 2: Implement

### 2a. Design Decision: IDs vs. Full Data

| Approach | Pros | Cons |
| --- | --- | --- |
| Store IDs only, re-fetch on render | Session stays tiny (~50 bytes for 3 IDs). Data always fresh. | Extra API calls on homepage load. |
| Store listing summaries in session | No extra API calls on render. Instant display. | Cookie size limit (~4KB). Data goes stale if price/title changes. |

**Recommendation for interview:** Store IDs + minimal display data (title, price, thumbnail URL).
This avoids extra API calls while keeping the cookie small. Mention the trade-off out loud.

```python
# What we store per listing — ~150 bytes each, 3 items = ~450 bytes (well under 4KB)
{
    "id": 97305295,
    "title": "Fender Telecaster",
    "price_display": "$1,200",
    "thumbnail": "https://rvb-img.reverb.com/..."
}
```

### 2b. Record View — Update `app.py` (Detail Route)

Assuming Scenario 1's detail page route exists:

```python
from flask import session

MAX_RECENT = 3


@app.route("/listings/<listing_id>")
def listing_detail(listing_id):
    listing = _load_listing(listing_id)
    _record_recently_viewed(listing)
    return render_template("listing_detail.html", listing=listing)


def _record_recently_viewed(listing):
    """Add listing to session's recently-viewed list (most recent first, capped)."""
    recent = session.get("recently_viewed", [])

    # Build minimal summary to keep cookie small
    entry = {
        "id": listing["id"],
        "title": listing["title"],
        "price_display": listing.get("price", {}).get("display", ""),
        "thumbnail": listing.get("photos", [{}])[0]
            .get("_links", {}).get("thumbnail", {}).get("href", ""),
    }

    # Remove if already in list (avoid duplicates), then prepend
    recent = [r for r in recent if r["id"] != listing["id"]]
    recent.insert(0, entry)

    # Cap at MAX_RECENT
    session["recently_viewed"] = recent[:MAX_RECENT]
```

**What to say:** "I'm storing a minimal summary — just enough to render a card without
hitting the API again. I deduplicate by ID so viewing the same listing twice doesn't fill
the list. Most recent goes first."

### 2c. Display on Homepage — Update Route

```python
@app.route("/")
@app.route("/categories")
def categories():
    query = request.args.get("query")
    categories = _search_categories(query)
    recently_viewed = session.get("recently_viewed", [])

    if not query:
        flash("Search using a query string...", "warning")
    elif not categories:
        flash(f"No category results for: {query}. Try something different", "info")

    return render_template(
        "categories.html",
        categories=categories,
        recently_viewed=recently_viewed,
    )
```

### 2d. Template — `templates/categories.html` (or `base.html`)

```html
{% if recently_viewed %}
<section class="recently-viewed">
  <h2>Recently Viewed</h2>
  <div class="recent-listings">
    {% for item in recently_viewed %}
      <a href="{{ url_for('listing_detail', listing_id=item.id) }}" class="recent-card">
        {% if item.thumbnail %}
          <img src="{{ item.thumbnail }}" alt="{{ item.title }}">
        {% endif %}
        <span class="title">{{ item.title }}</span>
        <span class="price">{{ item.price_display }}</span>
      </a>
    {% endfor %}
  </div>
</section>
{% endif %}
```

**Key template decisions:**

- Only renders the section if there's something to show (first-time visitors see nothing)
- Each card links back to the detail page (which also re-records the view, moving it to front)
- Defensive `{% if item.thumbnail %}` — some listings might not have photos

### 2e. Session Configuration

Flask's default session uses a signed cookie (client-side). Ensure `app.secret_key` is set
(it already is in the codebase):

```python
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-secret")
```

**What to say:** "Flask signs the cookie with the secret key so users can't tamper with it —
they can read it (it's base64, not encrypted) but can't modify the IDs or inject fake data.
For a production app with sensitive session data, I'd use server-side sessions with Redis."

______________________________________________________________________

## Phase 3: Test

### Route test — Recording a view

```python
@patch("app.ReverbClient")
def test_viewing_listing_records_in_session(self, MockClient):
    mock_instance = MockClient.return_value
    mock_instance.listing.return_value = {
        "id": 123,
        "title": "Fender Tele",
        "price": {"display": "$800"},
        "photos": [{"_links": {"thumbnail": {"href": "http://img/thumb.jpg"}}}],
    }

    with self.client.session_transaction() as sess:
        self.assertEqual(sess.get("recently_viewed"), None)

    self.client.get("/listings/123")

    with self.client.session_transaction() as sess:
        recent = sess["recently_viewed"]
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["id"], 123)
        self.assertEqual(recent[0]["title"], "Fender Tele")
```

### Route test — Deduplication and ordering

```python
@patch("app.ReverbClient")
def test_recently_viewed_deduplicates_and_reorders(self, MockClient):
    mock_instance = MockClient.return_value

    def make_listing(lid, title):
        return {
            "id": lid, "title": title,
            "price": {"display": "$100"},
            "photos": [],
        }

    mock_instance.listing.side_effect = [
        make_listing(1, "First"),
        make_listing(2, "Second"),
        make_listing(1, "First"),  # revisit
    ]

    self.client.get("/listings/1")
    self.client.get("/listings/2")
    self.client.get("/listings/1")  # should move to front

    with self.client.session_transaction() as sess:
        recent = sess["recently_viewed"]
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["id"], 1)  # most recent first
        self.assertEqual(recent[1]["id"], 2)
```

### Route test — Cap at MAX_RECENT

```python
@patch("app.ReverbClient")
def test_recently_viewed_caps_at_max(self, MockClient):
    mock_instance = MockClient.return_value

    for i in range(5):
        mock_instance.listing.return_value = {
            "id": i, "title": f"Listing {i}",
            "price": {"display": "$100"}, "photos": [],
        }
        self.client.get(f"/listings/{i}")

    with self.client.session_transaction() as sess:
        recent = sess["recently_viewed"]
        self.assertEqual(len(recent), 3)  # MAX_RECENT = 3
        self.assertEqual(recent[0]["id"], 4)  # most recent
```

### Route test — Homepage displays recently viewed

```python
@patch("app.ReverbClient")
def test_homepage_shows_recently_viewed(self, MockClient):
    mock_instance = MockClient.return_value
    mock_instance.categories.return_value = []

    with self.client.session_transaction() as sess:
        sess["recently_viewed"] = [
            {"id": 1, "title": "Fender Tele", "price_display": "$800", "thumbnail": ""},
        ]

    response = self.client.get("/")
    self.assertIn(b"Recently Viewed", response.data)
    self.assertIn(b"Fender Tele", response.data)


@patch("app.ReverbClient")
def test_homepage_hides_recently_viewed_when_empty(self, MockClient):
    mock_instance = MockClient.return_value
    mock_instance.categories.return_value = []

    response = self.client.get("/")
    self.assertNotIn(b"Recently Viewed", response.data)
```

______________________________________________________________________

## Phase 4: Trade-off Discussion

| Topic | What to say |
| --- | --- |
| Cookie vs. server session | "Cookie is fine for 3 IDs + summaries (~450 bytes). If we needed 50 items or sensitive data, I'd use Flask-Session with Redis." |
| Stale data | "If a listing's price changes after I cached it in the session, the card shows the old price. Acceptable for 'recently viewed' — it's a convenience shortcut, not a source of truth. Clicking through shows the live detail page." |
| Privacy | "The cookie is signed but not encrypted — a user could decode it and see their own IDs. That's fine for recently-viewed. If it were 'saved for later' with authentication, I'd use a database." |
| Performance | "Zero extra API calls on the homepage — the session data is already in the cookie. This is effectively free rendering." |
| Alternative: IDs only | "If I stored only IDs, I'd need to batch-fetch 3 listings on every homepage load. The API doesn't have a batch endpoint, so that's 3 sequential requests. Storing summaries avoids this entirely." |
| Cross-device | "Cookie sessions don't sync across devices. For authenticated users on the A&R team, you'd move this to the database so 'recently viewed' follows them across mobile and desktop." |

______________________________________________________________________

## A&R Team Framing

- "Recently viewed is a **retention** feature — it gives returning users immediate context: 'here's what you were looking at.' It reduces the effort to re-engage."
- "On mobile, where sessions are shorter and interrupted, recently-viewed is critical — a user who got distracted can pick up exactly where they left off."
- "I'd instrument this with analytics: do users who see recently-viewed listings have higher session depth? Do they convert (click → purchase) at a higher rate than fresh search?"
- "For **activation**: new users who browse 3+ listings are showing engagement. I'd use the session to trigger a 'Sign up to save your favorites' prompt once `recently_viewed` hits 3 items."

______________________________________________________________________

## Complexity Self-Assessment

**Time to implement cold:** ~20-25 minutes (session logic + route changes + template + 2-3 tests)

**New patterns vs. existing scenarios:**

- Flask `session` read/write (completely new — no prior scenario uses sessions)
- Cross-route state (write in one route, read in another)
- List manipulation with dedup + cap (mild Python data wrangling)
- Conditional template section (similar to empty-state patterns)
- Cookie size awareness (architectural constraint unique to this approach)

**Why this is realistic for the interview:** An A&R team interviewer might ask "how would
you keep users engaged between visits?" This is the simplest concrete implementation of
that. It doesn't require a database, doesn't require auth, and fits cleanly into the
existing Flask app structure.

______________________________________________________________________

## Extension Prompts (If Time Remains)

If the interviewer says "nice, what would you add?":

1. **"Clear history" button** — `session.pop("recently_viewed", None)` on a POST route
2. **"Save for later" promotion** — after 3 views, show a CTA to create an account
3. **Time-based decay** — store timestamps, fade out items older than 7 days
4. **Server-side upgrade** — `Flask-Session` + Redis for unlimited history and cross-device sync
