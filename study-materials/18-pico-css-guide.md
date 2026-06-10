# Chapter 18: Pico CSS v2 — Interview Reference Guide

A focused field guide for the interview. What Pico styles for free, the small set
of utility classes worth knowing, the patterns most likely to come up while
extending this codebase, and how to handle interactive patterns Pico
intentionally leaves to the platform.

Read [Chapter 17](17-pico-css-audit.md) first for the audit of how Pico is
*actually used* in the codebase. This chapter is the toolkit.

---

## Mental Model

Pico v2 is a **semantic CSS framework**. It styles native HTML elements directly.
Most of what you need is:

1. Write semantic HTML
2. Add one of ~5 utility classes when you need them
3. Customize via `--pico-*` CSS custom properties
4. Use HTML5 elements (`<details>`, `aria-*` attributes) for declarative
   interactivity — no JavaScript framework

Pico ships at ~10KB, has no JavaScript, and intentionally has no utility classes
in the Tailwind/Bootstrap sense. If you find yourself reaching for `.mt-4`
or `.col-md-6`, you're in the wrong framework.

---

## What Pico Styles For Free (Semantic Defaults)

These are the elements you can drop into a template with no class and get
sensible styles. Know this list cold — it's the foundation of every Pico answer.

### Document structure

| Element | Pico default |
|---|---|
| `<body>` | Sets base font, color, background from theme |
| `<header>` `<main>` `<footer>` (inside `<body>`) | Vertical spacing as page sections |
| `<article>` | **Card** — border, border-radius, padding, margin |
| `<section>` | Vertical spacing only — no visual chrome |
| `<aside>` | Sidebar styling; turns `<nav>` inside it into vertical stack |
| `<hr>` | Themed horizontal rule |
| `<blockquote>` | Indented quote with left border |
| `<figure>` `<figcaption>` | Centered figure with muted caption |

### Typography

| Element | Pico default |
|---|---|
| `<h1>` … `<h6>` | Scaled headings using `--pico-h{n}-font-size` tokens |
| `<p>` | Standard paragraph spacing |
| `<small>` | 0.875em — useful for helper text under inputs |
| `<mark>` | Highlight (uses theme color) |
| `<code>` `<pre>` `<kbd>` | Monospace with subtle background |
| `<abbr title="...">` | Dotted underline + tooltip on hover |
| `<strong>` `<b>` `<em>` `<i>` | Bold / italic (use `<strong>`/`<em>` for semantics) |
| `<a>` | Themed accent color, underline on hover |

### Lists

| Element | Pico default |
|---|---|
| `<ul>` `<ol>` `<li>` | Standard bullets/numbers with spacing |
| `<ul>` inside `<nav>` | Horizontal inline list (no bullets) |
| `<ul>` inside `<aside>` | Vertical stack |
| `<dl>` `<dt>` `<dd>` | Definition list with indented descriptions |

### Forms

| Element | Pico default |
|---|---|
| `<input>` (text, email, etc.) | Full-width, themed, themed focus ring |
| `<select>` | Styled with a chevron icon |
| `<textarea>` | Resizable, themed |
| `<button>` `<input type="submit">` | Primary button styling, full-width inside `<form>` |
| `<input type="reset">` | Secondary style by default |
| `<input type="checkbox">` `<input type="radio">` | Themed |
| `<input type="checkbox" role="switch">` | Toggle switch |
| `<input type="range">` | Themed slider |
| `<input type="file">` | Themed file picker |
| `<input type="color">` | Themed color swatch |
| `<fieldset>` `<legend>` | Grouped form section with label |
| `<label>` | Stacks naturally above its input |
| `<progress>` | Themed progress bar |
| `<small>` after an input | Muted helper text |

### Tables

| Element | Pico default |
|---|---|
| `<table>` | Full-width, themed borders |
| `<thead>` `<tbody>` `<tfoot>` | Distinct header styling |
| `<th>` `<td>` | Padded cells, left-aligned text |

