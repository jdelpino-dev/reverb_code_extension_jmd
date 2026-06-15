# Systems Design Interview Notes (2026 Edition)

Modern Internet, Cloud, Full-Stack, and Distributed Systems Reality

A distilled set of principles, numbers, tradeoffs, and architectural patterns relevant to a modern (2026) Engineer II systems design interview like Reverb's.

**How to use this doc:** Part I is the modern "reality check" — mental models and the progressive-scaling philosophy. Part II adds classic interview fundamentals and genuinely 2026-specific topics (connection pooling, real-time, edge, serverless, AI/LLM). All numbers are approximate, intended for back-of-the-envelope reasoning rather than precision.

---

## Part I — Modern Reality & Core Principles

### 1. The Most Important Modern Shift

Classic systems design resources were written in the:

- HDD era
- Single-datacenter era
- Server-centric era

Modern systems operate in the:

- **NVMe era**
- **Cloud era**
- **CDN era**
- **Managed services era**
- **API era**

The fundamental bottlenecks have changed.

---

### 2. Modern Bottlenecks

In 2026 most web applications are **NOT** bottlenecked by:

- CPU
- RAM
- Raw storage

They **are** bottlenecked by:

- Network round trips
- Database queries
- Cache misses
- Cross-service communication
- Distributed coordination

> **Mental model: CPU is cheap. Moving data is expensive.**

---

### 3. The Modern Latency Hierarchy

Think in orders of magnitude:

| Operation           | Latency        |
|---------------------|----------------|
| L1 cache            | ~0.5 ns        |
| RAM                 | ~100 ns        |
| NVMe                | ~100 μs        |
| Redis               | ~100–1,000 μs  |
| DB query            | ~1–10 ms       |
| Service call        | ~1–20 ms       |
| Cross-region        | ~70–150 ms     |
| Intercontinental    | ~100–250 ms    |

> A single database query costs **thousands to millions** of CPU operations.

---

### 4. The Most Important Optimization

Not: *a better algorithm.*

Usually: **fewer round trips.**

**Bad:** 100 DB queries, 100 Redis calls, 100 HTTP calls.

**Good:** 1 DB query, 1 Redis lookup, 1 HTTP request.

Modern systems optimize via:

- Batching
- Aggregation
- Prefetching
- Caching
- Denormalization

---

### 5. Storage Reality

**Text is cheap. Media dominates.**

| Cheap (tiny)                          | Expensive (dominant) |
|---------------------------------------|----------------------|
| URLs, users, metadata, course records | Images, audio, video, PDFs |

**Standard pattern:** Object storage (S3 / R2 / GCS).

> Do **not** store large media in PostgreSQL.

---

### 6. Modern Image Pipeline

```plaintext
Upload original
  ↓
Store in object storage
  ↓
Queue job
  ↓
Worker creates variants
  ↓
Store variants
  ↓
Serve via CDN
```

Avoid: resizing images during the user request.

> **Compute once. Serve thousands of times.**

---

### 7. Redis Reality

Redis is fast, but:

> **Redis ≠ RAM.** A Redis lookup still involves: network + serialization + another process + kernel overhead.

Redis is useful when it avoids:

- Expensive queries
- Expensive computation
- Distributed coordination

#### Good Redis uses

- Homepage payload
- Search results
- Recommendations
- Sessions
- Rate limits
- Distributed locks

#### Bad Redis uses

- Site title
- Single config value
- Trivial tiny data

> **Cache expensive work. Not tiny values.**

---

### 8. CDN Reality

CDNs are one of the **highest ROI optimizations** available.

CDN edge handles:

- Cache lookup
- Header evaluation
- Compression
- TLS termination

…avoiding:

- Origin server hits
- Database queries
- Cross-region network traversal

> **Modern principle: push content closer to users.**

---

### 9. Compression Reality

Worth it (compresses 60–90%):

- HTML, JSON, CSS, JavaScript, Markdown, SVG

**Do not compress** (already compressed):

- JPEG, WebP, AVIF, MP4, MP3

---

### 10. Modern Database Scaling Progression

Most systems **never need sharding.**

