# CLAUDE.md

## Project Purpose

**PropertyProfiler** is a property insights platform for Australian homeowners. A homeowner types their address, the app looks up their property from authoritative datasets, runs an automated analysis of the land and existing structures, and provides zoning, council, and subdivision intelligence.

**Two audiences:** homeowners (single property analysis, Phase 1) and professionals (multi-property tracking, Phase 2).

---

## Architecture Overview

Two services share one PostgreSQL database:

```
Browser → Next.js (web/)           localhost:3000
               ↓ HTTP (on cache miss)
          Python FastAPI (data-layer/service/)   localhost:8001
               ↓ both read/write
          PostgreSQL + PostGIS      localhost:5432
```

- **`data-layer/`** — Python 3.11. Import scripts (run manually to load datasets) + FastAPI analysis microservice.
- **`web/`** — Next.js 16 App Router. Frontend UI, API routes, and blog (MDX). Uses `pg` (node-postgres) directly — no ORM.
- **`db/migrations/`** — SQL files applied manually in order.

### On-demand analysis with caching

Analysis is triggered from the UI when a user searches an address. Results are cached by cadastre parcel (`lot + plan`). The cache lives in the `property_analysis` table.

Full flow: [docs/architecture.md](docs/architecture.md)

---

## Running Locally

Two terminals required:

```bash
# Terminal 1 — Python analysis service
cd data-layer
source venv/bin/activate
uvicorn service.main:app --port 8001 --reload

# Terminal 2 — Next.js
cd web
npm run dev       # http://localhost:3000
```

### Next.js commands

```bash
cd web
npm install
npm run dev           # development server
npm run build         # production build
npm run type-check    # TypeScript check without building
```

### Python commands

```bash
cd data-layer

# Set up (Python 3.11 required)
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Import datasets (run once, or when datasets are refreshed)
python import/import_gnaf_full.py --data-dir <path>
python import/import_qld_cadastre.py --gdb <path>
python import/import_qld_pools.py --csv <path>
python import/import_qld_lga.py --src <path>
python import/import_qld_zones.py --src <path>
python import/import_admin_boundaries.py --src <path>
```

### Database migrations

Run SQL files in order — see [db/migrations/](db/migrations/) for the full list:

```bash
psql $DATABASE_URL -f db/migrations/001_immutable_datasets.sql
# ... through to the latest migration
```

---

## Environment Variables

See [data-layer/.env](data-layer/.env) and [web/.env.local](web/.env.local) for the required variables. Templates for both are in [docs/architecture.md](docs/architecture.md).

---

## Database Rules

- **Never add custom columns to immutable tables** — `gnaf_data_*`, `gnaf_admin_*`, `qld_cadastre_parcels`, `qld_pools_registered`, `qld_lga_boundaries`, `qld_planning_zones`. These are refreshed by import scripts and custom columns will be lost.
- **All spatial data uses SRID 7844** (GDA2020). Never SRID 4326 (WGS84).
- **No ORM.** Use `pg` with parameterised queries (`$1`, `$2`, …).
- **`property_analysis` is parcel-centric** — one row per `lot/plan`, shared across users. Do not duplicate analysis per user.

---

## Key Files

| File | Purpose |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Full system architecture |
| [db/migrations/](db/migrations/) | All schema migrations (apply in order) |
| `data-layer/service/main.py` | FastAPI entry point |
| `data-layer/service/analyser.py` | Analysis pipeline orchestrator |
| `web/lib/db.ts` | pg connection pool |
| `web/lib/address-validation.ts` | Google Address Validation API — cache-backed lookup |
| `web/lib/zone-rules.ts` | Static QLD zone rules lookup |
| `web/app/api/properties/lookup/route.ts` | GET — address validation → spatial cadastre → enrichment |
| `web/app/api/analysis/request/route.ts` | POST — trigger or return cached analysis |
| `web/app/api/analysis/status/route.ts` | GET — poll for analysis progress |
| `web/content/blog/*.mdx` | Blog post content (MDX with frontmatter) |

---

