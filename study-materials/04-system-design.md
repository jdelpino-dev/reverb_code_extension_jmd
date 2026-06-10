# Chapter 4: System Design

## Framework for System Design Discussions

### The DEBASE Method

1. **Define** — Clarify requirements, scope, constraints
2. **Estimate** — Traffic, storage, latency budgets
3. **Build** — High-level architecture (boxes and arrows)
4. **API** — Define the interface contracts
5. **Scale** — Identify bottlenecks, add redundancy
6. **Extend** — Monitoring, failure modes, future features

### For a Mid-Level Interview

Focus on **Build** and **API** — clear architecture and well-thought API design.
Show awareness of where data lives, how components communicate, and what happens
when things fail.

---

## Architecture Patterns

### Monolith → Service-Oriented (Reverb's Stack)

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  React App  │────▶│  GraphQL GW  │────▶│  Rails API  │
│  (Frontend) │     │   (Gateway)  │     │ (Monolith)  │
└─────────────┘     └──────────────┘     └─────────────┘
                                               │
                            ┌──────────────────┼─────────────┐
                            ▼                  ▼             ▼
                    ┌──────────────┐  ┌────────────┐  ┌──────────┐
                    │  PostgreSQL  │  │   Redis    │  │ Sidekiq  │
                    │  (Primary)   │  │  (Cache)   │  │  (Jobs)  │
                    └──────────────┘  └────────────┘  └──────────┘
```

### Event-Driven Architecture

```text
┌───────────┐       ┌─────────────┐       ┌────────────────┐
│  Service  │──────▶│  Event Bus  │──────▶│  Consumer A    │
│           │       │  (Kafka/SQS)│       │  (Notifications)│
└───────────┘       └─────────────┘       ├────────────────┤
                          │               │  Consumer B    │
                          └──────────────▶│  (Analytics)   │
                                          └────────────────┘
```

---

## Simple Service Design Examples

### URL Shortener (Tiny-URL)

**Requirements:** Create short URLs, redirect to original, track clicks, expire after N days.

**Architecture:**

```text
┌──────────┐     ┌──────────────┐     ┌────────────┐
│  Client  │────▶│  API Server  │────▶│ PostgreSQL │
└──────────┘     └──────────────┘     └────────────┘
                        │                     │
                        ▼                     │
                 ┌────────────┐               │
                 │   Redis    │◀──────────────┘
                 │  (cache)   │
                 └────────────┘
```

**API:**

```text
POST /urls     { original_url: "..." }  → { short_code: "abc123", short_url: "..." }
GET  /:code    → 301 Redirect to original_url
GET  /:code/stats → { clicks: 1234, created_at: "...", expires_at: "..." }
```

**Key decisions:**

- Short code generation: Base62 encoding of auto-increment ID (simple) vs. random (no enumeration)
- Caching: Redis for hot URLs (99% of reads hit cache)
- Expiration: TTL on Redis + background job to clean DB

### Rate Limiter

**Token bucket in Redis:**

```python
import redis
import time

def check_rate_limit(user_id, max_requests=100, window_seconds=3600):
    r = redis.Redis()
    key = f"rate:{user_id}"
    current = r.get(key)

    if current and int(current) >= max_requests:
        return False  # Rate limited

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    pipe.execute()
    return True
```

---

## Designing a Notification System

### Requirements (Music Marketplace Context)

- Multi-channel: email, push, in-app
- User preferences: per-channel enable/disable + frequency
- Rate limiting: max N per channel per hour
- Deduplication: don't send same notification twice
- Priority: order updates > price drops > marketing

### Architecture

```text
┌──────────┐    ┌────────────┐    ┌─────────────┐    ┌──────────────┐
│  Intake  │───▶│ Preference │───▶│ Rate Limiter│───▶│ Deduplicator │
│  (API)   │    │   Filter   │    │ (Redis)     │    │ (Redis SET)  │
└──────────┘    └────────────┘    └─────────────┘    └──────┬───────┘
                                                            │
                                                   ┌────────▼────────┐
                                                   │ Priority Queue  │
                                                   │ (Redis Sorted)  │
                                                   └────────┬────────┘
                                                            │
                                          ┌─────────────────┼──────────┐
                                          ▼                 ▼          ▼
                                   ┌──────────┐     ┌────────┐  ┌────────┐
                                   │  Email   │     │  Push  │  │ In-App │
                                   │(SendGrid)│     │(FCM)   │  │(WS)    │
                                   └──────────┘     └────────┘  └────────┘
```

### Data Model

```sql
CREATE TABLE notification_preferences (
    user_id BIGINT PRIMARY KEY,
    email_enabled BOOLEAN DEFAULT true,
    email_frequency VARCHAR DEFAULT 'immediate',
    push_enabled BOOLEAN DEFAULT true,
    in_app_enabled BOOLEAN DEFAULT true
);

CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    channel VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    content_hash VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'pending',
    sent_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_notifications_dedup ON notifications (user_id, content_hash, created_at);
```

### Deduplication

```python
import hashlib
import redis

def already_sent(user_id, content):
    r = redis.Redis()
    hash_key = hashlib.sha256(f"{user_id}:{content}".encode()).hexdigest()
    key = f"dedup:{hash_key}"
    # SET NX: only sets if key doesn't exist; returns True if set (not sent before)
    return not r.set(key, 1, ex=86400, nx=True)  # 24h dedup window