```plaintext
Single Postgres
  ↓
Bigger Postgres
  ↓
Indexes
  ↓
Redis (cache)
  ↓
Read replicas
  ↓
Partitioning
  ↓
Sharding
```

> Many teams jump to sharding and microservices far too early.

---

## 11. When Replicas Are Enough

Usually sufficient when:

- Reads dominate writes
- Data fits on one machine
- Write throughput is manageable

Examples: CMS, marketplace, learning platform, most SaaS products.

---

## 12. When Sharding Becomes Necessary

Potential triggers:

- Writes saturate primary
- Storage exceeds one node
- Indexes become unmanageable
- Global local-write requirements
- Large tenant isolation needs

**Not triggered by:** "We reached 1M users."
Many systems with tens or hundreds of millions of users never shard.

---

### 13. Read-After-Write Consistency

Classic problem:

```plaintext
Write to primary
  ↓
Read from replica
  ↓
Replica lag → user sees stale data
```

Solutions:

- Read from primary briefly after write
- Write-through cache
- Session affinity

Usually implemented through **business logic**, not exotic infrastructure.

---

### 14. Sessions in 2026

#### Client-side sessions

Examples: Rails cookie store, Flask signed cookies.

- Simple, stateless, no Redis required.

#### Server-side sessions

Examples: Redis, Postgres, Memcached.

- Large session state, shared state, instant revocation.

---

### 15. High Availability Reality

Most SaaS products target **99.9% to 99.99%**, not 99.999%.

| Availability | Downtime/year |
|-------------|---------------|
| 99%         | 3.65 days     |
| 99.9%       | 8.77 hours    |
| 99.99%      | 52.6 minutes  |
| 99.999%     | 5.26 minutes  |

---

### 16. Multi-AZ vs Multi-Region

#### Multi-AZ

- One region, multiple datacenters.
- Protects against: datacenter failures, power failures, rack failures.

#### Multi-Region

- Multiple geographic regions (e.g., Ohio, Frankfurt, Singapore).
- Protects against: full regional failures.
- **Much harder** to implement and operate.

---

### 17. PITR (Point-In-Time Recovery)

Built from: **Backups + WAL logs.**

Allows restoring the database to any precise moment in time.

Protects against:

- Bad migrations
- Accidental deletes
- Application bugs

> **HA and PITR solve different problems.** Both are needed.

---

### 18. Modern Feed Architecture Pattern

Separate the write path from the read path:

#### Write Path

- Create post → Fanout → Notifications → Analytics
- Optimized for: durability, background processing.

#### Read Path

- Get feed
- Optimized for: cache hits, low latency.

This pattern appears across: feeds, recommendations, search, dashboards.

---

### 19. Queues and Workers

A queue is not just about background work. It is about:

- **Decoupling** services
- **Smoothing** traffic spikes
- **Scaling** independently

Queue-appropriate work:

- Email / notifications
- Analytics events
- Thumbnail generation
- Recommendations
- Search indexing

---

### 20. Modern Search Progression

```plaintext
Postgres indexes
  ↓
Postgres Full-Text Search (FTS)
  ↓
OpenSearch / Elasticsearch
```

> Don't start with OpenSearch. Add it only when requirements force it.

---

### 21. Modern Full-Stack Scaling Ladder

| Version | Added Component        |
|---------|------------------------|
| V1      | App + Postgres         |
| V2      | Indexes                |
| V3      | Redis (cache)          |
| V4      | Workers (queue)        |
| V5      | CDN                    |
| V6      | Read replicas          |
| V7      | Search service         |
| V8      | High availability (HA) |
| V9      | Multi-region           |
| V10     | Sharding               |

---

### 22. Architecture Evaluation Framework

Evaluate every design decision against:

1. **Correctness** — Does it work?
2. **Simplicity** — Can it be simpler?
3. **Latency** — Is it fast enough?
4. **Cost** — Is it cost-reasonable?
5. **Complexity** — Is the added complexity justified?

---

### 23. Common Engineer II Mistakes to Avoid

**Avoid jumping to:**

- Microservices
- Sharding
- Kafka
- Multi-region
- Kubernetes

**Before you have:**

- Measured the actual bottleneck
- Exhausted simpler options
- A real requirement driving the complexity

