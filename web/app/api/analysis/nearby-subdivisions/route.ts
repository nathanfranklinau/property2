/**
 * GET /api/analysis/nearby-subdivisions?parcel_id=...
 *
 * Returns counts of distinct plans (excluding the current plan) that contain
 * multiple lots — indicating prior subdivision activity — within each radius
 * band, restricted to the same LGA.
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function GET(req: NextRequest) {
  const parcelId = req.nextUrl.searchParams.get("parcel_id");

  if (!parcelId) {
    return NextResponse.json({ error: "parcel_id is required" }, { status: 400 });
  }

  try {
    const result = await db.query<{
      within_2km: string;
      within_5km: string;
      within_10km: string;
      within_20km: string;
      within_50km: string;
    }>(
      `WITH ref AS (
         SELECT ST_Centroid(geometry) AS geom, lga_name, cadastre_plan
         FROM parcels
         WHERE id = $1
       ),
       subdivided_nearby AS (
         SELECT
           cp.plan,
           MIN(ST_Distance(ST_Centroid(cp.geometry)::geography, ref.geom::geography)) AS dist_m
         FROM qld_cadastre_parcels cp, ref
         WHERE cp.shire_name = ref.lga_name
           AND cp.plan != ref.cadastre_plan
           AND cp.plan != ''
           AND ST_DWithin(cp.geometry::geography, ref.geom::geography, 50000)
         GROUP BY cp.plan
         HAVING COUNT(*) > 1
       )
       SELECT
         COUNT(*) FILTER (WHERE dist_m <= 2000)  AS within_2km,
         COUNT(*) FILTER (WHERE dist_m <= 5000)  AS within_5km,
         COUNT(*) FILTER (WHERE dist_m <= 10000) AS within_10km,
         COUNT(*) FILTER (WHERE dist_m <= 20000) AS within_20km,
         COUNT(*) FILTER (WHERE dist_m <= 50000) AS within_50km
       FROM subdivided_nearby`,
      [parcelId]
    );

    return NextResponse.json(result.rows[0]);
  } catch (err) {
    console.error("Nearby subdivisions error:", err);
    return NextResponse.json({ error: "Failed to fetch nearby subdivisions" }, { status: 500 });
  }
}