```

---

## Caching Strategy

### When to Cache (This Codebase)

| Endpoint | Cache? | Why |
| --- | --- | --- |
| Categories | Yes (long TTL) | Rarely change, same for all users |
| Listings | Maybe (short TTL) | Change frequently, but same query = same results briefly |
| Single listing | Yes (medium TTL) | Changes infrequently, frequently viewed |

### Simple Python Caching

```python
from functools import lru_cache
import time

# In-memory cache (simple, per-process)
@lru_cache(maxsize=1)
def _load_categories():
    return ReverbClient().categories()

# With TTL (manual)
_cache = {}

def _load_categories_cached(ttl=300):
    if 'categories' in _cache:
        data, timestamp = _cache['categories']
        if time.time() - timestamp < ttl:
            return data
    data = ReverbClient().categories()
    _cache['categories'] = (data, time.time())
    return data
```

---

## Scaling Considerations

### Horizontal Scaling

```text
┌─────────────┐
│ Load Balancer│
└──────┬──────┘
       │
  ┌────┼────┐
  ▼    ▼    ▼
┌───┐┌───┐┌───┐
│W1 ││W2 ││W3 │  ← Gunicorn workers (stateless)
└───┘└───┘└───┘
```

Flask with Gunicorn: multiple workers, each handles requests independently.
Works because the app is stateless — no session data, no in-memory state.

### Database Patterns

- **Read replicas** — for read-heavy workloads
- **Connection pooling** — prevent connection exhaustion
- **Indexing** — B-tree for exact match, GIN for full-text search

### Resilience Patterns

| Pattern | What it does | When to use |
| --- | --- | --- |
| Timeout | Fail fast on slow dependencies | Always (this codebase is missing it) |
| Retry with backoff | Handle transient failures | Network calls, queue jobs |
| Circuit breaker | Stop calling a failing service | After N consecutive failures |
| Bulkhead | Isolate failure domains | Multiple dependencies |
| Fallback/cache | Serve stale data when source is down | Read-heavy endpoints |

---

## Interview Framing

When asked about system design in the context of this codebase:

> "This app is a thin read-only client for the Reverb API. If I were designing
> it for production scale, I'd add: a caching layer (Redis) for categories since
> they rarely change, a timeout + circuit breaker for the API calls, and
> pagination to avoid loading unbounded data. For write operations, I'd add a
> queue (Celery/Redis) for async processing."

### How This App Relates to Reverb's Architecture

> "This interview app consumes the same public API that Reverb's React frontend
> consumes through their GraphQL gateway. In their real architecture, the Gateway
> handles caching, auth, and rate limiting — things this simple Flask app skips
> because it's read-only and unauthenticated."

---

## New Codebase Addendum (June 2026)

The system-design framework above is unchanged. What changes is the set of
tools at your disposal when answering "how would you extend this?" — the new
codebase opens doors that the old one didn't.

### New levers for system-design discussions

| Concern | New codebase tool | What it unlocks |
|---|---|---|
| Async I/O | `httpx` (already in use) | Swap `httpx.get` for `httpx.AsyncClient` to fan out parallel calls (e.g., dashboard pulling categories + listings + featured items concurrently) |
| Partial rendering | HTMX (already loaded) | Server-driven progressive enhancement — search results, pagination, filter panels update without full reloads or a JS framework |
| Lazy loading | HTMX `hx-trigger="toggle"` + `<details>` | Show-more / show-on-demand UX with zero JS |
| Declarative interactivity | `data-*` + `aria-*` attributes | Loading states, validation, tooltips, disclosure — all without a JS framework |
| Service-layer extension point | Currently absent | Adding a `services/` module is the natural seam for caching, pagination, and combining client calls |

### "How would you add caching?" — updated answer

The original answer (`@lru_cache` on `_load_categories`) doesn't apply since the
service helper no longer exists. Two clean options for the new codebase:

1. **Decorate the client function directly** — `@lru_cache` on `reverb.categories()`.
   Simple, but ties caching policy to the IO function.
2. **Reintroduce a service layer** for caching:

   ```python
   # app/services/categories.py
   from functools import lru_cache
   from app.clients import reverb

   @lru_cache(maxsize=1)
   def all_categories():
       return reverb.categories()
   ```

   Then routes call `categories_service.all_categories()` instead of
   `reverb.categories()`. This is the right shape for any non-trivial caching
   (TTL, per-locale keys, invalidation).

### "How would you add pagination?" — updated

The client already accepts `per_page`. To add real pagination:

1. Add `page` to `reverb.listings(per_page=10, page=1)` and pass it through.
2. Return the full response envelope (not just the `listings` key) so the route
   can read pagination metadata (`total`, `total_pages`, `current_page`).
3. Route extracts `page` from `request.args.get("page", 1, type=int)`.
4. Template renders prev/next links with `{{ url_for('listings.index', page=...) }}`.
5. If HTMX is wired up: `hx-get="/listings?page=2" hx-target="#listing-grid"` for
   in-place pagination with no full reload.

### "How would you handle dashboard composition?" — new answer

The new stack makes a parallel-fetch dashboard trivial with `httpx.AsyncClient`:

```python
import httpx, asyncio

async def dashboard_data():
    async with httpx.AsyncClient() as client:
        cats, listings = await asyncio.gather(
            client.get(f"{HOST}/api/categories/flat"),
            client.get(f"{HOST}/api/listings"),
        )
    return {"categories": cats.json()["categories"], "listings": listings.json()["listings"]}
```

With Flask 3.1, the route can be `async def` and Flask handles the event loop.
This is genuinely useful for dashboard scenarios and is a strong differentiator
vs the old `requests`-based codebase, where you'd need threads or a separate
async framework.

See [Chapter 16](16-new-codebase-stack-guide.md) for the full stack reference.
