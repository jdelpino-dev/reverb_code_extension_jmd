# Reverb Code Extension — Interview Scenario Practice Plan

## Codebase Summary (What You're Extending)

A thin full-stack app (Ruby/Python/React — pick one) that:

- Fetches **categories** from Reverb's public API, with client-side or server-side text filtering
- Fetches **listings** from Reverb's public API, displayed as title + thumbnail

Architecture per stack:

| Layer | Ruby | Python | React |
| -- | -- | -- | -- |
| API client | `ReverbClient` class (HTTParty) | `ReverbClient` class (requests) | `API.js` (fetch) |
| Routing | `config/routes.rb` (resourceful) | Flask decorators | react-router `<Switch>` |
| View | ERB templates | Jinja2 templates | Functional components + hooks |
| Tests | RSpec + WebMock | pytest + unittest.mock | Jest + Enzyme |

Key API endpoints already in use:

- `GET /api/categories/flat` → `{ categories: [...] }`
- `GET /api/listings/all?per_page=N` → `{ listings: [...] }`

______________________________________________________________________

## Interview Flow (Same for Every Scenario)

1. **Read** — Candidate opens the code, traces request flow end-to-end
2. **Explain** — "Walk me through how categories search works"
3. *(Optional)* **Explain** — "Walk me through how listings works" *(used as warm-up for listing-focused scenarios)*
4. **Implement** — Interviewer reveals the feature ask
5. **Test** — Write/update tests for the new behavior
6. **Discuss** — Trade-offs, what would you do differently with more time

______________________________________________________________________

## Scenarios

### Scenario 1: Listing Detail Page

### Scenario 2: Search / Filter Listings

### Scenario 3: Pagination

### Scenario 4: Category → Listings Navigation

### Scenario 5: Error Handling & Loading States

### Scenario 6: Price Display + Sort

Each scenario has its own detailed spec below. Practice each on a **separate git branch**.

______________________________________________________________________

## Branch Strategy for Your Fork

```plaintext
main                                ← upstream untouched
practice                            ← your base branch (specs + scenario docs live here)
  practice/scenario-1-detail-page
  practice/scenario-2-search-listings
  practice/scenario-3-pagination
  practice/scenario-4-category-nav
  practice/scenario-5-error-handling
  practice/scenario-6-price-sort
```

Each scenario sub-branch starts fresh from `practice` (clean codebase + docs).
Commit incrementally as you would in the live interview:

1. First commit: the API client change
2. Second commit: the route/controller/component
3. Third commit: the view/template
4. Fourth commit: tests
