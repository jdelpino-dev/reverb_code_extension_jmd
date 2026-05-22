# Chapter 5: Pair Coding Interview

## What Makes Pair Coding Different

A pair coding interview simulates daily collaboration. The interviewer plays the
role of a coworker — they want to see what it's like to build something *with* you.

**Dual evaluation:**

| What they assess | How it shows up |
| --- | --- |
| Technical competence | You write working code, debug effectively |
| Collaboration quality | You communicate, adapt, incorporate feedback |
| Judgment with AI tooling | You use AI as a tool, not a crutch — review critically, explain reasoning |

Most candidates prepare only for the first. The second (and now third) is where
offers are won or lost at equal technical levels.

**Note:** AI tooling (GitHub Copilot) is explicitly allowed in this interview.
See [14-ai-use-strategy.md](14-ai-use-strategy.md) for the full strategy.

---

## The Pairing Mindset

**You are not performing — you are collaborating.**

- Ask questions naturally (not defensively)
- Treat their suggestions as useful (not as tests)
- Share your reasoning (not your polished answer)
- Admit uncertainty early (not after wasting 5 minutes)
- Use AI as a collaborator, not a replacement for your thinking
- Always explain *why* you accept or reject an AI suggestion

---

## The Do's

### 1. Establish Shared Understanding First (60-90 Seconds)

Before writing any code:

- Read the requirement aloud or paraphrase it
- Confirm scope: "So we're building X that does Y — does that sound right?"
- State your plan: "I'm going to start with the client method, then the route, then template, then test"

### 2. Think Out Loud Continuously

Narrate every *decision* (not every keystroke):

- "I'll add the service helper first for consistency with categories"
- "I'm passing `query=None` as a keyword arg so existing callers don't break"
- "Let me check the test to see what shape the mock expects"

**Golden ratio:** ~70% doing, ~30% narrating. Don't go silent for more than 15 seconds.

### 3. Treat Suggestions as Gifts

When the interviewer says:

- "What if we tried..." → They're steering toward a better solution
- "Have you considered..." → They're hinting at something you missed
- "What about edge case X?" → They're telling you X is important

**Response:** "Oh good point — let me adjust for that." Then immediately incorporate it.

### 4. Ask Small, Targeted Questions

- "Does the Reverb API support a query param on listings?"
- "Should I handle the empty state, or focus on the happy path first?"
- "Do you want me to write the test first or implement then test?"

### 5. Use Tests as the Shared Feedback Loop

- Run tests frequently (every 2-3 minutes of coding)
- Share the result: "OK, passing. Let me add the template now."
- Use output to plan: "Failing because the mock doesn't include photos. Let me fix that."

### 6. Timebox and Pivot

If something isn't working after 2-3 minutes:

- "This approach is taking longer than expected. Let me try a simpler version."
- "I think I'm overcomplicating this. Can we step back?"

### 7. Close the Loop

When you finish:

- Summarize what you built
- Mention what you'd add with more time
- Ask if they want you to go deeper on anything

---

## The Don'ts

### Don't Go Silent

Silence signals you're stuck and not asking for help. If you need to think:
"Give me 10 seconds to think about the data structure here."

### Don't Ignore Hints

The interviewer's suggestions are not random. Even if you disagree:
"Interesting — I was thinking X because of Y, but your approach handles Z better."

### Don't Over-Explain Before Coding

30-second plan, then start coding. Explain as you go. Don't spend 5 minutes
describing what you'll do.

### Don't Apologize Excessively

- Bad: "Sorry, I'm blanking on the syntax... sorry..."
- Good: "Let me check the syntax real quick." (then check and move on)

### Don't Argue About Approach

If redirected: "Sure, let me try it that way." You can note the tradeoff but
follow their lead. They wrote the exercise.

### Don't Freeze When You Hit a Bug

Bugs are opportunities to demonstrate debugging skill:

- "Hmm, that's not what I expected. Let me add a print to see what we're getting."
- "The test expects X but we're returning Y. Let me trace back."

---

## Interview Flow for This Codebase

### Phase 1: Orientation (0-5 min)

Open the code, trace request flow. Narrate:

1. "I'll start with the routes to see what endpoints exist"
2. "Two routes: categories with search, listings flat list"
3. "Both use ReverbClient to fetch from the external API"
4. "Tests mock `requests.get` — nothing hits the network"

### Phase 2: Explain Architecture (5-10 min)

Use the three-sentence pattern for each component:

- **What:** "ReverbClient wraps the Reverb API and returns parsed JSON"
- **How:** "Uses requests library with versioned headers"
- **Why:** "Centralizing means tests can stub one place"

### Phase 3: Implement Feature (10-35 min)

Work in this order:

1. **Client method** — the data foundation
2. **Service helper** — business logic boundary
3. **Route** — wire it up
4. **Template** — render the data
5. **Test** — verify it works

Run tests after each step.

### Phase 4: Test (35-42 min)

Add at least one meaningful test. Say:

- "I'll start with a client test since that's the new IO boundary"
- "I'm mocking at the HTTP level to match the existing pattern"

### Phase 5: Discussion (42-45 min)

Trade-offs, what you'd do differently, what you'd add with more time.

---

## Development Loop (Show This)

```text
1. Read the requirement/test → understand what's needed
2. Write minimal code → just enough to make progress
3. Run the specific test → get feedback
4. Read the output → understand what happened
5. Adjust → fix the issue
6. Repeat until green
7. Move to next step
```

**Narrate each step:**

- "OK, this test checks that the listing title renders..."
- "Let me add the route... `pipenv run pytest -vxs -k test_detail`"
- "Green. Now the template."

---

## Handling Common Situations

### "I don't know the exact API response shape"

State your assumption, then verify:

> "I expect the listing endpoint returns a dict with title, price, and photos.
> Let me write code against that assumption — if it's different, the fix is just
> updating the key path."

### "My approach has a flaw"

Say it immediately:

> "Actually, this won't work because (reason). The better approach is (alternative).
> Let me refactor."

### "The interviewer is silent"

Pause 3-5 seconds, then: "Shall I move on to the template?" or "Does that
answer your question?"

### "I'm stuck on syntax"

> "Let me check the syntax for Flask URL params real quick..."
> (look at existing code in the file for the pattern)

### "I finished early"

Don't gold-plate. Instead:

- Add a test for an edge case
- Mention what you'd add next
- Clean up any TODO comments

### Using AI During the Session

Copilot suggestions will appear naturally as you code. Handle them like this:

- **Accept with narration:** "Copilot's suggesting the response parsing — that
  looks right, it matches the pattern we used for categories."
- **Reject with reason:** "That suggestion adds error handling I don't need yet —
  let me stay focused on the happy path."
- **Modify:** "The autocomplete is close but it's using the wrong key. Let me
  adjust."

Do NOT:

- Silently accept every suggestion without reviewing
- Ask AI to generate entire implementations while you stay silent
- Pretend AI isn't there — acknowledge it naturally
- Let AI drive the architecture decisions

---

## Pre-Interview Physical Checklist

- [ ] Editor: can open files, split panes, navigate quickly
- [ ] Terminal: accessible within editor, can run pytest
- [ ] Familiar with the project file layout (6 files that matter)
- [ ] Verified `pipenv run pytest -vs` works
- [ ] Done a live `curl` against the Reverb API to see response shapes
- [ ] Practiced the 3-minute narration out loud at least twice
- [ ] GitHub Copilot configured and working in VS Code
- [ ] Live Share extension installed and tested
- [ ] Practiced accepting/rejecting Copilot suggestions while narrating
- [ ] Prepared opening line about AI tooling (see chapter 14)
