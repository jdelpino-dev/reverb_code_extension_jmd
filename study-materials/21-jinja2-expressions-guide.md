# Jinja2 Templating Expressions — Study Guide & Reference

A practical guide to **Jinja templating expressions**, with special attention to **filters** (where Jinja diverges most from Python).

> Jinja expressions are **Python-like template expressions**, not Python expressions. They are evaluated by the Jinja engine, not the Python interpreter.

---

## 1. The Three Core Jinja Syntaxes

Jinja templates are mostly HTML/text with Jinja syntax embedded inside.

### Output expressions: `{{ ... }}`

Use `{{ ... }}` to print a value into the template.

```jinja
<h1>{{ listing.title }}</h1>
<p>{{ listing.description }}</p>
<small>{{ categories|length }} categories</small>
```

**Mental model:** `{{ ... }}` = evaluate this expression and render the result here.

```jinja
<p>Hello, {{ user.name }}.</p>
```

If `user.name` is `"José"`, output is `<p>Hello, José.</p>`.

### Statements: `{% ... %}`

Use `{% ... %}` for template logic: loops, conditionals, inheritance, includes, blocks, macros.

```jinja
{% if categories %}
  <p>Categories found.</p>
{% endif %}
{% for category in categories %}
  <li>{{ category.name }}</li>
{% endfor %}
```

**Mental model:** `{% ... %}` = execute template logic, but do not directly print this tag itself.

### Comments: `{# ... #}`

```jinja
{# This comment is visible only in the template source. #}
```

Nothing appears in the rendered output.

---

## 2. Jinja Expressions Are Not Python

| Python | Jinja |
| --- | --- |
| `len(categories)` | `categories\|length` |
| `name.upper()` | `name\|upper` |
| `value if condition else fallback` | `value if condition else fallback` (similar, but Jinja rules) |
| `isinstance(x, str)` | `x is string` |

Jinja is designed for **rendering**, not application logic. Application prepares data; Jinja displays, formats, loops, branches, composes.

---

## 3. Variables and Attribute Access

Dot syntax works for object attributes **and** dict keys:

```jinja
{{ user.name }}
{{ listing.price }}
{{ category.slug }}
```

Bracket syntax also works:

```jinja
{{ user["name"] }}
```

Convention:

- Use **dot** for normal readability.
- Use **brackets** when the key is dynamic or awkward.

```jinja
{{ data[field_name] }}
```

---

## 4. Literals in Jinja Expressions

```jinja
{{ "Hello" }}
{{ 42 }}
{{ 3.14 }}
{{ true }}
{{ false }}
{{ none }}
```

Jinja uses **lowercase** constants: `true`, `false`, `none`. (`True` / `False` / `None` may also be accepted, but standardize on lowercase in templates.)

---

## 5. Basic Operators

### Arithmetic

```jinja
{{ price + shipping }}
{{ total - discount }}
{{ quantity * unit_price }}
{{ total / count }}
{{ total // count }}
{{ count % 2 }}
{{ 2 ** 3 }}
```

Use sparingly. Business calculations belong in Python.

**Good:** `<p>{{ page + 1 }}</p>`

**Questionable:** `<p>{{ ((price * tax_rate) - discount + shipping) / installment_count }}</p>` — precompute in Python.

### Comparisons

```jinja
{% if price > 100 %}<p>Premium listing</p>{% endif %}
{% if category.slug == "guitars" %}<p>Guitar category</p>{% endif %}
{% if user.role != "admin" %}<p>Regular user</p>{% endif %}
```

### Boolean logic

```jinja
{% if user and user.is_active %}<p>Active user</p>{% endif %}
{% if not categories %}<p>No categories found.</p>{% endif %}
{% if query or category %}<p>Filters applied.</p>{% endif %}
```

Jinja uses `and`, `or`, `not` like Python.

### Membership

```jinja
{% if "admin" in user.roles %}<p>Admin</p>{% endif %}
{% if category.slug in ["guitars", "pedals", "amps"] %}<p>Popular category</p>{% endif %}
```

---

## 6. Conditional Expressions

```jinja
{{ "Open" if details.open else "Closed" }}
```

```jinja
<button>{{ "Show less" if expanded else "Read more" }}</button>
```

