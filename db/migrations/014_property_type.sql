-- Migration 014: Property type classification
-- Adds property type metadata to the parcels table for per-type UI adaptation.

ALTER TABLE parcels ADD COLUMN IF NOT EXISTS property_type VARCHAR(30);
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS plan_prefix VARCHAR(5);
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS address_count INTEGER;
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS flat_types TEXT[];
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS building_name VARCHAR(200);
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS complex_geometry geometry(MultiPolygon, 7844);
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS complex_lot_count INTEGER;
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS tenure_type VARCHAR(50);
