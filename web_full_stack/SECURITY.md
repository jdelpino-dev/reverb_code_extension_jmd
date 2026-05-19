# Security Analysis — Reverb Code Extension (Python/Flask)

## Key Security Concepts (Definitions)

Before diving into specifics, these are the security concepts most relevant to this codebase:

### XSS (Cross-Site Scripting)

An attacker injects malicious scripts into content viewed by other users. There are three types:

- **Reflected XSS** — malicious input in the URL is echoed back in the response (e.g., `?query=<script>...`)
- **Stored XSS** — malicious content is saved (DB, file) and rendered to other users
- **DOM-based XSS** — client-side JavaScript manipulates the DOM unsafely

**Why it matters here:** User input (`query` param) and external API data (listing titles, descriptions) are rendered in HTML. Jinja2's auto-escaping is the primary defense.

### SSRF (Server-Side Request Forgery)

The server is tricked into making HTTP requests to unintended destinations. The attacker controls part of a URL the server fetches.

**Why it matters here:** `ReverbClient` constructs URLs from user input (`/listings/{listing_id}`). If the ID contains path traversal characters (`../`), the server could request unintended API endpoints.

### CSRF (Cross-Site Request Forgery)

An attacker tricks a user's browser into submitting a request to a site where the user is authenticated, performing unwanted actions.

**Why it matters here:** Currently low risk (GET-only forms, no auth), but becomes relevant the moment any scenario adds POST routes.

### DoS (Denial of Service) via Resource Exhaustion

An attacker triggers conditions that consume server resources (threads, memory, CPU) until the application becomes unresponsive.

**Why it matters here:** No request timeout means a single slow upstream response can block a worker indefinitely. Flask's default single-threaded dev server makes this trivially exploitable.

### Input Validation vs. Sanitization vs. Encoding

| Term | Definition | When to use |
| -- | -- | -- |
| **Validation** | Reject input that doesn't match expected format | At system boundaries (route params, query strings) |
| **Sanitization** | Transform input to remove dangerous parts | When accepting rich text (not applicable here) |
| **Encoding/Escaping** | Transform output so special chars are harmless | At rendering time (Jinja2 does this automatically) |

### Defense in Depth

Multiple layers of protection so that if one fails, others catch the issue. In this app:

1. `requests` URL-encodes params → prevents injection into API calls
2. Jinja2 auto-escapes output → prevents XSS in templates
3. (Missing) Input validation → would catch bad data before it even reaches layers 1-2

### Principle of Least Privilege

Code should have only the permissions it needs. This app:

- Uses no API key (public endpoints only) → good, no credentials to leak
- Runs Flask in debug mode → bad, debug gives excessive access

### ReDoS (Regular Expression Denial of Service)

A specially crafted input string causes a regex engine to enter catastrophic backtracking — exponential time complexity. The regex "hangs" the process.

**Example vulnerable pattern:** `re.search(r'(a+)+$', user_input)` — the input `"aaaaaaaaaaaaaaaaX"` causes the engine to try 2^n combinations before failing.

**Why it matters here:** If you implement listing search with `re.search(user_query, title)` and the user supplies a malicious regex pattern like `(.*){1,50}`, the server hangs.

**Defense:** Either use `in` (plain substring, no regex engine), or `re.escape(user_input)` which escapes all special regex chars.

### Path Traversal

An attacker uses sequences like `../` to escape the intended directory/path scope. In a filesystem context, `../../etc/passwd` reads outside the web root. In a URL context, `../../admin/users` reaches unintended API endpoints.

**Why it matters here:** The listing ID route `/listings/<listing_id>` interpolates user input into the API path. While `requests` will URL-encode the full path, understanding this risk shows awareness.

### Open Redirect

An application redirects users to a URL specified in a parameter (e.g., `?next=/dashboard`). If not validated, an attacker can craft `?next=https://evil.com` and the app redirects the user to a phishing site — using the trusted domain as a springboard.

**Why it matters here:** If category links redirect (e.g., `/go?url=/listings?category=guitars`), the redirect target must be validated as internal.

### Slowloris Attack

A denial-of-service technique where the attacker opens many connections to a server but sends requests very slowly — keeping each connection open as long as possible. The server's worker pool fills up and legitimate users can't connect.

**Why it matters here:** No timeout on `requests.get()` means the upstream API being slow (naturally or via attack) has the same effect — Flask's workers are all blocked waiting.

### Log Injection

An attacker includes newlines or control characters in input that gets written to logs. This can forge log entries, hide malicious activity, or exploit log viewers.

**Example:** Query `?query=admin%0a[CRITICAL] System compromised` creates a fake log line.

**Defense:** Strip `\n`, `\r`, and control characters from any user input before logging.

### Allowlist vs. Blocklist

