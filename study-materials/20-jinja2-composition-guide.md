# Jinja2 Template Composition — Study Guide & Reference

A consolidated reference for composing HTML templates in Jinja2: inheritance, blocks, includes, macros, imports, `call`, `with`, `set`, and how they map to "components" in a server-rendered app.

## Quick Map of Composition Tools

| Construct | Purpose |
| --- | --- |
| `extends` + `block` | Page / layout inheritance |
| `include` | Insert a reusable partial |
| `macro` | Reusable HTML function / component |
| `import` | Load macros as a namespace |
| `from ... import ...` | Load specific macros |
| `call` | Pass inner content into a macro |
| `with` | Create a local context |
| `set` | Assign or capture template values |
| `super()` | Reuse parent block content |

### Mental Model

- **Layout slots** → `{% block %}`
- **Reusable partials** → `{% include %}`
- **Reusable components with arguments** → `{% macro %}`
- **Component children / slots** → `{% call %}`

---

## 1. `{% extends %}` — Use a Parent Layout

Use `extends` when a page should inherit a larger layout.

### `base.html`

```jinja
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Gear Garage{% endblock %}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/app.css') }}">
  {% block styles %}{% endblock %}
</head>
<body>
  <header class="container">
    {% include "partials/navigation.html" %}
  </header>
  <main class="container">
    {% block content %}{% endblock %}
  </main>
  {% block scripts %}{% endblock %}
</body>
</html>
```

### `categories/index.html`

```jinja
{% extends "base.html" %}
{% block title %}Categories · Gear Garage{% endblock %}
{% block content %}
  <h1>Categories</h1>
  <p>Browse all gear categories.</p>
{% endblock %}
```

**Meaning:** Use `base.html` as the outer shell. Replace its named blocks with this page's content. Use `extends` for page-level composition.

---

## 2. `{% block %}` — Define Replaceable Layout Regions

A block is a named slot in a parent template.

```jinja
{% block content %}{% endblock %}
```

A child can override it:

```jinja
{% block content %}
  <h1>Listings</h1>
{% endblock %}
```

Blocks can have default content:

```jinja
<title>{% block title %}Gear Garage{% endblock %}</title>
```

If the child does not override `title`, the default `Gear Garage` is used.

Default page content example:

```jinja
<main class="container">
  {% block content %}
    <h1>Welcome to Gear Garage</h1>
    <p>Browse categories and listings.</p>
  {% endblock %}
</main>
```

**Common blocks:** `title`, `content`, `styles`, `scripts`, `sidebar`, `page_header`.

---

## 3. `{{ super() }}` — Include Parent Block Content

Inside an overridden block, `super()` renders the parent's default content.

**Base:**

```jinja
{% block scripts %}
  <script src="{{ url_for('static', filename='js/app.js') }}"></script>
{% endblock %}
```

**Child:**

```jinja
{% block scripts %}
  {{ super() }}
  <script src="{{ url_for('static', filename='js/listings.js') }}"></script>
{% endblock %}
```

**Rendered:**

```html
<script src="/static/js/app.js"></script>
<script src="/static/js/listings.js"></script>
```

Use `super()` when a child wants to **extend** the parent block rather than fully replace it.

---

## 4. `{% include %}` — Insert a Reusable Partial

```jinja
{% include "partials/navigation.html" %}
```

`partials/navigation.html`:

```jinja
<nav>
  <ul>
    <li><a href="{{ url_for('index') }}">Gear Garage</a></li>
  </ul>
  <ul>
    <li><a href="{{ url_for('categories.index') }}">Categories</a></li>
    <li><a href="{{ url_for('listings.index') }}">Listings</a></li>
  </ul>
</nav>
```

Use `include` for concrete reusable fragments: navigation, footer, flash messages, pagination, empty state, search form, listing card partial.

```jinja
{% include "partials/flash_messages.html" %}
{% include "partials/pagination.html" %}
```

`include` is like render-time copy/paste — the included template still accesses the current context.

---

## 5. `{% include ... ignore missing %}` — Optional Partials

```jinja
{% include "partials/sidebar.html" ignore missing %}
```

Prevents errors when the file is absent.

Fallback list:

```jinja
{% include ["partials/custom_card.html", "partials/default_card.html"] %}
```

Jinja uses the first template it finds.

---

## 6. `{% macro %}` — Reusable HTML Function / Component

