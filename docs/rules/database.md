# Database Rules

- **Never add custom columns to immutable tables** — `gnaf_data_*`, `gnaf_admin_*`, `qld_cadastre_parcels`, `qld_pools_registered`, `qld_lga_boundaries`, `qld_planning_zones`. These are refreshed by import scripts and custom columns will be lost.
- **All spatial data uses SRID 7844** (GDA2020). Never SRID 4326 (WGS84).
- **No ORM.** Use `pg` with parameterised queries (`$1`, `$2`, …).
- **`property_analysis` is parcel-centric** — one row per `lot/plan`, shared across users. Do not duplicate analysis per user.
- **Postgres MCP is read-only.** Use it for SELECT queries, schema inspection, counts, and aggregations. Never use it for INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, or TRUNCATE.