| Approach | Definition | Security posture |
| -- | -- | -- |
| **Allowlist** (whitelist) | Only permit explicitly known-good values | Strong — new attack patterns are blocked by default |
| **Blocklist** (blacklist) | Block known-bad values, permit everything else | Weak — attacker only needs one pattern you didn't anticipate |

**Rule:** Always prefer allowlists. Example: validating `sort` against `{'price_asc', 'price_desc'}` is an allowlist approach.

### Exponential Backoff with Jitter

A retry strategy where each subsequent retry waits exponentially longer (1s → 2s → 4s → 8s), plus a random "jitter" component to prevent synchronized retries from multiple clients.

**Why jitter matters:** Without jitter, all clients that failed at the same time retry at the same time — creating a "thundering herd" that overwhelms the recovering service.

```python
import random
import time

def retry_with_backoff(fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + random.uniform(0, 1)  # exponential + jitter
            time.sleep(wait)
```

### Thundering Herd

When many clients simultaneously retry or reconnect after a failure, overwhelming the service that just recovered. The service goes down again immediately, creating a cycle.

**Mitigations:** Exponential backoff with jitter (client-side), rate limiting (server-side), circuit breaker pattern (client-side).

### Circuit Breaker Pattern

A design pattern that prevents an application from repeatedly calling a failing service. Like an electrical circuit breaker:

- **Closed** (normal) — requests flow through
- **Open** (tripped) — requests fail immediately without calling the service (for a cooldown period)
- **Half-open** — after cooldown, allow one request through to test if the service recovered

**Why mention in interview:** Shows awareness of distributed system resilience without actually implementing it (overkill for this app).

### Rate Limiting

Restricting the number of requests a client can make in a time window. Prevents abuse (scraping, brute force, DoS).

**Common patterns:**

- Fixed window: "100 requests per minute"
- Sliding window: "100 requests in any 60-second span"
- Token bucket: Requests consume tokens; tokens refill at a fixed rate

**Where relevant here:** Pagination (Scenario 3) — without rate limiting, an attacker can scrape all listings by iterating all pages. In the interview, just mention it: "In production, I'd add rate limiting to prevent scraping."

---

## Existing Vulnerabilities in the Base Code

### 1. No Request Timeout (Denial of Service via Resource Exhaustion)

**File:** `reverb_client.py`
**Severity:** Medium
**OWASP:** A04 (Insecure Design)

**What's happening:**

```python
requests.get(self._base_uri + path, headers=self.HEADERS, params=params)
```

No `timeout` parameter. If the Reverb API hangs, the Flask worker thread blocks **indefinitely**. Under load, all workers exhaust → app becomes unresponsive.

**Why this is dangerous:** Flask's development server is single-threaded. Even in production with Gunicorn (typical: 2-4 workers per CPU core), a handful of hanging requests can consume all workers. This is a classic "slowloris" style vulnerability — the attacker doesn't need to send malicious data, they just need the upstream API to be slow (which they could trigger by DDoSing Reverb, or the API could simply be having a bad day).

**The tuple timeout pattern:**

```python
requests.get(..., timeout=(3.05, 10))  # (connect_timeout, read_timeout)
```

- **Connect timeout (3.05s):** How long to wait for the TCP handshake. The 0.05 accounts for a typical TCP retransmission timer (RFC 6298 says 1s + jitter).
- **Read timeout (10s):** How long to wait between bytes once connected. Should be generous enough for the API to process the request.

---

### 2. Mutable Default Argument (Subtle State Leakage)

**File:** `reverb_client.py`
**Severity:** Low (but demonstrates bad practice in an interview)
**Category:** Language-specific footgun (CWE-1321: Improperly Controlled Modification of Object Prototype Attributes)

**What's happening:**

```python
def _get(self, path, params={}):
```

**Why this matters:** In Python, default argument values are evaluated **once** at function definition time, not at each call. This means all calls share the same `{}` object. If any caller mutates it (e.g., `params['page'] = 2`), that mutation persists for subsequent calls.

**Demonstration of the bug:**

```python
def bad_append(item, lst=[]):
    lst.append(item)
    return lst

bad_append(1)  # [1]
bad_append(2)  # [1, 2] ← NOT [2]!
```

**In this codebase:** The `listings()` method passes `{'per_page': per_page}` as a new dict each time, so the mutable default in `_get()` is never actually used with mutation today. But the moment someone writes `params['query'] = query` inside `_get()`, the bug activates.

**Fix:**

```python
def _get(self, path, params=None):
    params = params or {}
```

---

### 3. No Error Handling on External API Response

**File:** `reverb_client.py`
**Severity:** Medium
**OWASP:** A04 (Insecure Design), A09 (Security Logging/Monitoring Failures)

**What's happening:**

```python
return requests.get(...).json()
```

**The failure cascade:**

1. Reverb returns HTTP 500 with an HTML error page
2. `.json()` attempts to parse HTML as JSON
3. Raises `json.decoder.JSONDecodeError` (subclass of `ValueError`)
4. Exception propagates up through Flask
5. Flask shows a stack trace (debug mode) or generic 500 (production)
6. No logging — you'd never know this happened unless a user reports it

