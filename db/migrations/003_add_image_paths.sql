-- Migration 003: Add additional image path columns to property_analysis
--
-- The analysis pipeline now generates two additional images per property:
--   satellite_masked.jpg  — satellite clipped to the property boundary
--   mask2.png             — colour-coded space usage visualisation
--
-- Apply:
--   psql $DATABASE_URL -f db/migrations/003_add_image_paths.sql

ALTER TABLE property_analysis
    ADD COLUMN IF NOT EXISTS image_satellite_masked_path VARCHAR(500),
    ADD COLUMN IF NOT EXISTS image_mask2_path            VARCHAR(500);
