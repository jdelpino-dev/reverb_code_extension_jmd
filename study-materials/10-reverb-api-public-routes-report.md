# Reverb Public API — Public Routes Exploration Report

**Date:** 2026-05-20
**API Base URL:** `https://api.reverb.com/api`
**API Version:** 3.0
**Content Type:** `application/hal+json`

---

## Summary

This report documents a hands-on exploration of Reverb's public API surface — the set of endpoints accessible without authentication. It covers response structure, caching behavior, pagination strategies, HAL+JSON conventions, and the full catalog of publicly available routes.

### General Character of the Public Endpoints

Reverb's public endpoints form a cohesive, well-designed read surface oriented toward marketplace consumption and client-building. The API is hypermedia-driven: every response includes navigational links that encode what actions are available and where related resources live, so clients discover capabilities at runtime rather than hardcoding URL patterns. Responses are uniformly structured with consistent field naming, predictable nesting, and clear separation between scalar metadata, nested domain objects, and link affordances. The caching strategy is intentional and differentiated — stable reference data is aggressively edge-cached while volatile transactional data is always fresh. Pagination is search-oriented rather than export-oriented, with caps that protect system stability and data integrity on a live marketplace. The endpoints collectively cover the full read-side surface a client needs: taxonomy, product browsing, reference metadata (conditions, currencies, regions, carriers), editorial content, pricing intelligence, and search suggestions. Header-driven content negotiation (language, currency, shipping region) allows the same endpoints to serve localized experiences worldwide without URL proliferation.

### Key Insights at a Glance

- **Pragmatic HAL:** The API uses `_links` extensively for HATEOAS navigation but skips `_embedded` entirely, inlining related data as plain JSON properties for simpler consumption.
- **Caching is binary and intentional:** Reference data gets 24-hour CDN caching with ETag support; marketplace data is never cached.
- **Pagination caps are a feature, not a bug:** The 50-page window on search results protects infrastructure and data freshness; partition queries to reach more data.
- **The API is one unified surface:** There is no separate "public API" — the same endpoints serve anonymous reads and authenticated mutations, differentiated only by token presence and scopes.
- **Headers shape the response:** Version, language, currency, and shipping region headers materially alter what data comes back from the same URL.
- **16 endpoints work without auth:** Covering taxonomy, listings, conditions, currencies, geography, shipping, collections, pricing, editorial content, and search suggestions.
- **Link-driven design is enforced:** Clients must not construct URLs — they follow `_links` to discover actions, navigate pages, and transition between resources.

---

## 1. What is HAL+JSON?

