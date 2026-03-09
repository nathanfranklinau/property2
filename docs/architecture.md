# Architecture

## Purpose

PropertyProfiler (renamed from SubdivideGuide) is a property insights platform for Australian homeowners. A homeowner types their address, the app looks up their property from authoritative datasets, runs an automated analysis of the land and its existing structures, and presents property intelligence including zoning, council info, and subdivision potential.

**Two audiences:** homeowners (single property analysis, Phase 1) and professionals (multi-property tracking, Phase 2).

---

## System Overview

```
Browser
  │  Google Places Autocomplete → address selected
  │
  ▼
Next.js 16 (web/)                         localhost:3000
  │
  ├── Instant: Cadastre + LGA + Zoning lookup → PostgreSQL
  │     Returns: lot/plan, area, boundary, council, zone
  │
  ├── Cache check: property_analysis table
  │     HIT  → return results immediately (no waiting)
  │     MISS → create 'pending' record → call Python service
  │
  ├── Poll /api/analysis/status?parcel_id=... every 3s until complete
  │
  ├── Blog: MDX posts at /blog (SSG, SEO)
  │
  ▼
Python FastAPI Service (data-layer/service/)   localhost:8001
  │   Triggered by Next.js on cache miss
  │   Runs analysis pipeline as background task
  │
  ├── Download imagery from Google Maps Static API
  ├── Detect buildings via OpenCV (styled map image, HSV)
  ├── Detect pools via YOLO v8 (satellite image)
  ├── Calculate available space
  └── Write results to property_analysis table
  │
  ▼
PostgreSQL + PostGIS                           localhost:5432
  ├── Immutable datasets (GNAF, Cadastre, Pools, LGA boundaries, Zones)
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
| `import/import_gnaf_full.py` | GNAF PSV files (all states) | `gnaf_data_*` — 35 tables (all states, all address/street/locality data) |
| `import/import_qld_cadastre.py` | QLD DCDB GeoPackage | `qld_cadastre_parcels` |
| `import/import_qld_pools.py` | QLD pools CSV | `qld_pools_registered` |
| `import/import_qld_lga.py` | QLD LGA boundaries (GeoPackage/Shapefile) | `qld_lga_boundaries` |
| `import/import_qld_zones.py` | QLD Planning Scheme Zones (GeoPackage/Shapefile) | `qld_planning_zones` |
| `import/import_admin_boundaries.py` | Geoscape Admin Boundaries (all states) | `gnaf_admin_lga`, `gnaf_admin_localities`, `gnaf_admin_state_boundaries`, `gnaf_admin_wards` |

**These scripts are deliberately simple** — the previous versions had Docker-specific complexity that is not needed when running native PostgreSQL on macOS. The simplified versions use `psycopg2.copy_expert` for GNAF and `ogr2ogr` for spatial datasets.

**Rule:** Never add custom columns to the tables these scripts populate. They will be lost when datasets are refreshed.

### Analysis Service — `data-layer/service/`

A FastAPI microservice that runs the property analysis pipeline. Called by Next.js via HTTP when a property hasn't been analysed yet.

| File | Role |
|---|---|
| `main.py` | FastAPI entry point. Routes: `POST /analyse`, `GET /analyse/{id}` |
| `analyser.py` | Orchestrates the pipeline, updates `property_analysis` table as each step completes |
| `image_retrieval.py` | Downloads satellite + styled map images from Google Maps Static API |
| `building_detection.py` | Detects building footprints from styled map using OpenCV HSV |
| `building_detector_utils.py` | Shared CV utilities |
| `pool_detection.py` | YOLO v8 pool detection on satellite-masked images |

**Building detection approach:**
- Input: Cloud-styled Google Maps image (yellow buildings, pink roads on dark purple — map_id=813ac30c17e4a918b39744c0)
- Property boundary: identified as the largest red contour in the image
- Buildings: detected via HSV yellow range (H=20-38), S>100, V>100
- Pixel areas converted to m² using the known cadastral parcel area
- Contours converted to geographic coordinates via Mercator math (zoom=20, scale=2, image_size=640)
- Output: building count, footprint areas (as lat/lon polygons), available space calculation

**Pool detection approach:**
- Model: custom pool model at `YOLO_MODEL_PATH` (gitignored — must be sourced separately)
- Input: satellite image clipped to property boundary (prevents neighbour false positives)
- Output: pool count, coordinates, area estimate

---

## Web Layer (`web/`)

Next.js 16 (App Router), TypeScript, Tailwind CSS 4. Uses `pg` (node-postgres) directly — no ORM.

### Route Structure

```
app/
├── layout.tsx                          # Root layout (metadata, fonts)
├── sitemap.ts                          # Auto-generated sitemap
├── robots.ts                           # Robots.txt
├── (public)/                           # Route group: shared header/footer
│   ├── layout.tsx                      # SiteHeader + SiteFooter wrapper
│   ├── page.tsx                        # Landing — address search
│   └── blog/
│       ├── page.tsx                    # Blog index (category filtering)
│       └── [slug]/page.tsx             # Blog post (SSG via generateStaticParams)
├── analysis/
│   └── [id]/page.tsx                   # Progress screen → results dashboard
└── api/
    ├── analysis/
    │   ├── request/route.ts            # POST — trigger or return cached analysis
    │   └── status/route.ts             # GET — poll analysis progress
    ├── properties/
    │   └── lookup/route.ts             # GET — cadastre + LGA + zoning lookup
    └── images/
        └── [parcel_id]/[filename]/route.ts  # GET — proxy analysis images
