# Architecture

## Purpose

SubdivideGuide helps Australian homeowners navigate subdividing their land. A homeowner types their address, the app looks up their property from authoritative datasets, runs an automated analysis of the land and its existing structures, and then presents a personalised step-by-step journey covering every approval, consultation, and document required to complete a subdivision.

---

## System Overview

```
Browser
  │  Google Places Autocomplete → address selected
  │
  ▼
Next.js 15 (web/)                         localhost:3000
  │
  ├── Instant: GNAF + Cadastre lookup → PostgreSQL
  │     Returns: lot/plan, area, dimensions, boundary
  │
  ├── Cache check: property_analysis table
  │     HIT  → return results immediately (no waiting)
  │     MISS → create 'pending' record → call Python service
  │
  └── Poll /api/analysis/[id]/status every 3s until complete
  │
  ▼
Python FastAPI Service (data-layer/service/)   localhost:8001
  │   Triggered by Next.js on cache miss
  │   Runs analysis pipeline as background task
  │
  ├── Download imagery from Google Maps Static API
  ├── Detect buildings via OpenCV (roadmap image, HSV)
  ├── Detect pools via YOLO v8 (satellite image)
  ├── Calculate available space
  └── Write results to property_analysis table
  │
  ▼
PostgreSQL + PostGIS                           localhost:5432
  ├── Immutable datasets (GNAF, Cadastre, Pools)
  └── Application tables (parcels, property_analysis, …)
```

---

## Two Services, One Database

Locally you run two processes. They share the PostgreSQL database — the Python service writes analysis results, Next.js reads and serves them to the browser.

```bash
# Terminal 1
cd data-layer && source venv/bin/activate
uvicorn service.main:app --port 8001 --reload

# Terminal 2
cd web && npm run dev
```

---

## Data Layer (`data-layer/`)

Python 3.11. Single venv at `data-layer/venv`. All scripts use `.env` for config.

### Import Scripts — populate immutable tables (run once, or on dataset refresh)

| Script | Source data | Tables populated |
|---|---|---|
| `import/import_gnaf.py` | GNAF PSV files | `gnaf_address_detail`, `gnaf_address_site_geocode`, `gnaf_locality`, `gnaf_state` |
| `import/import_qld_cadastre.py` | QLD DCDB GeoPackage | `qld_cadastre_parcels` |
| `import/import_qld_pools.py` | QLD pools CSV | `qld_pools_registered` |

**These scripts are deliberately simple** — the previous versions had Docker-specific complexity (disk space monitoring, file splitting, spatial chunking, `/dev/shm` temp files) that is not needed when running native PostgreSQL on macOS. The simplified versions use `psycopg2.copy_expert` for GNAF and `ogr2ogr` for cadastre.

**Rule:** Never add custom columns to the tables these scripts populate. They will be lost when datasets are refreshed.

### Analysis Service — `data-layer/service/`

A FastAPI microservice that runs the property analysis pipeline. Called by Next.js via HTTP when a property hasn't been analysed yet.

| File | Role |
|---|---|
| `main.py` | FastAPI entry point. Routes: `POST /analyse`, `GET /analyse/{id}` |
| `analyser.py` | Orchestrates the pipeline, updates `property_analysis` table as each step completes |
| `image_retrieval.py` | Downloads roadmap, satellite, mask images from Google Maps Static API |
| `building_detection.py` | Detects building footprints from roadmap images using OpenCV HSV |
| `building_detector_utils.py` | Shared CV utilities |
| `pool_detection.py` | YOLO v8 pool detection on satellite-masked images |

**Building detection approach:**
- Input: Google Maps roadmap image (dark grey buildings stand out clearly)
- Property boundary: identified as the largest red contour in the image
- Buildings: detected via HSV grayscale range 200–245; green (vegetation) and blue (water) masked out
- Pixel areas converted to m² using the known cadastral parcel area
- Output: building count, footprint areas, available space calculation

**Pool detection approach:**
- Model: `yolov8s.pt` (kept in `data-layer/`, gitignored — download separately)
- Input: satellite image clipped to property boundary
- Output: pool count, coordinates, area estimate

---

## Web Layer (`web/`)

Next.js 15 (App Router), TypeScript, Tailwind CSS. Uses `pg` (node-postgres) directly — no ORM.

### On-demand analysis flow

