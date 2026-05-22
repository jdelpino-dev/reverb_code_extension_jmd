# Chapter 14: AI Use Strategy for the Interview

## Interview Context

- **Date:** Monday, June 1, 2026 at 1:00 PM - 1:45 PM CDT
- **Interviewer:** Steve Weber (Senior Engineering Manager, Engineering)
- **Role:** Engineer II - Activation & Retention
- **Language:** Python
- **Format:** Live Share pairing session via Google Meet
- **AI Policy:** Explicitly allowed. They recommend Copilot setup.

---

## What They Said

> "We also recommend connecting your GitHub account and setting up Copilot for
> free if you don't already have AI tooling configured."
>
> "You're welcome to use a browser at interview time instead, but AI tool access
> will be limited without a paid Copilot subscription."

**Translation:** AI tooling is permitted and expected. You have a paid Copilot
subscription — use it naturally.

---

## What They Are Actually Evaluating

AI changes the *what* they observe, not the *whether* you pass. They are
assessing:

| Skill | How AI changes the signal |
| --- | --- |
| Can you explain your thinking? | You narrate *why* you accept/reject suggestions |
| Can you review AI output critically? | You catch mistakes, adjust generated code |
| Can you debug? | AI can't debug for you in a live context |
| Can you understand the codebase? | You orient quickly, show comprehension |
| Can you collaborate with Steve? | You treat AI like a third pair-programmer, not a replacement for dialogue |
| Can you make good engineering decisions? | You choose when AI helps vs. when to write manually |

---

## Opening Statement (Memorize This)

At the start of the coding portion, say:

> "I saw the note about Copilot and AI tooling. I have Copilot configured in
> VS Code, so I'm happy to use it naturally during the session. I'll narrate
> my thinking as suggestions come up — accepting the good ones, adjusting or
> rejecting the rest. Let me know if you'd prefer I turn it off at any point."

This signals: **flexible, ethical, collaborative, not dependent on AI.**

---

## The 80/20 Rule for AI in This Interview

**80% you, 20% AI.** AI should accelerate, not replace:

- **Use AI for:** boilerplate, autocomplete of patterns you already understand,
  test scaffolding, syntax you'd otherwise look up
- **Don't use AI for:** architecture decisions, choosing what to build next,
  explaining code to Steve, debugging logic errors

---

## Tactical Patterns

### Pattern 1: Accept with Narration

Copilot suggests something correct:

> "Nice — Copilot got the response parsing right. That matches the pattern we
> used for categories. I'll keep it."

### Pattern 2: Reject with Reason

Copilot suggests something wrong or premature:

> "Copilot wants to add error handling here, but I'm going to defer that and
> focus on the happy path first — I'll circle back if we have time."

### Pattern 3: Modify

Copilot is close but not quite right:

> "The suggestion is mostly right, but it's using `listing['title']` when the
> API nests it under `listing['_embedded']['title']`. Let me fix that."

### Pattern 4: Ignore Gracefully

Copilot suggests irrelevant code:

> (Just press Escape and keep typing. No need to narrate every dismissed ghost.)

### Pattern 5: Proactive Use

You want Copilot to help with something specific:

> "Let me type the function signature and let Copilot fill in the body — then
> I'll review what it gives me."

---

## What NOT to Do

| Anti-pattern | Why it fails |
| --- | --- |
| Accept every suggestion silently | Shows no judgment, looks like you can't code without AI |
| Tab-complete your way through the whole feature | Steve can't evaluate *your* thinking |
| Ask AI to explain the codebase to Steve | You should demonstrate understanding |
| Apologize for using AI | They told you to use it |
| Refuse to use AI to prove "purity" | Wastes time, ignores their explicit guidance |
| Let AI drive while you narrate | The ratio should be 80% you, 20% AI |

---

## When to Turn AI Off (Mentally)

There are moments where AI adds noise, not value:

- **Explaining architecture** — This is a conversation, not a coding moment
- **Discussing tradeoffs** — Steve wants *your* judgment
- **Debugging a failing test** — Read the output, think, hypothesize
- **Asking clarifying questions** — Pure collaboration

In these moments, Copilot will be quiet anyway (no code being typed), so
this is natural.

---

## When AI Shines (Lean Into It)

- Writing the second test when the first establishes the pattern
- Filling in template HTML that follows an existing structure
- Autocompleting a client method that mirrors an existing one
- Generating a mock response dict from a known shape

Narrate: "This is a good spot for Copilot — it's the same pattern as above."

---

## If Steve Asks About Your AI Use

Possible questions and responses:

### "How do you typically use AI in your workflow?"

> "I use it as a pair programmer for boilerplate and pattern completion. The key
> is reviewing everything critically — AI is great at repeating patterns but
> often wrong on edge cases or project-specific logic. I always make sure I
> understand what it generated before committing."

### "Do you find it speeds you up?"

> "Definitely for repetitive code and tests. Less so for architecture decisions
> or debugging — those still require human reasoning about the specific context."

### "What if Copilot gives you something wrong?"

> "That's actually the most important skill — catching when it's wrong. I look
> for things like incorrect key paths, missing edge cases, or suggestions that
> don't match the project's existing patterns. I just demonstrated that
> when I rejected the suggestion about [specific example from session]."

---

## Live Share + AI Considerations

- Steve will see your editor in real-time via Live Share
- Copilot ghost text (gray suggestions) will be visible to him
- This is fine — it's natural. He sees how you evaluate suggestions
- If suggestions are distracting, you can briefly say "Let me dismiss that
  and think about this manually"

---

## Pre-Interview AI Prep Checklist

- [ ] GitHub Copilot extension active and authenticated
- [ ] Copilot Chat available (sidebar) in case you want to look something up
- [ ] Practiced coding with Copilot while narrating accept/reject decisions
- [ ] Tested that Live Share doesn't interfere with Copilot suggestions
- [ ] Prepared the opening statement (memorized, not scripted-sounding)
- [ ] Know where to turn Copilot off quickly if asked (command palette or
      status bar icon)

---

## Summary

The interview is **not** "can you avoid AI?" It is:

- Can you think clearly and make decisions?
- Can you collaborate with a human while AI assists?
- Can you catch AI mistakes and explain why they're wrong?
- Can you use AI to move faster without losing understanding?

**Be transparent. Be natural. Let AI accelerate your strengths — not mask
your weaknesses.**
