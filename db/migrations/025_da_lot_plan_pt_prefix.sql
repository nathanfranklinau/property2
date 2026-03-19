-- Migration 025: Fix lot_plan generated column to handle PT1/PT2 prefixes
--
-- Previous regex only stripped a leading "Lot " prefix.
-- Addresses like "PT1 Lot 506 SP329487" were not handled, producing "PT1Lot506SP329487".
--
-- New logic: strip everything up to and including "Lot " (case-insensitive),
-- then remove all remaining spaces.
-- e.g. "PT1 Lot 506 SP329487" -> "506SP329487"
--      "Lot 290 SP256801"     -> "290SP256801"
--      "Lot 0 BUP7947"        -> "0BUP7947"
--      NULL                   -> NULL

ALTER TABLE goldcoast_dev_applications
    DROP COLUMN IF EXISTS lot_plan;

ALTER TABLE goldcoast_dev_applications
    ADD COLUMN lot_plan TEXT GENERATED ALWAYS AS (
        REPLACE(REGEXP_REPLACE(lot_on_plan, '(?i)^.*lot\s+', ''), ' ', '')
    ) STORED;