Good for tiny display differences. **Avoid** dense nested ternaries:

```jinja
{{ "Premium" if price > 1000 else "Midrange" if price > 300 else "Budget" }}
```

Compute that in Python instead.

---

## 7. Filters: The Core Jinja Expression Feature

Filters **transform** values.

```jinja
{{ value|filter }}
```

```jinja
{{ name|upper }}
```

> Take `name`, pass it through the `upper` filter, render the result.

Python-ish equivalent: `name.upper()` — but Jinja uses **filter pipelines**.

---

## 8. Filter with Arguments

```jinja
{{ description|truncate(160) }}
{{ price|round(2) }}
{{ title|replace("Guitar", "Instrument") }}
{{ description|default("No description available.") }}
```

Pattern: `{{ value|filter(arg1, arg2, keyword=value) }}`

---

## 9. Chaining Filters

```jinja
{{ title|trim|title }}
```

> trim whitespace → title case → render.

```jinja
{{ description|striptags|truncate(140) }}
```

> remove HTML tags → truncate the plain text.

One of the most important Jinja idioms.

---

## 10. Common String Filters

### `upper` / `lower` / `title` / `capitalize`

```jinja
{{ "gear garage"|upper }}      {# GEAR GARAGE #}
{{ "Gear Garage"|lower }}      {# gear garage #}
{{ "gear garage"|title }}      {# Gear Garage #}
{{ "guitar pedals"|capitalize }} {# Guitar pedals #}
```

Be careful with `title` — names, acronyms, and real titles can be wrong.

### `trim`

```jinja
{{ title|trim }}
```

Removes leading/trailing whitespace. Good for user/CMS-entered strings.

### `replace`

```jinja
{{ title|replace("Reverb", "Gear Garage") }}
```

### `truncate`

```jinja
{{ description|truncate(160) }}
```

Useful for cards, previews, summaries.

```jinja
<p>{{ listing.description|striptags|truncate(160) }}</p>
```

### `striptags`

```jinja
{{ description_html|striptags }}
```

Removes HTML tags — useful for plain-text previews from HTML content.

---

## 11. Common Collection Filters

### `length`

```jinja
{{ categories|length }}
```

```jinja
<small>Showing {{ categories|length }} of {{ total }} results</small>
```

### `first` / `last`

```jinja
{{ categories|first }}
{{ categories|last }}
```

Often clearer with `set`:

```jinja
{% set first_category = categories|first %}
{{ first_category.name }}
```

### `join`

```jinja
{{ tags|join(", ") }}
```

If `tags = ["vintage", "fender", "guitar"]` → `vintage, fender, guitar`.

With attributes:

```jinja
{{ categories|map(attribute="name")|join(", ") }}
```

### `sort`

```jinja
{% for category in categories|sort(attribute="name") %}
  <li>{{ category.name }}</li>
{% endfor %}
```

Display-only. For real product/search/order semantics, sort in Python or the database.

### `reverse`

```jinja
{% for item in items|reverse %}
  <li>{{ item }}</li>
{% endfor %}
```

### `batch`

Groups items into fixed-size batches.

```jinja
{% for row in products|batch(3) %}
  <div class="grid">
    {% for product in row %}
      <article>{{ product.title }}</article>
    {% endfor %}
  </div>
{% endfor %}
```

Modern CSS Grid often handles this without `batch`:

```css
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
}
```

### `slice`

Slices a sequence into columns.

```jinja
{% for column in items|slice(3) %}
  <ul>
    {% for item in column %}
      <li>{{ item }}</li>
    {% endfor %}
  </ul>
{% endfor %}
```

---

## 12. Numeric Filters

```jinja
{{ value|int }}
{{ value|float }}
{{ rating|round(1) }}
{{ change|abs }}
```

```jinja
{{ request.args.get("page")|int }}
```

Template parsing of request args is okay for **display**, but actual pagination logic belongs in Python.

---

## 13. Default and Missing Values

```jinja
{{ listing.description|default("No description available.") }}
```

**Nuance:** by default, `default` only handles **undefined** values. Pass `true` as the second arg to also replace falsey values (empty string, etc.):

