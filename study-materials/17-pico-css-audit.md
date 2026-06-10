# Chapter 17: Pico CSS — How It's Actually Used in the Codebase

A close read of `layout.html`, the two page templates, `navigation.html`, and
`app.css` against the Pico v2 documentation. This covers what is correct, what
is redundant, what is missing, and where the code mixes approaches in ways Pico
doesn't recommend.

---

## What Pico CSS v2 Is (Quick Recap)

Pico v2 ships in three variants:

| Variant | Filename | Behavior |
|---|---|---|
| Default | `pico.min.css` | Styles semantic HTML. Also provides utility classes (`.container`, `.grid`) |
| Classless | `pico.classless.min.css` | Styles semantic HTML only. No utility classes at all |
| Fluid | `pico.fluid.min.css` | Like default but full-width (no max-width centering) |

The codebase loads `pico.min.css` — the **default variant**. This is the right
choice for an app that uses `.container` on `<header>` and `<main>`, since the
classless variant strips those utilities.

Pico also supports explicit theming via `data-theme` on `<html>`:

```html
<html data-theme="dark">   <!-- force dark -->
<html data-theme="light">  <!-- force light -->
<html>                     <!-- auto: follows prefers-color-scheme -->
```

---

## What Is Correct

### `.container` on layout landmarks

```html
<header class="container">...</header>
<main class="container">...</main>
```

This is the canonical Pico pattern — `.container` centers content with a max-width
and responsive padding. Using it on `<header>` and `<main>` rather than wrapping
everything in a single `<div class="container">` is semantically cleaner.

### Navigation pattern

```html
<nav>
  <ul><li><!-- logo --></li></ul>
  <ul><li>...</li><li>...</li></ul>
</nav>
```

This is Pico's documented split-nav pattern. Two `<ul>` elements inside `<nav>` get
`display: flex; justify-content: space-between` automatically — left side is the
logo, right side is the links. No CSS class needed. **Correct usage.**

### CSS custom properties referenced correctly

When `app.css` does reference Pico tokens, it does it correctly:

```css
border: 1px solid var(--pico-muted-border-color); /* adapts to light/dark */
border-radius: var(--pico-border-radius);
color: var(--pico-muted-color);
```

Using Pico's own `--pico-*` custom properties means those values will
automatically follow the active theme. This is the right pattern *when you need
to reference Pico values*. The problem is what those rules are attached to — see
"What Is Mixed" below.

### `<small>` in the empty state

```html
<p><small>Try a different search term</small></p>
```

Pico reduces `<small>` to `0.875em`. Works as intended.

---

## What Is Redundant (Double-Styling)

### `<article>` + manual `border-radius`

Pico styles `<article>` as a card using `box-shadow` — **not** `border`. The
actual Pico rules on `<article>` are:

- `border-radius: var(--pico-border-radius)` ✓
- `background: var(--pico-card-background-color)` ✓
- `box-shadow: var(--pico-card-box-shadow)` ✓ — this is what gives the card its
  elevation; there is no `border` property on `<article>`

So in `app.css`:

```css
.category-card,
.listing-card {
  border: 1px solid var(--pico-muted-border-color);   /* load-bearing — Pico does NOT set this */
  border-radius: var(--pico-border-radius);            /* redundant — <article> already has this */
}
```

Only `border-radius` is redundant here. The `border` rule is genuinely
load-bearing — without it the cards would have no visible border outline at all,
only a box-shadow.

**What could be removed:**

```css
/* Only border-radius is redundant — <article> already has it from Pico */
.category-card,
.listing-card {
  border-radius: var(--pico-border-radius);
}
```

---

## What Is Missing

### No `data-theme` on `<html>` — and that is correct

```html
<!-- Current — correct for automatic OS-based theming -->
<html lang="en">

<!-- Force light -->
<html lang="en" data-theme="light">

<!-- Force dark -->
<html lang="en" data-theme="dark">
```

Pico v2 has exactly **two** valid `data-theme` values: `"light"` and `"dark"`.
`data-theme="auto"` is **not** a documented Pico value and can silently break
theme switching. Pico's selectors are written as:

```css
:root:not([data-theme="dark"]) { /* light rules */ }

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* dark rules */ }
}
```

Setting `data-theme="auto"` puts a `data-theme` attribute on `<html>` with a
value that matches neither selector — it doesn't opt into `dark`, and it doesn't
opt out of the `prefers-color-scheme` dark media query (because that checks for
`data-theme="light"` specifically). The result is undefined behavior depending on
which Pico selectors fire.