**Other failure modes:**

| Reverb returns... | What happens | User sees |
| -- | -- | -- |
| 200 + valid JSON | Works correctly | Normal page |
| 200 + invalid JSON | `JSONDecodeError` | Flask 500 |
| 404 | `{'message': 'Not Found'}` — no `'listings'` key | `KeyError` → Flask 500 |
| 429 (rate limit) | JSON body but wrong shape | `KeyError` or partial render |
| 500 | HTML error page | `JSONDecodeError` → Flask 500 |
| Connection refused | `ConnectionError` | Flask 500 |
| DNS failure | `ConnectionError` | Flask 500 |

**Fix:**

```python
response = requests.get(..., timeout=5)
response.raise_for_status()  # Raises HTTPError for 4xx/5xx
return response.json()       # Now only called on 2xx responses
```

---

### 4. Debug Mode Enabled by Default

**File:** `.env`
**Severity:** High (in production) / Informational (dev-only repo)
**OWASP:** A05 (Security Misconfiguration)

**What's happening:**

```plaintext
FLASK_ENV=development
```

**What debug mode enables:**

| Feature | Security risk |
| -- | -- |
| Interactive Werkzeug debugger | **Remote Code Execution** — anyone who can trigger an error and knows the PIN can execute arbitrary Python in the server process |
| Full stack traces in responses | Information disclosure — reveals file paths, variable values, library versions |
| Auto-reloader | Low risk (watches filesystem) |

**How the Werkzeug debugger attack works:**

