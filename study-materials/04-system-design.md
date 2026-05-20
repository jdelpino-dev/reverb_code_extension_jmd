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
