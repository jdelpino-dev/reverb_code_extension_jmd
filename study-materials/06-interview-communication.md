# Chapter 6: Interview Communication

## The Meta-Skill: Thinking Out Loud

Technical interviews assess two things equally:

1. **Can you solve the problem?** (technical skill)
2. **Can I work with this person?** (communication, collaboration)
3. **Can they use tools effectively?** (judgment, critical review of AI output)

The way you communicate often matters more than arriving at the perfect solution.
With AI allowed, *how you narrate your use of AI* becomes part of the signal.

---

## Communication Frameworks

### The Tradeoff Framework (For Technical Decisions)

**Always present as:** "Option A gives us X but costs Y. Option B gives us Z but costs W. I chose A because..."

**Example:** "Should filtering happen client-side or server-side?"

> "Client-side filtering is instant — no network round-trip — and works great for
> categories since there are only a few hundred. But for listings (potentially
> thousands), server-side is better because the API supports full-text search
> natively. The trade-off is latency per query, which I'd handle with a submit
> button rather than as-you-type."

### The Three-Sentence Pattern (For Explaining Code)

1. **What it does** — "This class wraps the Reverb API and returns parsed JSON"
2. **How it does it** — "Uses the requests library with versioned headers"
3. **Why this way** — "Centralizing the client means tests can stub one place"

### Start Simple, Then Extend

1. Start with the simplest thing that works (happy path)
2. Add complexity one layer at a time (errors, edge cases)
3. Call out what you're deferring: "I'd handle X, but let me focus on Y first"

---

## Common Observations (How to Say Them)

| Observation | How to articulate |
| --- | --- |
| Missing error handling | "I notice there's no try/except — the happy path is clear, so that's probably where I'd start extending" |
| No caching | "Every request hits the API. For categories that rarely change, I'd add caching" |
| Service layer inconsistency | "Categories has a service helper but listings calls the client directly — I'd fix that for consistency" |
| No auth | "The public API doesn't require auth, which keeps this simple" |
| Mutable default | "I noticed the mutable default arg — harmless now since it's never mutated, but I'd fix it if I were adding mutation logic" |
| AI suggestion is wrong | "Copilot suggested X, but that won't work here because Y — let me write it this way instead" |
| AI suggestion is helpful | "Nice — Copilot got the pattern right. That matches what we did above." |

---

## Handling "How Would You..." Questions

### Template

1. **Clarify the scope** (30 seconds)
2. **State your approach** (1 sentence)
3. **Build it step by step** (main body)
4. **Discuss tradeoffs** (30 seconds)
5. **Mention what's next** (10 seconds)

### Example: "How would you add pagination?"

> **Clarify:** "So users need next/previous buttons, and the URL should reflect
> the current page for sharing?"
>
> **Approach:** "I'd pass a page param through the client to the API, extract
> pagination metadata from the response, and render controls in the template."
>
> **Build:** (implement step by step)
>
> **Tradeoffs:** "I'm relying on the API's pagination rather than fetching all
> and slicing — that scales better but means a round-trip per page."
>
> **Next:** "With more time I'd add page size options and handle the edge case
> where page > total_pages."

---

## Trade-offs They'll Probe

| Decision | Pro | Con |
| --- | --- | --- |
| Client-side filtering | Instant UI, no extra requests | Needs all data upfront |
| Server-side filtering | Works at any scale | Latency per query |
| Separate API client class | Testable, single responsibility | Extra abstraction |
| Inline fetch in route | Simple, fewer files | Harder to test, can't reuse |
| URL-based state (query params) | Shareable, back-button works | More wiring |
| Caching API responses | Faster repeat visits | Stale data risk |

### Phrases That Show Maturity

- "For this scope it's fine, but at scale I'd..."
- "The trade-off here is between X and Y — I chose X because..."
- "I'm keeping it simple now but the interface is open for extension"
- "I'd want to understand the usage pattern before optimizing"

---

## Questions to Ask THEM

### Show Technical Curiosity

- "Does the Reverb API support query params on this endpoint?"
- "Should the search be instant (as-you-type) or on submit?"
- "Do you care about the URL reflecting filter state?"
- "Should I handle the empty state, or focus on the happy path first?"
- "Do you want me to write the test first or implement then test?"

### Show Product Thinking

- "What's the expected data volume here — dozens or thousands of results?"
- "Is there a specific listing field you'd like displayed, or should I pick a reasonable set?"
- "How would users typically navigate — from category to listings?"

---

## Anti-Patterns to Avoid

- **Don't critique code unprompted** — don't say "this should be refactored"
- **Don't over-explain basics** — don't say "so Flask is a micro-framework..."
- **Don't stay silent while reading** — narrate your thought process
- **Don't dive into code without discussing approach** — talk before typing
- **Don't say "I don't know" without follow-up** — say "I'm not sure, but I'd approach it by..."
- **Don't apologize for style** — write your best code, move on
- **Don't argue about tools** — "I'd use X, but if the team prefers Y, that works too"
- **Don't silently accept AI suggestions** — always narrate what Copilot gave you and why you kept/rejected it
- **Don't let AI go unchecked** — review every suggestion; catching an AI mistake shows strong judgment
- **Don't hide AI use** — be transparent; they explicitly allowed it

---

## The 30-Second Rule

For complex questions, take 30 seconds to think before speaking:

> "That's a good question. Let me think about the best approach..."
> (30 seconds of actual thinking)
> "OK, here's how I'd approach this..."

Silence is not awkward — it shows you're thoughtful.

---

## Pacing & Time Management

Typical 45-minute interview breakdown:

| Phase | Time | What to do |
| --- | --- | --- |
| Intro/orientation | 0-5 min | Read code, ask clarifying questions |
| Explain architecture | 5-10 min | Walk through the request flow |
| Implement feature | 10-35 min | Code iteratively, talk while coding |
| Test | 35-42 min | Add at least one meaningful test |
| Wrap-up discussion | 42-45 min | Trade-offs, what you'd do next |

### If You Get Stuck

1. Say "Let me think about this for a moment"
2. Re-read the relevant code — don't guess
3. State your hypothesis: "I think the issue is X, let me verify"
4. Ask the interviewer: "Can I check — does this API return nested or flat?"

### If You Finish Early

- Add a test for an edge case
- Mention what you'd add next
- Don't gold-plate or refactor working code

---

## Verbal Walkthrough Practice (Record Yourself)

Set a timer for 3 minutes. Open the repo cold. Narrate:

> "I'll start with `app.py` — two routes: categories at `/` and `/categories`,
> listings at `/listings`. Categories reads a query param, delegates to
> `_search_categories` which fetches ALL categories from the API and filters
> client-side using a case-insensitive substring match. Listings just calls
> the client directly — I notice there's no service helper here, which is an
> inconsistency I'd want to fix.
>
> The client is in `reverb_client.py` — thin wrapper around requests with
> Accept headers and API versioning. No auth, no error handling, no timeout.
>
> Tests mock `requests.get` at the module level. Integration tests use Flask's
> test client and assert on HTML via BeautifulSoup. No error case tests.
>
> If I were extending this, I'd add `_load_listings()` first for consistency,
> then build whatever feature is asked on top of that service boundary."

---

## Post-Feature Completion (What to Say)

After implementing:

> "So we have a working endpoint that [describes feature]. The test verifies
> [what it checks]. With more time I'd add [1-2 specific improvements]:
> error handling for API failures, and an empty state message when no results
> match."