1. Attacker triggers an error (e.g., requests a URL that causes an exception)
2. Browser shows the interactive traceback with the debugger console
3. Console prompts for a PIN (displayed in terminal output)
4. If the PIN is guessed or leaked (it's derived from machine-id + username + module path — all potentially predictable), attacker gets a full Python REPL in the server process

**Interview talking point:** "In production I'd ensure `FLASK_ENV=production` or simply not set it at all — Flask defaults to production mode since 2.3. The Werkzeug debugger is effectively an intentional backdoor for development."

---

### 5. No Input Validation on Query Parameters

**File:** `app.py`
**Severity:** Low (currently safe due to server-side filtering only)
**OWASP:** A03 (Injection — potential)

**What's happening:**

```python
query = request.args.get('query')
```

The `query` value goes directly into a `filter()` lambda — no length limit, no type check, no format validation. Currently safe because:

- It's only used in a Python `in` comparison (not regex, not SQL, not shell)
- Jinja2 auto-escapes output (prevents XSS)
- `requests` URL-encodes params (prevents injection into API URLs)

**Why mention it anyway:** This is "safe by accident." If the code evolves (e.g., someone adds `re.search(query, name)` for "fuzzy" matching), the lack of validation becomes exploitable. Defensive programming means validating at the boundary regardless of current usage.

**The defense-in-depth approach:**

```python
# 1. Limit length (prevents memory abuse)
query = request.args.get('query', '')[:200]

# 2. Strip control characters (prevents log injection)
query = query.strip()

# 3. If using regex later, escape it
import re
pattern = re.escape(query)  # Treats all special chars as literal
```

---

### 6. Unsafe Deep Nested Access in Template (Application Crash)

**File:** `templates/listings.html`
**Severity:** Medium (availability impact)
**OWASP:** A04 (Insecure Design)

**What's happening:**

```jinja
{{ listing['photos'][0]['_links']['thumbnail']['href'] }}
```

**The chain of assumptions that must ALL be true:**

1. `listing` has a `'photos'` key
2. `listing['photos']` is a non-empty list
3. `listing['photos'][0]` has a `'_links'` key
4. `listing['photos'][0]['_links']` has a `'thumbnail'` key
5. `listing['photos'][0]['_links']['thumbnail']` has an `'href'` key

If ANY of these fail → `KeyError` or `IndexError` → Flask 500.

**Why this is a security issue:** An attacker (or just an API change) that returns a listing without photos causes the entire page to crash — not just one listing card. This is a **Denial of Service via malformed data**. It also means a single bad listing poisons the entire listings page for all users.

**Fix options:**

```jinja
{# Option 1: Jinja2 conditional #}
{% set photos = listing.get('photos', []) %}
{% if photos %}
  <img src="{{ photos[0]['_links']['thumbnail']['href'] }}" />
{% endif %}
```

```python
# Option 2: Handle in Python before passing to template
def get_thumbnail(listing):
    try:
        return listing['photos'][0]['_links']['thumbnail']['href']
    except (KeyError, IndexError):
        return '/static/placeholder.png'
```

---

### 7. No CSRF Protection

**File:** `templates/categories.html`
**Severity:** Low (GET forms are safe; becomes relevant if POST forms are added)
**OWASP:** A01 (Broken Access Control)

**What CSRF is:** A malicious site includes a form/request that targets your app. If the user is authenticated on your app, their browser automatically sends cookies — the request executes as if the user initiated it.

**Why it's low risk here:** The only form uses `method="get"`, which by HTTP semantics is idempotent (no side effects). GET requests should never modify state.

**When it becomes relevant:** The moment any scenario adds a POST route (e.g., "add to cart," "save a listing"), CSRF protection is mandatory.

**Fix (if adding POST routes):**

```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
```

```jinja
<form method="post">
  {{ csrf_token() }}
  ...
</form>
```

---

### 8. No Content Security Policy Headers

**Severity:** Low
**OWASP:** A05 (Security Misconfiguration)

**What CSP does:** Content Security Policy is an HTTP response header that tells the browser which sources of content (scripts, styles, images, etc.) are allowed. If an attacker manages to inject a `<script>` tag, CSP blocks it from executing because the source isn't in the allowlist.

**Current state:** No CSP headers are set. The app loads Bootstrap from a CDN (with integrity hash, which is good), but there's no policy preventing injection of arbitrary scripts if XSS is somehow achieved.

**What a reasonable CSP would look like for this app:**

```python
@app.after_request
def set_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' https://stackpath.bootstrapcdn.com; "
        "script-src 'self'; "
        "img-src 'self' https://*.reverb.com https://images.reverb.com; "
    )
    return response
```

**Interview mention:** "I'd add a CSP header — it's a second layer of XSS defense beyond auto-escaping."

---

### 9. CDN Dependency Without Fallback

**File:** `templates/base.html`
**Severity:** Low (availability)

**What's happening:** Bootstrap loads from `stackpath.bootstrapcdn.com`. The SRI (Subresource Integrity) hash ensures no one has tampered with the file, but if the CDN is down, blocked by a corporate firewall, or DNS fails, the entire UI renders unstyled.

**What SRI provides:**

```html
<link rel="stylesheet" href="https://cdn.example.com/bootstrap.css"
      integrity="sha384-HASH..." crossorigin="anonymous">
```

- `integrity` — browser computes a SHA-384 hash of the downloaded file and compares it. If tampered, the file is rejected.
- `crossorigin="anonymous"` — required for SRI to work on cross-origin resources.

**What SRI does NOT provide:** Availability. If the CDN is unreachable, the stylesheet simply isn't loaded.

---

## Security Considerations Per Scenario

### Scenario 1: Listing Detail Page

| Risk | Detail | Mitigation |
| -- | -- | -- |
| **Path traversal in listing ID** | Route is `/listings/<listing_id>` — if passed to file system operations, it's dangerous | Only used in URL construction to Reverb API — safe, but validate as alphanumeric |
| **SSRF (Server-Side Request Forgery)** | `listing_id` is interpolated into the API URL: `f'/listings/{listing_id}'` | If user controls the path and base_uri has no path prefix validation, they could craft `../../admin`. Reverb's API would reject it, but validate anyway |
| **XSS via listing content** | Listing `description` may contain HTML/markdown | Jinja2 auto-escapes by default — safe unless you use `\| safe` filter |

**Best practice to mention:**

```python
@app.route('/listings/<listing_id>')
def listing_detail(listing_id):
    # Validate ID format before sending to external API
    if not listing_id.isalnum() and '-' not in listing_id:
        abort(400)
    ...
```

---

### Scenario 2: Search / Filter Listings

| Risk | Detail | Mitigation |
| -- | -- | -- |
| **Query injection into external API** | `query` param forwarded to Reverb API as `?query=USER_INPUT` | `requests` URL-encodes params automatically — safe |
| **ReDoS (Regex Denial of Service)** | If you implement filtering with `re.search(query, ...)` | User-supplied regex could be catastrophic. Use `re.escape()` or stick with `in` operator |
| **Response size amplification** | No `per_page` limit on search results | Always cap `per_page` server-side |
| **Reflected XSS** | If you echo the query back in the template: `You searched for: {{ query }}` | Jinja2 auto-escapes — safe. But never use `\| safe` on user input |

**Best practice to mention:**

```python
# Cap query length to prevent abuse
query = request.args.get('query', '')[:200]
```

---

### Scenario 3: Pagination

| Risk | Detail | Mitigation |
| -- | -- | -- |
| **Integer overflow / negative page** | `?page=-1` or `?page=99999999` | Validate: `page = max(1, min(int(page), total_pages))` |
| **Type coercion error** | `?page=abc` → `int('abc')` → `ValueError` → 500 | Use `request.args.get('page', 1, type=int)` — Flask returns default on parse failure |
| **Enumeration / scraping** | Unbounded pagination allows scraping all listings | Rate limiting (not in scope for interview, but worth mentioning) |

**Best practice to mention:**

```python
# Flask's type parameter handles invalid values gracefully
page = request.args.get('page', 1, type=int)
page = max(1, page)  # Never allow page < 1
```

---

### Scenario 4: Category → Listings Navigation

| Risk | Detail | Mitigation |
| -- | -- | -- |
| **Open redirect** | If category slug is used to construct a redirect URL | Don't redirect to user-supplied paths; use `url_for()` |
| **Injection via category slug** | `?category=<script>alert(1)</script>` passed to API | `requests` encodes it; Jinja2 escapes display — safe on both sides |
| **UUID validation** | If using `category_uuid` param | Validate format: `uuid.UUID(value)` to reject garbage |

---

### Scenario 5: Error Handling

| Risk | Detail | Mitigation |
| -- | -- | -- |
| **Information disclosure in error messages** | Showing raw exception: `"API returned 500: Internal error at reverb.com"` | Never expose internal API details to end users |
| **Stack trace exposure** | Flask debug mode shows full traceback | Ensure `FLASK_DEBUG=0` in production |
| **Timing attacks via error paths** | Different response times for "not found" vs "error" | Not relevant here, but worth knowing |
| **Retry storms** | Aggressive retries on failure DDoS the upstream API | Use exponential backoff with jitter |

**Best practice to mention:**

```python
@app.errorhandler(500)
def internal_error(e):
    # Log the real error server-side
    app.logger.error(f"Internal error: {e}")
    # Show generic message to user
    return render_template('error.html', message="Something went wrong."), 500
```

---

### Scenario 6: Price Display + Sort

| Risk | Detail | Mitigation |
| -- | -- | -- |
| **Sort parameter injection** | `?sort=; DROP TABLE` — if sort is passed to DB | No DB here, but validate against allowlist: `{'price_asc', 'price_desc'}` |
| **Float comparison issues** | `"amount": "1200.00"` is a string — must convert safely | Use `Decimal` for money, not `float` |
| **Currency confusion** | Displaying amount without currency code | Always show currency: `$1,200 USD` |
| **Locale-dependent parsing** | `"1.200,00"` vs `"1,200.00"` | Use the API's `display` field (already formatted) rather than formatting yourself |

**Best practice to mention:**

```python
VALID_SORTS = {'price_asc', 'price_desc', 'newest'}

sort = request.args.get('sort', 'newest')
if sort not in VALID_SORTS:
    sort = 'newest'  # Default, don't error
```

---

## General Security Principles to Demonstrate in the Interview

### The "mention casually" list (shows security awareness without over-engineering)

1. **"I'd add a timeout to this request"** — shows awareness of resource exhaustion (DoS)
2. **"Jinja2 auto-escapes, so XSS is handled here"** — shows you know WHY it's safe, not just that it is
3. **"I'd validate this parameter against an allowlist"** — shows input validation thinking (defense in depth)
4. **"In production, debug mode would be off"** — shows deployment awareness (misconfiguration)
5. **"I'll use Flask's `type=int` to handle malformed params"** — shows defensive parsing (fail safely)
6. **"I'm using the `params` dict rather than string formatting for the URL"** — shows awareness of injection via URL construction
7. **"I'll log the error server-side but show a generic message to the user"** — shows info disclosure awareness

### How to phrase security observations (sound natural, not paranoid)

**Do say:**

- "I notice there's no timeout on this request — I'll add one since a hung connection would block the worker"
- "This is safe because Jinja2 auto-escapes, but if we ever needed raw HTML we'd want to sanitize it first"
- "I'll validate this against a set of known values rather than passing it through unchecked"

**Don't say:**

- "This is a critical vulnerability that could allow..."
- "An attacker could exploit this by..."
- "We need to implement a comprehensive security framework..."

The goal is to sound like an engineer who writes secure code by default — not a security auditor doing a pentest.

### What NOT to do (over-engineering signals)

- Don't add a full authentication system unless asked
- Don't add rate limiting code (just mention it)
- Don't add CSP headers in code (just mention you'd want them)
- Don't build input sanitization beyond what the scenario needs
- Don't add logging infrastructure (just add the right `app.logger.error()` calls)
- Don't implement retry logic unless the scenario specifically asks for resilience