```jinja
{{ listing.description|default("No description available.", true) }}
{{ user.display_name|default(user.email, true) }}
{{ listing.condition|default("Unknown condition", true) }}
```

Extremely useful in server-rendered UI.

---

## 14. Escaping and HTML-Safety Filters

High-stakes area. Flask/Jinja typically autoescape HTML templates. So:

```jinja
{{ user_input }}
```

renders `<script>alert("xss")</script>` as **text**, not executable script.

### `escape` / `e`

```jinja
{{ value|escape }}
{{ value|e }}
```

Usually unnecessary when autoescape is on.

### `safe`

```jinja
{{ description_html|safe }}
```

Tells Jinja: "Do not escape this — it is already safe HTML."

Use **only** when:

- HTML was generated by your trusted system, OR
- It was sanitized with a real HTML sanitizer, OR
- It comes from trusted CMS/admin content where you accept the risk.

**Dangerous:**

```jinja
{{ request.args.get("q")|safe }}
```

Never. Policy:

- Use `|safe` only at clear trusted HTML boundaries.
- Never use `|safe` on ordinary user input.
- Prefer sanitizing **before** storing or rendering.

### `tojson`

For embedding data into JavaScript:

```jinja
<script>
  const listing = {{ listing_data|tojson }};
</script>
```

**Bad:**

```jinja
<script>
  const name = "{{ user.name }}";
</script>
```

Breaks on quotes/special chars.

**Better:**

```jinja
<script>
  const name = {{ user.name|tojson }};
</script>
```

---

## 15. URL Encoding Filters

```jinja
<a href="/search?q={{ query|urlencode }}">Search</a>
```

In Flask, prefer `url_for` for application routes:

```jinja
<a href="{{ url_for('listings.index', q=query) }}">Search</a>
```

---

## 16. Selection and Mapping Filters

### `map`

Extract or transform values from a list.

```jinja
{{ categories|map(attribute="name")|join(", ") }}
```

→ `Guitars, Pedals, Amps`

### `select` / `reject`

```jinja
{% for item in items|select("string") %}{{ item }}{% endfor %}
{% for item in items|reject("none") %}{{ item }}{% endfor %}
```

### `selectattr` / `rejectattr`

```jinja
{% for listing in listings|selectattr("is_featured") %}
  <article>{{ listing.title }}</article>
{% endfor %}
```

With a test:

```jinja
{% for listing in listings|selectattr("price", "gt", 500) %}
  <article>{{ listing.title }}</article>
{% endfor %}
```

```jinja
{% for listing in listings|rejectattr("is_sold") %}
  <article>{{ listing.title }}</article>
{% endfor %}
```

**Warning:** nice for small display logic, but filtering should usually happen in Python/database if it affects business behavior, pagination, performance, or correctness.

---

## 17. Tests: `is ...`

Tests ask **questions** (filters transform values).

```jinja
{% if value is string %}
```

Syntax: `value is test`.

```jinja
{% if listing.price is number %}<p>${{ listing.price }}</p>{% endif %}
{% if category is defined %}<p>{{ category.name }}</p>{% endif %}
{% if description is none %}<p>No description.</p>{% endif %}
```

### Common tests

```
defined, undefined, none,
string, number, iterable, mapping,
sameas, escaped,
divisibleby, even, odd
```

```jinja
{% if page is even %}<p>Even page.</p>{% endif %}
{% if user.email is defined %}<p>{{ user.email }}</p>{% endif %}
{% if value is sameas false %}<p>Explicitly false.</p>{% endif %}
```

---

## 18. Jinja Functions / Globals

Flask exposes globals to templates.

```jinja
{{ url_for("static", filename="css/app.css") }}
<a href="{{ url_for('listings.show', listing_id=listing.id) }}">View listing</a>
```

Other common globals:

```jinja
{{ range(1, 5) }}
{{ dict(a=1, b=2) }}
```

Do not overuse function calls in templates — keep Python logic in Python.

---

## 19. Loops and Loop Variables

```jinja
<ul>
  {% for category in categories %}
    <li>{{ category.name }}</li>
  {% endfor %}
</ul>
```

### Loop helpers

| Variable | Meaning |
| --- | --- |
| `loop.index` | 1-based index |
| `loop.index0` | 0-based index |
| `loop.first` | true on first iteration |
| `loop.last` | true on last iteration |
| `loop.length` | total items |
| `loop.cycle(...)` | cycle through values |

