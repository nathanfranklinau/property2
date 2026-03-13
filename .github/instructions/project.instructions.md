---
description: "Key information relating to the project and its architecture"
applyTo: "*"
---

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