---

## OWASP Top 10 Mapping (2021)

The OWASP Top 10 is the industry-standard classification of the most critical web application security risks. Here's how each category maps to this specific codebase:

| # | OWASP Category | Description | Relevant? | Where in this codebase |
| -- | -- | -- | -- | -- |
| A01 | Broken Access Control | Users act outside intended permissions | No (no auth) | Would matter if adding favorites, cart, etc. |
| A02 | Cryptographic Failures | Sensitive data exposure via weak/missing crypto | No | No secrets stored, no user data, no sessions with sensitive content |
| A03 | Injection | Hostile data sent to an interpreter | Low risk | Query params → external API (URL-encoded by `requests` lib) |
| A04 | Insecure Design | Missing/ineffective security controls by design | **Yes** | No timeout, no error handling, mutable default, no input validation |
| A05 | Security Misconfiguration | Insecure default configs, verbose errors | **Yes** | `FLASK_ENV=development` exposes debugger + stack traces, no CSP |
| A06 | Vulnerable/Outdated Components | Using known-vulnerable dependencies | **Yes** | Python 3.8 (EOL Oct 2024), requests 2.25.1, urllib3 1.x |
| A07 | Auth Failures | Broken authentication/session management | No | No auth system present |
| A08 | Software/Data Integrity Failures | Assumptions about software updates, CI/CD, data without verification | Low | CDN with SRI hash (good practice) |
| A09 | Security Logging/Monitoring Failures | No audit trail for security events | **Yes** | No logging of API errors, no request logging beyond Flask's access log |
| A10 | SSRF | Server makes requests to unintended destinations | Low | User input in URL path (`/listings/{id}`) — exploitable if not validated |