A macro is a function that returns rendered template output.

```jinja
{% macro button(label, href=None) %}
  {% if href %}
    <a href="{{ href }}" role="button">{{ label }}</a>
  {% else %}
    <button type="button">{{ label }}</button>
  {% endif %}
{% endmacro %}
```

Usage:

```jinja
{{ button("Search") }}
{{ button("View listing", href="/listings/123") }}
```

Renders:

```html
<button type="button">Search</button>
<a href="/listings/123" role="button">View listing</a>
```

### React Analogy

```jsx
function Button({ label, href }) {
  if (href) return <a href={href} role="button">{label}</a>;
  return <button type="button">{label}</button>;
}
```

Use macros for parameterized UI: buttons, badges, cards, form fields, alerts, listing cards, disclosures, pagination controls.

---

## 7. `{% import %}` — Import Macros as a Namespace

`templates/macros/ui.html`:

```jinja
{% macro button(label, href=None, type="button") %}
  {% if href %}
    <a href="{{ href }}" role="button">{{ label }}</a>
  {% else %}
    <button type="{{ type }}">{{ label }}</button>
  {% endif %}
{% endmacro %}
{% macro badge(text, tone="default") %}
  <span class="badge badge-{{ tone }}">{{ text }}</span>
{% endmacro %}
```

Page template:

```jinja
{% import "macros/ui.html" as ui %}
{{ ui.button("Search", type="submit") }}
{{ ui.badge("New", tone="success") }}
```

The namespace name (`ui`, `components`, `m`) is your choice. `ui` is a clean convention for general UI helpers.

---

## 8. `{% from ... import ... %}` — Import Specific Macros

```jinja
{% from "macros/ui.html" import button %}
{{ button("Search") }}
```

Multiple:

```jinja
{% from "macros/ui.html" import button, badge, card %}
```

| Form | Usage |
| --- | --- |
| `{% import "macros/ui.html" as ui %}` | `ui.button(...)` |
| `{% from "macros/ui.html" import button %}` | `button(...)` |

For larger codebases, namespaced imports are usually clearer:

```jinja
{{ ui.button("Search") }}
{{ forms.input("search") }}
{{ listings.card(listing) }}
```

---

## 9. `{% call %}` — Pass Inner Content into a Macro

`call` lets a macro receive a block of inner template content — similar to React children.

**React:**

```jsx
<Card title="Filters">
  <form>...</form>
</Card>
```

**Jinja:**

```jinja
{% call ui.card("Filters") %}
  <form>...</form>
{% endcall %}
```

Macro definition:

```jinja
{% macro card(title) %}
  <article>
    <header><h2>{{ title }}</h2></header>
    <div>{{ caller() }}</div>
  </article>
{% endmacro %}
```

`{{ caller() }}` is where the content between `{% call %}` and `{% endcall %}` gets inserted.

Use `call` for wrapper components: cards, panels, modals, disclosures, form sections, empty states, accordion sections.

---

## 10. Macros Can Call Other Macros

`macros/ui.html`:

```jinja
{% macro button(label, type="button") %}
  <button type="{{ type }}">{{ label }}</button>
{% endmacro %}
{% macro card(title) %}
  <article>
    <header><h2>{{ title }}</h2></header>
    <div>{{ caller() }}</div>
  </article>
{% endmacro %}
{% macro search_card(title="Search") %}
  {% call card(title) %}
    <form>
      <input name="search" placeholder="Search...">
      {{ button("Apply", type="submit") }}
    </form>
  {% endcall %}
{% endmacro %}
```

A macro can also import macros from another file:

```jinja
{% import "macros/forms.html" as forms %}
{% macro search_card(title="Search") %}
  <article>
    <header><h2>{{ title }}</h2></header>
    <form>
      {{ forms.search_input() }}
      <button type="submit">Apply</button>
    </form>
  </article>
{% endmacro %}
```

This is component composition.

---

## 11. `{% with %}` — Create Local Context

```jinja
{% with title="Advanced filters", open=false %}
  {% include "partials/disclosure.html" %}
{% endwith %}
```

Passing an object:

```jinja
{% with item=listing %}
  {% include "partials/listing_card.html" %}
{% endwith %}
```

Inside `partials/listing_card.html`:

```jinja
<article>
  <h2>{{ item.title }}</h2>
  <p>{{ item.summary }}</p>
</article>
```

