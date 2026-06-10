# Chapter 19: `data-*` Attributes & `.dataset` — The Browser-Native Hook System

A study guide for the browser's standard way to attach custom metadata to HTML
elements. Critical for the kind of codebase you are studying: server-rendered
HTML, semantic markup, Pico CSS styling, and small **vanilla JS enhancements**
that progressively layer interactivity on top.

This pattern is what lets you stay frameworkless while still building things
like "Show more / Show less" toggles, lazy HTMX swaps with config, click-outside
dropdowns, and busy-state buttons — all without inventing fake attributes,
overloading CSS classes, or shipping a JS framework.

---

## Why This Matters For Your Interview

The new codebase has a clear philosophy:

```text
Flask renders semantic HTML
+
Pico CSS styles it
+
HTMX adds AJAX behavior declaratively
+
A tiny amount of vanilla JS handles what Pico/HTMX can't
```

Every time you add interactivity that isn't covered by `<details>`, `aria-busy`,
or HTMX, you reach for `data-*` attributes. If asked "how would you add a
'Show more' toggle that changes its label?" or "how would you wire a
click-outside-to-close dropdown?", the answer involves `data-*` attributes and
`.dataset`. Knowing this pattern cold is what makes a vanilla-JS answer feel
professional instead of hacky.

---

## 1. What `data-*` Attributes Are

Any HTML attribute that starts with `data-` is a **custom data attribute**.
The HTML spec defines them as a standard, valid way to attach private metadata
to an element — metadata that the browser will not act on, but your CSS and
JavaScript can read.

```html
<button data-action="open-cart">Cart</button>

<details data-description-disclosure
         data-label-closed="Read more"
         data-label-open="Show less">
  <summary>Read more</summary>
  <p>Full description…</p>
</details>
```

The contract is simple:

- **You** invent the attribute name (with the `data-` prefix)
- **The browser** validates it as HTML, stores it, and exposes it to JS
- **Nothing** happens automatically — you write the CSS or JS that consumes it

This makes `data-*` the cleanest way to declare "this element participates in
this behavior" or "this element carries this small config value" without
inventing fake non-standard attributes (`my-disclosure="true"` would not be
valid HTML) or overloading classes (which should be for styling).

---

## 2. `data-*` Attributes Have **Three** Distinct Uses

Most articles only show one. Internalize all three — they map to different
mental models.

### 2A. Behavior markers (presence-based)

The attribute says "this element participates in this behavior." The value is
irrelevant — only the presence matters.

```html
<details data-description-disclosure>
  <summary>Read more</summary>
  <p>...</p>
</details>

<form data-busy-on-submit>...</form>

<button data-copy-button>Copy link</button>
```

You select these with attribute selectors:

```javascript
document.querySelectorAll("[data-description-disclosure]");
document.querySelectorAll("[data-busy-on-submit]");
document.querySelectorAll("[data-copy-button]");
```

This is much better than using classes as JS hooks:

```javascript
// Anti-pattern — classes are for styling
document.querySelectorAll(".description-disclosure");
```

The reason is a separation-of-concerns rule that has held up across decades of
front-end work:

```text
class="..."   →  styling
data-...      →  JS behavior / configuration
aria-...      →  accessibility semantics / state
```

When you rename a class for design reasons, you don't want JS to break. When
you remove a behavior, you don't want CSS to break. Separating styling hooks
from behavior hooks keeps the two evolving independently.

### 2B. Configuration values (key/value)

The attribute carries a small string the JS needs to do its job.

```html
<button data-loading-text="Saving…">Save</button>

<details data-description-disclosure
         data-label-closed="Read more"
         data-label-open="Show less">
  <summary>Read more</summary>
  <p>...</p>
</details>

<a data-confirm-message="Delete this listing?">Delete</a>
```

JS reads these via `.dataset` (see section 3). This is especially powerful in a
server-rendered app because the **server can render the configuration directly
into the HTML** — no JSON bootstrap, no separate config endpoint, no
JS-template-string concatenation. Jinja2 just writes it:

```jinja2
<button data-loading-text="{{ _('Saving') }}…">{{ _('Save') }}</button>
```

### 2C. State storage (read/write)

Less common, but valid: use `data-*` to track lightweight state your JS owns.

```html
<button data-state="idle">Submit</button>
```

```javascript
button.dataset.state = "loading";
// DOM is now: <button data-state="loading">Submit</button>
```

**Use this sparingly.** For most state, prefer the platform's own primitives:

