# Next.js Best Practices (2026)

## Project Structure & Organization

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

## Server and Client Component Integration

**Never use `next/dynamic` with `{ ssr: false }` inside a Server Component.** This causes a build/runtime error.

- Move all client-only logic/UI into a dedicated Client Component (`'use client'` at the top).
- Import and use that Client Component directly in the Server Component — no `next/dynamic` needed.

## Async Request APIs (Next.js 16+)

- `cookies()`, `headers()`, and `draftMode()` are async in the App Router — always `await` them.
- `params` / `searchParams` route props may be Promises in Server Components — `await` them.
- Accessing request data opts the route into dynamic rendering. Isolate dynamic parts behind `Suspense` where appropriate.

## Component Best Practices

- **Server Components** (default): data fetching, heavy logic, non-interactive UI.
- **Client Components:** add `'use client'`. Use for interactivity, state, or browser APIs.
- Create a component if a UI pattern is reused, complex/self-contained, or improves readability.
- Use TypeScript interfaces for props.

## Naming Conventions

- **Folders:** `kebab-case`
- **Component files:** `PascalCase`
- **Utilities/hooks:** `camelCase`
- **Static assets:** `kebab-case`
- **Variables/functions:** `camelCase`
- **Types/interfaces:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- Context providers: `XyzProvider`

## API Routes (Route Handlers)

- Place in `app/api/` (e.g., `app/api/users/route.ts`).
- Export async functions named after HTTP verbs (`GET`, `POST`, etc.).
- Use `NextRequest`/`NextResponse` for advanced features.
- Always validate and sanitize input.
- **Do not call your own Route Handlers from Server Components** — extract shared logic into `lib/` instead.

## General

- TypeScript strict mode everywhere.
- `NEXT_PUBLIC_` variables are inlined at build time — changing them post-build has no effect.
- `serverRuntimeConfig` / `publicRuntimeConfig` are removed in Next.js 16 — use env vars.

## Caching & Revalidation (Next.js 16)

- Prefer **Cache Components** (`cacheComponents: true` in `next.config.*` + `use cache` directive).
- Use `cacheTag(...)` and `cacheLife(...)` to control cache scope and lifetime.
- Prefer `revalidateTag(tag, 'max')` (stale-while-revalidate). Single-arg form is legacy.
- Use `updateTag(...)` in Server Actions for immediate consistency.
- Avoid `unstable_cache` — treat as legacy.

## Tooling (Next.js 16)

- Turbopack is the default dev bundler. Configure via `turbopack` in `next.config.*` (not `experimental.turbo`).
- Typed routes are stable via `typedRoutes`.

## Docs

Before any Next.js work, read the relevant doc in `node_modules/next/dist/docs/`. Training data is outdated — the installed docs are the source of truth.

## Misc

- Do not create example/demo files (e.g. `ModalExample.tsx`) unless explicitly requested.