## YOLO Model

The YOLO model (`yolov8s.pt`) is gitignored. Download it separately and place at `data-layer/yolov8s.pt`:

```bash
pip install ultralytics
python -c "from ultralytics import YOLO; YOLO('yolov8s.pt')"
```

---

## Project Phases

- **Phase 1 (current):** Public prototype — address search, property analysis, LGA/zoning lookup, blog. No auth required.
- **Phase 2:** Auth + paywall — login, save properties/markups, multi-property tracking, subdivision journey tracking.
- **Phase 3:** Multi-state — NSW, VIC support. Schema already includes `state`/`jurisdiction` columns.

---

# Simplicity & Anti-Overengineering Rules

## Core Principle
- Solve the problem at hand. Do not solve problems that don't exist yet.

## Solution Design
- Prefer the simplest solution that satisfies the requirements
- Do NOT add abstractions, layers, or patterns unless they are needed RIGHT NOW
- Do NOT anticipate future requirements — build for today, refactor when the future arrives
- If a function, a variable, or a plain object works, do not reach for a class
- Avoid design patterns unless the problem clearly calls for one
- Avoid creating new files, modules, or directories unless the code genuinely warrants it

## Code Style
- Short, readable functions over long "flexible" ones
- Inline logic is fine for simple cases — avoid premature extraction
- Duplication is acceptable; over-abstraction is worse than mild repetition
- Prefer explicit code over clever code

## Dependencies & Infrastructure
- Do NOT introduce new libraries or tools without asking first
- Do NOT add configuration systems, plugin architectures, or dynamic loaders unless explicitly requested
- Avoid wrapping native APIs or built-in language features unnecessarily

## When Asked to Improve or Refactor
- Fix what is broken or asked for — do not refactor unrelated code
- Do NOT expand scope beyond the stated task
- If you see an opportunity to simplify, mention it — but do not act on it uninstructed

## Check Yourself Before Responding
- Ask: "Is this the simplest thing that works?"
- Ask: "Am I adding this because it's needed, or because it seems like good practice?"
- If the answer to the second question is yes → remove it

## Fallbacks & Mock Data
- NEVER use fallback values, default data, or mock/stub data unless explicitly told to
- NEVER implement fallback logic or error-recovery paths unless explicitly asked — if something fails, let it fail visibly
- If real data is unavailable, missing, or failing — STOP and tell the user; do not substitute silently
- Do NOT hardcode placeholder values, example responses, or dummy content as a workaround
- Do NOT add "temporary" fallbacks with the intention of replacing them later
- If an API, service, or data source fails — surface the real error; do not mask it with a default
- When a function would return nothing, return nothing (null/empty/error) — do not invent a value

---

# Next.js Best Practices for LLMs (2026)

This document summarizes the latest, authoritative best practices for building, structuring, and maintaining Next.js applications. It is intended for use by LLMs and developers to ensure code quality, maintainability, and scalability.

---

# Project Structure & Organization

- **Use the `app/` directory** (App Router) for all new projects. Prefer it over the legacy `pages/` directory.
- **Top-level folders:**
  - `app/` — Routing, layouts, pages, and route handlers
  - `public/` — Static assets (images, fonts, etc.)
  - `lib/` — Shared utilities, API clients, and logic
  - `components/` — Reusable UI components
  - `contexts/` — React context providers
  - `styles/` — Global and modular stylesheets
  - `hooks/` — Custom React hooks
  - `types/` — TypeScript type definitions
- **Colocation:** Place files (components, styles, tests) near where they are used, but avoid deeply nested structures.
- **Route Groups:** Use parentheses (e.g., `(admin)`) to group routes without affecting the URL path.
- **Private Folders:** Prefix with `_` (e.g., `_internal`) to opt out of routing and signal implementation details.
- **Feature Folders:** For large apps, group by feature (e.g., `app/dashboard/`, `app/auth/`).
- **Use `src/`** (optional): Place all source code in `src/` to separate from config files.

# Next.js 16+ App Router Best Practices

## Server and Client Component Integration (App Router)

