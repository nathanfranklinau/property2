-- Migration 033: Add cadastre_suburb to goldcoast_dev_applications
--
-- Separates the two suburb sources on the parent table:
--   suburb          → parsed from location_address text only
--   cadastre_suburb → authoritative locality from resolving the primary lot/plan
--                     (populated during enrich/monitor via the child table lookup)

ALTER TABLE goldcoast_dev_applications ADD COLUMN cadastre_suburb TEXT;
