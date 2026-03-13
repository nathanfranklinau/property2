\timing on

-- Approach: use address point geometry for fast spatial filtering,
-- then only join to parcels for the small set of matching plans.
-- EXPLAIN ANALYZE
WITH ref AS (
  SELECT
    ST_Centroid(geometry) AS geom,
    lga_name,
    cadastre_plan,
    lot_area_sqm,
    zone_name
  FROM parcels
  WHERE id = '19a3590c-28ce-40b3-a8ef-94184af6b804'
),
addr_candidates AS (
  -- Fast: scan address POINTS within 20km, filter by subdivision signals
  SELECT
    a.plan,
    COUNT(DISTINCT a.lot) AS lot_count,
    bool_or(a.unit_number IS NOT NULL AND a.unit_number != '') AS has_unit,
    bool_or(a.street_no_1_suffix IS NOT NULL AND a.street_no_1_suffix != '') AS has_suffix,
    array_agg(DISTINCT a.address ORDER BY a.address) FILTER (WHERE a.address IS NOT NULL AND a.address != '') AS addresses,
    MIN(ST_Distance(a.geometry::geography, ref.geom::geography)) AS dist_m
  FROM qld_cadastre_address a, ref
  WHERE a.plan LIKE 'SP%'
    AND a.local_authority = ref.lga_name
    AND a.plan != ref.cadastre_plan
    AND ST_DWithin(a.geometry::geography, ref.geom::geography, 20000)
  GROUP BY a.plan
  HAVING COUNT(DISTINCT a.lot) BETWEEN 2 AND 6
    AND (
      bool_or(a.unit_number IS NOT NULL AND a.unit_number != '')
      OR bool_or(a.street_no_1_suffix IS NOT NULL AND a.street_no_1_suffix != '')
    )
)
SELECT
  ac.plan,
  ac.lot_count,
  ac.addresses,
  ac.dist_m,
  SUM(cp.lot_area) AS total_area_sqm,
  ST_AsGeoJSON(ST_Simplify(ST_Union(cp.geometry), 0.00005)) AS boundary_geojson,
  ST_Y(ST_Centroid(ST_Union(cp.geometry))) AS centroid_lat,
  ST_X(ST_Centroid(ST_Union(cp.geometry))) AS centroid_lon
FROM addr_candidates ac
JOIN qld_cadastre_parcels cp ON cp.plan = ac.plan
GROUP BY ac.plan, ac.lot_count, ac.addresses, ac.dist_m
ORDER BY ac.dist_m
LIMIT 100;
