/**
 * GET /api/properties/lookup?lat=...&lon=...&address=...
 *
 * Looks up a lat/lon against the QLD Cadastre and returns the matching parcel.
 * The display address comes from the caller (Google Places) rather than being
 * reconstructed from GNAF, since GNAF address_detail lacks street name columns.
 *
 * Query params:
 *   lat      - latitude from Google Places API
 *   lon      - longitude from Google Places API
 *   address  - formatted address string from Google Places (used as display_address)
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const lat = parseFloat(searchParams.get("lat") ?? "");
  const lon = parseFloat(searchParams.get("lon") ?? "");
  const address = searchParams.get("address") ?? "";

  if (isNaN(lat) || isNaN(lon)) {
    return NextResponse.json(
      { error: "lat and lon query parameters are required" },
      { status: 400 }
    );
  }

  try {
    // Find the cadastre parcel containing this coordinate.
    // ST_SetSRID(ST_MakePoint(lon, lat), 7844) creates a GDA2020 point.
    const parcelResult = await db.query<{
      lot: string;
      plan: string;
      lot_area: number;
      geometry_json: string;
      centroid_lat: number;
      centroid_lon: number;
    }>(
      `SELECT
         lot,
         plan,
         lot_area,
         ST_AsGeoJSON(geometry) AS geometry_json,
         ST_Y(ST_Centroid(geometry)) AS centroid_lat,
         ST_X(ST_Centroid(geometry)) AS centroid_lon
       FROM qld_cadastre_parcels
       WHERE ST_Within(
         ST_SetSRID(ST_MakePoint($1, $2), 7844),
         geometry
       )
       LIMIT 1`,
      [lon, lat]
    );

    if (parcelResult.rows.length === 0) {
      return NextResponse.json(
        { error: "No cadastre parcel found at this location. Is the property in Queensland?" },
        { status: 404 }
      );
    }

    const parcel = parcelResult.rows[0];

    return NextResponse.json({
      lot: parcel.lot,
      plan: parcel.plan,
      lot_area_sqm: parcel.lot_area,
      display_address: address || `Lot ${parcel.lot} on ${parcel.plan}`,
      // Use the cadastral centroid as the image centre so the boundary
      // polygon is always visually centred in generated images, regardless
      // of where Google Places geocoded the address within the lot.
      lat: parseFloat(parcel.centroid_lat as unknown as string),
      lon: parseFloat(parcel.centroid_lon as unknown as string),
      geometry: JSON.parse(parcel.geometry_json),
    });
  } catch (err) {
    console.error("Property lookup error:", err);
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: "Lookup failed", detail: message }, { status: 500 });
  }
}