---

## Quick Reference: Secure Patterns for Each Layer

```python
# reverb_client.py — defensive
def _get(self, path, params=None):
    params = params or {}
    try:
        response = requests.get(
            self._base_uri + path,
            headers=self.HEADERS,
            params=params,
            timeout=(3.05, 10)
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise ApiError("Request timed out")
    except requests.exceptions.HTTPError as e:
        raise ApiError(f"API error: {e.response.status_code}")
    except ValueError:
        raise ApiError("Invalid response from API")

# app.py — parameter validation
page = request.args.get('page', 1, type=int)
page = max(1, page)

query = request.args.get('query', '')[:200]

sort = request.args.get('sort', 'newest')
if sort not in VALID_SORTS:
    sort = 'newest'

# templates — safe defaults
{{ listing.get('price', {}).get('display', 'Price not available') }}
```

---

## Scenario Security Checklists — What to Highlight and Look For

### Scenario 1: Listing Detail Page — Security Checklist

**Primary concern:** SSRF via path injection in listing ID

| Step | What to look for | What to say |
| -- | -- | -- |
| Define route | Is the URL param typed? (`<int:listing_id>` vs `<listing_id>`) | "I'll use a converter or validate the format" |
| Build API URL | Is the ID interpolated raw into a path? | "I'll validate this is alphanumeric before using it in the URL" |
| Render detail | Does the template access deeply nested fields? | "I'll add safe access patterns for optional fields like description" |
| Display description | Is `\| safe` used to render HTML content? | "I won't use `\| safe` — auto-escaping protects against XSS from API data" |

**One-liner to drop naturally:** "I'll validate the listing ID format before hitting the API — even though Reverb would reject garbage, I don't want to forward arbitrary paths."

---

### Scenario 2: Search / Filter Listings — Security Checklist

**Primary concern:** Input handling (ReDoS, response amplification)

| Step | What to look for | What to say |
| -- | -- | -- |
| Read query param | Is there a length limit? | "I'll cap this at 200 chars to prevent abuse" |
| Filter implementation | Are you using `re.search()` with user input? | "I'll use `in` operator — regex on user input risks ReDoS" |
| Echo query in template | Does the search term appear in the page? | "Jinja2 auto-escapes, so reflected XSS isn't possible here" |
| Forward to API | Is the query URL-encoded? | "requests handles encoding automatically via the `params` dict" |
| Response rendering | What if API returns 1000 results? | "I'll enforce per_page server-side as a max, not just a default" |

**One-liner to drop naturally:** "I'm using the `in` operator rather than regex here — user-supplied patterns could cause catastrophic backtracking."

---

### Scenario 3: Pagination — Security Checklist

**Primary concern:** Type coercion and integer boundary validation

| Step | What to look for | What to say |
| -- | -- | -- |
| Read page param | What happens with `?page=abc`? | "Flask's `type=int` returns the default on parse failure — no crash" |
| Validate range | What about `?page=-1` or `?page=0`? | "I'll clamp to `max(1, page)` — negative pages shouldn't reach the API" |
| Build pagination links | Do links use `url_for()` or string concatenation? | "I'll use `url_for` to avoid URL injection in pagination links" |
| Display total pages | Is API metadata trusted? | "I'll cap total_pages to a sane max in case the API returns garbage" |

**One-liner to drop naturally:** "I'll use Flask's built-in type coercion for the page parameter — it gracefully handles non-integer input without crashing."

---

### Scenario 4: Category → Listings Navigation — Security Checklist

**Primary concern:** Open redirect and parameter injection

| Step | What to look for | What to say |
| -- | -- | -- |
| Category link construction | Is the slug/UUID from API data used raw in href? | "The slug comes from our API call, not user input, so it's trusted — but I'll still escape it" |
| Category param forwarding | Is `?category=X` passed directly to external API? | "requests URL-encodes params, so injection into the API URL isn't possible" |
| Display category name | Could a category name contain HTML? | "Auto-escaping handles this — even if a category is named `<script>`, it renders as text" |
| Redirect patterns | Are you redirecting based on user input? | "I'll use `url_for()` instead of constructing redirect URLs from params" |

