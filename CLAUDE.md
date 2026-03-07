# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

**SubdivideGuide** is a web application that helps Australian homeowners navigate the process of subdividing their land. A homeowner types their address, the app looks up their property from authoritative datasets, runs an automated analysis of the land and existing structures, and guides them step-by-step through every approval, consultation, and document needed to subdivide.

This is **not** a property investment tool. Audience: homeowners, not investors or developers.

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

- **`data-layer/`** — Python 3.11. Import scripts (run manually to load datasets) + FastAPI analysis microservice (runs alongside Next.js).
- **`web/`** — Next.js 15 App Router. Handles both frontend UI and API routes. Uses `pg` (node-postgres) directly — no ORM.
- **`db/migrations/`** — SQL files applied manually in order.

### On-demand analysis with caching

Analysis is triggered from the UI when a user searches an address. Results are cached by cadastre parcel (`lot + plan`) — if two users look up the same property, the second gets the cached result instantly. The cache lives in the `property_analysis` table.

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
npm run start         # serve production build
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
python import/import_gnaf.py
python import/import_qld_cadastre.py
python import/import_qld_pools.py

# Analysis service
uvicorn service.main:app --port 8001 --reload
```

### Database migrations

Run SQL files in order against your local database:

```bash
psql $DATABASE_URL -f db/migrations/001_immutable_datasets.sql
psql $DATABASE_URL -f db/migrations/002_application_tables.sql
```

---

## Environment Variables

### `data-layer/.env`

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=subdivide
POSTGRES_USER=
POSTGRES_PASSWORD=
GOOGLE_MAPS_API_KEY=
IMAGES_DIR=./images
YOLO_MODEL_PATH=./yolov8s.pt
```

### `web/.env.local`

```
DATABASE_URL=postgresql://user:password@localhost:5432/subdivide
ANALYSIS_SERVICE_URL=http://localhost:8001
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=
NEXTAUTH_SECRET=
NEXTAUTH_URL=http://localhost:3000
```

---

## Database Rules

- **Never add custom columns to immutable tables** — `gnaf_*`, `qld_cadastre_parcels`, `qld_pools_registered`. These are refreshed by import scripts and custom columns will be lost.
- **All spatial data uses SRID 7844** (GDA2020). Never SRID 4326 (WGS84).
- **No ORM.** Use `pg` with parameterised queries (`$1`, `$2`, …).
- **`property_analysis` is parcel-centric** — one row per `lot/plan`, shared across users. Do not duplicate analysis per user.

---

## Key Files

| File | Purpose |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Full system architecture |
| [docs/subdivision-process.md](docs/subdivision-process.md) | QLD subdivision steps (source for journey_steps seed data) |
| [db/migrations/001_immutable_datasets.sql](db/migrations/001_immutable_datasets.sql) | GNAF, Cadastre, Pools table schemas |
| [db/migrations/002_application_tables.sql](db/migrations/002_application_tables.sql) | App table schemas (parcels, property_analysis, …) |
| `data-layer/service/main.py` | FastAPI entry point |
| `data-layer/service/analyser.py` | Analysis pipeline orchestrator |
| `web/lib/db.ts` | pg connection pool |
| `web/app/api/analysis/request/route.ts` | POST — trigger or return cached analysis |
| `web/app/api/analysis/[id]/status/route.ts` | GET — poll for analysis progress |

---

## YOLO Model

The YOLO model (`yolov8s.pt`) is gitignored. Download it separately and place at `data-layer/yolov8s.pt`:

```bash
pip install ultralytics
python -c "from ultralytics import YOLO; YOLO('yolov8s.pt')"
```

---

## Project Phases

- **Phase 1 (current):** Public prototype — address search, property analysis, results. No auth required.
- **Phase 2:** Auth + paywall — login, save properties, start subdivision journey, step tracking.
- **Phase 3:** Multi-state — NSW, VIC support. Schema already includes `state`/`jurisdiction` columns.

---

## Migration Notes

This is a rewrite of `../realestateopportunities`. The Python analysis pipeline (building detection, pool detection, image retrieval) is carried across and moved into `data-layer/service/`. The investor-focused scoring, two-database architecture, and promotion pipeline are not migrated. The old import scripts are rewritten without Docker workarounds (they were 900–1200 lines; new versions are ~200 lines each).