> **Measure first. Optimize the actual bottleneck. Add complexity only when required.**

---

### 24. Systems Design Interview Meta-Pattern

**Step 1 — Clarify requirements:** Scale? Users? QPS? Availability? Analytics? Security constraints?

**Step 2 — Estimate:** QPS, storage, growth rate, bandwidth

**Step 3 — Simple design:** App + DB + core flow only

**Step 4 — Identify bottlenecks:** DB? Cache? Network? Storage?

**Step 5 — Scale incrementally:** Cache → Workers → Replicas → CDN → HA

**Step 6 — Discuss tradeoffs:** Consistency vs. availability, Cost vs. complexity

---

## Part II — Fundamentals & 2026 Deep Dives

### 25. Back-of-the-Envelope Estimation

Interviewers expect rough numbers fast. Use round figures and powers of ten.

**Handy constants:**

- 1 day ≈ 86,400 s ≈ **10^5 s** (great for mental math)
- Therefore: **requests/day ÷ 100,000 ≈ average QPS**
- Peak QPS ≈ 2–3× average (more for spiky workloads)
- Bandwidth: 1 KB/s ≈ ~2.5 GB/month (×1,000 for MB/s → ~2.5 TB/month)

**Throughput rules of thumb:**

- Single Postgres: thousands–tens of thousands of simple queries/sec
- Read replicas multiply read capacity
- Redis: 100k+ ops/sec per instance
- Object storage (S3/R2/GCS): effectively unlimited capacity & throughput
- A single modern server: tens of thousands of concurrent connections

**Worked example — feed / learning platform:**

- 10M DAU × 10 actions/day = 100M req/day
- Avg QPS ≈ 100M ÷ 10^5 ≈ **~1,000 QPS**
- Peak ≈ 3× ≈ **~3,000 QPS**
- Read:write ≈ 100:1 → ~30 writes/s, ~3,000 reads/s
- User metadata: 10M × ~1 KB ≈ **10 GB** (trivial — fits in RAM)
- Conclusion: **one primary + replicas + cache.** No sharding. This is the norm, not the exception.

> Always estimate: QPS (avg + peak), storage, bandwidth, growth.

---

### 26. Tail Latency (p50 vs p99)

Averages lie. Design for **percentiles**.

- p50 = median; p99 = "1 in 100 requests is at least this slow."
- At scale the tail dominates UX: a page making 100 backend calls will *usually* hit its p99 on at least one of them.
- Fan-out amplifies tails — more parallel calls → higher chance one is slow.

**Mitigations:** timeouts, hedged requests, fewer dependencies per request, caching, and keeping the critical path short.

> Optimize the **tail**, not just the average.

---

### 27. Caching Patterns & Pitfalls

**Write/read strategies:**

- **Cache-aside (lazy):** app checks cache; on miss, reads DB and populates. Most common.
- **Write-through:** write cache + DB together. Fresh reads, slower writes.
- **Write-back (write-behind):** write cache, flush to DB async. Fast, risk of loss.
- **Write-around:** write DB only; cache fills on read. Avoids caching write-once data.

**Eviction:** LRU (most common), LFU, FIFO, TTL-based.

**The hard parts:**

- **Invalidation** — "There are only two hard things… cache invalidation and naming things."
- **Stampede / thundering herd** — many misses hit the DB at once on expiry. Fix with locks, request coalescing, jittered TTLs, or `stale-while-revalidate`.
- **Hit rate** is the metric that matters; a low-hit-rate cache adds latency for nothing.

---

### 28. Consistency Models

- **Strong / linearizable:** every read sees the latest write. Easy to reason about, costly across regions. (Payments, inventory, auth.)
- **Eventual:** replicas converge over time; reads may be briefly stale. Cheap, highly available. (Feeds, counts, search, analytics.)
- **Read-your-writes / monotonic reads:** practical middle grounds (see §13).

**CAP:** under a network partition, choose Consistency *or* Availability.
**PACELC:** even without a partition, there's a Latency-vs-Consistency tradeoff.

> Pick consistency **per feature**, not per system. Most apps mix both.

---

### 29. SQL vs NoSQL

**Default to a relational DB (Postgres).** It handles JSON, full-text search, geo, and very large scale.