### Media

| Element | Pico default |
|---|---|
| `<img>` `<video>` `<iframe>` | Responsive (`max-width: 100%`) |
| `<picture>` | Behaves like `<img>` |

### Interactive (declarative — no JS)

| Element | Pico default |
|---|---|
| `<details>` `<summary>` | Native collapsible disclosure widget |
| `<dialog>` | Modal styling (use `dialog.showModal()` in JS to open) |
| `<details class="dropdown">` | Dropdown menu (still no JS — uses native `<details>`) |
| `<button data-tooltip="...">` | Tooltip on hover |
| `aria-busy="true"` | Loading spinner on the element |
| `aria-invalid="true"` / `"false"` | Red / green validation state on inputs |

---

## The Utility Classes Worth Knowing

Pico has very few utility classes. This is the full set you actually need:

### Layout

| Class | Effect |
|---|---|
| `.container` | Centered, max-width, responsive padding |
| `.container-fluid` | Full-width, responsive padding |
| `.grid` | Equal-width auto-layout columns (collapses to 1 col below 768px) |
| `.overflow-auto` | Wraps a `<table>` for horizontal scroll on overflow |

### Button / link variants (only with default `pico.min.css`, not classless)

| Class | On `<button>` / `<a>` / `role="button"` |
|---|---|
| `.secondary` | Muted secondary button style |
| `.contrast` | High-contrast button style |
| `.outline` | Outlined variant — combine with `.secondary` / `.contrast` |

### Grouping

| Class | Effect |
|---|---|
| `role="group"` (on a `<div>` or `<fieldset>`) | Joins children edge-to-edge (button bars, input+button pairs) |

### Nav links

| Class | On `<a>` inside `<nav>` |
|---|---|
| `.secondary` | Muted nav link |
| `.contrast` | High-contrast nav link |

### Dropdown

| Class | Effect |
|---|---|
| `.dropdown` (on `<details>`) | Turns it into a dropdown menu |
| `role="button"` (on `<summary>`) | Renders the dropdown trigger as a button |
| `dir="rtl"` (on the dropdown `<ul>`) | Aligns the menu to the right edge |

**That is the full set.** No spacing utilities (`mt-*`, `p-*`), no display
utilities (`d-flex`, `d-none`), no color utilities. If you need those, write
them in `app.css` or override `--pico-*` tokens.

---

## Customization via CSS Custom Properties

This is the Pico way to override anything. The `--pico-*` tokens are namespaced
and theme-aware (they change with light/dark mode).

### Most-used tokens

| Token | Purpose |
|---|---|
| `--pico-spacing` | Default spacing unit (1rem) |
| `--pico-border-radius` | Default border radius |
| `--pico-border-width` | Default border width (1px) |
| `--pico-muted-border-color` | Subtle border color (cards, inputs) |
| `--pico-muted-color` | Muted text color |
| `--pico-color` | Main text color |
| `--pico-background-color` | Body background |
| `--pico-card-background-color` | Card surface color |
| `--pico-card-sectioning-background-color` | Card header/footer surface |
| `--pico-primary` / `--pico-primary-hover` | Link / button accent |
| `--pico-secondary` | Secondary button color |
| `--pico-form-element-spacing-vertical` | Input padding (vertical) |
| `--pico-form-element-spacing-horizontal` | Input padding (horizontal) |
| `--pico-typography-spacing-vertical` | Spacing between `<p>`, `<ul>`, etc. |
| `--pico-nav-element-spacing-vertical` | Nav item vertical spacing |
| `--pico-nav-element-spacing-horizontal` | Nav item horizontal spacing |

### Two scopes for overrides

```css
/* Global — applies everywhere */
:root {
  --pico-primary: hsl(280 80% 50%);
  --pico-border-radius: 0.25rem;
}

/* Scoped — only this element and its children */
.dashboard-card {
  --pico-card-background-color: hsl(220 20% 95%);
}
```

