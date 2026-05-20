# Reverb Public API — Public Routes Exploration Report

**Date:** 2026-05-20
**API Base URL:** `https://api.reverb.com/api`
**API Version:** 3.0
**Content Type:** `application/hal+json`

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

### 2.6 Caching Behavior

- **Categories endpoint:** `Cache-Control: max-age=86400, public` — cached for 24 hours (static data).
- **Listings endpoint:** `Cache-Control: no-cache` — always fresh (dynamic data).

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

### 3.4 Total Categories

```bash
# Command:
curl -s ... "https://api.reverb.com/api/categories/flat" | jq '.categories | length'

# Result:
320
```

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

**Note:** Despite ~2.5M total listings, `total_pages` is capped at 50 (a common API pattern to prevent deep pagination abuse).

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

In the collection view (`/listings/all`), only **1 photo** is returned per listing. The individual listing endpoint (`/api/listings/{id}`) likely returns more.

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

## 5. Complete Command Reference

Below is the full list of every `curl | jq` command used in this exploration, in the order they were executed.

### 5.1 Categories Endpoint Commands

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
```

### 5.2 Listings Endpoint Commands

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

## 6. Key Observations Summary

1. **HAL compliance is partial** — Reverb uses `_links` extensively but does not use `_embedded`. Related resources are inlined as plain JSON properties instead.
2. **Categories are flat, not hierarchical** — All 320 subcategories are returned in a single flat array. Parent-child relationships are expressed via `root_uuid` / `root_slug` rather than nesting.
3. **Listings pagination is capped** — Despite ~2.5M total listings, `total_pages` is capped at 50 regardless of `per_page`. Deep pagination requires filters.
4. **No authentication required** — Both endpoints work without auth tokens for read access.
5. **Caching differs by endpoint** — Categories are edge-cached for 24 hours; listings are never cached (`no-cache`).
6. **The `cart` link demonstrates HATEOAS** — The correct cart URL (`/api/cart/{listing_id}`) is discovered through `_links.cart.href` on each listing, not constructed manually. Attempting to GET this URL directly returns an error — it likely only accepts POST (to add items to cart) and requires authentication.
7. **Photos are HAL sub-resources** — The `photos` array uses `_links` internally (with `large_crop`, `small_crop`, `full`, `thumbnail`), making photos the closest thing to `_embedded` resources in the response, even though they aren't wrapped in `_embedded`.
8. **Price is triple-encoded** — Prices include `amount` (string), `amount_cents` (integer), and `display` (formatted string with symbol), giving consumers flexibility.