Reach for NoSQL when a *specific* access pattern demands it:

- **Key-value** (Redis, DynamoDB): simple, massive-scale lookups.
- **Document** (MongoDB): flexible / nested schemas.
- **Wide-column** (Cassandra, Bigtable): huge write throughput, known query patterns.
- **Graph** (Neo4j): deep relationship traversal.
- **Time-series** (Timescale, InfluxDB): metrics / events.
- **Vector** (pgvector, Pinecone): embeddings / similarity search (see §37).

> "Postgres until it hurts" is a sound 2026 default.

---

### 30. Load Balancing

- **L4 (transport):** routes by IP/port — fast, protocol-agnostic.
- **L7 (application):** routes by path/header/cookie — enables routing, A/B, TLS termination.
- **Algorithms:** round-robin, least-connections, weighted, consistent-hashing (sticky).
- **Health checks** remove unhealthy nodes; **sticky sessions** pin a user to a node (avoid when possible — prefer stateless apps).

---

### 31. API Design

- **REST:** resource-oriented, cache-friendly, ubiquitous. Default choice.
- **GraphQL:** client picks fields; avoids over/under-fetching; watch for N+1 and expensive queries.
- **gRPC:** binary, fast, streaming; great service-to-service, weak in browsers.

**Essentials:**

- **Pagination:** prefer **cursor/keyset** over `OFFSET` at scale.
- **Idempotency keys** for unsafe operations that may be retried (e.g. payments).
- **Versioning** (`/v1/…`) and backward compatibility.
- Beware the **N+1 query** problem (batch / `JOIN` / dataloader).

---

### 32. Rate Limiting

- **Token bucket:** tokens refill at a rate; allows bursts. Most popular.
- **Leaky bucket:** smooths to a constant outflow.
- **Fixed window:** simple per-window counter; suffers boundary spikes.
- **Sliding window (log/counter):** smoother and more accurate.

Usually implemented in **Redis/Valkey** (atomic counters), keyed by user / IP / API-key.

---

### 33. Resilience Patterns

Distributed systems fail *partially*. Design for it:

- **Timeouts** on every network call (never wait forever).
- **Retries** with **exponential backoff + jitter** (avoid retry storms).
- **Circuit breaker:** stop calling a failing dependency; fail fast, recover gradually.
- **Idempotency:** make retried writes safe (dedupe keys).
- **Backpressure / load shedding:** reject early instead of collapsing.
- **Dead-letter queue (DLQ):** park messages that repeatedly fail.
- **Graceful degradation:** serve stale/partial data rather than a hard error.

> Delivery semantics: most queues are **at-least-once** → consumers must be **idempotent**.

---

### 34. Connection Pooling

Databases handle limited concurrent connections (Postgres: low hundreds). Each app or serverless instance opening its own connections causes **connection storms**.

- Use a pooler: **PgBouncer** (transaction pooling), in-app pools (HikariCP, etc.), or serverless data proxies.
- Critical with serverless/edge, where instances scale horizontally and multiply connections.

> Pool connections; don't let every request or instance open its own.

---

### 35. Real-Time Delivery

From cheapest to richest:

- **Short polling:** client asks repeatedly. Simple, wasteful.
- **Long polling:** server holds the request until data is ready.
- **SSE (Server-Sent Events):** one-way server→client stream over HTTP. Great for notifications and LLM token streaming.
- **WebSockets:** full-duplex persistent connection. Chat, presence, collaboration, multiplayer.

Back it with a **pub/sub** layer (Redis, NATS, Kafka) to fan out across server instances.

---

### 36. Edge & Serverless

Genuinely 2026 building blocks:

- **Edge functions** (Cloudflare Workers, Vercel / Lambda@Edge): run logic at the CDN edge — auth, redirects, personalization — close to users.
- **Serverless / FaaS:** scales to zero, pay-per-use; watch **cold starts** and per-invocation limits.
- **Serverless databases** (Neon, PlanetScale, Aurora Serverless, DynamoDB): autoscaling, but mind connection limits (→ §34) and cold starts.

**Tradeoff:** great for spiky/uneven load and ops simplicity; less ideal for sustained high throughput or long-lived connections.

