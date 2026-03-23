-- Migration 028: Replace cadastre_plan with cadastre_lotplan on goldcoast_dev_applications
--
-- cadastre_plan (added in 027) is too coarse — plan-level matching fans out to
-- all neighbours for RP/SP plans with many distinct residential lots.
--
-- cadastre_lotplan stores the resolved FULL lot+plan from qld_cadastre_parcels:
--   - Exact match in parcels   → that parcel's lotplan (e.g. "16RP56124")
--   - Unit lot (address only)  → the largest Lot Type Parcel for the same plan
--                                (Lot 0 common property, e.g. "0SP267345")
--   - No match anywhere        → NULL
--
-- At query time the join is simply:  da.cadastre_lotplan = p.cadastre_lot || p.cadastre_plan

ALTER TABLE goldcoast_dev_applications
    ADD COLUMN IF NOT EXISTS cadastre_lotplan TEXT;

-- Populate: step 1 — exact match in parcels (Groups 1 and 3)
UPDATE goldcoast_dev_applications da
SET cadastre_lotplan = da.lot_plan
WHERE da.lot_plan IS NOT NULL
  AND EXISTS (SELECT 1 FROM qld_cadastre_parcels cp WHERE cp.lotplan = da.lot_plan);

-- Populate: step 2 — address-table-only unit lots (Group 2)
-- Resolve to the largest Lot Type Parcel for the same plan
UPDATE goldcoast_dev_applications da
SET cadastre_lotplan = (
    SELECT cp.lotplan
    FROM qld_cadastre_parcels cp
    WHERE cp.plan = da.cadastre_plan
      AND cp.parcel_typ = 'Lot Type Parcel'
      AND cp.lot_area > 0
    ORDER BY cp.lot_area DESC
    LIMIT 1
)
WHERE da.lot_plan IS NOT NULL
  AND da.cadastre_plan IS NOT NULL
  AND da.cadastre_lotplan IS NULL
  AND EXISTS (SELECT 1 FROM qld_cadastre_address ca WHERE ca.lotplan = da.lot_plan);

-- Drop the intermediate cadastre_plan column (no longer needed)
ALTER TABLE goldcoast_dev_applications DROP COLUMN IF EXISTS cadastre_plan;

CREATE INDEX IF NOT EXISTS idx_da_cadastre_lotplan
    ON goldcoast_dev_applications (cadastre_lotplan)
    WHERE cadastre_lotplan IS NOT NULL;