**Never use `next/dynamic` with `{ ssr: false }` inside a Server Component.** This is not supported and will cause a build/runtime error.

**Correct Approach:**

- If you need to use a Client Component (e.g., a component that uses hooks, browser APIs, or client-only libraries) inside a Server Component, you must:
  1. Move all client-only logic/UI into a dedicated Client Component (with `'use client'` at the top).
  2. Import and use that Client Component directly in the Server Component (no need for `next/dynamic`).
  3. If you need to compose multiple client-only elements (e.g., a navbar with a profile dropdown), create a single Client Component that contains all of them.

**Example:**

```tsx
// Server Component
import DashboardNavbar from "@/components/DashboardNavbar";

export default async function DashboardPage() {
  // ...server logic...
  return (
    <>
      <DashboardNavbar /> {/* This is a Client Component */}
      {/* ...rest of server-rendered page... */}
    </>
  );
}
```

**Why:**

- Server Components cannot use client-only features or dynamic imports with SSR disabled.
- Client Components can be rendered inside Server Components, but not the other way around.

**Summary:**
Always move client-only UI into a Client Component and import it directly in your Server Component. Never use `next/dynamic` with `{ ssr: false }` in a Server Component.

## Next.js 16+ async request APIs (App Router)

- **Assume request-bound data is async in Server Components and Route Handlers.** In Next.js 16, APIs like `cookies()`, `headers()`, and `draftMode()` are async in the App Router.
- **Be careful with route props:** `params` / `searchParams` may be Promises in Server Components. Prefer `await`ing them instead of treating them as plain objects.
- **Avoid dynamic rendering by accident:** Accessing request data (cookies/headers/searchParams) opts the route into dynamic behavior. Read them intentionally and isolate dynamic parts behind `Suspense` boundaries when appropriate.

---

# Component Best Practices

- **Component Types:**
  - **Server Components** (default): For data fetching, heavy logic, and non-interactive UI.
  - **Client Components:** Add `'use client'` at the top. Use for interactivity, state, or browser APIs.
- **When to Create a Component:**
  - If a UI pattern is reused more than once.
  - If a section of a page is complex or self-contained.
  - If it improves readability or testability.
- **Naming Conventions:**
  - Use `PascalCase` for component files and exports (e.g., `UserCard.tsx`).
  - Use `camelCase` for hooks (e.g., `useUser.ts`).
  - Use `snake_case` or `kebab-case` for static assets (e.g., `logo_dark.svg`).
  - Name context providers as `XyzProvider` (e.g., `ThemeProvider`).
- **File Naming:**
  - Match the component name to the file name.
  - For single-export files, default export the component.
  - For multiple related components, use an `index.ts` barrel file.
- **Component Location:**
  - Place shared components in `components/`.
  - Place route-specific components inside the relevant route folder.
- **Props:**
  - Use TypeScript interfaces for props.
  - Prefer explicit prop types and default values.
- **Testing:**
  - Co-locate tests with components (e.g., `UserCard.test.tsx`).

# Naming Conventions (General)

