/**
 * GET /api/analysis/cityplan?parcel_id=...
 *
 * Returns Gold Coast City Plan overlay data for a property.
 * Performs spatial intersection against all qld_goldcoast_* tables
 * using the parcel's geometry. Returns null fields when the property
 * doesn't intersect a given overlay (or isn't in Gold Coast at all).
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function GET(req: NextRequest) {
  const parcelId = req.nextUrl.searchParams.get("parcel_id");

  if (!parcelId) {
    return NextResponse.json({ error: "parcel_id is required" }, { status: 400 });
  }

  try {
    // First check if this parcel is in Gold Coast LGA
    const lgaCheck = await db.query<{ lga_name: string }>(
      `SELECT lga_name FROM parcels WHERE id = $1`,
      [parcelId]
    );

    if (lgaCheck.rows.length === 0) {
      return NextResponse.json({ error: "Parcel not found" }, { status: 404 });
    }

    const lga = lgaCheck.rows[0].lga_name;
    if (!lga || !lga.toLowerCase().includes("gold coast")) {
      // Not a Gold Coast property — return empty (no City Plan data)
      return NextResponse.json(null);
    }

    // Run all spatial queries in parallel against the parcel geometry
    const [zone, height, bushfire, dwelling, mls, airport, density, buffer] = await Promise.all([
      // Zone
      db.query(
        `SELECT z.lvl1_zone, z.zone, z.zone_precinct, z.building_height, z.bh_category
         FROM qld_goldcoast_zones z
         JOIN parcels p ON ST_Intersects(z.geometry, p.geometry)
         WHERE p.id = $1
         ORDER BY ST_Area(ST_Intersection(z.geometry, p.geometry)) DESC
         LIMIT 1`,
        [parcelId]
      ),
      // Building height overlay
      db.query(
        `SELECT bh.height_in_metres, bh.storey_number, bh.height_label
         FROM qld_goldcoast_building_height bh
         JOIN parcels p ON ST_Intersects(bh.geometry, p.geometry)
         WHERE p.id = $1
         ORDER BY ST_Area(ST_Intersection(bh.geometry, p.geometry)) DESC
         LIMIT 1`,
        [parcelId]
      ),
      // Bushfire hazard
      db.query(
        `SELECT bf.ovl2_desc
         FROM qld_goldcoast_bushfire_hazard bf
         JOIN parcels p ON ST_Intersects(bf.geometry, p.geometry)
         WHERE p.id = $1
         ORDER BY ST_Area(ST_Intersection(bf.geometry, p.geometry)) DESC
         LIMIT 1`,
        [parcelId]
      ),
      // Dwelling house overlay
      db.query(
        `SELECT 1 AS applies
         FROM qld_goldcoast_dwelling_house_overlay dh
         JOIN parcels p ON ST_Intersects(dh.geometry, p.geometry)
         WHERE p.id = $1
         LIMIT 1`,
        [parcelId]
      ),
      // Minimum lot size
      db.query(
        `SELECT ml.mls
         FROM qld_goldcoast_minimum_lot_size ml
         JOIN parcels p ON ST_Intersects(ml.geometry, p.geometry)
         WHERE p.id = $1
         ORDER BY ST_Area(ST_Intersection(ml.geometry, p.geometry)) DESC
         LIMIT 1`,
        [parcelId]
      ),
      // Airport noise
      db.query(
        `SELECT an.sensitive_use_type, an.buffer_source
         FROM qld_goldcoast_airport_noise an
         JOIN parcels p ON ST_Intersects(an.geometry, p.geometry)
         WHERE p.id = $1
         LIMIT 1`,
        [parcelId]
      ),
      // Residential density
      db.query(
        `SELECT rd.residential_density
         FROM qld_goldcoast_residential_density rd
         JOIN parcels p ON ST_Intersects(rd.geometry, p.geometry)
         WHERE p.id = $1
         ORDER BY ST_Area(ST_Intersection(rd.geometry, p.geometry)) DESC
         LIMIT 1`,
        [parcelId]
      ),
      // Buffer area
      db.query(
        `SELECT 1 AS applies
         FROM qld_goldcoast_buffer_area ba
         JOIN parcels p ON ST_Intersects(ba.geometry, p.geometry)
         WHERE p.id = $1
         LIMIT 1`,
        [parcelId]
      ),
    ]);

    const zoneRow = zone.rows[0] ?? null;
    const heightRow = height.rows[0] ?? null;
    const bushfireRow = bushfire.rows[0] ?? null;
    const mlsRow = mls.rows[0] ?? null;
    const airportRow = airport.rows[0] ?? null;
    const densityRow = density.rows[0] ?? null;

    return NextResponse.json({
      zone: zoneRow
        ? {
            lvl1_zone: zoneRow.lvl1_zone,
            zone: zoneRow.zone,
            zone_precinct: zoneRow.zone_precinct !== "None" ? zoneRow.zone_precinct : null,
            building_height: zoneRow.building_height,
            bh_category: zoneRow.bh_category,
          }
        : null,
      building_height: heightRow
        ? {
            height_in_metres: heightRow.height_in_metres,
            storey_number: heightRow.storey_number,
            height_label: heightRow.height_label,
          }
        : null,
      bushfire_hazard: bushfireRow ? { level: bushfireRow.ovl2_desc } : null,
      dwelling_house_overlay: dwelling.rows.length > 0,
      minimum_lot_size: mlsRow ? { mls: mlsRow.mls } : null,
      airport_noise: airportRow
        ? {
            sensitive_use_type: airportRow.sensitive_use_type,
            buffer_source: airportRow.buffer_source,
          }
        : null,
      residential_density: densityRow
        ? { code: densityRow.residential_density }
        : null,
      buffer_area: buffer.rows.length > 0,
    });
  } catch (err) {
    console.error("City Plan lookup error:", err);
    return NextResponse.json({ error: "Failed to fetch City Plan data" }, { status: 500 });
  }
}