Scoped overrides are almost always better than global ones. They keep changes
local and avoid the cascade problems described in [Chapter 17](17-pico-css-audit.md).

---

## Deciding: Default, `var(--pico-*)`, or Token Override?

Three situations come up constantly when writing `app.css` against Pico, and
mixing them up is the most common source of redundancy and cascade fights:

1. The value is **already applied** by Pico → your rule is redundant
2. The value is **not** applied, and you want it theme-aware → reference a token
3. The value **is** applied via a token but you want a different value → override
   the token, don't write a competing property

Each has a concrete way to check.

### 1. "Does Pico already set this on the element?"

The fastest check is **browser DevTools**. Inspect the element and look at the
**Styles** or **Computed** panel. If a rule comes from `pico.min.css`, Pico is
already applying it — adding the same property in `app.css` is dead weight.

A second check is to search the [Pico source on GitHub](https://github.com/picocss/pico/tree/main/scss)
for the element name (`article`, `h1`, `button`, etc.) and read the rule.

Quick reference for the most common cases:

| Element | What Pico already sets |
|---|---|
| `<article>` | `border-radius`, `padding` (via `--pico-block-spacing-*`), `background`, `box-shadow` — but **not** `border` |
| `<h1>`–`<h6>` | `font-weight`, `font-size`, `margin-bottom` |
| `<a>` | `color` (via `--pico-primary`), underline on hover |
| `<button>` | padding, background, `border-radius`, `font-weight` |
| `<input>` | padding, border, `border-radius`, `width: 100%` |
| `<small>` | `font-size: 0.875em` |

If Pico already provides it → **delete your rule**. Example from the codebase:

```css
/* Redundant — <article> already has border-radius from Pico */
.category-card {
  border-radius: var(--pico-border-radius);
}
```

### 2. "When should I write `var(--pico-*)` in a new rule?"

Ask one question:

> *Would this value need to change if the user switched to dark mode, or if Pico's theme was customized?*

- **Yes** → reference the token, so the value follows the theme automatically
- **No** → hardcode it; tokens for app-specific values don't exist and shouldn't

```css
/* Theme-sensitive — use tokens */
.listing-card {
  border: 1px solid var(--pico-muted-border-color);
  color: var(--pico-muted-color);
}

/* Layout dimensions — no token exists, hardcoding is correct */
.search-form {
  max-width: 600px;
}

.listings-grid {
  gap: 1.5rem;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
}
```

Things that almost always *should* use a token:

- Colors of any kind (`color`, `background`, `border-color`)
- `border-radius`
- `border-width`
- Spacing values that match `--pico-spacing` (1rem) or the typography spacing

Things that almost always *should not*:

- `gap` (no Pico equivalent)
- Layout dimensions (`max-width`, `min-height`, grid track sizes)
- Brand-specific font sizes and weights for non-text components (logos, icons)
- Asset dimensions (logo SVG `width`/`height`)

### 3. "When should I override a token instead of setting a property?"

This is the subtle case. If Pico already styles the element **through a token**,
and you want a *different value*, the Pico-idiomatic way is to **reassign the
token on your scoped class** — not to write a higher-specificity property
declaration that fights Pico's own rule.

```css
/* Wrong — fights Pico's cascade with a competing property
   Pico's <article> rule still runs; yours just overrides it with a raw value
   that won't track theme changes. */
.category-card {
  padding: 0.75rem;
}

/* Right — override the token Pico itself uses
   Pico's <article> rule reads --pico-block-spacing-* and picks up your value. */
.category-card {
  --pico-block-spacing-vertical: 0.75rem;
  --pico-block-spacing-horizontal: 0.75rem;
}
```

Why this matters:

- Your override stays *inside* Pico's token system, so dark-mode and theme
  changes still flow through.
- You don't increase specificity, so other Pico rules (hover states, focus
  rings, breakpoint adjustments) keep working.