```jinja
{% for category in categories %}
  <li>{{ loop.index }}. {{ category.name }}</li>
{% endfor %}
```

```jinja
{% for category in categories %}
  <article class="{{ loop.cycle('odd', 'even') }}">
    <h2>{{ category.name }}</h2>
  </article>
{% endfor %}
```

Prefer CSS `:nth-child` selectors when possible. Use loop helpers when the HTML itself needs different content.

---

## 20. Conditionals

```jinja
{% if categories %}
  <p>Found {{ categories|length }} categories.</p>
{% else %}
  <p>No categories found.</p>
{% endif %}
```

```jinja
{% if total == 0 %}
  <p>No results.</p>
{% elif total == 1 %}
  <p>One result.</p>
{% else %}
  <p>{{ total }} results.</p>
{% endif %}
```

Combined with tests:

```jinja
{% if listing.description is defined and listing.description %}
  <p>{{ listing.description }}</p>
{% endif %}
```

---

## 21. Inline Comments vs HTML Comments

```jinja
{# This will not render. #}
```

```html
<!-- This will render into the final HTML source. -->
```

Use Jinja comments for internal notes. Use HTML comments only when you want the comment in the delivered HTML.

---

## 22. Whitespace Control

Jinja can trim whitespace with `-`.

Normal:

```jinja
{% for item in items %}
  {{ item }}
{% endfor %}
```

Whitespace-controlled:

```jinja
{%- for item in items %}
  {{ item }}
{%- endfor %}
```

Also: `{{- value -}}`.

Useful for text files, emails, config generation, compact HTML — but can hurt readability. For normal HTML, don't obsess unless it affects layout/output.

---

## 23. Expression Examples (Practical)

### Showing result count

```jinja
<small>Showing {{ categories|length }} of {{ total }} results</small>
```

### Empty state

```jinja
{% if categories %}
  <ul>
    {% for category in categories %}<li>{{ category.name }}</li>{% endfor %}
  </ul>
{% else %}
  <p>No categories found.</p>
{% endif %}
```

### Search query display

```jinja
{% if query %}
  <p>Search results for <strong>{{ query }}</strong></p>
{% endif %}
```

### List of tags

```jinja
<p>{{ listing.tags|map(attribute="name")|join(", ") }}</p>
```

### Safe fallback for missing description

```jinja
<p>{{ listing.summary_description|default("No summary available.", true) }}</p>
```

### Description preview from HTML

```jinja
<p>{{ listing.complete_description_html|striptags|truncate(180) }}</p>
```

### Trusted sanitized HTML

```jinja
<div class="description-complete">
  {{ listing.complete_description_html|safe }}
</div>
```

Only use `|safe` if HTML is trusted/sanitized.

---

## 24. Custom Filters

Define your own filters in Python.

```python
@app.template_filter("currency")
def currency(value):
    if value is None:
        return "Price unavailable"
    return f"${value:,.2f}"
```

Then in Jinja:

```jinja
<p>{{ listing.price|currency }}</p>
```

→ `<p>$1,299.00</p>`

```python
@app.template_filter("pluralize")
def pluralize(count, singular, plural=None):
    if count == 1:
        return singular
    return plural or f"{singular}s"
```

```jinja
<p>{{ total }} {{ total|pluralize("result") }}</p>
```

→ `1 result`, `8 results`

### Good custom filters

- currency
- date formatting
- pluralization
- title fallback
- duration formatting
- markdown rendering (if sanitized)

### Bad custom filters

- database queries
- API calls
- permission checks with side effects
- complex business workflows

---

## 25. Custom Tests

```python
@app.template_test("external_url")
def is_external_url(value):
    return isinstance(value, str) and value.startswith(("http://", "https://"))
```

```jinja
{% if link.href is external_url %}
  <a href="{{ link.href }}" rel="noopener noreferrer">External link</a>
{% endif %}
```

Use custom tests for readable template conditions.

---

## 26. Where to Draw the Line

### Good in Jinja

- render values
- escape values
- loop over already-prepared collections
- show/hide sections
- simple formatting with filters
- template composition
- small display-only decisions

