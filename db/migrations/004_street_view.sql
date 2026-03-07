-- Migration 004: Add Street View image path to property_analysis
--
-- The analysis pipeline now fetches a Google Street View hero shot for each
-- property. image_street_view_path is NULL if no Street View coverage exists
-- at that location.
--
-- Apply:
--   psql $DATABASE_URL -f db/migrations/004_street_view.sql

ALTER TABLE property_analysis
    ADD COLUMN IF NOT EXISTS image_street_view_path VARCHAR(500);