**One-liner to drop naturally:** "I'm using `url_for` with the category as a query param rather than building URLs by hand — avoids any chance of open redirect."

---

### Scenario 5: Error Handling — Security Checklist

**Primary concern:** Information disclosure and retry storms

| Step | What to look for | What to say |
| -- | -- | -- |
| Error messages | Does the user see the raw exception or API details? | "I'll log the real error server-side and show a generic message to users" |
| Stack traces | Is debug mode on? | "In production, Flask shows a generic 500 page — no stack traces leak" |
| Retry logic | How aggressive are retries? | "I'd use exponential backoff with jitter to avoid thundering herd" |
| Timeout values | Is there a timeout? | "I'll add `timeout=(3, 10)` — connect and read timeouts separately" |
| Logging | Are you logging sensitive data? | "I'll log the status code and path, never request/response bodies" |

**One-liner to drop naturally:** "I'll make sure error messages shown to users are generic — I don't want to leak internal API structure or status codes."

---

### Scenario 6: Price Display + Sort — Security Checklist

**Primary concern:** Allowlist validation for sort params, safe numeric handling

| Step | What to look for | What to say |
| -- | -- | -- |
| Sort param | Is it validated against an allowlist? | "I'll check against a set of valid values — anything else gets the default" |
| Price parsing | Are you using `float()` for money? | "I'd use `Decimal` to avoid floating-point precision issues with currency" |
| Price display | Are you formatting the price yourself or using API's `display` field? | "I'll use the API's pre-formatted `display` string — avoids locale issues" |
| Sort implementation | Is `sorted()` using a key with potential `None` values? | "I'll provide a default for missing prices so `sorted()` doesn't crash on `None`" |
| Template rendering | What if `price` key is missing from a listing? | "I'll use `.get()` with a fallback — not every listing may have a price" |

**One-liner to drop naturally:** "I'm validating the sort parameter against an allowlist — even without a database, it's good practice to never pass arbitrary user input into ordering logic."

---

## Security Mental Model for the Interview

### The 30-second security scan (do this for EVERY scenario)

```plaintext
1. INPUT  → What user-controlled data enters this code path?
2. FLOW   → Where does that data travel? (URL, API call, template, log)
3. OUTPUT → Is the output encoded/escaped for its context?
4. FAIL   → What happens when the external dependency fails?
5. TRUST  → Am I trusting data that could be manipulated?
```

### When to speak up vs. when to just code it

| Situation | Action |
| -- | -- |
| You notice an existing vuln in the base code | Mention it verbally: "I notice there's no timeout here — I'll add one" |
| You're about to add something that could be insecure | Say why you're doing it the safe way: "I'll validate against an allowlist" |
| You see a theoretical risk that's not exploitable | Brief mention, don't fix: "In theory this could be an issue if we added auth, but it's fine for now" |
| You'd add something in production but it's overkill here | Name it: "In production I'd add rate limiting and a circuit breaker" |

### The hierarchy of things interviewers care about (most to least)

1. **You don't introduce new vulnerabilities** — basic competence
2. **You notice existing issues and mention them** — awareness
3. **You explain WHY something is safe** — understanding (e.g., "Jinja2 auto-escapes, so this is safe")
4. **You know what you'd add in production** — maturity (timeout, retries, CSP, logging)
5. **You can name the specific attack** — expertise (SSRF, ReDoS, slowloris)

---

## Glossary: Flask/Python Security Patterns Referenced in This Document

### `response.raise_for_status()`

A `requests` library method that checks the HTTP status code and raises `requests.exceptions.HTTPError` if it's 4xx or 5xx. Without this call, non-200 responses are silently treated as successful.

```python
response = requests.get(url)
response.raise_for_status()  # Does nothing on 200; raises on 404, 500, etc.
data = response.json()       # Only reached on success
```

### `re.escape(pattern)`

Escapes all regex metacharacters in a string, making it safe to use as a literal pattern. Converts `user.*input` to `user\.\*input` so it matches the literal text.

```python
import re
user_input = "guitars (acoustic)"
safe_pattern = re.escape(user_input)  # "guitars \\(acoustic\\)"
re.search(safe_pattern, text)         # Matches literal text, not regex
```

### `abort(status_code)`

Flask function that immediately halts request processing and returns an HTTP error response. Used for input validation failures.

```python
from flask import abort

@app.route('/listings/<listing_id>')
def listing_detail(listing_id):
    if not listing_id.isalnum():
        abort(400)  # Returns "400 Bad Request" immediately
    ...
```

### `url_for(endpoint, **values)`

Flask function that generates URLs by endpoint name rather than hardcoding paths. Security benefit: prevents URL injection since Flask controls the URL format.

