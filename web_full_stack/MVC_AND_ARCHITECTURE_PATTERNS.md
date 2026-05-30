# MVC and Full-Stack Architecture Patterns

Conceptual reflection on when MVC applies and what other patterns better
describe modern full-stack systems.

---

## What MVC actually is (CMV)

MVC is a **presentation pattern** for separating UI, data, and controlling
logic within a single application boundary. It was designed for interactive UIs
(originally Smalltalk GUIs), not for describing entire distributed systems.

```text
User input → Controller → Model (data + business logic) → View → Output
```

Key insight: MVC assumes all three layers live in the **same process** and
collaborate around rendering a UI. It doesn't describe network boundaries,
API contracts, or multi-service systems.

The correct order is more CMV than MVC: Controller → Model → View.

---

## When MVC applies cleanly

### Classic server-rendered monolith (Rails, Django, Laravel, ASP.NET MVC, Flask)

```text
Browser → Controller → Model (ORM/DB) → Server-rendered View → HTML → Browser
```

All three layers are in one process. The framework enforces the separation.
This is MVC's natural habitat.

In the case of Flask fullstack applications, Flask and Werkzeug collectively
perform many of the controller/dispatcher responsibilities: receiving requests,
parsing them into request objects, matching URLs to endpoints, invoking
the correct handler, managing request/response lifecycles, and returning
responses. The route function then performs the application-specific
controller logic for a particular endpoint.

### This Flask app (partially) -> ExVC

```text
Browser → Route/Controller → (no Model) → Jinja2 View → HTML → Browser
                ↓
         ReverbClient → External API
```

Missing the M. Raw dicts flow from API to template with no domain objects.
It's **VC + Client wrapper**, not MVC. Service helpers (`_search_categories`)
absorb what would be Model responsibilities.

---

## When MVC does NOT describe the system well

### React SPA + JSON API backend (decoupled client-server)

```text
React UI (View + hooks/state) → HTTP → Backend (Controller/Service/Model) → JSON
```

This is an **API-driven client-server architecture**, not "an MVC app":

- The backend doesn't render views — it returns JSON. No V in backend MVC.
- React is a UI library, not an MVC framework. Components are the View, but
  they absorb controller-like responsibilities (hooks, actions, route loaders,
  state managers).
- The system has a network boundary between the two halves. MVC doesn't model
  network boundaries.

The backend alone might use MVC internally (especially Rails/Django), but the
*whole system* is better described as **separated frontend/backend** or
**API-driven architecture**.

### Comparison of request flows

```text
Classic server-rendered MVC:
  Browser → Controller → Model → View → HTML response

SPA + API backend:
  React View → fetch/axios → API Controller → Service → Model → JSON response
                                                                      ↓
  React updates UI ← state hook ← response data ←────────────────────┘
```

---

## The Next.js hybrid case

Next.js blurs these boundaries because it can act as a **full-stack monolith**
that is both server and client — or as a pure SPA, or anything in between.

### Next.js as server-rendered monolith (Pages Router or App Router with SSR)

```text
Browser → Next.js server (route handler) → Data fetching → Server Component → HTML
```

This is close to classic MVC again:

- **Controller**: Route handlers, `getServerSideProps`, Server Actions, route.ts handlers
- **Model**: Prisma/Drizzle schemas, server-side data fetching, validation (Zod)
- **View**: React Server Components render HTML on the server

The key difference from Rails-style MVC: the "View" is React components that
can hydrate into interactive client components. So it's MVC *for the initial
render*, then becomes a client-side component tree.

### Next.js as API + React SPA (API routes + client components)

```text
Client Component → fetch('/api/...') → API route handler → DB/Service → JSON
```

Now you're back to the decoupled pattern — same as React + Express. The API
routes are controllers, but there's no server-rendered View in the MVC sense.

### Next.js hybrid (the common real-world case)

```text
Server Components (SSR) ──→ HTML (initial paint, SEO)
     +
Client Components ──→ Interactive UI, client-side state
     +
Server Actions / API routes ──→ Mutations, data fetching
```

This doesn't fit MVC cleanly. It's better described as:

- **Islands architecture** (interactive islands in a server-rendered page)
- **React Server Components architecture** (server/client component boundary)
- **Full-stack React** (one framework spanning both sides)

### Where MVC-like thinking still helps in Next.js

| MVC concept | Next.js equivalent |
| --- | --- |
| Controller | Route handlers, Server Actions, middleware |
| Model | Prisma/Drizzle schema, server-side services, Zod validation |
| View | React components (Server + Client) |

You can *organize* a Next.js app using MVC principles (`/controllers/`,
`/models/`, `/views/` or `/components/`), but the framework doesn't enforce it
and the execution model (server vs client, streaming, partial hydration) goes
far beyond what MVC describes.

---

## Summary: Which label fits which system?

| System | Best architectural label |
| --- | --- |
| Rails/Django/Laravel monolith | MVC |
| This Flask app (no Model) | Layered: Route → Service → Client |
| React SPA + Express API | API-driven client-server (decoupled) |
| Next.js with SSR + DB | Hybrid full-stack (MVC-like on server side) |
| Next.js as API + client components | API-driven (same as React + Express) |
| Microservices + SPA frontend | Distributed system with API gateway |

---

## Interview framing

**If asked "Is this MVC?":**

> "Not as a whole. The backend may be organized using MVC or a layered variant,
> but if the frontend is a standalone SPA and the backend exposes JSON APIs
> rather than rendering views, I'd describe it as a decoupled client-server
> architecture. MVC may exist inside one side of the system, but it doesn't
> describe the full-stack architecture precisely."

**If asked about Next.js specifically:**

> "Next.js with server components and a database is the closest modern
> equivalent to classic MVC — the server renders views, handles routing, and
> accesses data. But it goes beyond MVC because components can hydrate
> client-side, you have streaming and partial rendering, and Server Actions blur
> the controller boundary. I'd call it hybrid full-stack rather than MVC."

**Key principle:**

> MVC is a *presentation pattern* for one application boundary. Once you have a
> network boundary between frontend and backend, you need a different vocabulary:
> client-server, API-driven, decoupled, layered, hexagonal, etc.
