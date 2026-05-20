# Chapter 9: Security Awareness

## Why This Matters in an Interview

You won't be asked to implement security features, but **mentioning awareness**
when relevant signals engineering maturity. A single sentence like "I'd add a
timeout here to prevent resource exhaustion" is worth more than silence.

---

## Vulnerabilities in This Codebase

### 1. No Request Timeout (DoS via Resource Exhaustion)

**File:** `reverb_client.py`
**Severity:** Medium

```python
# Current: hangs indefinitely if API is slow
requests.get(self._base_uri + path, headers=self.HEADERS, params=params)

# Fixed: fail fast
requests.get(..., timeout=(3.05, 10))  # (connect_timeout, read_timeout)
```

Flask's dev server is single-threaded. Even with Gunicorn, a handful of hanging
requests exhausts all workers.

**What to say:** "I'd add a timeout to prevent a slow upstream from blocking
all workers."

### 2. Mutable Default Argument (State Leakage)

**File:** `reverb_client.py`

```python
# Current: shared dict across calls
def _get(self, path, params={}):

# Fixed:
def _get(self, path, params=None):
    params = params or {}
```

Not a security issue today, but becomes one if params accumulate across requests
(data leakage between users in a multi-tenant context).

### 3. No Error Handling on API Responses

**File:** `reverb_client.py`

```python
# Current: .json() on any response (including HTML error pages)
return requests.get(...).json()

# Failure cascade: API 500 → JSONDecodeError → Flask 500 → stack trace exposed
```

In debug mode, the stack trace reveals file paths, variable values, library versions.

**Fix:**

```python
response = requests.get(..., timeout=5)
response.raise_for_status()  # HTTPError for 4xx/5xx
return response.json()
```

### 4. Debug Mode (Remote Code Execution Risk)

**Severity:** High in production

The Werkzeug debugger enables an interactive Python REPL accessible via browser.
If the PIN is guessed (derived from predictable machine values), attacker gets
full RCE.

**What to say:** "In production I'd ensure debug mode is off. The Werkzeug
debugger is effectively an intentional backdoor for development."

### 5. No Input Validation

**File:** `app.py`

`query` param passes straight through to filter logic. Currently safe because
it's used with Python's `in` operator (not regex). But if you implement search
with `re.search(user_query, title)`, a malicious regex could cause ReDoS.

**Defense:** Use `in` for substring match (safe), or `re.escape(user_input)` if
regex is needed.

---

## Security Concepts to Know

### XSS (Cross-Site Scripting)

Attacker injects scripts into content viewed by other users.

**This app's defense:** Jinja2 auto-escapes all `{{ }}` output. `?query=<script>alert(1)</script>`
renders as harmless text, not executable JS.

**When to mention:** If using `| safe` filter or rendering raw HTML.

### SSRF (Server-Side Request Forgery)

Server is tricked into making requests to unintended destinations.

**Relevance:** `ReverbClient` constructs URLs from user input
(`/listings/{listing_id}`). Path traversal (`../../admin`) could hit unintended
endpoints — though `requests` URL-encodes by default.

**What to say:** "I'd validate that `listing_id` matches an expected format
before interpolating it into the URL."

### CSRF (Cross-Site Request Forgery)

Currently low risk (GET-only forms, no auth). Becomes relevant the moment
any scenario adds POST routes.

**If adding POST routes:** "I'd add CSRF protection via flask-wtf."

---

## What to Mention (And When)

### During Implementation

| Situation | One-liner to say |
| --- | --- |
| Adding a client method | "I'd add a timeout here in production" |
| Adding a route with URL param | "I should validate this ID format" |
| Adding error handling | "In debug mode errors expose internals — production needs generic messages" |
| Using user input in a filter | "Using `in` is safe — no regex engine involved" |
| Adding pagination | "Without rate limiting, someone could scrape all pages" |

### During Trade-off Discussion

> "The codebase has no error handling, so any API failure crashes the page. The
> biggest security implication is that Flask in debug mode shows full stack traces
> including file paths and variable values. In production, I'd disable debug mode
> and add proper error pages."

---

## Defense in Depth (This App)

| Layer | Defense | Status |
| --- | --- | --- |
| Input | Validation of query params | Missing |
| Transport | HTTPS to Reverb API | Present (hardcoded URL) |
| Processing | Safe string operations (no regex on user input) | Present |
| Output | Jinja2 auto-escaping | Present |
| Infrastructure | Debug mode off, timeouts, error handling | Missing |

---

## Quick Security Vocabulary

| Term | One-sentence definition |
| --- | --- |
| **Allowlist** | Only permit known-good values (prefer over blocklist) |
| **Exponential backoff** | Each retry waits longer: 1s → 2s → 4s (+ random jitter) |
| **Circuit breaker** | Stop calling failing service after N failures |
| **Idempotency** | Same request produces same result (safe to retry) |
| **Rate limiting** | Restrict requests per time window |
| **Content-Security-Policy** | HTTP header restricting what scripts can execute |
| **ReDoS** | Malicious regex input causing exponential backtracking |
| **Path traversal** | Using `../` to escape intended directory/path scope |
