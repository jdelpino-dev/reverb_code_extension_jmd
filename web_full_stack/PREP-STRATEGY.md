# 6-Day Prep Strategy

This plan is tuned for the **Python/Flask** track and the interview flow
you will actually see: read code, explain it, implement a feature, test it,
and discuss trade-offs.

**Status:** Orientation is complete. Architecture is internalized. Scenario 0
and Scenario 5 are already implemented. The mode now is **performance reps**,
not study expansion.

## Focus

Prioritize these in order:

1. `python/app.py` and `python/reverb_client.py`
2. `python/templates/`
3. `python/tests/`
4. Scenarios `1`, `2`, `3`, `4`, and `6` (implementation reps)
5. Scenario `5` failure-path tests (already implemented -- prove it works)
6. Scenarios `7`-`9` verbal only unless extra time remains

## Daily cadence

Each session follows a strict cold-first workflow:

1. **Implement from memory** (35-45 min) -- no hints open
2. **Check hints** (10 min) -- compare against scenario doc
3. **Test + explain out loud** (15 min) -- narrate while running tests

If you get stuck, stop expanding the scope and return to the happy path first.
Never open hints before attempting the implementation cold.

## Day 1 -- Scenario 1: listing detail page

Goal: deliver a complete feature end-to-end without looking at hints.

- Add `ReverbClient.listing(listing_id)`
- Add `/listings/<listing_id>` route with `_load_listing()` service helper
- Create `listing_detail.html` template
- Link from `listings.html` to detail
- Write one route test and one client test
- After timer: check scenario-1 doc for missed edge cases

Checkpoint: you can build a new feature cold in under 45 minutes.

## Day 2 -- Scenario 2: search listings

Goal: replicate the existing categories search pattern for listings.

- Read `request.args.get("query")`
- Pass optional `query` into `ReverbClient.listings(...)`
- Preserve query in the search form value
- Handle empty results state
- Test: assert the API receives the query param

Checkpoint: you can adapt an existing pattern to a parallel feature.

## Day 3 -- Scenario 3: pagination

Goal: handle a client return-type change and URL state management.

- Current `listings()` returns only `response["listings"]`
- Pagination needs `current_page`, `total_pages`, `_links`
- Therefore the client return type must change -- notice this before coding
- Add `page` param to route and template (prev/next links)
- Use `_links.next` presence as the canonical "has more" signal

Checkpoint: you can explain breaking changes and backward compatibility.

## Day 4 -- Scenario 4 + 6: category navigation + price/sort

Goal: connect existing features and work with nested data.

- Make category names clickable links to filtered listings
- Pass `category` or `category_uuid` to the listings endpoint
- Display `price.display` in listings
- Sort by `price.amount_cents` (integer), not `price.amount` (string)
- Handle missing price defensively

Checkpoint: you can explain why a param belongs in the URL and sort
numerically not lexicographically.

## Day 5 -- Timed mock interview

Goal: simulate the real thing under pressure.

- Pick one scenario at random (1, 2, 3, or 4+6)
- 5 min: read and ask clarifying questions aloud
- 25 min: implement happy path
- 10 min: write tests
- 5 min: discuss trade-offs and next steps
- No hints until after the timer

Checkpoint: you can finish a feature calmly without docs open.

## Day 6 -- Error handling validation + verbal prep

Goal: prove Scenario 5 works and rehearse discussion-only topics.

- Write failure-path tests: API timeout, HTTP 500, invalid JSON, missing key
- Assert route still returns 200 with flash message
- Rehearse Scenario 9 talking points (timeout, session, retries) verbally
- Rehearse Scenario 8 talking points (partial failure, parallel fetch) verbally
- Practice this line: "In a server-rendered Flask app, there is no true
  client-side loading state unless we add JavaScript. The best server-side
  version is timeout plus graceful error UI."

Checkpoint: you can clearly separate happy path, empty state, and error state
-- and prove it with tests.

## Engineer II signals to optimize for

These are the specific signals that matter at this level:

- "I know where this change belongs in the architecture."
- "I can preserve existing behavior while extending."
- "I can write a meaningful test that proves the change works."
- "I can explain why I chose this approach over alternatives."
- "I can name edge cases without boiling the ocean to fix them all."
- "I can recover when I discover my first approach is wrong."

Do NOT optimize for:

- Perfect architecture or maximum abstraction
- Production-grade retries/caching/throttling everywhere
- Memorizing every API field
- Writing the most clever Python

## What to remember on interview day

- Start with the entry point, not random files
- Say what you notice before you change anything
- Keep the first implementation small and correct
- Test the change immediately
- Mention trade-offs, but do not over-engineer
- When stuck: restate the problem, check the simplest path, ask a
  clarifying question -- do not spin silently

## If time gets tight

Drop bonus material before core practice:

- Skip deep React/Ruby comparisons
- Skip advanced client caching/retry design
- Skip Scenario 8 unless the interviewer asks for dashboard composition
- Skip Scenario 7 (POST) unless the interviewer specifically asks for write ops

The goal is not to know everything. The goal is to **ship a small feature
confidently, explain your choices, and recover cleanly when the first pass
needs adjustment**.
