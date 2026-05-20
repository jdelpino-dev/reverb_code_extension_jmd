# Chapter 8: Debugging Methodology

## The Systematic Framework

### REPRODUCE → ISOLATE → FIX → VERIFY

```text
1. REPRODUCE  — Can you trigger the bug reliably? Run the failing test.
2. ISOLATE    — What's the smallest code path that exhibits it?
3. FIX        — Change one thing, understand why it works.
4. VERIFY     — Does the fix work? Did it break anything else?
```

### In an Interview Context

**Narrate your process out loud.** The interviewer evaluates your debugging
*method*, not just whether you find the bug:

> "First I'll run the test to see the exact failure... OK, it's returning None
> where we expect a list. Let me trace backward from the return value to find
> where it becomes None..."

---

## The 5-Step Recovery Loop (When Stuck)

1. **Read the error message** (fully, not just the last line)
2. **Read the test** (what is it actually checking?)
3. **Add a print statement** (what value do you actually have?)
4. **Run just that one test** (`pipenv run pytest -xvs -k "test_name"`)
5. **Narrate what you learned** ("OK, the issue is X, which means I need Y")

### What to Say When Stuck

- "Let me read this error more carefully..."
- "I'm going to add a print here to see what's actually happening..."
- "The test expects X, so I need to trace back to where that value comes from..."
- "I'm going to run this one test in isolation to confirm my hypothesis..."

### What NOT to Do

- Don't stare silently for more than 20 seconds
- Don't randomly change code without a hypothesis
- Don't apologize repeatedly
- Don't ask "is this right?" — run the test and see

---

## Common Bug Patterns in This Codebase

### 1. KeyError from Nested Dict Access

**Symptom:** `KeyError: 'photos'` or `IndexError: list index out of range`

**Where:** Template accesses `listing['photos'][0]['_links']['thumbnail']['href']`

**Cause:** A listing has no photos, or the photo structure differs from expected.

**Fix:**

```python
# In service layer, normalize data before passing to template
def _safe_thumbnail(listing):
    try:
        return listing['photos'][0]['_links']['thumbnail']['href']
    except (KeyError, IndexError):
        return '/static/no-image.png'
```

### 2. Mock Not Matching Real API Shape

**Symptom:** Test passes but feature is broken in browser.

**Cause:** Mock data is simplified (`{'title': 'Test'}`) but template accesses
deeply nested fields that aren't in the mock.

**Fix:** Match mock to real API response shape. Use `curl` to verify.

### 3. `filter()` Returns Iterator, Not List

**Symptom:** `len(results)` raises `TypeError: object of type 'filter' has no len()`

**Where:** `_search_categories` returns `filter(...)`.

**Fix:** Wrap in `list()` if you need length/indexing. Or use list comprehension:

```python
return [c for c in categories if query.lower() in c['full_name'].lower()]
```

### 4. Mocking the Wrong Path

**Symptom:** Mock has no effect — real HTTP call is made (or different error).

**Cause:** Patched `'requests.get'` instead of `'reverb_client.requests.get'`.

**Rule:** Patch where the thing is USED, not where it's DEFINED.

### 5. Missing `type=int` on Query Params

**Symptom:** `page` is `"2"` (string) instead of `2` (int). Math breaks.

**Cause:** `request.args.get('page')` returns strings. Forgot `type=int`.

**Fix:** `request.args.get('page', 1, type=int)`

### 6. Template Variable Not Passed

**Symptom:** `UndefinedError: 'query' is undefined` in Jinja2.

**Cause:** Forgot to pass the variable in `render_template(...)`.

**Fix:** Add it: `render_template('listings.html', listings=results, query=query)`

### 7. Route Returns None

**Symptom:** `TypeError: The view function did not return a valid response`

**Cause:** A code path in the route function doesn't hit a `return` statement.

**Fix:** Ensure every branch returns a response.

---

## Common Python/Flask Bugs

### Mutable Default Argument

```python
# Bug: params dict shared across calls
def _get(self, path, params={}):
    params['extra'] = 'value'  # Mutates the shared default!

# Fix
def _get(self, path, params=None):
    params = params or {}
    params['extra'] = 'value'  # Safe — new dict each time
```

### Import Order Issues

```python
# Bug: circular import
# app.py imports from reverb_client
# reverb_client imports from app  ← circular!

# Fix: Keep dependencies one-directional
# app.py → reverb_client → requests (never back to app)
```

### Flask Context Errors

```python
# Bug: using request outside a request context
from flask import request

def helper():
    query = request.args.get('query')  # RuntimeError if called outside request!

# Fix: pass the value as a parameter
def helper(query):
    ...
```

---

## Debugging Workflow (Show This in Interview)

```text
1. Read the error → understand what's expected vs. actual
2. Hypothesis → "I think the issue is..."
3. Verify → add print() or run specific test
4. Fix → change one thing
5. Confirm → run test again
6. Narrate → "That fixed it because..."
```

### pytest Debugging Commands

```bash
# See full traceback with local variables
pipenv run pytest -l tests/test_listings.py

# Stop on failure and open debugger
pipenv run pytest --pdb tests/test_listings.py

# Show print() output (normally captured)
pipenv run pytest -s tests/test_listings.py

# Run just the failing test
pipenv run pytest -xvs -k "test_displays_listings"
```

### Quick Print Debugging

```python
# In app.py (temporary — remove before committing)
@app.route('/listings')
def listings():
    results = ReverbClient().listings()
    print(f"DEBUG: got {len(results)} listings")  # Shows in test with -s flag
    print(f"DEBUG: first listing keys: {results[0].keys()}")
    return render_template('listings.html', listings=results)
```

---

## Reading Error Messages

### AssertionError in Test

```text
AssertionError: assert 'Guitars' in ''
```

**Translation:** Expected 'Guitars' in the output, but got empty string.
**Likely:** Template isn't rendering, or data isn't reaching the template.

### KeyError

```text
KeyError: 'listings'
```

**Translation:** Tried to access `response['listings']` but key doesn't exist.
**Likely:** API response has a different shape (maybe an error response).

### JSONDecodeError

```text
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Translation:** `.json()` called on a non-JSON response (HTML error page, empty body).
**Likely:** API returned an error status with HTML body.

### AttributeError: 'NoneType'

```text
AttributeError: 'NoneType' object has no attribute 'text'
```

**Translation:** `select_one(...)` returned None (element not found in HTML).
**Likely:** The CSS selector doesn't match what the template actually renders.

---

## Debugging Strategy by Scenario

| Scenario | Common bug | How to diagnose |
| --- | --- | --- |
| Detail page | Wrong URL path (missing `/listings/` prefix) | Print `mock_get.call_args` |
| Search | Query not passed to client | Print params dict before request |
| Pagination | Return type changed but tests use old shape | Print client response |
| Error handling | Exception not caught (wrong exception class) | Print exception type in except |
| Sort | `float()` on missing price | Print listing dict before sort |