- A reader can see immediately that you intentionally customized a Pico value,
  rather than that you added a one-off rule.

How to find the right token: inspect the element in DevTools, find the Pico
rule that sets the property, and look at which `--pico-*` variable it
references. That's the token to override on your class.

### Decision tree

```text
Does Pico already apply this value to the element?
│
├── Yes
│   │
│   ├── Same value I want?      → DELETE my rule (redundant)
│   │
│   └── Different value?
│       │
│       ├── Pico set it via a --pico-* token?
│       │       → OVERRIDE the token on a scoped class
│       │
│       └── Pico set it directly (no token)?
│               → Write a property override, scoped as tightly as possible
│
└── No, Pico doesn't set this
    │
    ├── Should the value follow the theme?
    │       → Use var(--pico-*)
    │
    └── App-specific (gap, max-width, brand size)?
            → Hardcode it
```

### Applied to the current `app.css`

| Rule | Verdict | Reason |
|---|---|---|
| `.category-card { border-radius: var(--pico-border-radius) }` | Delete | `<article>` already has it |
| `.category-card { padding: 1rem }` | Override token instead | Pico sets padding via `--pico-block-spacing-*` |
| `.listing-card { border: 1px solid var(--pico-muted-border-color) }` | Keep | Pico uses `box-shadow`, not border, on `<article>` — load-bearing |
| `.listing-card img { margin-bottom: 1rem }` | Use token | `1rem` is exactly `--pico-spacing` |
| `.empty-state { color: var(--pico-muted-color) }` | Keep | Theme-aware color, correct usage |
| `.search-form { max-width: 600px }` | Hardcode | No Pico token for form widths |
| `.listings-grid { gap: 1.5rem }` | Hardcode | No `--pico-gap` exists |

---

## Patterns Likely To Come Up Extending This Codebase

The interview scenarios involve adding features to the existing pages. These are
the Pico patterns you would most likely reach for.

### A real button instead of `<input type="submit">`

```html
<!-- Current in categories/index.html -->
<input type="submit" value="Search">

<!-- Replacement — same look, can hold icons/loading state -->
<button type="submit">Search</button>
```

### Helper text below an input (e.g. for pagination, "showing X of Y")

```html
<input type="text" name="search" placeholder="Search...">
<small>Showing {{ results|length }} of {{ total }} results</small>
```

### Loading state on a button (for slow API calls)

```html
<!-- Submit button while waiting for the Reverb API -->
<button type="submit" aria-busy="true">Searching…</button>

<!-- Icon-only spinner -->
<button aria-busy="true" aria-label="Please wait..."></button>
```

### Input validation state (for empty search, invalid filter)

```html
<input
  type="text"
  name="price_min"
  aria-invalid="true"
  aria-describedby="price-error">
<small id="price-error">Minimum price must be a number</small>
```

### Card with header and footer (for a richer listing card)

```html
<article>
  <header>
    <strong>Fender Stratocaster</strong>
  </header>
  <img src="..." alt="...">
  <p>Mint condition, all original parts.</p>
  <footer>
    <a href="#" role="button">View details</a>
  </footer>
</article>
```

### Group: input + button pair (search form on one line)

```html
<form>
  <fieldset role="group">
    <input type="text" name="search" placeholder="Search...">
    <input type="submit" value="Search">
  </fieldset>
</form>
```

`role="group"` joins them edge-to-edge with no gap and a shared border radius.

### Breadcrumb nav

```html
<nav aria-label="breadcrumb">
  <ul>
    <li><a href="{{ url_for('categories.index') }}">Home</a></li>
    <li><a href="{{ url_for('categories.index') }}">Categories</a></li>
    <li>Guitars</li>
  </ul>
</nav>
```

The `aria-label="breadcrumb"` triggers Pico's breadcrumb styling with `>`
dividers automatically.

### Loading skeleton on a card (during HTMX swap)

```html
<article aria-busy="true">
  <!-- Pico renders a spinner; content can be empty during load -->
</article>
```