### Better in Python

- database queries
- API calls
- permission logic
- pagination logic
- sorting for correctness
- filtering for correctness
- complex calculations
- data normalization
- security decisions

**Too much Jinja:**

```jinja
{% for listing in listings|selectattr("price", "gt", 500)|sort(attribute="created_at")|reverse %}
  ...
{% endfor %}
```

**Better — do it in Python:**

```python
listings = Listing.query.filter(Listing.price > 500).order_by(Listing.created_at.desc()).all()
```

Then Jinja stays clean:

```jinja
{% for listing in listings %}
  ...
{% endfor %}
```

---

## 27. Common Mistakes

### Using Python functions by instinct

**Wrong:**

```jinja
{{ len(categories) }}
```

**Better:**

```jinja
{{ categories|length }}
```

### Forgetting values are autoescaped

```jinja
{{ listing.description_html }}
```

may render HTML tags as text if autoescape is on. If the HTML is trusted/sanitized:

```jinja
{{ listing.description_html|safe }}
```

But don't use `safe` casually.

### Using `default` without understanding falsey values

```jinja
{{ description|default("No description") }}
```

may not replace an empty string. For empty strings too:

```jinja
{{ description|default("No description", true) }}
```

### Putting business logic in filters

**Okay:** `{{ price|currency }}`

**Not okay:** `{{ user|get_recommended_products }}`

Templates should not be secretly doing application work.

---

## 28. Practical Filter Cheat Sheet

### Text

```jinja
{{ value|upper }}
{{ value|lower }}
{{ value|title }}
{{ value|capitalize }}
{{ value|trim }}
{{ value|replace("old", "new") }}
{{ value|truncate(160) }}
{{ value|striptags }}
```

### Collections

```jinja
{{ items|length }}
{{ items|first }}
{{ items|last }}
{{ items|join(", ") }}
{% for item in items|sort %}
{% for item in items|reverse %}
{% for row in items|batch(3) %}
{% for column in items|slice(3) %}
```

### Objects / attributes

```jinja
{{ categories|map(attribute="name")|join(", ") }}
{% for item in items|selectattr("active") %}
{% for item in items|rejectattr("archived") %}
```

### Numbers

```jinja
{{ value|int }}
{{ value|float }}
{{ value|round(2) }}
{{ value|abs }}
```

### Safety / HTML / JSON

```jinja
{{ value|escape }}
{{ value|e }}
{{ trusted_html|safe }}
{{ data|tojson }}
```

### Fallbacks

```jinja
{{ value|default("Fallback") }}
{{ value|default("Fallback", true) }}
```

---

## 29. Best Mental Model

```
Python route/service:
  prepares clean data
Jinja template:
  composes HTML
  uses filters for presentation formatting
  uses tests for simple condition checks
  uses blocks/includes/macros for structure
Pico:
  styles semantic HTML
HTMX/vanilla JS:
  adds progressive interactivity
```

**Key expression rule:**

> Inside `{{ ... }}` and `{% ... %}`, you are writing **Jinja**, not Python.

**Most important filter rule:**

> Use filters for **display transformation**, not business logic.

### Final practical example

```jinja
{% extends "base.html" %}
{% import "macros/ui.html" as ui %}
{% block title %}
  {{ category.name|default("Categories", true) }} · Gear Garage
{% endblock %}
{% block content %}
  <header>
    <h1>{{ category.name }}</h1>
    <small>Showing {{ listings|length }} of {{ total }} results</small>
  </header>
  {% if listings %}
    <section class="listings-grid">
      {% for listing in listings %}
        <article>
          <h2>{{ listing.title }}</h2>
          <p>
            {{ listing.summary_description|default("No summary available.", true)|truncate(160) }}
          </p>
          {% if listing.tags %}
            <small>{{ listing.tags|map(attribute="name")|join(", ") }}</small>
          {% endif %}
          {{ ui.button("View listing", href=url_for("listings.show", listing_id=listing.id)) }}
        </article>
      {% endfor %}
    </section>
  {% else %}
    <p>No listings found.</p>
  {% endif %}
{% endblock %}
```

The sweet spot: Python-like enough to be comfortable, but still clearly a template language focused on rendering.
