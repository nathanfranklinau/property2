-- Migration 041: Add 5 new Development.i milestone stage columns
-- Discovered on Ipswich PDAEE application types (e.g. 2913/2023/PDAEE).
-- These stages are used by pre-construction/engineering DAs and were previously
-- silently skipped during enrichment.

-- Completed dates
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS submission_review_date                DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS outstanding_matters_request_date      DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS outstanding_matters_response_date     DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS precon_certification_date             DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS maintenance_date                      DATE;

-- Statuses
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS submission_review_status              TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS outstanding_matters_request_status    TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS outstanding_matters_response_status   TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS precon_certification_status           TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS maintenance_status                    TEXT;

-- Start dates
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS submission_review_start_date          DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS outstanding_matters_request_start_date DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS outstanding_matters_response_start_date DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS precon_certification_start_date       DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS maintenance_start_date                DATE;
