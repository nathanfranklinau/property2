-- Migration 024: Add lot_plan as a generated column on goldcoast_dev_applications
--
-- lot_plan is derived from lot_on_plan by:
--   1. Stripping a leading "Lot " prefix (case-insensitive)
--   2. Removing all spaces
-- e.g. "Lot 290 SP256801" -> "290SP256801"
--      "Lot 0 BUP7947"   -> "0BUP7947"
--      NULL              -> NULL

ALTER TABLE goldcoast_dev_applications
    ADD COLUMN IF NOT EXISTS lot_plan TEXT GENERATED ALWAYS AS (
        REPLACE(REGEXP_REPLACE(lot_on_plan, '(?i)^\s*lot\s+', ''), ' ', '')
    ) STORED;