| Need | Use, not `data-*` |
|---|---|
| Open / closed disclosure | `details.open` |
| Disabled control | `button.disabled` |
| Hidden element | `element.hidden` |
| Checked input | `input.checked` |
| Selected option | `option.selected` |
| ARIA expanded | `aria-expanded="true"` |
| ARIA busy | `aria-busy="true"` |
| Visual state class | `classList.add("is-active")` |

`data-state` is fine for app-specific states the platform has no name for
(e.g. `data-step="confirmation"` in a multi-step form), but reach for native
state first.

---

## 3. The `.dataset` API — Reading and Writing

Every `HTMLElement` has a `.dataset` property. It's a `DOMStringMap` that
exposes the element's `data-*` attributes as JS properties.

### The dash-case ↔ camelCase rule

The browser translates the dash-case after `data-` into camelCase in `.dataset`:

```text
HTML attribute              JS dataset property
-----------------------------------------------
data-label-closed     →     element.dataset.labelClosed
data-label-open       →     element.dataset.labelOpen
data-loading-text     →     element.dataset.loadingText
data-user-id          →     element.dataset.userId
data-description-id   →     element.dataset.descriptionId
data-action           →     element.dataset.action
```

The transformation is mechanical: the first letter after each hyphen is
uppercased, hyphens are removed. Going the other way — assigning
`element.dataset.fooBar = "x"` — adds `data-foo-bar="x"` to the DOM.

### Reading

```javascript
const summary = document.querySelector("summary");

summary.dataset.labelClosed;
// "Read more"

summary.dataset.labelOpen;
// "Show less"

summary.dataset.nonExistent;
// undefined
```

### Writing

```javascript
summary.dataset.labelClosed = "More info";
// DOM is now: <summary data-label-closed="More info">...</summary>

delete summary.dataset.labelClosed;
// data-label-closed attribute is removed
```

### Checking presence