When a reusable component needs **clear arguments**, prefer macros:

```jinja
{{ listings.card(listing) }}
```

Macros make the API more explicit than `with` + `include`.

---

## 12. `{% set %}` — Assign Variables or Capture Output

```jinja
{% set page_title = "Categories" %}
<h1>{{ page_title }}</h1>
```

Computed values:

```jinja
{% set has_results = results|length > 0 %}
{% if has_results %}
  <p>Showing {{ results|length }} results.</p>
{% else %}
  <p>No results found.</p>
{% endif %}
```

Capture rendered template output:

```jinja
{% set description %}
  <p>This is a longer HTML description.</p>
{% endset %}
<article>{{ description }}</article>
```

Use `set` for local template state, not complex business logic.

---

## 13. Nested Layout Inheritance

Multiple layout layers.

**`base.html`:**

```jinja
<!DOCTYPE html>
<html lang="en">
<head><title>{% block title %}Gear Garage{% endblock %}</title></head>
<body>
  {% include "partials/navigation.html" %}
  {% block body %}{% endblock %}
</body>
</html>
```

**`layouts/app.html`:**

```jinja
{% extends "base.html" %}
{% block body %}
  <main class="container">
    {% block content %}{% endblock %}
  </main>
{% endblock %}
```

**`layouts/admin.html`:**

```jinja
{% extends "base.html" %}
{% block body %}
  <div class="admin-layout">
    <aside>{% include "partials/admin_sidebar.html" %}</aside>
    <main>{% block content %}{% endblock %}</main>
  </div>
{% endblock %}
```

**Page:**

```jinja
{% extends "layouts/app.html" %}
{% block content %}
  <h1>Listings</h1>
{% endblock %}
```

Layout family:

```plaintext
base.html
  layouts/app.html
  layouts/admin.html
  layouts/auth.html
```

---

## 14. No Native Twig-Style `{% embed %}`

Jinja models that with:

- `macro` + `call`
- `include` + `with`
- `extends` + `block`

For component-like wrappers, use:

```jinja
{% call ui.card("Title") %}
  ...
{% endcall %}
```

---

## Practical File Organization

```plaintext
templates/
  base.html
  layouts/
    app.html
    admin.html
    auth.html
  partials/
    navigation.html
    footer.html
    flash_messages.html
    pagination.html
  macros/
    ui.html
    forms.html
    listings.html
  categories/
    index.html
    show.html
  listings/
    index.html
    show.html
```

| Folder | Responsibility |
| --- | --- |
| `base.html` | Global HTML shell: doctype, html, head, global CSS/JS, nav, main slots |
| `layouts/` | Page-family structures: app, admin, auth, dashboard |
| `partials/` | Concrete reusable fragments with little or no parameterization |
| `macros/` | Parameterized reusable UI components |
| pages | Route-level templates that extend a layout and fill blocks |

---

## Composition Decision Guide

### Use `{% extends %}` when…

Building a page that should inherit a shared layout.

```jinja
{% extends "base.html" %}
```

For: normal pages, admin pages, auth pages, dashboard pages.

### Use `{% block %}` when…

A parent layout needs a region that child templates can replace.

```jinja
{% block content %}{% endblock %}
```

For: `title`, `content`, `styles`, `scripts`, `sidebar`, `page_header`.

### Use `{% include %}` when…

You want to insert a concrete reusable fragment.

```jinja
{% include "partials/navigation.html" %}
```

For: navigation, footer, flash messages, pagination, static search form.

### Use `{% macro %}` when…

You want a reusable component with arguments.

```jinja
{{ ui.button("Search", type="submit") }}
```

For: buttons, badges, form inputs, cards, alerts, listing cards, disclosures.

### Use `{% call %}` when…

You want a reusable wrapper component with inner content.

```jinja
{% call ui.card("Filters") %}
  <form>...</form>
{% endcall %}
```

For: cards with custom content, panels, modals, form sections, description disclosures.

### Use `{% with %}` when…

You want a small local context, especially around an include.

```jinja
{% with item=listing %}
  {% include "partials/listing_card.html" %}
{% endwith %}
```

### Use `{% set %}` when…

You want a local variable or captured template output.

```jinja
{% set has_results = results|length > 0 %}
```

---

## Concrete Pico + Jinja Example

**`macros/ui.html`:**

