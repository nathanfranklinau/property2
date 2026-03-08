-- Add LGA and zoning columns to parcels table.
-- Populated on first lookup via spatial join against qld_lga_boundaries / qld_planning_zones.

ALTER TABLE parcels ADD COLUMN IF NOT EXISTS lga_name VARCHAR(200);
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS zone_code VARCHAR(50);
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS zone_name VARCHAR(200);