**HAL** stands for **Hypertext Application Language**. It is a convention for defining hypermedia (links and embedded resources) in JSON responses. The formal media type is `application/hal+json`, defined in the [IETF Internet Draft](https://datatracker.ietf.org/doc/html/draft-kelly-json-hal) by Mike Kelly.

HAL adds two reserved properties to standard JSON:

- **`_links`** — Contains named link relations pointing to related resources. Each link is an object with at least an `href` property. Links act as the navigational controls of the API, allowing clients to discover actions and related resources dynamically rather than hardcoding URLs.
- **`_embedded`** — Contains named embedded resources (full sub-resource representations inlined into the response). This avoids extra round-trips by including related resources directly in the parent response.

A minimal HAL document looks like:

```json
{
  "name": "Example",
  "_links": {
    "self": { "href": "/api/example/1" },
    "related": { "href": "/api/other/42" }
  },
  "_embedded": {
    "child": { "id": 42, "title": "Child Resource" }
  }
}
```

### Key Design Principles of HAL

1. **Discoverability (HATEOAS):** Clients navigate the API by following links, not by constructing URLs. This makes the API self-documenting and resilient to URL structure changes.
2. **Uniform interface:** Every resource shares the same `_links` / `_embedded` structure, making generic client parsers easy to write.
3. **Link relations are semantic:** Link names like `self`, `next`, `prev`, `edit`, `cart` describe what the link *means*, not where it goes.

---

## 2. How Reverb Specifically Uses HAL+JSON

Reverb implements a **HATEOAS-style REST API** using `application/hal+json` as its primary media type. Here is how their implementation maps to the HAL spec:

### 2.1 Required Headers

Every request must include:

```plaintext
Accept: application/hal+json
Accept-Version: 3.0
Content-Type: application/hal+json
```

The server responds with `Content-Type: application/hal+json` and `X-Reverb-Version: 3.0`.

### 2.1.1 The `Accept` Header is a Documentation Convention, Not a Requirement

The `Accept` header has **zero effect** on the response. Verified across 5 variations:

| Sent `Accept` | Response `Content-Type` | HTTP Status |
|---|---|---|
| `application/hal+json` | `application/hal+json` | 200 |
| `application/json` | `application/hal+json` | 200 |
| `*/*` | `application/hal+json` | 200 |
| `text/html` | `application/hal+json` | 200 |
| *(omitted entirely)* | `application/hal+json` | 200 |

Three notable details:

1. **`Content-Type` is always present in the response** — it is never absent, always `application/hal+json`.
2. **No `406 Not Acceptable`** — a proper HTTP content-negotiating server should reject `Accept: text/html` with a 406 if it cannot serve that format. Reverb does not. The `Accept` header is silently ignored.
3. **The `Vary` header is the tell** — the response includes `Vary: Accept-Language, Accept-Version, X-Display-Currency, ...` but notably `Accept` is **not** in that list. This is the server self-documenting that it does not vary its output based on the `Accept` header, which is consistent with ignoring it entirely.

So `Accept: application/hal+json` is a documentation convention (signaling intent to consume HAL), not a technical requirement for receiving a response.

### 2.2 Use of `_links`

Reverb uses `_links` extensively at **two levels**:

- **Collection level** — Pagination links (`next`, `prev`) and action links (`listing`) appear on the top-level response envelope.
- **Resource level** — Each category or listing resource contains its own `_links` block with actions relevant to that specific resource (`self`, `web`, `edit`, `cart`, `make_offer`, `watchlist`, `follow`, `listings`, `image`, `photo`).

Some links include a `method` property when the default GET does not apply:

```json
"make_offer": {
  "href": "https://api.reverb.com/api/listings/12345/offer",
  "method": "POST"
}
```

### 2.3 Use of `_embedded`

Reverb **does not use `_embedded`** in the two public endpoints explored. Instead, related data is inlined directly as regular JSON properties (e.g., `shop`, `condition`, `price`, `categories`, `photos` are nested objects/arrays without the `_embedded` wrapper). This is a pragmatic deviation from strict HAL — it simplifies consumption but means clients cannot rely on a generic `_embedded` parser.

### 2.4 Pagination Convention

Collection responses use a custom envelope with explicit metadata fields (`total`, `total_pages`, `current_page`, `per_page`) alongside HAL `_links.next` / `_links.prev` for cursor-based navigation.

### 2.5 Vary Headers and Content Negotiation

Reverb uses extensive `Vary` headers to enable edge caching based on locale, currency, shipping region, and API version:

```plaintext
Vary: Accept-Language, Accept-Version, X-Display-Currency, X-Shipping-Region, X-Item-Region, X-Postal-Code
```

#### Does the `Accept` header change the response?

No. The Reverb API **does not perform content negotiation** on the `Accept` request header. It always returns `application/hal+json` regardless of what — or whether — you send an `Accept` header. This was verified across four variations:

```bash
# Variation A — correct HAL header (recommended)
curl -s -I -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/categories/flat" | grep -i content-type
# → content-type: application/hal+json

# Variation B — plain JSON
curl -s -I -H "Accept: application/json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/categories/flat" | grep -i content-type
# → content-type: application/hal+json   ← same

# Variation C — wildcard
curl -s -I -H "Accept: */*" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/categories/flat" | grep -i content-type
# → content-type: application/hal+json   ← same

# Variation D — completely wrong type
curl -s -I -H "Accept: text/html" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/categories/flat" | grep -i content-type
# → content-type: application/hal+json   ← same, no 406 returned

# Variation E — no Accept header at all
curl -s -I -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/categories/flat" | grep -i content-type
# → content-type: application/hal+json   ← same
```

The body structure is also identical across all variations — the `_links` field, all keys, and all values are the same:

```bash
# Body key comparison: hal+json vs plain json Accept — categories
curl -s -H "Accept: application/hal+json" ... | jq '.categories[0] | keys'
curl -s -H "Accept: application/json"    ... | jq '.categories[0] | keys'
# → identical output in both cases: ["_links", "collection_title", "full_name", ...]

# Body key comparison: hal+json vs json vs no-header — listings
curl -s -H "Accept: application/hal+json" ... | jq '.listings[0] | keys'
curl -s -H "Accept: application/json"    ... | jq '.listings[0] | keys'
curl -s                                   ... | jq '.listings[0] | keys'
# → identical output in all three cases: ["_links", "auction", "buyer_price", ...]
```

**What this means in practice:**

- The server **always** includes `Content-Type: application/hal+json` in every response.
- Sending `Accept: application/hal+json` is a convention the Reverb docs require, but the server does not enforce or vary on it — it is essentially documentation-driven, not technically enforced.
- Sending an unsupported type like `Accept: text/html` does **not** return a `406 Not Acceptable` error, which would be the correct HTTP/1.1 behaviour for a server that truly negotiates content.
- The `Vary: Accept-Language,Accept-Version,...` response header notably does **not** include `Accept` itself, which is consistent with the server ignoring it for format negotiation.

### 2.6 Caching Behavior

Both endpoints were verified with `curl -sI` to extract response caching headers directly.

#### Categories (`/api/categories/flat`)

```bash
curl -s -I \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| grep -iE "cache|etag|age|vary|cf-"

# Result:
cache-control: max-age=86400, public
etag: W/"27bca2a233cebe6f57204ebb2785c5b0"
age: 84245
cf-cache-status: HIT
vary: Accept-Language,Accept-Version,X-Display-Currency,X-Shipping-Region,X-Item-Region,X-Postal-Code
vary: accept-encoding
```

- **`Cache-Control: max-age=86400, public`** — origin instructs CDN and any downstream caches to cache this response for 24 hours.
- **`ETag: W/"..."`** — a weak entity tag. Clients can use this with `If-None-Match` for conditional GETs.
- **`age: 84245`** — the response had already been in the Cloudflare edge cache for ~23.4 hours at time of request. The CDN is actively serving stale-within-TTL.
- **`cf-cache-status: HIT`** — Cloudflare served this directly from its edge cache; the origin Rails server was not hit at all.

#### Can you bypass the CDN cache for categories?

No. Sending `Cache-Control: no-cache` as a **request** header has no effect — Cloudflare ignores client-side bypass hints for publicly cached resources:

```bash
curl -s -I \
  -H "Cache-Control: no-cache" \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/categories/flat" \
| grep -iE "cache|etag|age|cf-"

# Result — CF still serves from cache despite the request header:
cache-control: max-age=86400, public
etag: W/"27bca2a233cebe6f57204ebb2785c5b0"
age: 84271
cf-cache-status: HIT    ← still a cache hit
```

This is by design. Cloudflare by default strips or ignores `Cache-Control: no-cache` and `Pragma: no-cache` from **incoming requests** to prevent cache poisoning and to protect the origin from cache-busting storms. The CDN TTL is controlled solely by the origin's response headers (`Cache-Control: max-age=86400`).

#### The ETag / Conditional GET pattern (works correctly)

What *does* work is `If-None-Match`, which lets clients avoid downloading the ~312 KB body when nothing has changed:

```bash
curl -s -I \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H 'If-None-Match: W/"27bca2a233cebe6f57204ebb2785c5b0"' \
  "https://api.reverb.com/api/categories/flat" \
| grep -iE "HTTP/|cache|etag|age|cf-"

# Result:
HTTP/2 304     ← Not Modified — no body transferred
cache-control: max-age=86400, public
etag: W/"27bca2a233cebe6f57204ebb2785c5b0"    ← same ETag, data unchanged
cf-cache-status: HIT
age: 84281
```

A well-behaved client should:

1. Store the `ETag` from the first response.
2. On subsequent polls, send `If-None-Match: <stored-etag>`.
3. On `304`: use cached data. On `200`: update cache and ETag.

This saves ~312 KB of transfer per poll when the taxonomy hasn't changed.

#### Listings (`/api/listings/all`)

```bash
curl -s -I \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| grep -iE "cache|etag|age|vary|cf-"

# Result:
cache-control: no-cache
vary: Accept-Language,Accept-Version,X-Display-Currency,X-Shipping-Region,X-Item-Region,X-Postal-Code
cf-cache-status: MISS
```

- **`Cache-Control: no-cache`** — origin tells Cloudflare and all downstream caches not to serve a stored response without revalidating with the origin. Every request hits the origin server.
- **No `ETag`** — no conditional GET support. Cannot check for changes without fetching the full response.
- **No `age` header** — nothing was served from cache; there is no age.
- **`cf-cache-status: MISS`** — Cloudflare bypassed its edge cache and forwarded directly to the origin Rails app (note the higher `x-runtime: 0.601269` compared to categories' `x-runtime: 0.011453`).

This means **no CDN bypass is needed or possible** for listings — the CDN already never caches it.

### 2.7 ETags and Conditional GET — Per Endpoint

An **ETag** (Entity Tag) is an HTTP response header that identifies a specific version of a resource. The server generates it (usually a hash of the response body) and the client stores it. On the next request the client sends it back via `If-None-Match`; the server compares it to the current version and responds either:

- **`304 Not Modified`** — data unchanged, no body sent. Client reuses its cached copy.
- **`200 OK`** with a new body and a new ETag — data changed, client updates its cache.

This is the correct mechanism to avoid re-downloading a large static resource on every poll.

#### Categories: ETag supported — use `If-None-Match`

The categories endpoint returns a **weak ETag** (`W/"..."`) because the response body is deterministic and stable:

```bash
# Step 1 — first request: note the ETag in the response
curl -s -I \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/categories/flat" \
| grep -i etag

# Result:
etag: W/"27bca2a233cebe6f57204ebb2785c5b0"
```

```bash
# Step 2 — subsequent requests: send the stored ETag
curl -s -I \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H 'If-None-Match: W/"27bca2a233cebe6f57204ebb2785c5b0"' \
  "https://api.reverb.com/api/categories/flat" \
| grep -iE "HTTP/|etag|cf-cache"

# Result (taxonomy unchanged):
HTTP/2 304             ← no body, ~312 KB saved
etag: W/"27bca2a233cebe6f57204ebb2785c5b0"
cf-cache-status: HIT

# Result (taxonomy changed — new categories added/removed):
HTTP/2 200             ← new body + new ETag
etag: W/"<new_hash>"
```

**Practical pattern for a polling client:**

```python
# Pseudocode
stored_etag = None

def fetch_categories():
    global stored_etag
    headers = {"Accept": "application/hal+json", "Accept-Version": "3.0"}
    if stored_etag:
        headers["If-None-Match"] = stored_etag

    response = requests.get("https://api.reverb.com/api/categories/flat", headers=headers)

    if response.status_code == 304:
        return CACHED  # nothing changed, reuse stored data

    stored_etag = response.headers["ETag"]
    return response.json()  # new data
```

Note that `cf-cache-status: HIT` on the `304` shows Cloudflare itself is handling the conditional validation at the edge — the origin Rails server is not involved at all.

#### Listings: No ETag — conditional GET not supported

The listings endpoint does **not** return an ETag:

```bash
curl -s -I \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| grep -i etag

# Result:
(no output — no ETag header present)
```

This is intentional and consistent with `Cache-Control: no-cache` and `cf-cache-status: MISS`. The listings result set is inherently dynamic — new listings are published every second, prices change, items sell. There is no stable "version" to hash. Sending `If-None-Match` here would have no effect; the server would simply ignore the header and return a full `200` response every time.

**Summary table:**

```plaintext
Endpoint               ETag    If-None-Match   304 possible   CDN cached
/api/categories/flat   YES     YES             YES            YES (24h)
/api/listings/all      NO      NO              NO             NO (MISS)
```

---

## 3. Endpoint: `/api/categories/flat`

### 3.1 HTTP Request

```bash
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat"
```

### 3.2 HTTP Response Metadata

```plaintext
HTTP/2 200
Content-Type: application/hal+json
Cache-Control: max-age=86400, public
ETag: W/"27bca2a233cebe6f57204ebb2785c5b0"
X-Reverb-Version: 3.0
Response Size: ~319,344 bytes (~312 KB)
```

### 3.3 Top-Level Structure

```bash
# Command:
curl -s ... "https://api.reverb.com/api/categories/flat" | jq 'keys'

# Result:
["categories"]
```

The response has a single top-level key `categories` containing an array.

### 3.4 Total Categories — No Pagination, Complete Dump

```bash
# Command:
curl -s ... "https://api.reverb.com/api/categories/flat" | jq '.categories | length'

# Result:
320
```

The endpoint returns **all categories in a single response with no pagination**. This is confirmed by three checks:

```bash
# 1. No pagination keys in the response envelope
curl -s ... "https://api.reverb.com/api/categories/flat" | jq 'keys'
# → ["categories"]   ← no total, total_pages, current_page, per_page, or _links

# 2. Pagination params are silently ignored — still returns all 320
curl -s ... "https://api.reverb.com/api/categories/flat?per_page=5&page=1" \
| jq '{keys: keys, count: (.categories | length)}'
# → {"keys": ["categories"], "count": 320}

# 3. page=2 returns the same 320 — there is no second page
curl -s ... "https://api.reverb.com/api/categories/flat?page=2" \
| jq '{keys: keys, count: (.categories | length)}'
# → {"keys": ["categories"], "count": 320}

# 4. All entries are unique — no duplication or truncation
curl -s ... "https://api.reverb.com/api/categories/flat" \
| jq '{total: (.categories | length), unique_uuids: ([.categories[] | .uuid] | unique | length), unique_full_names: ([.categories[] | .full_name] | unique | length)}'
# → {"total": 320, "unique_uuids": 320, "unique_full_names": 320}
```

This is a **static reference endpoint** by design: the category taxonomy is small (~320 entries, ~312 KB), changes infrequently, and is needed in full by any client that wants to build a category picker or filter. Returning it as a single uncapped list is the correct trade-off. This also explains the `Cache-Control: max-age=86400, public` — it is safe to cache at the CDN edge for 24 hours because the data is stable.

All 320 categories have `listable: true`:

```bash
# Command:
... | jq '[.categories[] | .listable] | group_by(.) | map({value: .[0], count: length})'

# Result:
[{"value": true, "count": 320}]
```

### 3.5 Category Object Schema

```bash
# Command:
curl -s ... "https://api.reverb.com/api/categories/flat" | jq '.categories[0] | map_values(type)'

# Result:
{
  "uuid": "string",
  "full_name": "string",
  "name": "string",
  "root_uuid": "string",
  "root_slug": "string",
  "slug": "string",
  "collection_title": "string",
  "listable": "boolean",
  "_links": "object"
}
```

### 3.6 Example Category Object

```bash
# Command:
curl -s ... "https://api.reverb.com/api/categories/flat" | jq '.categories[0]'

# Result:
{
  "uuid": "14d6cc96-ed7b-4521-bc21-7713c61e9dc5",
  "full_name": "Acoustic Guitars / 12-String",
  "name": "12-String",
  "root_uuid": "3ca3eb03-7eac-477d-b253-15ce603d2550",
  "root_slug": "acoustic-guitars",
  "slug": "12-string",
  "collection_title": "12-String Acoustic Guitars",
  "listable": true,
  "_links": {
    "image": { "href": "https://static.reverb-assets.com/assets/products/blank_medium-..." },
    "self": { "href": "https://api.reverb.com/api/categories/14d6cc96-..." },
    "listings": { "href": "https://api.reverb.com/api/listings?category_uuid=14d6cc96-..." },
    "follow": { "href": "https://api.reverb.com/api/my/follows/categories/14d6cc96-..." },
    "collection_header_image": { "href": "https://rvb-img.reverb.com/i/s--..." },
    "web": { "href": "/en-be/marketplace?category=12-string&product_type=acoustic-guitars" }
  }
}
```

### 3.7 Category `_links` Structure

```bash
# Command:
... | jq '.categories[0]._links | map_values(type)'

# Result:
{
  "image": "object",
  "self": "object",
  "listings": "object",
  "follow": "object",
  "collection_header_image": "object",
  "web": "object"
}
```

Each link is an object containing `{ "href": "..." }`.

Link descriptions:

- **`self`** — Canonical API URL for this category.
- **`listings`** — Pre-built URL to fetch all listings in this category.
- **`follow`** — Endpoint to follow/unfollow this category (requires auth).
- **`image`** — Default product image for the category.
- **`collection_header_image`** — Banner/hero image for the category collection page.
- **`web`** — Relative URL to the web marketplace page for this category.

### 3.8 Root Categories (14 total)

```bash
# Command:
... | jq '[.categories[] | .root_slug] | unique | sort'

# Result:
["accessories", "acoustic-guitars", "amps", "band-and-orchestra", "bass-guitars",
 "dj-and-lighting-gear", "drums-and-percussion", "effects-and-pedals",
 "electric-guitars", "folk-instruments", "home-audio", "keyboards-and-synths",
 "parts", "pro-audio"]
```

### 3.9 Subcategory Distribution per Root

```bash
# Command:
... | jq '[.categories[] | .root_slug] | group_by(.) | map({root: .[0], count: length}) | sort_by(-.count)'

# Result (sorted by count descending):
drums-and-percussion      42
keyboards-and-synths      40
home-audio                34
pro-audio                 31
effects-and-pedals        29
accessories               28
amps                      24
band-and-orchestra        19
parts                     17
acoustic-guitars          15
folk-instruments          14
electric-guitars          12
bass-guitars               8
dj-and-lighting-gear       7
```

### 3.10 Example: Subcategories of "electric-guitars"

```bash
# Command:
... | jq '[.categories[] | select(.root_slug == "electric-guitars") | .name]'

# Result:
["12-String", "Archtop", "Baritone", "Electric Guitars", "Hollow Body",
 "Lap Steel", "Left-Handed", "Pedal Steel", "Semi-Hollow", "Solid Body",
 "Tenor", "Travel / Mini"]
```

### 3.11 `_embedded` Check

```bash
# Command:
... | jq '.categories[0]._embedded // "NOT PRESENT"'

# Result:
"NOT PRESENT"
```

The `_embedded` HAL property is not used in this endpoint.

### 3.12 Category Hierarchy: How Many Levels Deep?

The `/api/categories/flat` name is slightly misleading — the data is returned as a **flat array**, but the categories themselves encode a **multi-level hierarchy** inside the `full_name` field using ` / ` as a path separator.

There is **no explicit `parent_uuid` field**. The only relational anchors available per category are `root_uuid` and `root_slug`, which only point to the top-level ancestor — intermediate parent nodes must be inferred by parsing `full_name`.

#### Depth Distribution

```bash
# Command — count unique depth levels by splitting full_name:
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '[.categories[] | .full_name | split(" / ") | length] | unique | sort'

# Result:
[1, 2, 3, 4, 5]
```

There are **5 hierarchy levels**. The distribution by level:

```bash
# Command — count and sample examples per depth:
... | jq '[.categories[] | {depth: (.full_name | split(" / ") | length), full_name}]
  | group_by(.depth)
  | map({depth: .[0].depth, count: length, examples: [.[].full_name] | .[0:3]})'

# Result:
Depth 1 →   14 categories  (root nodes, e.g. "Accessories", "Acoustic Guitars")
Depth 2 →  148 categories  (e.g. "Acoustic Guitars / 12-String")
Depth 3 →  151 categories  (e.g. "Amps / Guitar Amps / Acoustic Guitar Amps")
Depth 4 →    6 categories  (all under "Keyboards and Synths")
Depth 5 →    1 category    (deepest node in the entire tree)
```

The vast majority of categories sit at **depth 2–3**. Only 7 nodes (all in the `keyboards-and-synths` root) go deeper.

#### The Deepest Node (Level 5)

```bash
# Command — all categories at depth >= 4:
... | jq '[.categories[] | select((.full_name | split(" / ") | length) >= 4)
  | {depth: (.full_name | split(" / ") | length), full_name, slug, root_slug}]
  | sort_by(.depth)'

# Result (depth 4):
"Keyboards and Synths / Keyboard and Synth Accessories / Modular Synth Accessories / Blank Modular Synth Panels"
"Keyboards and Synths / Keyboard and Synth Accessories / Modular Synth Accessories / Modular Synth DSP Cards"
"Keyboards and Synths / Keyboard and Synth Accessories / Modular Synth Accessories / Modular Synth Power Supplies"
"Keyboards and Synths / Synths / Modular Synths / Complete Modular Synth Systems"
"Keyboards and Synths / Synths / Modular Synths / Modular Synth Cases"
"Keyboards and Synths / Synths / Modular Synths / Synth Modules"

# Result (depth 5 — the only one):
"Keyboards and Synths / Keyboard and Synth Accessories / Modular Synth Accessories / Modular Synth Splitters / Hubs"
```

**The single deepest category** is `modular-synth-splitters-slash-hubs` — note the `slash` in the slug itself is URL-encoded because the `/` in "Splitters / Hubs" is a name separator within the node, not a hierarchy separator.

#### Max Depth per Root Category

```bash
# Command:
... | jq '[.categories[] | {depth: (.full_name | split(" / ") | length), root_slug}]
  | group_by(.root_slug)
  | map({root: .[0].root_slug, max_depth: (map(.depth) | max), avg_depth: (map(.depth) | add / length | floor)})
  | sort_by(-.max_depth)'

# Result:
keyboards-and-synths    max=5  avg=2   ← only root reaching depth 5
accessories             max=3  avg=2
amps                    max=3  avg=2
band-and-orchestra      max=3  avg=2
drums-and-percussion    max=3  avg=2
electric-guitars        max=3  avg=2
home-audio              max=3  avg=2
parts                   max=3  avg=2
pro-audio               max=3  avg=2
acoustic-guitars        max=2  avg=1
bass-guitars            max=2  avg=1
dj-and-lighting-gear    max=2  avg=1
effects-and-pedals      max=2  avg=1
folk-instruments        max=2  avg=1
```

#### Key Structural Observations

1. **`/api/categories/flat` returns a denormalized tree** — every path from root to leaf is a separate record in the array. There are no nested arrays or parent pointers.
2. **Hierarchy is implicit, encoded in `full_name`** — clients must parse ` / ` splits to reconstruct the tree. `root_uuid`/`root_slug` only anchor to depth-1, not intermediate nodes.
3. **`slug` is always the leaf node name only** — e.g. `"acoustic-guitar-amps"` not `"guitar-amps/acoustic-guitar-amps"`. The full path is only in `full_name`.
4. **Depth is uneven across roots** — simpler roots like `acoustic-guitars` max out at depth 2; the highly specialized `keyboards-and-synths` (Eurorack/modular ecosystem) reaches depth 5.
5. **The deepest node's slug encodes its own internal `/`** — `"modular-synth-splitters-slash-hubs"` reveals that the node name itself contains " / " ("Splitters / Hubs"), which was serialized as `slash` to avoid ambiguity with the path separator used in `full_name`.

---

## 4. Endpoint: `/api/listings/all`

### 4.1 HTTP Request

```bash
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1"
```

### 4.2 HTTP Response Metadata

```plaintext
HTTP/2 200
Content-Type: application/hal+json
Cache-Control: no-cache
X-Reverb-Version: 3.0
X-Runtime: 0.601269
Response Size: ~22,398 bytes (~22 KB) for 5 listings
```

### 4.3 Top-Level Structure

```bash
# Command:
... | jq 'keys'

# Result:
["_links", "current_page", "humanized_params", "listings", "per_page", "ships_to", "total", "total_pages"]
```

### 4.4 Pagination Metadata

```bash
# Command:
... | jq '{total, total_pages, current_page, per_page, ships_to, humanized_params}'

# Result:
{
  "total": 2537869,
  "total_pages": 50,
  "current_page": 1,
  "per_page": 5,
  "ships_to": "Everywhere Else",
  "humanized_params": "Gear"
}
```

**Note:** Despite ~2.5M total listings, `total_pages` is capped at 50. This is intentional product/API design — the endpoint is **search-window paginated, not cursor-export paginated**. The cap is per query result set, not a global limit. Reasons include:

- **Deep offset pagination is expensive and unstable.** A request like `?page=30000&per_page=50` forces the search index to skip a huge ranked set. On a live marketplace where listings are constantly added, sold, bumped, and reordered, deep pages are not stable — page 30,000 at 10:00 AM may differ at 10:05 AM.
- **This is a search/browse endpoint, not a bulk export endpoint.** Reverb's docs describe the API as tooling for shop integrations and automations, not full-marketplace harvesting.
- **Anti-scraping protection.** The cap limits full-catalog extraction (price intelligence, seller cloning, AI training datasets, etc.).

#### Reaching Listings Beyond the Cap: Query Partitioning

The correct strategy is to narrow the search rather than paginate deeper. The cap applies per query, so filtered queries expose different windows:

```bash
GET /api/listings/all?category=...
GET /api/listings/all?query=fender+stratocaster
GET /api/listings/all?condition=...
GET /api/listings/all?price_min=...&price_max=...
GET /api/listings/all?make=...
GET /api/listings/all?shipping_region=...
```

A robust algorithm:

1. Pull `/api/categories/flat`.
2. For each category, query listings. If `total_pages < 50`, paginate normally.
3. If `total_pages == 50`, split further by price buckets, condition, make, or keyword.
4. Deduplicate by listing `id` or `_links.self.href`.
5. Stop splitting when each query returns below the cap.

**Header note:** Omitting `X-Shipping-Region` returns the broadest result set. Including it filters to listings that ship to that region.

### 4.5 Collection-Level `_links` (Pagination)

```bash
# Command:
... | jq '._links'

# Result:
{
  "next": { "href": "https://api.reverb.com/api/listings/all?page=2&per_page=5" },
  "listing": { "href": "https://reverb.com/sell" }
}
```

- **`next`** — URL to the next page of results (absent on the last page).
- **`listing`** — Link to the "create a listing" web page.

### 4.6 Listing Object Schema

```bash
# Command:
... | jq '.listings[0] | map_values(type)'

# Result:
{
  "id": "number",
  "make": "string",
  "model": "string",
  "finish": "string",
  "year": "string",
  "title": "string",
  "created_at": "string",
  "shop_name": "string",
  "shop": "object",
  "description": "string",
  "condition": "object",
  "price": "object",
  "buyer_price": "object",
  "inventory": "number",
  "has_inventory": "boolean",
  "offers_enabled": "boolean",
  "categories": "array",
  "listing_currency": "string",
  "published_at": "string",
  "state": "object",
  "auction": "boolean",
  "shop_id": "number",
  "price_guide_id": "string",
  "shipping": "object",
  "sku": "string",
  "us_outlet": "boolean",
  "_links": "object",
  "photos": "array"
}
```

### 4.7 Scalar Fields Example

```bash
# Command:
... | jq '.listings[0] | {id, make, model, finish, year, title, created_at, shop_name,
  listing_currency, published_at, auction, shop_id, sku, us_outlet, has_inventory, inventory, offers_enabled}'

# Result:
{
  "id": 97305232,
  "make": "Silvertone",
  "model": "1448 with Case Amp Black",
  "finish": "Black",
  "year": "60s",
  "title": "Silvertone 1448 with Case Amp Black 60s (USED)",
  "created_at": "2026-05-20T10:42:48-06:00",
  "shop_name": "Micarelli Music LLC",
  "listing_currency": "USD",
  "published_at": "2026-05-20T10:42:49-06:00",
  "auction": false,
  "shop_id": 104300,
  "sku": "331929",
  "us_outlet": false,
  "has_inventory": false,
  "inventory": 1,
  "offers_enabled": true
}
```

### 4.8 Nested Object: `shop`

```bash
# Command:
... | jq '.listings[0].shop'

# Result:
{
  "slug": "micarellimusic",
  "preferred_seller": true
}
```

### 4.9 Nested Object: `condition`

```bash
# Included in the compound command below.

# Result:
{
  "uuid": "f7a3f48c-972a-44c6-b01a-0cd27488d3f6",
  "display_name": "Good",
  "slug": "good"
}
```

### 4.10 Nested Object: `price` / `buyer_price`

```bash
# Command:
... | jq '.listings[0].price | map_values(type)'

# Result:
{
  "tax_included": "boolean",
  "amount": "string",
  "amount_cents": "number",
  "currency": "string",
  "symbol": "string",
  "display": "string"
}
```

Example values:

```json
{
  "tax_included": false,
  "amount": "450.00",
  "amount_cents": 45000,
  "currency": "USD",
  "symbol": "$",
  "display": "$450"
}
```

`buyer_price` shares the same schema — it may differ from `price` when currency conversion or buyer-specific pricing applies.

### 4.11 Nested Object: `state`

```json
{
  "slug": "live",
  "description": "Live"
}
```

### 4.12 Nested Object: `shipping`

```bash
# Command:
... | jq '.listings[0].shipping'

# Result (abbreviated):
{
  "free_expedited_shipping": false,
  "local": true,
  "rates": [
    {
      "region_code": "US_CON",
      "rate": {
        "amount": "100.00",
        "amount_cents": 10000,
        "currency": "USD",
        "symbol": "$",
        "display": "$100"
      },
      "carrier_calculated": false,
      "regional": false,
      "destination_postal_code_needed": false
    }
  ],
  "initial_offer_rate": { ... }
}
```

Shipping rates per listing range from **1 to 4** entries. Observed region codes across the sample:

```bash
# Command:
... | jq '[.listings[] | .shipping.rates[] | .region_code] | unique'

# Result:
["EUR_EU", "FR", "US", "US_CON", "XX"]
```

### 4.13 Nested Array: `categories`

```json
[
  {
    "uuid": "dfd39027-d134-4353-b9e4-57dc6be791b9",
    "full_name": "Electric Guitars"
  }
]
```

Each listing has one or more category references (uuid + full_name).

### 4.14 Nested Array: `photos`

Each photo is a HAL-style object with `_links` containing four image variants:

```json
{
  "_links": {
    "large_crop": { "href": "https://rvb-img.reverb.com/..." },
    "small_crop": { "href": "https://rvb-img.reverb.com/..." },
    "full":       { "href": "https://rvb-img.reverb.com/..." },
    "thumbnail":  { "href": "https://rvb-img.reverb.com/..." }
  }
}
```

In the collection view (`/listings/all`), only **1 photo** is returned per listing. The individual listing endpoint (`/api/listings/{id}`) returns **all photos** (e.g., 3+) with multiple size variants.

### 4.15 Listing-Level `_links`

```bash
# Command:
... | jq '.listings[0]._links | keys'

# Result:
["cart", "edit", "make_offer", "photo", "self", "watchlist", "web"]
```

Full values:

```json
{
  "photo":      { "href": "https://rvb-img.reverb.com/..." },
  "self":       { "href": "https://api.reverb.com/api/listings/97305295-fender-..." },
  "edit":       { "href": "https://api.reverb.com/api/listings/97305295-fender-.../edit" },
  "web":        { "href": "https://reverb.com/item/97305295-fender-..." },
  "make_offer": { "href": "https://api.reverb.com/api/listings/97305295-fender-.../offer", "method": "POST" },
  "cart":       { "href": "https://api.reverb.com/api/cart/97305295" },
  "watchlist":  { "href": "https://api.reverb.com/api/wants/97305295-fender-..." }
}
```

Link descriptions:

- **`self`** — Canonical API URL for this listing (GET for details, PUT for update).
- **`web`** — Human-readable URL on reverb.com.
- **`edit`** — Edit endpoint (requires auth).
- **`make_offer`** — Submit an offer (POST, requires auth).
- **`cart`** — Add this listing to cart (requires auth). **This is the correct cart URL — it must be discovered via `_links`, not constructed manually.**
- **`watchlist`** — Add/remove from watch list (requires auth).
- **`photo`** — Direct link to the primary photo.

### 4.16 Sample Listings

```bash
# Command:
... | jq '[.listings[] | {id, title, make, price: .price.display, condition: .condition.display_name}]'

# Result:
[
  { "id": 97305407, "title": "MEINL Woodcraft Cajon",                        "make": "Meinl",      "price": "$169.99", "condition": "Brand New" },
  { "id": 97099329, "title": "Tanglewood Hollow-Body Archtop Electric...",    "make": "Tanglewood", "price": "$399.99", "condition": "Very Good" },
  { "id": 97305405, "title": "Mackie Micro Series 1202 Mixer, Recent",       "make": "Mackie",     "price": "$95",     "condition": "Very Good" },
  { "id": 97305364, "title": "EMG 81 Humbucking Active Guitar Pickup...",     "make": "EMG",        "price": "$129",    "condition": "Brand New" },
  { "id": 97305320, "title": "Elixir Nanoweb 12052 10/46 Light...",          "make": "Elixir",     "price": "$16",     "condition": "Brand New" }
]
```

### 4.17 `_embedded` Check

```bash
# Command:
... | jq '.listings[0]._embedded // "NOT PRESENT"'

# Result:
"NOT PRESENT"
```

Not used in this endpoint either.

---

## 5. Other Public Endpoints (No Auth Required)

The API root (`GET /api`) exposes a `_links` map that serves as the entry point for discovery. Beyond the two endpoints explored in depth above, the following endpoints return `200 OK` without any authentication token. They provide reference/metadata useful for building clients that consume listings and categories.

### 5.1 `/api/listing_conditions`

Returns the condition taxonomy used across all listings.

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/listing_conditions" | jq '.conditions[] | {display_name, uuid}'
```

**Response:** `{ "conditions": [...] }` — array of 8 condition objects.

| `display_name` | `uuid` |
|---|---|
| Brand New | `7c3f45de-2ae0-4c81-8400-fdb6b1d74890` |
| Mint | `ac5b9c1e-dc78-466d-b0b3-7cf712967a48` |
| Excellent | `df268ad1-c462-4ba6-b6db-e007e23922ea` |
| Very Good | `ae4d9114-1bd7-4ec5-a4ba-6653af5ac84d` |
| Good | `f7a3f48c-972a-44c6-b01a-0cd27488d3f6` |
| Fair | `98777886-76d0-44c8-865e-bb40e669e934` |
| Poor | `6a9dfcad-600b-46c8-9e08-ce6e5057921e` |
| Non Functioning | `fbf35668-96a0-4baa-bcde-ab18d6b1b329` |

Each object also has a `description` field explaining the condition semantics.

**Dual-mode behavior:** When called with a shop's API token, this endpoint returns only the conditions that shop is authorized to use (e.g., B-Stock and Mint with inventory are restricted to enabled accounts).

### 5.2 `/api/currencies/display`

Returns the list of currencies buyers can use for price display (via `X-Display-Currency` header).

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/currencies/display"
```

**Response:** `{ "currencies": ["USD", "CAD", "EUR", "GBP", "AUD", "JPY", "NZD", "MXN", "DKK", "SEK", "CHF", "BRL", "HKD", "NOK", "PHP", "PLN"] }` — 16 display currencies.

### 5.3 `/api/currencies/listing`

Returns the list of currencies sellers can use when creating listings.

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/currencies/listing"
```

**Response:** `{ "currencies": ["USD", "CAD", "EUR", "GBP", "AUD", "JPY", "NZD", "MXN"] }` — 8 listing currencies (subset of display currencies).

### 5.4 `/api/countries`

Returns all 241 countries with subregion data (used for shipping address forms).

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/countries" | jq '.countries | length'
# 241
```

**Object schema:** `{ country_code, name, subregion_required, subregions: [{ code, name, id }] }`

### 5.5 `/api/shipping/regions`

Returns the 8 top-level shipping regions with nested country children. These codes correspond to the `region_code` values seen in listing shipping rates.

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/shipping/regions" | jq '[.shipping_regions[] | .code]'
# ["XX", "AFRICA", "ASIA", "EUR_NON_EU", "EUR_EU", "NORTH_AMERICA", "OCEANIA", "SOUTH_AMERICA"]
```

**Object schema:** `{ code, name, region_type, children: [{ code, name, region_type, children }], shipping_rate_name }`

Region types: `everywhere_else`, `superregion`, `country`.

### 5.6 `/api/shipping/providers`

Returns the list of supported shipping carriers (used when providing tracking info).

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/shipping/providers" | jq '[.shipping_providers[] | .name]'
```

**Response:** 30 providers including UPS, USPS, FedEx, DHL (multiple variants), Canada Post, Royal Mail, Australia Post, La Poste, GLS, DPD, and Others.

### 5.7 `/api/categories` (Hierarchical)

Unlike `/api/categories/flat` (which returns all 320 categories in a flat array), this endpoint returns only the **14 root categories** with a `subcategories` array nested inside each.

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/categories" | jq '.categories | length'
# 14
```

**Object schema:** Same as flat categories but adds `subcategories: [...]` field. Useful when building hierarchical navigation UI.

### 5.8 `/api/collections`

Returns curated editorial collections (hand-picked listing groups). Each collection includes links to its listings.

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/collections" | jq '.collections | length'
# 11
```

**Object schema:** `{ name, description, _links: { image, self, listings, follow } }`

Example collection: "Best of Used: Deals & Steals" — `_links.listings.href` points to `GET /api/listings?curated_set_id=8`.

### 5.9 `/api/priceguide`

Returns paginated price guide entries (~116K total products). Price guides provide historical market pricing data for specific make/model/year combinations.

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/priceguide" | jq '{total, total_pages, current_page}'
# { "total": 116279, "total_pages": 4845, "current_page": 1 }
```

**Object schema:** `{ id, title, make, model, year, finish, categories, description, _links }`

**Note:** This endpoint reports `total_pages: 4845` — significantly more than the listings cap of 50, suggesting price guides use a different (or no) pagination cap.

### 5.10 `/api/articles`

Returns paginated editorial articles (gear news, reviews, guides).

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/articles" | jq '{total, total_pages, current_page}'
```

**Object schema:** `{ id, title, summary, author_name, author_email, published_at, categories, photo, horizontal_photo, square_photo, _links }`

Also available: `GET /api/articles/featured` — returns featured/promoted articles.

### 5.11 `/api/autocomplete?query=...`

Returns make and model suggestions for search form autocomplete.

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/autocomplete?query=fender" | jq 'keys'
# ["makes", "models"]
```

**Response:** `{ "makes": ["Fender", ...], "models": [...] }` — arrays of brand/model name strings.

### 5.12 `/api/autosuggest?query=...`

Returns rich search suggestions grouped by section (searches, categories, shops, etc.) with full HAL `_links` to listings and web pages.

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/autosuggest?query=fender" | jq '.sections | keys'
# ["searches"]
```

**Response:** `{ "original": "fender", "sections": { "searches": { "name": "Suggested Searches", "results": [...] } } }`

Each suggestion includes `_links.web.href` and `_links.listings.href` plus contextual sub-suggestions (e.g., "Fender in Parts").

### 5.13 `/api/listings/{id}` (Single Listing)

Individual listing detail — returns significantly more data than the collection view.

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/listings/64997892" | jq '. | length'
# 47 keys (vs 26 in collection view)

curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/listings/all" | jq '.listings[0] | length'
# 26 keys
```

**URL format:** The API accepts both the bare numeric ID and the full ID+slug form:

```bash
# Both return the same listing:
GET /api/listings/64997892
GET /api/listings/64997892-positive-grid-bias-modulation-twin-effect-pedal
```

The `_links.self.href` always returns the canonical slug form.

**Fields shared with the collection view (26):**

`id`, `make`, `model`, `finish`, `year`, `title`, `created_at`, `shop_name`, `shop`, `description`, `condition`, `price`, `buyer_price`, `inventory`, `has_inventory`, `offers_enabled`, `categories`, `listing_currency`, `published_at`, `state`, `auction`, `shop_id`, `shipping`, `us_outlet`, `_links`, `photos`

**21 additional fields only in the detail endpoint:**

| Field | Type | Category |
| -- | -- | -- |
| `accepted_payment_methods` | array | User-facing — how to pay |
| `location` | object | User-facing — item origin |
| `shipping_policy` | string | User-facing — shipping terms |
| `payment_policy` | string | User-facing — payment terms |
| `return_policy` | object | User-facing — refund conditions |
| `videos` | array | User-facing — demo/media |
| `stats` | object | User-facing — views, watchers (social proof) |
| `offer_count` | number | User-facing — demand signal |
| `handmade` | boolean | User-facing — product characteristic |
| `sold_as_is` | boolean | User-facing — no warranty disclosure |
| `local_pickup_only` | boolean | User-facing — no shipping available |
| `in_watchlist` | boolean | Auth-dependent — requires token |
| `has_offer_for_buyer` | boolean | Auth-dependent — requires token |
| `is_my_listing` | boolean | Auth-dependent — requires token |
| `draft` | boolean | Internal — seller admin state |
| `live` | boolean | Internal — seller admin state |
| `cloudinary_photos` | array | Internal — duplicate CDN format |
| `upc_does_not_apply` | boolean | Internal — seller metadata |
| `origin_country_code` | string | Internal — redundant with `location` |
| `same_day_shipping_ineligible` | boolean | Internal — minor, covered by `shipping_policy` |
| `comparison_shopping_page_id` | string | Internal — Reverb routing |

**Photos:** Returns **all photos** (e.g., 3+) with multiple size variants, vs. only 1 photo in the collection view.

**Key takeaway for the detail page:** of the 21 extra fields, ~11 are worth rendering (payment methods, location, policies, videos, stats, handmade, sold-as-is, local-pickup-only). The remaining ~10 are internal/admin/auth-dependent state.

### 5.14 `/api/shops/{slug}`

Returns public shop/seller profile information.

```bash
curl -s -H "Accept: application/hal+json" -H "Accept-Version: 3.0" \
  "https://api.reverb.com/api/shops/micarellimusic" | jq '{name, preferred_seller, quick_responder, quick_shipper, feedback_count}'
```

**Key fields:** `id`, `name`, `description`, `address`, `avatar`, `banner`, `preferred_seller`, `quick_responder`, `quick_shipper`, `feedback_count`, `on_vacation`, `payment_methods`, `payment_policy`, `direct_checkout`, `_links`.

### 5.15 Summary Table

| Endpoint | Purpose | Paginated | Key for |
|---|---|---|---|
| `/api/categories/flat` | All 320 subcategories, flat | No | Category filtering |
| `/api/categories` | 14 root categories with nested subcategories | No | Hierarchical navigation |
| `/api/listings/all` | Marketplace search/browse | Yes (capped at 50 pages) | Product listing |
| `/api/listings/{id}` | Single listing detail | No | Detail page |
| `/api/shops/{slug}` | Public seller profile | No | Seller pages |
| `/api/listing_conditions` | 8 condition levels | No | Filter/form UI |
| `/api/currencies/display` | 16 display currencies | No | Currency selection |
| `/api/currencies/listing` | 8 listing currencies | No | Seller forms |
| `/api/countries` | 241 countries + subregions | No | Address forms |
| `/api/shipping/regions` | 8 shipping superregions | No | Shipping config |
| `/api/shipping/providers` | 30 carriers | No | Tracking forms |
| `/api/collections` | 11 curated sets | No | Editorial features |
| `/api/priceguide` | ~116K price guides | Yes (4845 pages) | Market pricing |
| `/api/articles` | Editorial content | Yes | Content/SEO |
| `/api/autocomplete?query=` | Make/model suggestions | No | Search typeahead |
| `/api/autosuggest?query=` | Rich search suggestions with links | No | Search UI |

---

## 6. Complete Command Reference

Below is the full list of every `curl | jq` command used in this exploration, in the order they were executed.

### 6.1 Categories Endpoint Commands

```bash
# 1. Top-level keys
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq 'keys'

# 2. Total number of categories
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '.categories | length'

# 3. Full first category object
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '.categories[0]'

# 4. Field types of a category object
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '.categories[0] | map_values(type)'

# 5. _links structure types
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '.categories[0]._links | map_values(type)'

# 6. All unique root category slugs
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '[.categories[] | .root_slug] | unique | sort'

# 7. Subcategory count per root category
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '[.categories[] | .root_slug] | group_by(.) | map({root: .[0], count: length}) | sort_by(-.count)'

# 8. Listable field distribution
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '[.categories[] | .listable] | group_by(.) | map({value: .[0], count: length})'

# 9. Subcategories under electric-guitars
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '[.categories[] | select(.root_slug == "electric-guitars") | .name]'

# 10. Check for _embedded
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '.categories[0]._embedded // "NOT PRESENT"'

# 11. HTTP headers (status, content-type, size)
curl -s -o /dev/null -w '%{http_code}\n%{content_type}\n%{size_download}\n' \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat"

# 12. Full HTTP response headers
curl -s -I \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat"

# 13. Unique depth levels in the hierarchy (splits full_name on " / ")
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '[.categories[] | .full_name | split(" / ") | length] | unique | sort'

# 14. Count and examples for each depth level
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '[.categories[] | {depth: (.full_name | split(" / ") | length), full_name}]
  | group_by(.depth)
  | map({depth: .[0].depth, count: length, examples: [.[].full_name] | .[0:3]})'

# 15. All categories at depth 4 and 5 (deepest nodes)
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '[.categories[] | select((.full_name | split(" / ") | length) >= 4)
  | {depth: (.full_name | split(" / ") | length), full_name, slug, root_slug}]
  | sort_by(.depth)'

# 16. Max and average depth per root category
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '[.categories[] | {depth: (.full_name | split(" / ") | length), root_slug}]
  | group_by(.root_slug)
  | map({root: .[0].root_slug, max_depth: (map(.depth) | max), avg_depth: (map(.depth) | add / length | floor)})
  | sort_by(-.max_depth)'

# 17. Full depth tree for keyboards-and-synths (the deepest root)
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/categories/flat" \
| jq '[.categories[] | select(.root_slug == "keyboards-and-synths")
  | {depth: (.full_name | split(" / ") | length), full_name}]
  | sort_by(.depth)'
