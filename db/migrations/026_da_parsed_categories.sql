-- Migration 026: Add parsed description category columns to DA table
--
-- Structured fields extracted from free-text descriptions to enable
-- filtering and analytics on development applications.

ALTER TABLE goldcoast_dev_applications
    ADD COLUMN IF NOT EXISTS development_category TEXT,
    ADD COLUMN IF NOT EXISTS dwelling_type TEXT,
    ADD COLUMN IF NOT EXISTS unit_count INTEGER,
    ADD COLUMN IF NOT EXISTS lot_split_from INTEGER,
    ADD COLUMN IF NOT EXISTS lot_split_to INTEGER,
    ADD COLUMN IF NOT EXISTS assessment_level TEXT;

CREATE INDEX IF NOT EXISTS idx_gc_da_development_category ON goldcoast_dev_applications (development_category);
CREATE INDEX IF NOT EXISTS idx_gc_da_dwelling_type ON goldcoast_dev_applications (dwelling_type);
CREATE INDEX IF NOT EXISTS idx_gc_da_assessment_level ON goldcoast_dev_applications (assessment_level);
