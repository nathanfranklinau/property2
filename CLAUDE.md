# CLAUDE.md

## Project Purpose

**PropertyProfiler** is a property insights platform for Australian homeowners. A homeowner types their address, the app looks up their property from authoritative datasets, runs an automated analysis of the land and existing structures, and provides zoning, council, and subdivision intelligence.

**Two audiences:** homeowners (single property analysis, Phase 1) and professionals (multi-property tracking, Phase 2).

---

## Architecture Overview

Two services share one PostgreSQL database:

```
Browser → Next.js (web/)                      localhost:3000
               ↓ HTTP (on cache miss)
          Python FastAPI (data-layer/service/) localhost:8001
               ↓ both read/write
          PostgreSQL + PostGIS                 localhost:5432
```

- **`data-layer/`** — Python 3.11. Import scripts + FastAPI analysis microservice.
- **`web/`** — Next.js 16 App Router. Frontend UI, API routes, blog (MDX). Uses `pg` directly — no ORM.
- **`db/migrations/`** — SQL files applied manually in order.

Analysis is triggered from the UI on address search. Results are cached by cadastre parcel (`lot + plan`) in the `property_analysis` table.

Full flow: [docs/architecture.md](docs/architecture.md)

---

## Project Phases

- **Phase 1 (current):** Public prototype — address search, property analysis, LGA/zoning lookup, blog. No auth.
- **Phase 2:** Auth + paywall — login, save properties/markups, multi-property tracking.
- **Phase 3:** Multi-state — NSW, VIC support. Schema already includes `state`/`jurisdiction` columns.

---

## Environment Variables

See [data-layer/.env](data-layer/.env) and [web/.env.local](web/.env.local). Templates in [docs/architecture.md](docs/architecture.md).

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

## Rules

@docs/rules/database.md
@docs/rules/simplicity.md
@docs/rules/nextjs.md
@docs/rules/tools.md
@docs/rules/verification.md

### Python (`data-layer/`)

@docs/rules/python.md