```

### On-demand analysis flow

```
1. User types address
   └─ Google Places Autocomplete (AU only)

2. Address selected → GET /api/properties/lookup?lat=&lon=&address=
   ├─ Cadastre lookup: lot, plan, area, boundary (PostGIS ST_Within)
   ├─ LGA lookup: council name (PostGIS ST_Within on qld_lga_boundaries)
   ├─ Zoning lookup: zone code/name (PostGIS ST_Intersects on qld_planning_zones)
   └─ Returns: parcel data + lga_name + zone_code + zone_name

3. POST /api/analysis/request with parcel data
   ├─ Cache check: SELECT from property_analysis WHERE lot = ? AND plan = ?
   │   HIT  → { status: 'complete', ...results }  (instant)
   │   MISS → INSERT parcels + property_analysis (status='pending')
   │        → POST http://localhost:8001/analyse { lot, plan, parcel_id }
   │        → { parcel_id, analysis_id, status: 'pending' }

4. Redirect to /analysis/[parcel_id]
   └─ Polls GET /api/analysis/status?parcel_id=... every 3s
      ✓ Property found — 823m² at 42 Smith St
      ⏳ Downloading aerial imagery...
      ⏳ Detecting buildings...
      ⏳ Calculating available space...

5. When status = 'complete' → results dashboard
   - Interactive satellite map with building footprint polygons
   - Drawing/editing tools (polygon, rectangle, rotation, buffer zones)
   - Sidebar: lot size, lot/plan, council, zone, free space, buildings, pools
   - Subdivision potential estimate