```

### 6.2 Listings Endpoint Commands

```bash
# 13. Top-level keys
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq 'keys'

# 14. Pagination metadata
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '{total, total_pages, current_page, per_page, ships_to, humanized_params}'

# 15. Collection-level _links
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '._links'

# 16. Listing field types
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '.listings[0] | map_values(type)'

# 17. Scalar fields of a listing
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '.listings[0] | {id, make, model, finish, year, title, created_at, shop_name, listing_currency, published_at, auction, shop_id, sku, us_outlet, has_inventory, inventory, offers_enabled}'

# 18. Nested shop object
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '.listings[0].shop'

# 19. Nested objects: condition, price, buyer_price, state, shipping
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '.listings[0] | {condition, price, buyer_price, state, shipping}'

# 20. Categories array in listing
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '.listings[0].categories'

# 21. Listing _links keys
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '.listings[0]._links | keys'

# 22. Full listing _links with hrefs
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '.listings[0]._links'

# 23. Photos array
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '.listings[0].photos'

# 24. Description field length
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '.listings[0].description | length'

# 25. All listing IDs
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '[.listings[] | .id]'

# 26. Summary of all listings
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '[.listings[] | {id, title, make, price: .price.display, condition: .condition.display_name}]'

# 27. All unique _links keys across listings
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '[.listings[] | ._links | keys] | flatten | unique | sort'