**The real "auto" mode in Pico is no `data-theme` attribute at all** — exactly
what the codebase does. `<html lang="en">` is correct: Pico defaults to light and
activates dark rules automatically via `@media (prefers-color-scheme: dark)`.

### Pico's `.grid` class is not used — and that is the right call

Pico v2 provides a small `.grid` helper for simple equal-column layouts:

```html
<div class="grid">
  <div>Column 1</div>
  <div>Column 2</div>
</div>
```

Pico itself is explicit that this is **intentionally minimal** — it is not a full
grid system. There are no column spans, offsets, ordering utilities, or advanced
breakpoint controls. Columns collapse to a single column below `768px`. It is
suitable for forms, quick two/three-column groups, and simple prototypes:

```html
<!-- Good fit for Pico .grid -->
<fieldset class="grid">
  <input name="first_name" placeholder="First name">
  <input name="last_name" placeholder="Last name">
</fieldset>
```

For responsive card/list layouts — exactly what `.categories-list` and
`.listings-grid` are — custom CSS Grid is the correct choice:

```css
.listings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1.5rem;
}
```

This says: create as many columns as fit the viewport, each at least 250px wide,
and let them expand evenly. Pico's `.grid` cannot express this — it has no
`minmax` or `auto-fill` equivalent. **The codebase is making the right call here,
not missing a Pico feature.**

Practical rule:

```plaintext
Use Pico .grid   → simple equal columns, forms, quick prototypes
Use custom Grid  → responsive card grids, listings, search results
```

---

## What Is Also Redundant (More Than Just Border/Radius)

### `.category-card { padding: 1rem }`

Pico's `<article>` already includes padding via `--pico-card-spacing`. Adding
`padding: 1rem` on the class overrides it with a hardcoded raw value — which
will not adapt if Pico's spacing scale changes and breaks the token-based
approach the rest of the file attempts.

---

## What Is Mixed (Inconsistent Approaches)

### `<input type="submit">` vs `<button type="submit">`

```html
<!-- Current in categories/index.html -->
<input type="submit" value="Search">

<!-- Pico-idiomatic — more styleable, can contain HTML -->
<button type="submit">Search</button>
```

Pico styles both, but `<button>` is the modern HTML standard for interactive
controls. `<input type="submit">` is a legacy pattern — it cannot contain child
elements, making it harder to add an icon or spinner later. A small inconsistency
but it's the kind of thing Pico's own docs show as `<button>`.

### `<b>` instead of `<strong>` in the listings template

```jinja2
{# Current — presentational bold #}
<b>{{ listing["title"] }}</b>

{# Semantic — emphasis with importance #}
<strong>{{ listing["title"] }}</strong>
```

`<b>` is presentational (just bold). `<strong>` signals importance to screen
readers. Pico styles both identically. Minor, but signals awareness of semantic
HTML if you bring it up unprompted.

### Hero section: two class names for the same pattern

```html
<section class="search-hero">  <!-- categories page -->
<section class="examples-hero"> <!-- listings page -->
```

`app.css` styles them together under a grouped selector:

```css
.search-hero,
.examples-hero {
  text-align: center;
  margin-bottom: 2rem;
}
```

They're identical in behavior. A single `.page-hero` class would avoid the
duplication. This is the kind of small inconsistency AI-generated code commonly
produces — each template was written independently and got its own class name.

### `<section>` for non-landmark content

```html
<section class="search-hero">
  <h1>Category Search</h1>
  <p>Search for musical gear categories</p>
</section>
```

HTML5 `<section>` implies a thematic grouping that should appear in a document
outline. A hero intro with a heading and tagline isn't really a landmark section
— `<div>` or `<header>` (scoped to the page content, not the site) would be more
semantically accurate. Pico doesn't style `<section>` specially, so functionally
it's identical to a `<div>` here.

### Global `h1` element override

```css
/* app.css */
h1 {
  background: linear-gradient(...);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;  /* ← non-standard webkit property */
  background-clip: text;
  font-weight: 700;
  display: inline-block;
}
```

This is a **global element override** — it targets every `h1` on every page.
Pico's recommended approach for customizing typography is to override its own
CSS custom properties (`--pico-font-weight`, `--pico-h1-font-size`, etc.) so
the change flows through Pico's system. A raw `h1 {}` rule bypasses that entirely
and fights Pico's cascade rather than working with it.

Additional issues in this rule:

- `-webkit-text-fill-color` is a non-standard WebKit property. It's widely
  supported but is not part of the CSS spec. The standard approach is
  `color: transparent` combined with `background-clip: text`.
- `display: inline-block` is required to make the gradient text clip work, but
  it implicitly changes `h1` from a block-level element to inline-block
  everywhere — a side effect that could break layout in future pages.
