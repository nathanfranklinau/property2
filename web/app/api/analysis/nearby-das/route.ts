/**
 * GET /api/analysis/nearby-das?parcel_id=...&radius_m=...
 *
 * Returns development applications near a property, with centroid coordinates
 * for map display. Joins goldcoast_dev_applications to qld_cadastre_address
 * via the lot_plan column to get point coordinates for spatial filtering.
 *
 * Only returns DAs that are matched to cadastre records (~58% of all DAs).
 * Unmatched DAs (no cadastre record) cannot be placed on the map.
 *
 * Gold Coast only — returns null for other LGAs.
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export type NearbyDA = {
  application_number: string;
  description: string | null;
  application_type: string | null;
  lodgement_date: string | null;
  status: string | null;
  suburb: string | null;
  location_address: string | null;
  development_category: string | null;
  dwelling_type: string | null;
  assessment_level: string | null;
  unit_count: number | null;
  lot_split_from: number | null;
  lot_split_to: number | null;
  epathway_id: number | null;
  lat: number;
  lng: number;
  distance_m: number;
};

export type NearbyDASummary = {
  total: number;
  by_type: Record<string, number>;
  by_category: Record<string, number>;
  by_status: Record<string, number>;
};

export async function GET(req: NextRequest) {
  const parcelId = req.nextUrl.searchParams.get("parcel_id");
  const radiusM = parseInt(req.nextUrl.searchParams.get("radius_m") ?? "1000", 10);

  if (!parcelId) {
    return NextResponse.json({ error: "parcel_id is required" }, { status: 400 });
  }

  // Cap radius to prevent expensive queries
  const safeRadius = Math.min(Math.max(radiusM, 100), 5000);

  try {
    // Check Gold Coast
    const check = await db.query(
      `SELECT ST_Centroid(geometry) AS geom FROM parcels WHERE id = $1 AND lga_name ILIKE '%gold coast%'`,
      [parcelId]
    );
    if (check.rows.length === 0) return NextResponse.json(null);

    const result = await db.query<NearbyDA>(
      `WITH ref AS (
         SELECT ST_Centroid(geometry) AS geom
         FROM parcels
         WHERE id = $1
       )
       SELECT DISTINCT ON (da.application_number)
         da.application_number,
         da.description,
         da.application_type,
         da.lodgement_date::text,
         da.status,
         da.suburb,
         da.location_address,
         da.development_category,
         da.dwelling_type,
         da.assessment_level,
         da.unit_count,
         da.lot_split_from,
         da.lot_split_to,
         da.epathway_id,
         ST_Y(a.geometry) AS lat,
         ST_X(a.geometry) AS lng,
         ST_Distance(a.geometry::geography, ref.geom::geography)::int AS distance_m
       FROM goldcoast_dev_applications da
       JOIN qld_cadastre_address a ON a.lotplan = da.lot_plan
       CROSS JOIN ref
       WHERE da.lot_plan IS NOT NULL
         AND ST_DWithin(a.geometry::geography, ref.geom::geography, $2)
       ORDER BY da.application_number, distance_m
       LIMIT 500`,
      [parcelId, safeRadius]
    );

    // Build summary counts
    const applications = result.rows;
    const by_type: Record<string, number> = {};
    const by_category: Record<string, number> = {};
    const by_status: Record<string, number> = {};

    for (const da of applications) {
      const t = da.application_type ?? "Unknown";
      by_type[t] = (by_type[t] ?? 0) + 1;

      const c = da.development_category ?? "Other";
      by_category[c] = (by_category[c] ?? 0) + 1;

      const s = normaliseStatus(da.status ?? "Unknown");
      by_status[s] = (by_status[s] ?? 0) + 1;
    }

    return NextResponse.json({
      applications,
      total: applications.length,
      summary: { by_type, by_category, by_status },
    });
  } catch (err) {
    console.error("Nearby DAs error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

function normaliseStatus(status: string): string {
  const s = status.toLowerCase();
  if (s.includes("approved") && !s.includes("part")) return "Approved";
  if (s.includes("approved in part")) return "Approved in Part";
  if (s.includes("refused")) return "Refused";
  if (s.includes("withdrawn")) return "Withdrawn";
  if (s.includes("lapsed")) return "Lapsed";
  if (s.includes("current") || s.includes("pending") || s.includes("assessment")) return "Current";
  return "Other";
}
