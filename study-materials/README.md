# Study Materials — Reverb Code Extension (Python/Flask)

Preparation materials for a code interview focused on **extending a Python/Flask
web application** that consumes the Reverb public API. Covers the codebase
architecture, testing patterns, interview scenarios, and communication strategy.

## How to Use These Materials

1. **Read chapters 01-03 first** — understand the codebase cold before practicing
2. **Practice scenarios on branches** — each scenario is a standalone exercise
3. **Drill communication** — practice explaining concepts out loud (record yourself)
4. **Use the quick reference** — skim before the interview for a final refresh

## Priority Reading (Based on Interview Format)

The interview format is: **Read code → Explain architecture → Implement feature → Test → Discuss trade-offs**

| Priority | Chapters | Why |
| --- | --- | --- |
| **CRITICAL** | 01 (Architecture), 05 (Pair Coding), 06 (Communication), 13 (A&R Team Fit) | Direct match to every phase of the interview |
| **HIGH** | 02 (Testing), 03 (Flask Patterns), 07 (Quick Reference) | Technical depth you'll demonstrate live |
| **MEDIUM** | 04 (System Design), 08 (Debugging) | Discussion topics and "what if" questions |
| **LOWER** | 09 (Security) | Good awareness signals but unlikely to be tested directly |

## Table of Contents

| # | File | Topics |
| --- | --- | --- |
| 1 | [01-architecture-and-code-walkthrough.md](01-architecture-and-code-walkthrough.md) | Layered architecture, request flow, service layer gap, file-by-file breakdown |
| 2 | [02-testing-strategy.md](02-testing-strategy.md) | Mock patterns, test architecture, pytest mastery, what's tested vs. missing |
| 3 | [03-flask-python-patterns.md](03-flask-python-patterns.md) | Flask idioms, Jinja2, Python gotchas, key patterns to know cold |
| 4 | [04-system-design.md](04-system-design.md) | DEBASE method, architecture patterns, notification system, scaling |
| 5 | [05-pair-coding-interview.md](05-pair-coding-interview.md) | Pairing dynamics, do's/don'ts, handling feedback, pacing |
| 6 | [06-interview-communication.md](06-interview-communication.md) | Thinking out loud, trade-off framework, questions to ask, pacing |
| 7 | [07-quick-reference.md](07-quick-reference.md) | Cheat sheets, commands, common patterns, status codes |
| 8 | [08-debugging-methodology.md](08-debugging-methodology.md) | Systematic debugging, common Python/Flask bugs, "when stuck" strategy |
| 9 | [09-security-awareness.md](09-security-awareness.md) | Vulnerabilities in this codebase, OWASP patterns, what to mention |
| 13 | [13-ar-team-fit.md](13-ar-team-fit.md) | A&R product framing, Ruby/Rails talking points, non-traditional background, React fluency |

## Pre-Interview Checklist

- [ ] Can run `pipenv run pytest -vs` without thinking
- [ ] Can explain the full request flow for both `/categories` and `/listings`
- [ ] Know the mock pattern: `patch('reverb_client.requests.get').start()`
- [ ] Can add a new route + client method + template + test from memory
- [ ] Practiced the "3-minute orientation" narration out loud
- [ ] Have 2-3 clarifying questions ready for any feature ask
- [ ] Can articulate the service-layer inconsistency and why it matters
- [ ] Can name the client issues: mutable default, no timeout, no error handling