```

### Blog System

MDX files in `web/content/blog/` with YAML frontmatter (title, date, category, description). Parsed by `web/lib/blog.ts` using `gray-matter` + `next-mdx-remote`. Posts are statically generated at build time. Categories: subdivision, zoning, property-tips, council-guides.

### Key Libraries

| Package | Purpose |
|---|---|
| `pg` | PostgreSQL client (parameterised queries, no ORM) |
| `@vis.gl/react-google-maps` | Google Maps React wrapper |
| `next-mdx-remote` | Server-side MDX rendering |
| `gray-matter` | YAML frontmatter parsing |
| `@tailwindcss/typography` | Prose styling for blog posts |

### Database Connection

`web/lib/db.ts` exports a `pg.Pool` (max: 3 connections). All queries use parameterised statements (`$1`, `$2`, etc.).

---

## Database

### Migrations

Applied in order via `psql $DATABASE_URL -f db/migrations/NNN_*.sql`:

| Migration | Purpose |
|---|---|
| `001_immutable_datasets.sql` | Cadastre, Pools table schemas (+ old partial GNAF tables, dropped in 012) |
| `002_application_tables.sql` | parcels, property_analysis, Phase 2 tables |
| `003_add_image_paths.sql` | satellite_masked + mask2 image path columns |
| `004_street_view.sql` | Street view image path column |
| `005_styled_map.sql` | Styled map image path (replaces roadmap/markup) |
| `006_building_footprints_geo.sql` | Building footprints JSONB + boundary coords + centroid |
| `007_qld_lga.sql` | QLD LGA boundary polygons table |
| `008_parcels_lga_zone.sql` | Add lga_name, zone_code, zone_name to parcels |
| `009_qld_zones.sql` | QLD planning zone polygons table |
| `010_admin_boundaries.sql` | Geoscape admin boundary tables (all states) |
| `011_gnaf_full_dataset.sql` | Full GNAF dataset — 35 gnaf_data_* tables |
| `012_drop_old_gnaf_tables.sql` | Drop partial gnaf_* tables superseded by gnaf_data_* |

### Immutable Tables (never modify, never add custom columns)

**`gnaf_data_address_detail`** — ~16.8M Australian addresses (all states)
Key fields: `address_detail_pid`, `locality_pid`, `street_locality_pid`, `number_first`, `postcode`

**`gnaf_data_address_site_geocode`** — ~20.6M address coordinates
Key fields: `address_site_geocode_pid`, `address_site_pid`, `longitude`, `latitude`, `geometry` (Point, SRID 7844)

**`gnaf_data_address_default_geocode`** — default geocode per address (~16.8M)
Key fields: `address_default_geocode_pid`, `address_detail_pid`, `longitude`, `latitude`, `geometry` (Point, SRID 7844)

**`gnaf_data_street_locality`** — ~764K streets
Key fields: `street_locality_pid`, `street_name`, `street_type_code`, `locality_pid`

**`gnaf_data_locality`** — ~17.6K localities (suburbs/towns)
Key fields: `locality_pid`, `locality_name`, `primary_postcode`, `state_pid`

**`gnaf_data_state`** — 9 states/territories

**`qld_cadastre_parcels`** — ~3.4M QLD property boundaries
Key fields: `lot`, `plan`, `lot_area` (m²), `geometry` (MultiPolygon, SRID 7844)

**`qld_pools_registered`** — ~448K QLD registered pools
Key fields: `site_name`, `suburb`, `postcode`, `number_of_pools`

**`qld_lga_boundaries`** — ~80 QLD Local Government Area boundaries
Key fields: `lga_name`, `lga_code`, `geometry` (MultiPolygon, SRID 7844)

**`qld_planning_zones`** — QLD state-wide planning scheme zones
Key fields: `zone_code`, `zone_name`, `planning_scheme`, `lga`, `geometry` (MultiPolygon, SRID 7844)

### Application Tables

**`parcels`** — app-owned cache of cadastre data for looked-up properties
- `id` UUID PK
- `cadastre_lot`, `cadastre_plan` — UNIQUE together
- `state` VARCHAR(3) DEFAULT 'QLD'
- `lot_area_sqm`, `frontage_m`, `depth_m`
- `display_address`, `geometry` (MultiPolygon, SRID 7844)
- `lga_name` — council name (cached from spatial join on first lookup)
- `zone_code`, `zone_name` — zoning info (cached from spatial join on first lookup)

**`property_analysis`** — analysis results, one per parcel (shared across all users who look up the same property)
- `id` UUID PK
- `parcel_id` UUID REFERENCES parcels — UNIQUE (one analysis per parcel)
- `image_status`: 'pending' | 'downloading' | 'complete' | 'failed'
- `analysis_status`: 'pending' | 'detecting' | 'complete' | 'failed'
- `image_satellite_path`, `image_styled_map_path`, `image_satellite_masked_path`, `image_street_view_path`, `image_mask2_path`
- `main_house_size_sqm`, `building_count`, `available_space_sqm`
- `pool_count_detected`, `pool_count_registered`, `pool_area_sqm`
- `building_footprints_geo` (JSONB), `boundary_coords_gda94` (JSONB), `centroid_lat`, `centroid_lon`
- `error_message`, `analyzed_at`

**Phase 2 tables** (auth + journey — not needed for prototype):
- `users`, `user_properties`, `subdivision_assessments`, `subdivision_journeys`, `journey_steps`, `journey_step_completions`

---

## Spatial Data Rules

- All geometry in **SRID 7844** (GDA2020 Geographic) — the Australian standard. Never WGS84/4326.
- All geometry columns require a PostGIS spatial index (`USING GIST`).
- Address → parcel join: `ST_Within(ST_MakePoint(lon, lat), cadastre.geometry)`.
- LGA lookup: `ST_Within(point, qld_lga_boundaries.geometry)`.
- Zoning lookup: `ST_Intersects(point, qld_planning_zones.geometry)`.
- Building footprints stored in GDA94 (EPSG:4283) for Google Maps alignment.

---

## Multi-State Design

Schema includes `state`/`jurisdiction` columns throughout. Queensland only initially. Import scripts are QLD-specific but named so NSW/VIC equivalents slot in without schema changes.

---

## Project Phases

- **Phase 1 (current):** Public prototype — address search, property analysis, LGA/zoning lookup, blog, interactive map. No auth. Unauthenticated proof of concept for market validation.
- **Phase 2:** Auth + paywall — login, save properties/markups, multi-property tracking, subdivision journey tracking.
- **Phase 3:** Multi-state — NSW, VIC support.

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
