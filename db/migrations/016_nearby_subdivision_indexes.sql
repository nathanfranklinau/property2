-- Indexes to speed up the nearby subdivisions query.
-- The query scans qld_cadastre_address by plan and local_authority,
-- then joins to qld_cadastre_parcels by plan.

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_address_plan
  ON qld_cadastre_address (plan);

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_address_local_authority
  ON qld_cadastre_address (local_authority);

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_parcels_plan
  ON qld_cadastre_parcels (plan);