```python
from flask import url_for

# In Python:
url_for('listings', category='guitars')  # → "/listings?category=guitars"

# In Jinja2:
# <a href="{{ url_for('listings', category=cat['slug']) }}">
```

**Why it's more secure than string concatenation:** `url_for` properly encodes parameter values. Manual string building like `f"/listings?category={slug}"` doesn't encode special characters.

### `request.args.get(key, default, type=int)`

Flask's safe way to read query parameters with automatic type coercion. If `type=int` is specified and the value can't be parsed, it returns `default` instead of raising an exception.

```python
# ?page=abc → returns 1 (default), no crash
page = request.args.get('page', 1, type=int)

# Without type=int:
# page = int(request.args.get('page', '1'))  → ValueError on "abc"!
```

### `@app.after_request`

Flask decorator that runs a function after every request, before the response is sent to the client. Used to add security headers to all responses.

```python
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response  # Must return the response object
```

### `@app.errorhandler(code)`

Flask decorator that registers a custom handler for a specific HTTP error code or exception class. Used to show user-friendly error pages without leaking internal details.

```python
@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Server error: {error}")  # Log real error
    return render_template('error.html',
                           message="Something went wrong."), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html',
                           message="Page not found."), 404
```

### `flask-wtf` / `CSRFProtect`

A Flask extension that adds CSRF (Cross-Site Request Forgery) protection. It works by:

1. Generating a unique token per session
2. Embedding it as a hidden field in every form
3. Validating the token on form submission — rejecting requests without a valid token

```python
# Setup (app.py):
from flask_wtf.csrf import CSRFProtect
app.config['SECRET_KEY'] = 'your-secret-key'  # Required for token generation
csrf = CSRFProtect(app)

# Template:
# <form method="post">
#   <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
#   ...
# </form>
```

**Why it works:** A malicious site can make the user's browser submit a form, but it can't read the CSRF token from your site (same-origin policy). So the forged request arrives without the token and gets rejected.

### `Decimal` vs. `float` for Money

Floating-point numbers (`float`) use binary representation that can't exactly represent most decimal fractions. This causes subtle rounding errors.

```python
>>> 0.1 + 0.2
0.30000000000000004  # NOT 0.3!

>>> from decimal import Decimal
>>> Decimal('0.1') + Decimal('0.2')
Decimal('0.3')  # Exact
```

**For money:** `$10.00 + $10.00 + $10.00` should equal `$30.00`, not `$29.999999999999996`. Always use `Decimal` (or integer cents) for currency arithmetic.

```python
from decimal import Decimal

price = Decimal(listing['price']['amount'])  # "1200.00" → Decimal('1200.00')
sorted_listings = sorted(listings, key=lambda l: Decimal(l['price']['amount']))
```

### `requests.Session()` with Retry

A `requests.Session` reuses TCP connections (connection pooling) and can be configured with automatic retry policies via `HTTPAdapter`.

```python
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = Session()
retry_strategy = Retry(
    total=3,                          # Max retry attempts
    backoff_factor=0.5,               # Wait 0.5s, 1s, 2s between retries
    status_forcelist=[500, 502, 503], # Only retry on these status codes
    allowed_methods=["GET"],          # Only retry idempotent methods
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)

# Now all requests through this session auto-retry on failure:
response = session.get("https://api.reverb.com/api/listings/all", timeout=5)
```

**Security note on retries:**

- Only retry idempotent methods (GET, HEAD) — retrying a POST could duplicate side effects
- Always use backoff — immediate retries make outages worse
- Set a reasonable `total` — infinite retries = infinite resource consumption

### Jinja2 `| safe` Filter (and Why to Avoid It)

Jinja2 auto-escapes all variables rendered with `{{ }}`. The `| safe` filter disables this escaping for a specific value.

```jinja
{{ user_name }}          → &lt;script&gt;alert(1)&lt;/script&gt;  (SAFE - escaped)
{{ user_name | safe }}   → <script>alert(1)</script>              (DANGEROUS - raw HTML)
```

**When `| safe` is acceptable:**

- Content you generated yourself (never from user input or external API)
- Pre-sanitized HTML (e.g., run through `bleach` library)
- Static content embedded in code

**When `| safe` is dangerous:**

- ANY data from users, APIs, databases, or URL parameters
- Listing descriptions from Reverb (could contain HTML)
- Category names (could contain `<script>` tags)

### `| urlencode` Filter

Jinja2 filter that percent-encodes a value for safe use in URLs. Converts spaces to `%20`, special chars to their percent-encoded equivalents.

```jinja
<a href="/search?q={{ query | urlencode }}">Search again</a>
{# "electric guitars" → "electric%20guitars" #}
```

**When to use:** Anytime you embed a variable in an `href` or `src` attribute as a query parameter. Note: `url_for()` handles this automatically — `| urlencode` is for manually constructed URLs only.
