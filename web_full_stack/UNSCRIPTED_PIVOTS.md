# Unscripted Pivots — Adaptability Under Pressure

The interviewer may redirect you mid-implementation. This isn't adversarial — it
tests whether you can shift gears cleanly without getting flustered. Your prep is
scenario-based; real pairing is not.

---

## The Meta-Skill

When the interviewer says "actually, let's..." your response is always:

1. **Acknowledge** — "Sure, makes sense."
2. **Stabilize** — Finish the current line/thought (don't leave broken syntax)
3. **Restate** — "So the priority now is X. Let me adjust."
4. **Proceed** — Start the new direction without mourning the old one

**Never:** argue for your current approach, ask "can I finish this first?" (unless
you're one line away), or go silent while mentally recalculating.

---

## Pivot Categories & Likely Triggers

### Category 1: "Handle the Error Case First"

**When it happens:** You're 5 minutes into the happy path implementation.

**Trigger phrases:**

- "What if the API is down?"
- "Before we go further — what happens if this call fails?"
- "Actually, let's make sure this degrades gracefully."

**How to pivot:**

- Stop writing the happy path feature
- Add a `try/except` in the route or a status check in `_get`
- Render a flash message or fallback template instead of crashing
- Say: "Good call — let me wrap this in error handling. I'll add `raise_for_status()` in the client and catch the exception at the route level."

**Code you'd write:**

```python
# In _get:
response = requests.get(...)
response.raise_for_status()
return response.json()

# In the route:
try:
    listings = _load_listings()
except requests.RequestException:
    flash("Unable to load listings. Please try again.", "error")
    listings = []
```

---

### Category 2: "Let's Write the Test First"

**When it happens:** You've started implementing but haven't touched tests yet.

**Trigger phrases:**

- "Can you show me how you'd test this?"
- "Let's write the test before we finish the implementation."
- "What should the test assert?"

**How to pivot:**

- Switch to the test file immediately
- Write a test for the behavior you were about to implement
- Run it (it should fail) — then go back and make it pass
- Say: "Sure — I'll write the test for what I expect this to do, then we'll make it green."

**Code you'd write:**

```python
def test_listing_detail_renders_title(self):
    mock_response = {"title": "Fender Telecaster", "price": {"display": "$1,200"}}
    with patch("app.ReverbClient.listing", return_value=mock_response):
        response = self.client.get("/listings/12345")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Fender Telecaster", response.data)
```

---

### Category 3: "What About Empty State?"

**When it happens:** Your implementation works for the happy path.

**Trigger phrases:**

- "What does the user see if there are no results?"
- "What if the API returns an empty array?"
- "How would you handle zero listings?"

**How to pivot:**

- Add a conditional in the template (or route logic)
- Render a helpful message instead of a blank page
- Say: "Right — empty state is important for UX. Let me add a conditional in the template."

**Code you'd write:**

```html
{% if listings %}
  {% for listing in listings %}
    ...
  {% endfor %}
{% else %}
  <p class="empty-state">No listings found. Try adjusting your search.</p>
{% endif %}
```

---

### Category 4: "Can You Refactor This?"

**When it happens:** Your code works but is messy or duplicated.

**Trigger phrases:**

- "This works — how would you clean it up?"
- "I notice some duplication here..."
- "Could this be more reusable?"

**How to pivot:**

- Don't refactor everything at once. Pick the most obvious duplication
- Extract a helper or consolidate repeated logic
- Run tests after to prove you didn't break anything
- Say: "Yeah, I see the repetition. Let me extract a helper — then I'll run the tests to make sure it still passes."

---

### Category 5: "Change the Data Shape"

**When it happens:** You've built around one API response shape, and they
reveal the data is actually structured differently.

**Trigger phrases:**

- "Actually, the detail endpoint returns the price nested under `price.display`"
- "The photos come back as an array of objects, not strings"
- "This field might be null — how does that change things?"

**How to pivot:**

- Update the template/code to handle the new shape
- Add defensive access (`.get()`, `or ""`, `{% if field %}`)
- Say: "OK, so the shape is different. Let me adjust the template to pull from `listing.price.display` and handle the case where it's missing."

**Code you'd write:**

```python
# Defensive access in template context or service helper:
price_display = listing.get("price", {}).get("display", "Price not available")
```

---

### Category 6: "Make It Work Without JavaScript" / "Server-Side Only"

**When it happens:** You propose a client-side solution.

**Trigger phrases:**

- "Let's keep this server-rendered"
- "Assume JavaScript is disabled"
- "Can you do this with just Flask and templates?"

**How to pivot:**

- Move logic from "I'd do this in JS" to route params + template conditionals
- Use URL query params for state (sort, filter, page)
- Say: "Makes sense — I'll use query parameters and re-render the full page. The form submits to the same route with `?sort=price_asc`."

---

### Category 7: "Add a URL Parameter"

**When it happens:** Your feature works but isn't linkable/bookmarkable.

**Trigger phrases:**

- "How would someone share this filtered view?"
- "Can the page state survive a refresh?"
- "What if I paste this URL to a coworker?"

**How to pivot:**

- Read state from `request.args` instead of (or in addition to) form data
- Preserve the param in links and form actions
- Say: "Good point — I'll read the filter from `request.args.get('query')` so it's in the URL. The form's action will preserve it on submit."

---

### Category 8: "What Would You Do Differently?"

**When it happens:** At the end, or after you've shipped something that works.

**Trigger phrases:**

- "If you had another hour, what would you change?"
- "What are you not happy with?"
- "What would you do in production that you skipped here?"

**How to pivot:**

This isn't a code pivot — it's a discussion pivot. Have 3-4 ready answers:

- "I'd add caching — the categories don't change often, so a 5-minute TTL would cut API calls"
- "I'd add request timeouts to the client — right now a slow API hangs the whole request"
- "I'd add structured logging so we can trace failed API calls in production"
- "I'd move the service helpers into their own module once we have more than 3-4 routes"

---

### Category 9: "Actually, Let's Do a Different Feature"

**When it happens:** Rare, but possible if time is running short or they want
to see breadth over depth.

**Trigger phrases:**

- "Let's leave this and try something simpler"
- "I want to see how you'd approach search instead"
- "Can you add sorting to what we already have?"

**How to pivot:**

- Don't show disappointment that your work is "wasted"
- Commit or stash mentally — "OK, that's in a good state. Let me switch to..."
- Apply the same pattern: client → route → template → test
- Say: "Sure — the pattern is the same. Let me start at the client layer again."

---

## Practice Drill

During your timed mock (Day 5 of prep), have someone (or a timer) interrupt you
at the 15-minute mark with one of these pivots chosen at random:

1. "Handle the error case"
2. "Write the test first"
3. "What about empty state?"
4. "The data shape is different — photos is an array of objects with `_links.large_crop`"
5. "Make the page state bookmarkable"

Practice the 4-step response: Acknowledge → Stabilize → Restate → Proceed.

---

## Signals You're Handling Pivots Well

- You don't repeat "but I was going to..."
- You incorporate their suggestion within 30 seconds
- You name the new plan before coding it
- Your code stays clean (no half-finished abandoned branches)
- You run tests after the pivot to re-establish confidence

## Red Flags to Avoid

- Going silent for 30+ seconds after a redirect
- Arguing for your original approach
- Asking "why?" in a defensive tone (asking for clarification is fine)
- Leaving broken code from the abandoned direction
- Rushing the pivot and introducing bugs