For marker attributes (value doesn't matter), prefer `hasAttribute`:

```javascript
if (element.hasAttribute("data-description-disclosure")) {
  // ...
}
```

`element.dataset.descriptionDisclosure` would return `""` (empty string) for
`<element data-description-disclosure>` — truthy/falsy logic on it is risky.

---

## 4. Critical Gotcha: Values Are Always Strings

This trips up everyone at least once.

Given:

```html
<button data-page-size="20"
        data-enabled="false"
        data-options='{"compact":true}'>...</button>
```

JS gives you:

```javascript
button.dataset.pageSize;   // "20"      ← string, not 20
button.dataset.enabled;    // "false"   ← string, not false
button.dataset.options;    // '{"compact":true}'  ← string, not an object
```

So:

```javascript
button.dataset.enabled         // "false"
Boolean(button.dataset.enabled) // true  ← any non-empty string is truthy!
```

You have to parse explicitly:

```javascript
const pageSize = Number(button.dataset.pageSize ?? 10);
const enabled = button.dataset.enabled === "true";
const options = JSON.parse(button.dataset.options ?? "{}");
```

For labels and other text, this is a non-issue — strings stay strings. For
booleans and numbers, always parse.

---

## 5. `data-*` Attributes Are NOT Real Boolean Attributes

This is one of the most misunderstood points. The platform has a small set of
**real** boolean HTML attributes:

```html
<input disabled>
<input checked>
<input required>
<input readonly>
<option selected>
<details open>
<script async>
<script defer>
```

For these, the presence of the attribute means `true` and the absence means
`false`. The browser's parser and the corresponding IDL property handle this
specially:

```javascript
input.disabled;  // true (boolean!)
details.open;    // true (boolean!)
```

**`data-*` attributes are not in this set.** The browser does not know that
`data-description-disclosure` should mean true. It just stores it as a custom
attribute with an empty-string value:

```html
<details data-description-disclosure>
```

is parsed as if you wrote:

```html
<details data-description-disclosure="">
```

So:

```javascript
details.hasAttribute("data-description-disclosure");
// true   ← presence is true

details.getAttribute("data-description-disclosure");
// ""     ← value is the empty string

details.dataset.descriptionDisclosure;
// ""     ← same as getAttribute
```

The value is **not** `true`. The **presence** is true. That's why the
attribute selector `[data-description-disclosure]` works for selection — it
matches on presence, not on a truthy value.

### Practical rule

| Type | Pattern | Read with |
|---|---|---|
| Marker (boolean-style) | `data-foo` (no value) | `hasAttribute("data-foo")` or `[data-foo]` selector |
| Configuration | `data-foo="value"` | `element.dataset.foo` |
| Boolean-like config | `data-animate="true"` | `element.dataset.animate === "true"` |

Note that for the third row you write the value explicitly as `"true"` /
`"false"` strings, then parse. You cannot rely on presence-as-truth the way
`disabled` works.

---

## 6. Naming Conventions

A few conventions keep `data-*` attributes readable across a codebase.

### Always dash-case in HTML

```html
<!-- Good -->
<button data-label-open="Show less">

<!-- Bad — JS still works but breaks convention -->
<button data-labelOpen="Show less">
<button data_label_open="Show less">
```

The dash-case form is the only one the HTML spec sanctions, and it's what
`.dataset` is designed for. Underscores and camelCase in attribute names
technically parse but are non-idiomatic.

### Group related keys with a shared prefix

When several attributes belong to the same behavior, put the common noun first
so they group naturally:

```html
<!-- Good — sorts together, scans as a group -->
<details data-label-closed="Read more"
         data-label-open="Show less">

<!-- Less good — the suffix changes, so they don't group -->
<details data-closed-label="Read more"
         data-open-label="Show less">
```

In JS:

```javascript
details.dataset.labelClosed
details.dataset.labelOpen
```

Pick one convention per codebase and stick to it. Supporting both
(`labelOpen ?? openLabel`) is only worth it for legacy compatibility.

### Marker name = behavior name

A marker attribute should read like a component or behavior name:

```html
<details data-description-disclosure>     <!-- a "description disclosure" behavior -->
<form data-busy-on-submit>                <!-- a "busy on submit" behavior -->
<a data-confirm-action>                   <!-- a "confirm action" behavior -->
```

Avoid generic names that could collide across behaviors:

```html
<!-- Too generic — what kind of "enabled"? -->
<button data-enabled>

<!-- Specific — clear what it enables -->
<button data-keyboard-shortcut-enabled>
```

### Put config on the behavior root, not on children

A common refactor improvement: keep configuration on the same element that
carries the marker, so the behavior's contract lives in one place.

```html
<!-- Less good — config scattered between root and child -->
<details data-description-disclosure>
  <summary data-label-closed="Read more"
           data-label-open="Show less">Read more</summary>
  <p>...</p>
</details>

<!-- Better — root carries both the marker and the config -->
<details data-description-disclosure
         data-label-closed="Read more"
         data-label-open="Show less">
  <summary>Read more</summary>
  <p>...</p>
</details>
```

Then JS reads everything off the behavior root:

```javascript
details.dataset.labelClosed
details.dataset.labelOpen
```

---

## 7. The Three-Attribute-System Pattern

This is the recommended division of labor in a Pico + vanilla JS codebase:

| Purpose | Use |
|---|---|
| Styling | `class="listing-card"` |
| Behavior hook / configuration | `data-description-disclosure`, `data-label-closed="…"` |
| Accessibility semantics & state | `aria-expanded="true"`, `aria-busy="true"`, `aria-label="…"`, `role="…"` |
| Real platform state | `open`, `disabled`, `hidden`, `checked`, `selected` |

So a richly-enhanced element might look like:

```html
<details class="description-disclosure"
         data-description-disclosure
         data-label-closed="Read more"
         data-label-open="Show less">
  <summary aria-expanded="false">Read more</summary>
  <p>...</p>
</details>
```

Where:

- `class="description-disclosure"` — styling hook for CSS
- `data-description-disclosure` — behavior marker for JS
- `data-label-closed` / `data-label-open` — configuration for the behavior
- `aria-expanded="false"` — accessibility state (the JS keeps it in sync)
- `<details open>` (when toggled) — the actual platform state

Each attribute has one job. CSS, JS, and assistive tech read different
attributes and don't fight each other.

---

## 8. Full Worked Example — "Show more / Show less"

This is the canonical pattern the rest of the codebase's enhancements would
mirror.

### HTML (server-rendered by Jinja2)

```jinja2
<details class="description-disclosure"
         data-description-disclosure
         data-label-closed="Read full description"
         data-label-open="Show less">
  <summary>Read full description</summary>
  <p>{{ listing.description }}</p>
</details>
```

### JavaScript (one small enhancement function)

```javascript
function enhanceDescriptionDisclosures(root = document) {
  const disclosures = root.querySelectorAll("[data-description-disclosure]");

  disclosures.forEach((details) => {
    const summary = details.querySelector("summary");
    if (!summary) return;

    const labelClosed = details.dataset.labelClosed ?? "Show more";
    const labelOpen = details.dataset.labelOpen ?? "Show less";

    const syncLabel = () => {
      summary.textContent = details.open ? labelOpen : labelClosed;
    };

    syncLabel();
    details.addEventListener("toggle", syncLabel);
  });
}

enhanceDescriptionDisclosures();
```

### What each piece does

| Line | What it does |
|---|---|
| `querySelectorAll("[data-description-disclosure]")` | Finds every element that opts into the behavior — selecting on the **marker**, not on a class |
| `details.querySelector("summary")` | Scopes the trigger lookup to inside the behavior root |
| `details.dataset.labelClosed ?? "Show more"` | Reads the closed-state label from config, falls back to a default |
| `details.open ? … : …` | Reads the native platform state (the `open` IDL property on `HTMLDetailsElement`) |
| `details.addEventListener("toggle", …)` | Listens to the native `toggle` event that `<details>` fires when its state changes |

The JS does **only** what the platform can't: synchronize the trigger label
with the open state. Everything else — the disclosure behavior, the keyboard
support, the focus management, the `aria-expanded` state, the visual styling —
is handled by the browser and Pico.

### Calling it after HTMX swaps content

If HTMX swaps in new content that contains new `data-description-disclosure`
elements, re-run the enhancer on just the new fragment:

```javascript
document.body.addEventListener("htmx:afterSwap", (e) => {
  enhanceDescriptionDisclosures(e.detail.target);
});
```

The optional `root` parameter exists for exactly this reason.

---

## 9. What NOT To Do With `data-*`

A few anti-patterns to recognize and avoid.

### Don't store secrets or sensitive data

```html
<!-- BAD — anyone can read this in DevTools -->
<form data-csrf-token="abc123">
<button data-user-email="alice@example.com">
```

The DOM is public to anyone with the page open. Use proper auth tokens in
headers, server-side session data, or HTTP-only cookies for anything sensitive.

### Don't stuff large JSON blobs

```html
<!-- BAD — gigantic attribute value, awkward to parse, fragile to escape -->
<div data-config='{"users":[{"id":1,...},{"id":2,...}], ...}'></div>
```

For more than a handful of fields, use a dedicated `<script type="application/json">`
block or a separate fetch:

```html
<script type="application/json" id="initial-state">
  {"users": [...], "filters": {...}}
</script>
```

```javascript
const state = JSON.parse(document.getElementById("initial-state").textContent);
```

### Don't use classes as JS hooks when the class is visual

```html
<!-- BAD — JS now depends on a CSS class name -->
<button class="btn-primary search-trigger">Search</button>
```

```javascript
document.querySelectorAll(".search-trigger")
```

When a designer renames the class, your JS breaks silently. Use a `data-*`
hook:

```html
<button class="btn-primary" data-search-trigger>Search</button>
```

### Don't mix naming styles

```html
<!-- BAD — three different conventions in one component -->
<details data-open-label="..."
         data-label-closed="..."
         data_is_active="...">
```

Pick one and stick to it.

---

## 10. Quick Reference

```text
SELECTING
[data-foo]              all elements with the attribute (any value)
[data-foo="bar"]        elements where value equals "bar"
[data-foo~="bar"]       elements where value is a space-separated list containing "bar"
[data-foo^="bar"]       value starts with "bar"
[data-foo$="bar"]       value ends with "bar"
[data-foo*="bar"]       value contains "bar"

READING (JS)
element.dataset.foo                  →  string value, or undefined
element.dataset.fooBar               →  reads data-foo-bar
element.hasAttribute("data-foo")     →  boolean for presence

WRITING (JS)
element.dataset.foo = "value"        →  sets data-foo="value"
delete element.dataset.foo           →  removes the attribute
element.setAttribute("data-foo", "") →  presence-only marker

PARSING (because values are strings)
const n = Number(el.dataset.count ?? 0);
const b = el.dataset.enabled === "true";
const o = JSON.parse(el.dataset.options ?? "{}");

CONVENTION
class="..."   →  styling
data-...      →  JS behavior / configuration
aria-...      →  accessibility semantics / state
open / disabled / checked / hidden  →  real platform state
```

---

## 11. Interview Script

> "The codebase is server-rendered HTML enhanced with small bits of vanilla JS,
> so `data-*` attributes are the right tool for any JS hook. I use them in
> three ways: presence-only markers like `data-description-disclosure` to flag
> which elements participate in a behavior, key/value pairs like
> `data-label-open="Show less"` to pass small configuration from the server-
> rendered HTML into the JS, and occasionally state storage when the platform
> has no native equivalent. I read them through `.dataset`, which handles the
> dash-case to camelCase mapping. The mental model I use: classes are for
> styling, ARIA attributes are for accessibility state, real boolean attributes
> like `open` and `disabled` are for native state, and `data-*` is for
> everything in between that my JS needs to wire up. The big trap is that
> `data-*` values are always strings — `data-enabled="false"` is **truthy** —
> so I always parse explicitly with `=== "true"`, `Number()`, or `JSON.parse()`
> when the value isn't already text."