- `font-weight: 700` duplicates what Pico already sets on headings.

### Global `nav a` color override

```css
nav a {
  color: var(--pico-color);  /* main text color */
  font-size: 0.875rem;
}
```

This overrides ALL anchor elements inside ANY `<nav>` globally. Pico uses
`--pico-primary` for link colors by default, which gives the standard blue/accent
look. Setting `color: var(--pico-color)` (the main text color) strips the link
accent color from nav links, making them look like plain text. This may be
intentional for the nav logo, but it applies to the content links too — and it
does so via a broad element selector, not a scoped class.

The `.nav-logo-link` class already handles the logo anchor specifically. A
tighter selector like `.nav-logo-link, nav ul:last-child a` would scope the
override without blanketing all nav links.

### Hardcoded values mixed with Pico tokens

The file uses Pico tokens for some values and raw hardcoded values for others
with no consistent rule:

```css
/* Uses Pico tokens */
border: 1px solid var(--pico-muted-border-color);
border-radius: var(--pico-border-radius);
color: var(--pico-muted-color);

/* Hardcoded — ignores equivalent Pico spacing tokens */
padding: 1rem;           /* Pico has --pico-spacing */
margin-bottom: 1rem;     /* Pico has --pico-typography-spacing-vertical */
gap: 1rem;               /* app-specific, no Pico token — fine */
padding: 3rem 1rem;      /* app-specific — fine */
```

`gap` and explicit layout dimensions (like `.search-form { max-width: 600px }`) are
legitimately app-specific and have no Pico token equivalent — hardcoding them is
correct. But `padding: 1rem` on `.category-card` overrides what `<article>` gets
from `--pico-card-spacing` with a raw value that won't follow theme changes.

### Media query breakpoint mismatch

```css
@media (min-width: 600px) {
  .categories-list,
  .listings-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

Pico v2 defines its own breakpoint scale:

| Token | Value |
|---|---|
| `--pico-breakpoint-xs` | 576px |
| `--pico-breakpoint-sm` | 768px |
| `--pico-breakpoint-md` | 1024px |
| `--pico-breakpoint-lg` | 1280px |

`600px` sits between Pico's xs (576px) and sm (768px), so it's out of sync with
the framework's grid system. Note: CSS custom properties cannot be used inside
`@media` queries (that's a CSS limitation, not a Pico issue), so `600px` can't
become `var(--pico-breakpoint-xs)`. The fix is to align the value to one of
Pico's breakpoints — `576px` or `768px` — by convention.

---

## Best Practice Fixes

### Gradient `h1`: scope it, drop the webkit property

The core problem is a global element selector with side effects. The fix is a
scoped class and standard CSS only:

```css
/* Before — global, non-standard, side-effects */
h1 {
  background: linear-gradient(...);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent; /* non-standard */
  background-clip: text;
  font-weight: 700;                     /* duplicates Pico */
  display: inline-block;                /* changes all h1 layout */
}

/* After — scoped, standard, no side effects */
.gradient-heading {
  background: linear-gradient(...);
  background-clip: text;
  color: transparent;                   /* standard property, not -webkit-text-fill-color */
  display: inline;                      /* inline wraps tightly without block side effects */
}
```

Apply it in templates where the gradient is actually wanted:

```jinja2
<h1><span class="gradient-heading">Category Search</span></h1>
```

Wrapping in `<span>` keeps `<h1>` as a block element; only the text node becomes
inline. `color: transparent` with `background-clip: text` is the standardised
approach — `-webkit-text-fill-color` overrides `color` in WebKit but is not in
the CSS spec and has no non-WebKit fallback path.

`font-weight: 700` can be dropped entirely — Pico already sets it on all headings
via `--pico-font-weight` on the `h1,h2,h3,...` rule.

### `nav a` color: tighten the selector

```css
/* Before — blankets all nav links */
nav a {
  color: var(--pico-color);
  font-size: 0.875rem;
}

/* After — only the logo anchor, leaving content links their Pico accent colour */
.nav-logo-link {
  color: var(--pico-color);
  font-size: 0.875rem;
}
```

The `.nav-logo-link` class is already in the codebase and already scopes the
logo anchor. There is no reason for the broader `nav a` rule. If the intent is
also to neutralise the colour on the right-hand nav links specifically, use:

```css
nav ul:last-child a {
  color: var(--pico-color);
  font-size: 0.875rem;
}
```

This targets only the second `<ul>` inside `<nav>` — the content links — without
affecting any other nav in the document.

### Card `border-radius`: just remove it

```css
/* Before */
.category-card,
.listing-card {
  border: 1px solid var(--pico-muted-border-color); /* keep — load-bearing */
  border-radius: var(--pico-border-radius);          /* remove — <article> already has this */
}

