/**
 * GET /api/analysis/da-count?parcel_id=...
 *
 * Returns the count of development applications for a property.
 * Works for all councils with DA data.
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
      `SELECT COUNT(DISTINCT da.application_number)::int AS da_count
       FROM parcels p
       JOIN development_application_addresses daa ON (
         CASE
           WHEN p.cadastre_lot = 'COMPLEX'
             THEN daa.cadastre_lotplan LIKE '%' || p.cadastre_plan
           ELSE
             daa.cadastre_lotplan = p.cadastre_lot || p.cadastre_plan
         END
       )
       JOIN development_applications da ON da.id = daa.application_id
       WHERE p.id = $1
       GROUP BY p.id`,
      [parcelId]
    );

    if (result.rows.length === 0) {
      return NextResponse.json(null);
    }

    return NextResponse.json({ count: result.rows[0].da_count });
  } catch (err) {
    console.error("DA count error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
