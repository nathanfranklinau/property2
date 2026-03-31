# Database Rules

- **Never add custom columns to immutable tables** — these are truncated and reloaded by import scripts; custom columns will be lost:
  - `gnaf_data_*`, `gnaf_admin_*` (GNAF address dataset)
  - `qld_cadastre_parcels`, `qld_cadastre_address` (QLD cadastre)
  - `qld_pools_registered` (QLD pool register)
  - `qld_lga_boundaries`, `qld_planning_zones` (admin boundaries / zones)
  - `qld_goldcoast_zones`, `qld_goldcoast_*` (Gold Coast City Plan layers)
  - `qld_heritage_register` (QLD heritage register)
  - **Exception:** `development_applications` — additional parsed/structured columns (e.g. `development_category`, `dwelling_type`) are intentionally added on top of scraped data and must be preserved.
- **All spatial data uses SRID 7844** (GDA2020). Never SRID 4326 (WGS84).
- **No ORM.** Use `pg` with parameterised queries (`$1`, `$2`, …).
- **`property_analysis` is parcel-centric** — one row per `lot/plan`, shared across users. Do not duplicate analysis per user.
- **Postgres MCP is read-only.** Use it for SELECT queries, schema inspection, counts, and aggregations. Never use it for INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, or TRUNCATE.