### Tooltip on a small UI hint

```html
<button data-tooltip="Save this search" data-placement="bottom">★</button>
```

### Modal (for confirmation dialogs, gear details overlay)

```html
<dialog id="confirm-dialog">
  <article>
    <header>
      <strong>Remove from favorites?</strong>
    </header>
    <p>This will remove the listing from your saved gear.</p>
    <footer>
      <button class="secondary" onclick="this.closest('dialog').close()">Cancel</button>
      <button>Remove</button>
    </footer>
  </article>
</dialog>

<script>
  document.getElementById('open-btn').addEventListener('click', () => {
    document.getElementById('confirm-dialog').showModal();
  });
</script>
```

`<dialog>` is a native HTML element. Pico styles it, but you still need
`dialog.showModal()` / `dialog.close()` in JS to open/close. The HTML and styling
are declarative; the trigger is not.

---

## Progressive Disclosure: Bootstrap Collapse vs Pico

This is a common interview topic because the patterns differ in philosophy.

### Bootstrap's approach (the "collapse toggle pair")

Bootstrap requires a trigger + target pair with `data-bs-toggle`/`data-bs-target`
attributes and a JS controller to wire them up:

```html
<button class="btn"
        data-bs-toggle="collapse"
        data-bs-target="#filters">
  Show filters
</button>

<div class="collapse" id="filters">
  ...filter controls...
</div>
```

Requires `bootstrap.bundle.js`. The JS reads the data attributes, finds the
target, manages `aria-expanded`, animates the collapse, and toggles the class.

### Pico's approach: native `<details>` / `<summary>`

Pico delegates to the **browser's built-in disclosure widget**. No JS, no data
attributes, no controller. The trigger and target are *the same element*:

```html
<details>
  <summary>Show filters</summary>
  <!-- Content lives inside <details>, hidden until summary is clicked -->
  <fieldset>
    <label>
      <input type="checkbox" name="condition" value="mint">
      Mint condition
    </label>
    <label>
      <input type="checkbox" name="condition" value="used">
      Used
    </label>
  </fieldset>
</details>
```

That is the entire pattern. The browser handles open/close, keyboard navigation
(Enter / Space), and `aria-expanded` automatically.

### Side-by-side comparison

| | Bootstrap Collapse | Pico `<details>` |
|---|---|---|
| HTML structure | Trigger + separate target | Single `<details>` wrapping both |
| JS required | Yes (`bootstrap.bundle.js`) | No |
| ARIA management | JS-managed | Native browser |
| Keyboard support | JS-managed | Native browser |
| Animation | CSS height transition (JS-driven) | Native (browser-dependent; usually instant) |
| Multiple targets per trigger | Yes (selector list) | No (1:1) |
| Trigger anywhere on the page | Yes | No — `<summary>` must be the first child of `<details>` |
| Persistence on refresh | No (without JS) | `open` attribute persists if server-rendered |

### When Pico's `<details>` is sufficient

- Filter panels
- "Show more" descriptions
- Optional form fields
- FAQ-style sections
- Sidebar menu groups

### When you actually need a Bootstrap-style collapse

- The trigger needs to live elsewhere on the page (e.g., a top-bar button
  opening a sidebar)
- You need to toggle multiple unrelated regions from one button
- You need custom animation tied to the toggle

### Accordion variant (only one section open at a time)

Pico supports this declaratively with the HTML `name` attribute on `<details>`:

```html
<details name="filters" open>
  <summary>Category</summary>
  <!-- options -->
</details>

<details name="filters">
  <summary>Price range</summary>
  <!-- options -->
</details>

<details name="filters">
  <summary>Condition</summary>
  <!-- options -->
</details>
```

When `<details>` elements share the same `name`, opening one automatically
closes the others. This is a **native HTML5 feature**, not a Pico feature —
Pico just styles it correctly.

### Dropdown menu (true menu, not just disclosure)