- **Folders:** `kebab-case` (e.g., `user-profile/`)
- **Files:** `PascalCase` for components, `camelCase` for utilities/hooks, `kebab-case` for static assets
- **Variables/Functions:** `camelCase`
- **Types/Interfaces:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`

# API Routes (Route Handlers)

- **Prefer API Routes over Edge Functions** unless you need ultra-low latency or geographic distribution.
- **Location:** Place API routes in `app/api/` (e.g., `app/api/users/route.ts`).
- **HTTP Methods:** Export async functions named after HTTP verbs (`GET`, `POST`, etc.).
- **Request/Response:** Use the Web `Request` and `Response` APIs. Use `NextRequest`/`NextResponse` for advanced features.
- **Dynamic Segments:** Use `[param]` for dynamic API routes (e.g., `app/api/users/[id]/route.ts`).
- **Validation:** Always validate and sanitize input. Use libraries like `zod` or `yup`.
- **Error Handling:** Return appropriate HTTP status codes and error messages.
- **Authentication:** Protect sensitive routes using middleware or server-side session checks.

## Route Handler usage note (performance)

- **Do not call your own Route Handlers from Server Components** (e.g., `fetch('/api/...')`) just to reuse logic. Prefer extracting shared logic into modules (e.g., `lib/`) and calling it directly to avoid extra server hops.

# General Best Practices

- **TypeScript:** Use TypeScript for all code. Enable `strict` mode in `tsconfig.json`.
- **ESLint & Prettier:** Enforce code style and linting. Use the official Next.js ESLint config. In Next.js 16, prefer running ESLint via the ESLint CLI (not `next lint`).
- **Environment Variables:** Store secrets in `.env.local`. Never commit secrets to version control.
  - In Next.js 16, `serverRuntimeConfig` / `publicRuntimeConfig` are removed. Use environment variables instead.
  - `NEXT_PUBLIC_` variables are **inlined at build time** (changing them after build won’t affect a deployed build).
  - If you truly need runtime evaluation of env in a dynamic context, follow Next.js guidance (e.g., call `connection()` before reading `process.env`).
- **Testing:** Use Jest, React Testing Library, or Playwright. Write tests for all critical logic and components.
- **Accessibility:** Use semantic HTML and ARIA attributes. Test with screen readers.
- **Performance:**
  - Use built-in Image and Font optimization.
  - Prefer **Cache Components** (`cacheComponents` + `use cache`) over legacy caching patterns.
  - Use Suspense and loading states for async data.
  - Avoid large client bundles; keep most logic in Server Components.
- **Security:**
  - Sanitize all user input.
  - Use HTTPS in production.
  - Set secure HTTP headers.
  - Prefer server-side authorization for Server Actions and Route Handlers; never trust client input.
- **Documentation:**
  - Write clear README and code comments.
  - Document public APIs and components.

# Caching & Revalidation (Next.js 16 Cache Components)

- **Prefer Cache Components for memoization/caching** in the App Router.
  - Enable in `next.config.*` via `cacheComponents: true`.
  - Use the **`use cache` directive** to opt a component/function into caching.
- **Use cache tagging and lifetimes intentionally:**
  - Use `cacheTag(...)` to associate cached results with tags.
  - Use `cacheLife(...)` to control cache lifetime (presets or configured profiles).
- **Revalidation guidance:**
  - Prefer `revalidateTag(tag, 'max')` (stale-while-revalidate) for most cases.
  - The single-argument form `revalidateTag(tag)` is legacy/deprecated.
  - Use `updateTag(...)` inside **Server Actions** when you need “read-your-writes” / immediate consistency.
- **Avoid `unstable_cache`** for new code; treat it as legacy and migrate toward Cache Components.

# Tooling updates (Next.js 16)

- **Turbopack is the default dev bundler.** Configure via the top-level `turbopack` field in `next.config.*` (do not use the removed `experimental.turbo`).
- **Typed routes are stable** via `typedRoutes` (TypeScript required).

# Avoid Unnecessary Example Files

Do not create example/demo files (like ModalExample.tsx) in the main codebase unless the user specifically requests a live example, Storybook story, or explicit documentation component. Keep the repository clean and production-focused by default.

# Always Use the Latest Documentation and Guides

Before any Next.js work, find and read the relevant doc in `node_modules/next/dist/docs/`. Your training data is outdated — the docs are the source of truth.


Here’s a **simple instruction block** you can drop into a rules file (Copilot, Cursor, Claude Code, etc.).

---

# Postgres MCP Usage (Read-Only)

Use the **Postgres MCP server** when database data needs to be retrieved from Postgres.

## When to use it

Use the MCP if the task requires:

* Querying data from PostgreSQL
* Inspecting tables or schemas
* Counting or aggregating records
* Checking relationships between tables

## When NOT to use it

```sql
INSERT
UPDATE
DELETE
CREATE
ALTER
DROP
TRUNCATE
```

# Git Commits

Every completed task should result in a git commit operation. Ensure GIT Commits are regularly completed.