```
1. User types address
   └─ Google Places Autocomplete

2. Address selected → POST /api/analysis/request
   ├─ GNAF lookup: address_detail_pid, coordinates
   ├─ Cadastre lookup: lot, plan, area, boundary (PostGIS spatial join)
   ├─ Cache check: SELECT from property_analysis WHERE lot = ? AND plan = ?
   │   HIT  → { status: 'complete', ...results }  (instant)
   │   MISS  → INSERT property_analysis (status='pending')
   │          → POST http://localhost:8001/analyse { lot, plan, parcel_id }
   │          → { analysis_id, status: 'pending' }

3. UI: progress screen (cache miss only)
   ✓ Property found — 823m² at 42 Smith St
   ⏳ Downloading aerial imagery...
   ⏳ Detecting buildings...
   ⏳ Checking pool registry...
   ⏳ Calculating available space...
   (polls GET /api/analysis/[id]/status every 3s)

4. When status = 'complete' → results page
   - Lot dimensions and area
   - Satellite + annotated roadmap images
   - Main house footprint (m²)
   - Available space (m²)
   - Pool count (detected + registered)
   - Basic subdivision eligibility assessment
   - CTA: "Start your subdivision journey"
```

### API Routes

| Route | Method | Purpose |
|---|---|---|
| `/api/analysis/request` | POST | Lookup + cache check + trigger analysis if needed |
| `/api/analysis/[id]/status` | GET | Poll analysis status (for progress screen) |
| `/api/properties/lookup` | GET | GNAF + cadastre lookup (address → parcel data) |

### Page Structure

```
app/
├── page.tsx                     # Landing — address search input
├── analysis/
│   └── [id]/page.tsx            # Progress screen → results (same route)
└── api/
    ├── analysis/
    │   ├── request/route.ts
    │   └── [id]/status/route.ts
    └── properties/
        └── lookup/route.ts
```

### Database Connection

`web/lib/db.ts` exports a `pg.Pool`. All queries use parameterised statements (`$1`, `$2`, etc.).

---

## Database

### Immutable Tables (never modify, never add custom columns)

**`gnaf_address_detail`** — ~16M Australian addresses
Key fields: `address_detail_pid`, `locality_pid`, `number_first`, `street_name`, `street_type_code`, `postcode`

**`gnaf_address_site_geocode`** — address coordinates
Key fields: `address_detail_pid`, `longitude`, `latitude`, `geometry` (Point, SRID 7844)

**`qld_cadastre_parcels`** — ~3.4M QLD property boundaries
Key fields: `lot`, `plan`, `lot_area` (m²), `shire_name`, `locality`, `geometry` (MultiPolygon, SRID 7844)

**`qld_pools_registered`** — ~448K QLD registered pools
Key fields: `legal_parcel_id`, `suburb`, `street_name`, `postcode`

### Application Tables

**`parcels`** — app-owned cache of cadastre data for looked-up properties
- `id` UUID PK
- `cadastre_lot`, `cadastre_plan` — UNIQUE together
- `state` VARCHAR(3) DEFAULT 'QLD'
- `lot_area_sqm`, `frontage_m`, `depth_m`
- `display_address`, `geometry` (MultiPolygon, SRID 7844)

**`property_analysis`** — analysis results, one per parcel (shared across all users who look up the same property)
- `id` UUID PK
- `parcel_id` UUID REFERENCES parcels — UNIQUE (one analysis per parcel)
- `image_status`: 'pending' | 'downloading' | 'complete' | 'failed'
- `analysis_status`: 'pending' | 'detecting' | 'complete' | 'failed'
- `image_roadmap_path`, `image_satellite_path`, `image_markup_path`
- `main_house_size_sqm`, `building_count`, `available_space_sqm`
- `pool_count_detected`, `pool_count_registered`, `pool_area_sqm`
- `error_message`, `analyzed_at`

**Phase 2 tables** (auth + journey — not needed for prototype):
- `users`, `user_properties`, `subdivision_assessments`, `subdivision_journeys`, `journey_steps`, `journey_step_completions`

---

## Spatial Data Rules

- All geometry in **SRID 7844** (GDA2020 Geographic) — the Australian standard. Never WGS84/4326.
- All geometry columns require a PostGIS spatial index (`USING GIST`).
- Address → parcel join: `ST_Within(gnaf_geocode.geometry, cadastre.geometry)`.

---

## Multi-State Design

Schema includes `state`/`jurisdiction` columns throughout. Queensland only initially. Import scripts are QLD-specific but named so NSW/VIC equivalents slot in without schema changes.

---

## Migration from `realestateopportunities`

| Component | Treatment |
|---|---|
| GNAF import | Rewrite simplified (~200 lines, no Docker workarounds) |
| QLD Cadastre import | Rewrite simplified (~200 lines, use `ogr2ogr`) |
| Pool import | Reuse, standardise env vars |
| Google Maps image retrieval | Reuse, move to `service/`, update table refs |
| Building detection (OpenCV) | Reuse, move to `service/`, update table refs |
| YOLO pool detection | Reuse, move to `service/` |
| Opportunity scoring | Not migrated — investor-focused |
| Two-database architecture | Not migrated — single DB only |
| Promotion pipeline | Not migrated |
| React/Vite frontend | Not migrated — replaced with Next.js |
| Express backend | Not migrated — replaced with Next.js API routes |