Pico extends `<details>` with `.dropdown` for menu-style behavior:

```html
<details class="dropdown">
  <summary>Sort by</summary>
  <ul>
    <li><a href="?sort=price_asc">Price: low to high</a></li>
    <li><a href="?sort=price_desc">Price: high to low</a></li>
    <li><a href="?sort=newest">Newest first</a></li>
  </ul>
</details>
```

Place inside a `<nav>` for a top-bar dropdown menu. Still no JS. Click outside
to close requires browser native behavior — note that `<details>` does *not*
auto-close when you click outside it; for true menu UX you may want a small
JS snippet or progressive enhancement.

### Combining with HTMX (for server-driven progressive disclosure)

```html
<details>
  <summary>Show recent searches</summary>
  <!-- Loaded only when opened -->
  <div hx-get="/searches/recent"
       hx-trigger="toggle from:closest details once"
       hx-swap="innerHTML">
    Loading…
  </div>
</details>
```

The content fetches lazily on first open. This is the pattern that matches the
new codebase's HTMX-ready setup.

---

## Description Disclosure Patterns

Two progressive enhancement patterns for "Read more / Show less" descriptions on
listing cards. Both build on native `<details>` — they differ in how much they
rely on JavaScript.

### Pattern 1 — JS label swap (dynamic trigger text)

The `<summary>` is always visible. Its text updates to reflect the open/closed
state. A `toggle` event listener reads `data-*` attributes to know what label
to display.

```html
<article>
  <h2>Fender American Professional II Stratocaster</h2>

  <p>
    A versatile modern Strat with V-Mod pickups, a comfortable neck profile,
    and classic Fender switching.
  </p>

  <details data-description-disclosure>
    <summary data-closed-label="Read full description" data-open-label="Show less">
      Read full description
    </summary>

    <div>
      <p>
        This guitar expands on the classic Stratocaster design with updated
        electronics, improved playability, and a more refined neck heel for
        upper-fret access.
      </p>

      <p>
        It is especially useful for players who want traditional Fender tones
        but need a more modern, stable, gig-ready instrument.
      </p>
    </div>
  </details>
</article>
```

```javascript
function enhanceDescriptionDisclosures(root = document) {
  root.querySelectorAll("[data-description-disclosure]").forEach((details) => {
    const summary = details.querySelector("summary");
    if (!summary) return;

    const closedLabel =
      summary.dataset.closedLabel ||
      summary.dataset.labelClosed ||
      "Read full description";

    const openLabel =
      summary.dataset.openLabel ||
      summary.dataset.labelOpen ||
      "Show less";

    const syncLabel = () => {
      summary.textContent = details.open ? openLabel : closedLabel;
    };

    syncLabel();
    details.addEventListener("toggle", syncLabel);
  });
}

enhanceDescriptionDisclosures();
```

**When to use:** The summary trigger is always present and accessible with no
extra markup. Simple and works even without CSS support.

### Pattern 2 — CSS visibility swap (summary ↔ close button)

The `<summary>` is only visible when the `<details>` is **closed**. When open,
it hides via CSS and a dedicated "Show less" button inside the content takes
over. The two triggers never appear at the same time.

```html
<article>
  <h2>Fender American Professional II Stratocaster</h2>

  <p>
    A versatile modern Strat with V-Mod pickups, a comfortable neck profile,
    and classic Fender switching.
  </p>

  <details data-description-disclosure>
    <summary>Read full description</summary>

    <div>
      <p>
        This guitar expands on the classic Stratocaster design with updated
        electronics, improved playability, and a more refined neck heel for
        upper-fret access.
      </p>

      <p>
        It is especially useful for players who want traditional Fender tones
        but need a more modern, stable, gig-ready instrument.
      </p>

      <!-- Only visible when open; hides the summary above -->
      <button type="button" class="secondary outline" data-close-disclosure>
        Show less
      </button>
    </div>
  </details>
</article>
```

