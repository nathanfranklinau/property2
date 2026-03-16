/**
 * GET /api/analysis/nearby-subdivisions?parcel_id=...
 *
 * Returns nearby plans that look like genuine residential subdivisions.
 * Detection uses address signals from the cadastre address table:
 *   - SP (Survey Plan) prefix only
 *   - 2–6 lots per plan
 *   - Total parcel area ≤ 6,000 m² (excludes estates/commercial plans)
 *   - Has unit numbers (e.g. U1/45) or street number suffixes (e.g. 45A)
 *     — these patterns distinguish genuine lot splits from estate stages
 *   - Same LGA as subject
 *   - Within 20 km (using address point geometry for fast spatial filtering)
 *
 * Returns plan details with all addresses, boundary geometry, and distance.
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

type NearbyPlanRow = {
  plan: string;
  lot_count: string;
  addresses: string[];
  total_area_sqm: string;
  dist_m: string;
  boundary_geojson: string;
  centroid_lat: string;
  centroid_lon: string;
  zone_name: string | null;
};

export async function GET(req: NextRequest) {
  const parcelId = req.nextUrl.searchParams.get("parcel_id");

  if (!parcelId) {
    return NextResponse.json({ error: "parcel_id is required" }, { status: 400 });
  }

  // Shared CTE fragment (used in both queries)
  const sharedCte = `
     ref AS (
       SELECT
         ST_Centroid(geometry) AS geom,
         lga_name,
         cadastre_plan
       FROM parcels
       WHERE id = $1
     ),
     addr_candidates AS (
       SELECT
         a.plan,
         COUNT(DISTINCT a.lot)  AS lot_count,
         array_agg(DISTINCT a.address ORDER BY a.address)
           FILTER (WHERE a.address IS NOT NULL AND a.address != '') AS addresses,
         MIN(ST_Distance(a.geometry::geography, ref.geom::geography)) AS dist_m
       FROM qld_cadastre_address a, ref
       WHERE (a.plan LIKE 'SP%' OR a.plan LIKE 'BUP%' OR a.plan LIKE 'GTP%')
         AND a.local_authority = ref.lga_name
         AND a.plan != ref.cadastre_plan
         AND ST_DWithin(a.geometry::geography, ref.geom::geography, 20000)
       GROUP BY a.plan
       HAVING COUNT(DISTINCT a.lot) BETWEEN 2 AND 6
         AND bool_and(a.street_no_2 IS NULL OR a.street_no_2 = '')
         AND (
           (
             bool_or(a.unit_number IS NOT NULL AND a.unit_number != '')
             AND COUNT(DISTINCT a.street_no_1) = 1
           )
           OR (COUNT(DISTINCT a.address) > 1 AND COUNT(DISTINCT a.street_no_1 || '-' || a.street_name) < COUNT(DISTINCT a.lot))
           OR bool_or(a.lot = '9999')
         )
     )`;

  try {
    // Run both queries in parallel: accurate counts (no geometry) + plan details (limited)
    const [countResult, result] = await Promise.all([
      db.query<{ within_2km: string; within_5km: string; within_10km: string; within_20km: string }>(
        `WITH ${sharedCte},
         filtered AS (
           SELECT ac.dist_m
           FROM addr_candidates ac
           JOIN qld_cadastre_parcels cp ON cp.plan = ac.plan
           GROUP BY ac.plan, ac.dist_m
           HAVING SUM(cp.lot_area) <= 6000
         )
         SELECT
           COUNT(*) FILTER (WHERE dist_m <= 2000)                      AS within_2km,
           COUNT(*) FILTER (WHERE dist_m > 2000  AND dist_m <= 5000)   AS within_5km,
           COUNT(*) FILTER (WHERE dist_m > 5000  AND dist_m <= 10000)  AS within_10km,
           COUNT(*) FILTER (WHERE dist_m > 10000 AND dist_m <= 20000)  AS within_20km
         FROM filtered`,
        [parcelId]
      ),
      db.query<NearbyPlanRow>(
        `WITH ${sharedCte},
         plan_geom AS (
           SELECT
             ac.plan,
             ac.lot_count,
             ac.addresses,
             ac.dist_m,
             ROUND(ST_Area(ST_Union(cp.geometry)::geography)::numeric) AS total_area_sqm,
             ST_AsGeoJSON(ST_Simplify(ST_Union(cp.geometry), 0.00005)) AS boundary_geojson,
             ST_Centroid(ST_Union(cp.geometry)) AS centroid
           FROM addr_candidates ac
           JOIN qld_cadastre_parcels cp ON cp.plan = ac.plan
           GROUP BY ac.plan, ac.lot_count, ac.addresses, ac.dist_m
           HAVING SUM(cp.lot_area) <= 6000
         )
         SELECT
           pg.plan, pg.lot_count, pg.addresses, pg.dist_m,
           pg.total_area_sqm, pg.boundary_geojson,
           ST_Y(pg.centroid) AS centroid_lat,
           ST_X(pg.centroid) AS centroid_lon,
           z.lvl1_zone AS zone_name
         FROM plan_geom pg
         LEFT JOIN LATERAL (
           SELECT gz.lvl1_zone
           FROM qld_goldcoast_zones gz
           WHERE ST_Intersects(gz.geometry, pg.centroid)
           LIMIT 1
         ) z ON true
         ORDER BY pg.dist_m`,
        [parcelId]
      ),
    ]);

    const cr = countResult.rows[0];
    const counts = {
      within_2km: Number(cr?.within_2km ?? 0),
      within_5km: Number(cr?.within_5km ?? 0),
      within_10km: Number(cr?.within_10km ?? 0),
      within_20km: Number(cr?.within_20km ?? 0),
    };

    if (result.rows.length === 0) {
      return NextResponse.json({ counts, plans: [] });
    }

    // Parse GeoJSON boundaries into [lat, lng] coordinate arrays
    const plans = result.rows.map((row) => {
      const geo = row.boundary_geojson ? JSON.parse(row.boundary_geojson) : null;
      let rings: [number, number][][] = [];

      if (geo && geo.type === "MultiPolygon") {
        rings = (geo.coordinates as number[][][][]).map((poly) =>
          poly[0].map(([lon, lat]) => [lat, lon] as [number, number])
        );
      } else if (geo && geo.type === "Polygon") {
        rings = [(geo.coordinates as number[][][])[0].map(([lon, lat]) => [lat, lon] as [number, number])];
      }

      return {
        plan: row.plan,
        addresses: row.addresses ?? [],
        lot_count: Number(row.lot_count),
        total_area_sqm: Math.round(Number(row.total_area_sqm)),
        distance_m: Math.round(Number(row.dist_m)),
        centroid: { lat: Number(row.centroid_lat), lng: Number(row.centroid_lon) },
        boundary_coords: rings,
        zone_name: row.zone_name ?? null,
      };
    });

    return NextResponse.json({ counts, plans });
  } catch (err) {
    console.error("Nearby subdivisions error:", err);
    return NextResponse.json({ error: "Failed to fetch nearby subdivisions" }, { status: 500 });
  }
}
