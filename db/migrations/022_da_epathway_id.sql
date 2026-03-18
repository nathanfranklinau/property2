-- Add epathway_id column to goldcoast_dev_applications.
-- Stores the numeric Id from the detail page URL:
-- EnquiryDetailView.aspx?Id=56066904&EnquiryListId=102
-- This allows enrichment to navigate directly to detail pages
-- without re-running a session + search workflow.

ALTER TABLE goldcoast_dev_applications
    ADD COLUMN IF NOT EXISTS epathway_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_gc_da_epathway_id
    ON goldcoast_dev_applications (epathway_id);