```css
/* Hide summary while open — the close button inside takes over */
details[data-description-disclosure][open] > summary {
  display: none;
}

/* Hide the close button while closed — summary is the trigger */
details[data-description-disclosure]:not([open]) [data-close-disclosure] {
  display: none;
}
```

```javascript
function enhanceDescriptionDisclosures(root = document) {
  root.querySelectorAll("[data-description-disclosure]").forEach((details) => {
    details.querySelectorAll("[data-close-disclosure]").forEach((btn) => {
      btn.addEventListener("click", () => {
        details.removeAttribute("open");
      });
    });
  });
}

enhanceDescriptionDisclosures();
```

**How it works:**

- `details[open] > summary { display: none }` — CSS hides the `<summary>` the
  moment the `<details>` opens; no JS needed for this half.
- `details:not([open]) [data-close-disclosure] { display: none }` — CSS hides
  the close button when closed; again, no JS.
- The single JS listener just calls `details.removeAttribute("open")` when the
  close button is clicked, since a button inside the content cannot close
  `<details>` natively.

**When to use:** When you want the trigger to visually disappear once the
content is revealed — for example, a "Read full description" link that should
not be visible alongside the description it reveals.

### Side-by-side comparison

| | Pattern 1 (label swap) | Pattern 2 (visibility swap) |
|---|---|---|
| Summary always visible | Yes | Only when closed |
| Close button inside content | No | Yes |
| Label logic | JS (`toggle` event) | CSS (`details[open]` selector) |
| JS required | Yes (label sync) | Yes (close button only) |
| Works without CSS | Yes (labels still update) | Partially (summary always visible) |
| Extra HTML | `data-*` attributes on summary | `<button data-close-disclosure>` in content |

---

## Improvements Worth Mentioning In The Interview

A short list of Pico-aware suggestions you can make if asked "what would you
improve about the UI?":

1. **Switch `<input type="submit">` to `<button type="submit">`** — same Pico
   style, but supports icons, loading state (`aria-busy`), and child elements.
2. **Add `aria-busy="true"` during HTMX requests** — Pico renders a spinner for
   free, perfect for the search form or listing reloads.
3. **Use `role="group"` for the search input + button pair** — joined visual
   treatment that signals they are one control.
4. **Add `<small>` helper text** under the search input — e.g., "Press Enter or
   click Search". Free Pico styling.
5. **Replace future "show filters" toggles with `<details>`** — no JS, native
   accessibility, server-renderable open/closed state via the `open` attribute.
6. **Use `aria-invalid` for empty-search or invalid-input state** — visual
   feedback with zero CSS.
7. **Scope the `h1` gradient to a class** (e.g., `.brand-heading`) instead of
   targeting `h1` globally — see [Chapter 17](17-pico-css-audit.md).
8. **Use `--pico-spacing` instead of hardcoded `1rem`** in `app.css` where
   spacing should follow the theme.

These are all **small, reversible changes** that demonstrate Pico fluency
without rewriting the app.

---

## Cheat Sheet (For The Interview)

```text
LAYOUT
.container             centered max-width
.container-fluid       full-width
.grid                  equal columns (form / quick column groups)
custom CSS Grid        for responsive card lists (use auto-fill + minmax)

VARIANTS (button, link, summary[role=button])
.secondary  .contrast  .outline

DISCLOSURE / MENUS (declarative, no JS)
<details><summary>...</summary>...</details>     simple toggle
<details name="x">...                            accordion (one open at a time)
<details class="dropdown">                       dropdown menu

STATE (attributes, no class)
aria-busy="true"                                 loading spinner
aria-invalid="true" / "false"                    validation
data-tooltip="..."                               tooltip
data-theme="light" | "dark"                      force theme (omit = auto)
role="group"                                     joined input/button bar

OVERRIDE
:root { --pico-primary: ... }                    global token override
.my-card { --pico-card-background-color: ... }   scoped token override
```