```jinja
{% macro button(label, href=None, type="button", loading_text=None) %}
  {% if href %}
    <a href="{{ href }}" role="button">{{ label }}</a>
  {% else %}
    <button
      type="{{ type }}"
      {% if loading_text %}data-loading-text="{{ loading_text }}"{% endif %}
    >
      {{ label }}
    </button>
  {% endif %}
{% endmacro %}
{% macro card(title) %}
  <article>
    <header><h2>{{ title }}</h2></header>
    <div>{{ caller() }}</div>
  </article>
{% endmacro %}
{% macro description_disclosure(label_closed="Read full description", label_open="Show less") %}
  <details
    data-description-disclosure
    data-label-closed="{{ label_closed }}"
    data-label-open="{{ label_open }}"
  >
    <summary>{{ label_closed }}</summary>
    <div class="description-complete">{{ caller() }}</div>
  </details>
{% endmacro %}
```

**`listings/show.html`:**

```jinja
{% extends "base.html" %}
{% import "macros/ui.html" as ui %}
{% block title %}{{ listing.title }} · Gear Garage{% endblock %}
{% block content %}
  <article>
    <h1>{{ listing.title }}</h1>
    <p>{{ listing.summary_description }}</p>
    {% if listing.complete_description %}
      {% call ui.description_disclosure("Read full description", "Show less") %}
        <p>{{ listing.complete_description }}</p>
      {% endcall %}
    {% endif %}
    {{ ui.button("Back to listings", href=url_for("listings.index")) }}
  </article>
{% endblock %}
```

This combines:

- `extends` → page uses base layout
- `block` → page fills title/content
- `import` → page loads UI macros
- `macro` → reusable button/disclosure
- `call` → disclosure receives inner content

---

## Jinja Composition ↔ React Concepts

| React | Jinja |
| --- | --- |
| Component | `macro` |
| Props | Macro arguments |
| Children | `call` / `caller()` |
| Layout component | `extends` + `block` |
| Shared component file | Macros file |
| Partial JSX fragment | `include` |

**Different runtime model:** React components can be interactive client-side units. Jinja macros render static HTML on the server. After rendering, Jinja output is just HTML — interactivity comes from native browser behavior, HTMX, or vanilla JS.

---

## Recommended Rules for a Pico + Jinja Codebase

1. Use semantic HTML first.
2. Use Pico for styling native elements.
3. Use base/layout templates for page structure.
4. Use includes for fixed reusable fragments.
5. Use macros for parameterized UI.
6. Use `call`/`caller` for wrapper components with inner content.
7. Use `data-*` attributes as vanilla JS enhancement hooks.
8. Keep imperative client behavior in small JS files, not inline template attributes.

**Good example:**

```jinja
{% call ui.card("Filters") %}
  <form
    data-busy-form
    hx-get="{{ url_for('listings.index') }}"
    hx-target="#results"
    hx-swap="innerHTML"
  >
    <input name="search" placeholder="Search...">
    {{ ui.button("Apply", type="submit", loading_text="Searching…") }}
  </form>
{% endcall %}
```

Each layer stays clean:

| Layer | Role |
| --- | --- |
| Jinja macro | Reusable structure |
| HTML | Semantic controls |
| Pico | Styling |
| HTMX | Fetch/swap |
| `data-*` | Enhancement hooks |
| Vanilla JS | Busy state + small interactivity |

---

## Final Cheat Sheet

```jinja
{% extends "base.html" %}
  Use a parent layout.

{% block content %}{% endblock %}
  Define or override a named slot.

{{ super() }}
  Include parent block content inside an override.

{% include "partials/nav.html" %}
  Render another template here.

{% macro button(label) %}...{% endmacro %}
  Define a reusable template function/component.

{% import "macros/ui.html" as ui %}
  Import macros as a namespace.

{% from "macros/ui.html" import button %}
  Import a specific macro directly.

{% call ui.card("Title") %}...{% endcall %}
  Pass inner content into a macro via caller().

{% with item=listing %}...{% endwith %}
  Create local context for a section.

{% set name = "value" %}
  Assign a local template variable.

{% set content %}...{% endset %}
  Capture rendered template output into a variable.
```

---

## One-Line Summary

> Jinja composition is **server-rendered component architecture**: blocks compose layouts, includes compose partials, macros compose reusable UI, and `call`/`caller` gives macros a "children" slot.
