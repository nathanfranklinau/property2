-- Migration 027: Add cadastre_plan to goldcoast_dev_applications
--
-- Stores the resolved plan number from qld_cadastre_parcels for each DA,
-- enabling fast plan-level joins without runtime fallback logic.
--
-- Resolution strategy (applied at enrichment time):
--   1. Exact match: da.lot_plan exists in qld_cadastre_parcels → use that plan
--   2. Address match: da.lot_plan exists in qld_cadastre_address → use that plan
--   3. No match → NULL
--
-- Examples:
--   "16RP56124"   → "RP56124"   (exact match in parcels)
--   "1001SP267345"→ "SP267345"  (unit lot matched via address table)
--   "0BUP9571"    → "BUP9571"   (Lot 0 common property, exact match in parcels)
--   "19C28536"    → NULL        (plan not in either table)

ALTER TABLE goldcoast_dev_applications
    ADD COLUMN IF NOT EXISTS cadastre_plan TEXT;

CREATE INDEX IF NOT EXISTS idx_da_cadastre_plan
    ON goldcoast_dev_applications (cadastre_plan)
    WHERE cadastre_plan IS NOT NULL;