# 28. Shipping rates count range
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '[.listings[] | .shipping.rates | length] | {min: min, max: max}'

# 29. Unique shipping region codes
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '[.listings[] | .shipping.rates[] | .region_code] | unique'

# 30. Photos per listing count
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '[.listings[] | .photos | length] | {min: min, max: max, values: .}'

# 31. Price field types
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '.listings[0].price | map_values(type)'

# 32. Check for _embedded
curl -s \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1" \
| jq '.listings[0]._embedded // "NOT PRESENT"'

# 33. HTTP headers (status, content-type, size)
curl -s -o /dev/null -w '%{http_code}\n%{content_type}\n%{size_download}\n' \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1"

# 34. Full HTTP response headers
curl -s -I \
  -H "Accept: application/hal+json" \
  -H "Accept-Version: 3.0" \
  -H "Content-Type: application/hal+json" \
  "https://api.reverb.com/api/listings/all?per_page=5&page=1"
```

---

## 7. Key Observations Summary

1. **HAL compliance is pragmatic, not pure** — Reverb relies heavily on `_links` but does not use `_embedded`; related resources are inlined as ordinary JSON properties. However, `_links` usage is meaningful and intentional — they are operational affordances, not decoration.
2. **Links are the canonical navigation mechanism** — Reverb explicitly warns developers not to construct URLs manually. Clients must follow `_links` to discover resource actions and transition endpoints. Links can represent verbs (`add_to_wishlist`) or nouns (`lists`), and endpoints may support only subsets of HTTP methods.
3. **Categories are available in two complementary forms** — `/api/categories/flat` returns all 320 subcategories as a denormalized flat array (hierarchy encoded in `full_name`), while `/api/categories` returns only the 14 root nodes with nested `subcategories`. Clients choose the shape that suits their UI pattern (flat filter list vs. hierarchical tree navigation).
4. **Listings pagination is search-window paginated, not cursor-export paginated** — Despite ~2.5M total listings, `total_pages` is capped at 50 per query. The cap protects search infrastructure, marketplace data, cache efficiency, and page stability on a live marketplace. To access listings outside the result window, partition queries using category, condition, price range, make/model, and shipping region filters, then deduplicate by listing ID.
5. **Pagination strategy varies by endpoint purpose** — The 50-page cap applies to volatile search results (`/api/listings/all`), but reference endpoints like `/api/priceguide` report 4,845 pages with no apparent cap. This reveals an intentional architectural choice: caps apply where deep pagination is unstable or abusable (live marketplace results), not where the data is stable and sequential (price history records).
6. **No authentication required for public reads** — Both endpoints explored work without auth tokens. However, the boundary is not "public API vs. private API" — it is one unified API where anonymous calls can read some resources, while account-scoped and mutating calls require Bearer tokens.
7. **Action links show domain capabilities, not anonymous permission** — Public listing responses include links like `cart`, `watchlist`, and `make_offer`. Their presence means the resource supports that action in the Reverb domain model. Executing the action still requires the correct HTTP method, authentication, scope, and account state.
8. **Caching is binary and intentional** — Categories are edge-cached for 24 hours with ETag/conditional GET support (saving ~312 KB per poll); listings are never cached (`no-cache`, `cf-cache-status: MISS`). There is no middle ground — an endpoint is either fully cacheable or fully dynamic. This reflects the volatility profile of the underlying data.
9. **ETags enable bandwidth-efficient polling** — The categories endpoint supports `If-None-Match` conditional requests. Cloudflare validates the ETag at the edge without hitting the origin, returning `304 Not Modified` with zero body transfer. This is the correct pattern for clients that periodically refresh stable reference data.
10. **Photos are HAL sub-resources** — The `photos` array uses `_links` internally (with `large_crop`, `small_crop`, `full`, `thumbnail`), making photos the closest thing to `_embedded` resources in the response.
11. **Price is consumer-friendly and machine-friendly** — Prices include `amount` (string), `amount_cents` (integer), `currency`, `symbol`, and `display` (formatted), giving consumers flexibility for both display and computation without requiring client-side currency formatting logic.
12. **Headers materially affect response shape** — `Accept-Version` defaults to 1.0; 3.0 is the current recommended version. `Accept-Language`, `X-Display-Currency`, and `X-Shipping-Region` can alter localization, price display, and listing visibility. The same endpoint can return different data depending on these headers.
13. **The public API surface is broad** — 16 publicly accessible endpoints exist (see §5), covering categories, listings, conditions, currencies, countries, shipping regions/providers, collections, price guides, articles, search suggestions, individual listings, and shop profiles. All work without authentication.
14. **The API root is the HATEOAS entry point** — `GET /api` returns a `_links` map that serves as the discovery surface for the entire API. A properly built client starts here and follows links rather than consulting external documentation for URL patterns.
15. **Reference data endpoints form a complete client bootstrap** — A client can fully initialize its UI (category filters, condition dropdowns, currency selectors, shipping region pickers, carrier lists) from public reference endpoints alone, before any user interaction or authentication occurs.
16. **Some metadata endpoints are dual-mode** — Endpoints like `/api/listing_conditions` work anonymously (returning general metadata) but return account-specific availability when called with a shop token (e.g., B-Stock and Mint conditions are only available to enabled accounts).
17. **Rate limits are behaviorally enforced** — Reverb returns 429 responses for excessive volume but does not publish precise quotas. Apps with higher requirements can request increases. A mature integration should include rate-limit backoff, pagination via `_links.next`, and throttled requests.

---

## 8. Authenticated API (Side Topic)

This section is included for architectural context. The interview exercise focuses on public endpoints, but understanding the authenticated surface helps explain design decisions visible in public responses.

### 8.1 One API, Two Access Levels

There is no separate "authenticated API." The same HAL-style API surface serves both anonymous reads and account-scoped operations. The `/my/...` prefix is the strongest indicator of account-scoped endpoints:

| Anonymous (public read) | Authenticated (account-scoped) |
| --- | --- |
| `GET /api/listings/all` | `GET /api/my/listings` |
| `GET /api/categories/flat` | `GET /api/my/orders/selling/all` |
| `GET /api/listing_conditions` | `GET /api/my/conversations` |
| `GET /api/currencies/display` | `POST /api/listings` |
| | `PUT /api/listings/:id` |
| | `POST /api/my/orders/selling/:order_number/ship` |

### 8.2 Authentication Model: Personal Access Tokens

Reverb uses **non-expiring Personal Access Tokens** (not OAuth). Tokens are generated from the user profile under "API & Integrations" and assigned scopes. The integration model is:

```plaintext
seller creates token → pastes into integration → integration acts as that seller
```

This is oriented toward seller/e-commerce sync integrations (Shopify, BigCommerce, Magento) rather than general consumer-facing third-party apps.

### 8.3 Scopes

| Scope family | What it covers |
| --- | --- |
| `public` | Read publicly available data |
| `read_listings` / `write_listings` | Seller inventory, listing state, price, bumps, sales |
| `read_orders` / `write_orders` | Order sync and fulfillment updates |
| `read_messages` / `write_messages` | Conversations with buyers/sellers |
| `read_offers` / `write_offers` | Negotiations / offers |
| `read_profile` / `write_profile` | Account and shop settings |
| `read_payouts` | Financial payout reporting |
| `read_lists` / `write_lists` | Wishlist/watchlist/feed behavior |

### 8.4 Listing State Machine

The authenticated API is not just CRUD — it includes marketplace-state transitions:

```plaintext
draft → published/live → ordered/sold/ended
```

- `POST /api/listings` creates a draft by default.
- `PUT /api/listings/:id` with `"publish": "true"` publishes.
- `/api/my/listings/:id/state/end` ends a listing.
- Inventory-enabled listings can auto-end at 0 stock; one-of-a-kind used items are locked after sale.

### 8.5 E-Commerce Sync Design

The authenticated API is optimized for marketplace synchronization:

```plaintext
External SKU changes
→ find listing via /api/my/listings?sku=...&state=all
→ follow _links.self.href
→ PUT listing update
→ optionally publish/end listing
→ periodically pull orders
→ push shipment/tracking info back to Reverb
```

### 8.6 Auth Does Not Remove the Public Search Cap

Authentication answers "who are you?" and "what can you mutate?" — it does not transform a public search endpoint into a bulk export endpoint. The 50-page cap on `/api/listings/all` likely remains even with a Bearer token. Auth expands account-scoped capabilities (`/api/my/listings` may paginate your own inventory differently) but should not be assumed to unlock unrestricted traversal of all public listings.

### 8.7 Order Action Links (HATEOAS in Practice)

Order responses expose action links that demonstrate HATEOAS beyond what public endpoints show:

- `ship`, `mark_picked_up` — fulfillment transitions
- `purchase_shipping_label`, `packing_slip` — logistics
- `feedback_for_buyer`, `feedback_for_seller` — trust system
- `conversation`, `start_conversation` — messaging
- `payments` — financial details