---

### 37. AI / LLM Workloads

Increasingly expected in 2026 designs:

- **Embeddings + vector DB** (pgvector, Pinecone, Weaviate) for semantic search / similarity.
- **RAG (Retrieval-Augmented Generation):** retrieve relevant chunks → inject into the prompt → generate. The standard pattern for grounding LLMs on private data.
- **Inference latency** is high and variable (hundreds of ms to seconds) → **stream tokens** (SSE) and run generation **async** via queues.
- **Cost & limits:** priced per token, with provider rate limits → budget and cap aggressively.
- **Semantic caching:** cache by embedding similarity (not exact key) to cut cost and latency.
- Treat the model as a **slow, expensive, non-deterministic network dependency** → apply timeouts, retries, and fallbacks (§33).

---

### 38. Observability

You can't "measure first" (§23) without it. The three pillars:

- **Logs:** discrete events (structured, searchable).
- **Metrics:** aggregated numbers over time (rates, latencies, errors).
- **Traces:** one request's path across services (find the slow hop).

Define **SLIs** (what you measure), **SLOs** (targets), and **error budgets** (allowed failure). Alert on symptoms (latency / error rate), not noise.

---

### 39. Security Essentials

- **AuthN vs AuthZ:** *who you are* vs *what you're allowed to do*.
- **Sessions vs JWT:** server-side sessions (revocable, stateful) vs stateless JWTs (scalable, hard to revoke — keep them short-lived).
- **In transit:** TLS everywhere. **At rest:** encrypt DB, backups, and buckets.
- **Secrets:** in a secrets manager / env — never in code or logs.
- **Input:** validate and escape — prevent SQL injection (parameterized queries) and XSS.
- **Abuse:** rate-limit, require authn on writes, use least-privilege DB roles.
- Know the **OWASP Top 10** at a high level.

---

### 40. The Optimization Ladder (Order Before Sharding)

The order isn't arbitrary — **each phase fixes a different bottleneck**, so apply the one your measurement points to: multi-AZ is availability; Redis, replicas, and the CDN are read scaling; partitioning is large-table maintainability; sharding is exceeding a single primary. Introduce each only when a measured bottleneck justifies the complexity.

- **Phase 0 — Measure the bottleneck.** p99, slow-query log, cache hit rate, replica lag, connection counts (§38). Never optimize on a hunch.
- **Phase 1 — Eliminate inefficiency.** Better queries, better schema, better indexes — the cheapest wins, no new infrastructure.
- **Phase 2 — Scale up.** Vertical scaling (a bigger box) + connection pooling (§34), before adding moving parts.
- **Phase 3 — Build high availability.** Multi-AZ database and multi-AZ web tier (§16) — availability, not throughput.
- **Phase 4 — Scale the read path.** Redis (§7), read replicas (§11), CDN (§8) — where most read-heavy systems win biggest.
- **Phase 5 — Offload specialized workloads.** Analytics, search (§20), reporting — off the OLTP hot path onto purpose-built stores.
- **Phase 6 — Manage large tables.** Partitioning — range-by-time for append-only data, hash-by-key otherwise (§10).
- **Phase 7 — Scale beyond a single primary.** Sharding — only when writes or storage exceed one node (§12).
- **Phase 8 — Global scale & disaster recovery.** Multi-region (§16) and PITR (§17) — the most complex, so last.

> **Sharding is Phase 7 — a near-last resort.** Most systems ride Phases 1–6 (especially Phase 4) to tens or hundreds of millions of users without ever sharding. Reach for it only when one primary's writes or storage are genuinely exhausted — not at a user-count milestone (§12).

This is the principled, bottleneck-ordered version of the progression in §10 and the scaling ladder in §21.

---

## Part III — The Big Picture

### 41. The One-Sentence Summary

> Use cheap compute, storage, and caching to avoid expensive data movement, network round trips, and distributed coordination.

This single idea explains why we use:

- CDNs
- Redis
- Queues & workers
- Read replicas
- Materialized views
- Search indexes
- Precomputed feeds
- Precomputed recommendations
- Precomputed thumbnails
- Analytics pipelines

It is the core of how most successful web systems are designed in 2026.
