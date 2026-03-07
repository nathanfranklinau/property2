-- 006: Add columns for geographic building footprints, boundary coords, and centroid.
--
-- building_footprints_geo: JSONB array of detected buildings with lat/lon polygons
--   Format: [{"area_sqm": 150.3, "coords": [[lat, lon], ...]}, ...]
--
-- boundary_coords_gda94: JSONB array of [lat, lon] tuples — the property boundary
--   transformed to GDA94 for Google Maps alignment.
--
-- centroid_lat/centroid_lon: GDA94-adjusted centroid of the property boundary.

ALTER TABLE property_analysis
  ADD COLUMN IF NOT EXISTS building_footprints_geo JSONB,
  ADD COLUMN IF NOT EXISTS boundary_coords_gda94   JSONB,
  ADD COLUMN IF NOT EXISTS centroid_lat             DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS centroid_lon             DOUBLE PRECISION;
