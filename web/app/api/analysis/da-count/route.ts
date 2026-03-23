/**
 * GET /api/analysis/da-count?parcel_id=...
 *
 * Returns the count of Gold Coast development applications for a property.
 * Gold Coast only — returns null for other LGAs.
 * For COMPLEX lots (BUP/GTP full complex view), counts all DAs across the plan.
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function GET(req: NextRequest) {
  const parcelId = req.nextUrl.searchParams.get("parcel_id");

  if (!parcelId) {
    return NextResponse.json({ error: "parcel_id is required" }, { status: 400 });
  }

  try {
    const result = await db.query<{ da_count: number }>(
      `SELECT COUNT(da.application_number)::int AS da_count
       FROM parcels p
       LEFT JOIN goldcoast_dev_applications da ON (
         CASE
           WHEN p.cadastre_lot = 'COMPLEX'
             THEN da.cadastre_lotplan LIKE '%' || p.cadastre_plan
           ELSE
             da.cadastre_lotplan = p.cadastre_lot || p.cadastre_plan
         END
       )
       WHERE p.id = $1
         AND p.lga_name ILIKE '%gold coast%'
       GROUP BY p.id`,
      [parcelId]
    );

    if (result.rows.length === 0) {
      // Not found or not Gold Coast
      return NextResponse.json(null);
    }

    return NextResponse.json({ count: result.rows[0].da_count });
  } catch (err) {
    console.error("DA count error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