/* After */
.category-card,
.listing-card {
  border: 1px solid var(--pico-muted-border-color);
}
```

Nothing changes visually. The rule was duplicating what Pico already applies to
every `<article>`.

### Card padding: override the Pico custom property instead of hardcoding

Pico applies padding to `<article>` via `--pico-block-spacing-vertical` and
`--pico-block-spacing-horizontal` (both default to `--pico-spacing`, which is
`1rem`). Overriding the property keeps the change inside Pico's token system:

```css
/* Before — hardcoded raw value, bypasses Pico's token system */
.category-card {
  padding: 1rem;
}

/* After — override the token; Pico's <article> rule picks it up automatically */
.category-card {
  --pico-block-spacing-vertical: 0.75rem;
  --pico-block-spacing-horizontal: 0.75rem;
}
```

If the intent is just to use the default `1rem`, remove the rule entirely — Pico
already produces that value.

### Media query: align to a Pico breakpoint

```css
/* Before — sits between Pico's xs (576px) and sm (768px) */
@media (min-width: 600px) {
  .categories-list,
  .listings-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* After — aligns to Pico's sm breakpoint */
@media (min-width: 768px) {
  .categories-list,
  .listings-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

`768px` is the better choice here because `600px` is narrower than most tablets
in landscape, so the three-column layout was activating on larger phones. `768px`
(Pico's `sm`) is the conventional tablet breakpoint and keeps the grid consistent
with how Pico's own `.container` expands.

---

## Summary Table

| Item | Verdict | Impact |
|---|---|---|
| `pico.min.css` (default variant) | Correct choice | — |
| `.container` on `<header>` and `<main>` | Correct | — |
| Nav `<ul>/<ul>` split pattern | Correct | — |
| `--pico-*` token references in `app.css` | Correct where used | — |
| `border` on `.category-card`, `.listing-card` | Not redundant — Pico uses `box-shadow` on `<article>`, not `border`; this is load-bearing | — |
| `border-radius` on `.category-card`, `.listing-card` | Redundant — `<article>` already has it | Visual noise |
| `padding: 1rem` on `.category-card` | Redundant — overrides `<article>`'s `--pico-card-spacing` with raw value | Low |
| No `data-theme` attribute | Correct — omitting it is the proper "auto" mode in Pico | — |
| Not using Pico's `.grid` | Correct — Pico `.grid` can't express `auto-fill`/`minmax`; custom Grid is the right tool for card layouts | — |
| Global `h1 {}` rule | Problem — bypasses Pico's custom property system; side-effects on layout; non-standard `-webkit-text-fill-color` | Medium |
| Global `nav a { color }` override | Problem — too broad; strips link accent color from all nav links | Low–Medium |
| Hardcoded spacing values mixed with Pico tokens | Inconsistent — some values use tokens, equivalent ones don't | Low |
| `@media (min-width: 600px)` | Out of sync with Pico's breakpoint scale (576 / 768px) | Low |
| `<input type="submit">` | Mixed — legacy HTML pattern | Low |
| `<b>` instead of `<strong>` | Mixed — presentational over semantic | Low |
| Two hero class names for same styles | Mixed — AI generation artifact | Low |
| `<section>` for hero divs | Mixed — overuse of semantic landmark element | Low |

---

## Interview Script

> "The core layout is solid — `.container`, the nav split pattern with two `<ul>`
> elements, and the card grid. A few things stand out though. The most structural
> issue is the global `h1` rule — it overrides Pico's typography system with a
> direct element selector, uses a non-standard `-webkit-text-fill-color` property,
> and sets `display: inline-block` on all headings as a side effect. The Pico way
> would be to scope it or override via `--pico-font-weight`. Similarly, `nav a`
> sets `color: var(--pico-color)` globally, which strips the accent link color
> from all nav links — a `.nav-logo-link` scoped rule would be cleaner. On the
> redundancy side, `<article>` already gets `border-radius` and card spacing
> from Pico, so those rules in `app.css` partially double up on what Pico
> provides. Worth noting: Pico uses `box-shadow`, not `border`, on `<article>`,
> so the explicit `border` in `app.css` is actually load-bearing. And the `@media (min-width: 600px)` breakpoint is between Pico's
> 576px and 768px marks — I'd align it to one of those to stay consistent with
> the framework. None of this is blocking, but it signals the CSS was written
> without fully reading the Pico docs."
