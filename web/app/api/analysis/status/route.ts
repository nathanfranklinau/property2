/**
 * GET /api/analysis/status?parcel_id=...
 *
 * Poll this endpoint every 3 seconds to check the progress of an analysis.
 * The Python service updates the database as each pipeline step completes.
 *
 * Returns the current state of property_analysis for the given parcel.
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
      parcel_id: string;
      image_status: string;
      analysis_status: string;
      main_house_size_sqm: number | null;
      building_count: number | null;
      available_space_sqm: number | null;
      pool_count_detected: number | null;
      pool_count_registered: number | null;
      pool_area_sqm: number | null;
      image_satellite_path: string | null;
      image_styled_map_path: string | null;
      image_mask2_path: string | null;
      image_street_view_path: string | null;
      error_message: string | null;
      lot_area_sqm: number | null;
      display_address: string | null;
      cadastre_lot: string;
      cadastre_plan: string;
      building_footprints_geo: object | null;
      boundary_coords_gda94: number[][] | null;
      centroid_lat: number | null;
      centroid_lon: number | null;
      lga_name: string | null;
      zone_code: string | null;
      zone_name: string | null;
      property_type: string | null;
      plan_prefix: string | null;
      address_count: number | null;
      flat_types: string[] | null;
      building_name: string | null;
      complex_geometry_json: string | null;
      complex_lot_count: number | null;
      tenure_type: string | null;
    }>(
      `SELECT
         p.id               AS parcel_id,
         p.cadastre_lot,
         p.cadastre_plan,
         p.lot_area_sqm,
         p.display_address,
         p.lga_name,
         p.zone_code,
         p.zone_name,
         p.property_type,
         p.plan_prefix,
         p.address_count,
         p.flat_types,
         p.building_name,
         ST_AsGeoJSON(p.complex_geometry) AS complex_geometry_json,
         p.complex_lot_count,
         p.tenure_type,
         pa.image_status,
         pa.analysis_status,
         pa.main_house_size_sqm,
         pa.building_count,
         pa.available_space_sqm,
         pa.pool_count_detected,
         pa.pool_count_registered,
         pa.pool_area_sqm,
         pa.image_satellite_path,
         pa.image_styled_map_path,
         pa.image_mask2_path,
         pa.image_street_view_path,
         pa.error_message,
         pa.building_footprints_geo,
         pa.boundary_coords_gda94,
         pa.centroid_lat,
         pa.centroid_lon
       FROM parcels p
       JOIN property_analysis pa ON pa.parcel_id = p.id
       WHERE p.id = $1`,
      [parcelId]
    );

    if (result.rows.length === 0) {
      return NextResponse.json({ error: "Analysis not found" }, { status: 404 });
    }

    const row = result.rows[0];

    return NextResponse.json({
      ...row,
      complex_geometry: row.complex_geometry_json
        ? JSON.parse(row.complex_geometry_json)
        : null,
      complex_geometry_json: undefined,
    });
  } catch (err) {
    console.error("Status poll error:", err);
    return NextResponse.json({ error: "Failed to fetch status" }, { status: 500 });
  }
}
