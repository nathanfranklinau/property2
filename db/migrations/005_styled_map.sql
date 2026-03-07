-- Migration 005: Replace roadmap/markup image columns with styled_map
--
-- roadmap.png and markup.png are no longer generated. The Cloud-styled map
-- (yellow buildings, pink roads on dark purple) replaces both — it serves as
-- the visual markup directly. The boundary polyline is detected from this image.
--
-- Apply:
--   psql $DATABASE_URL -f db/migrations/005_styled_map.sql

ALTER TABLE property_analysis
    ADD COLUMN IF NOT EXISTS image_styled_map_path VARCHAR(500),
    DROP COLUMN IF EXISTS image_roadmap_path,
    DROP COLUMN IF EXISTS image_markup_path;
