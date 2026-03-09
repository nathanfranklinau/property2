-- Migration 012: Drop partial GNAF tables
-- These four tables (gnaf_state, gnaf_locality, gnaf_address_detail,
-- gnaf_address_site_geocode) were created in migration 001 as a partial
-- subset of GNAF. They are superseded by the full gnaf_data_* tables
-- (35 tables, all states) created in migration 011.
-- No app or service code queries these tables.

DROP TABLE IF EXISTS gnaf_address_site_geocode CASCADE;
DROP TABLE IF EXISTS gnaf_address_detail CASCADE;
DROP TABLE IF EXISTS gnaf_locality CASCADE;
DROP TABLE IF EXISTS gnaf_state CASCADE;
