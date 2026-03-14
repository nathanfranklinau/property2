/**
 * GET /api/properties/addresses?lot=...&plan=...
 *
 * Returns formatted address strings for all units on a given lot/plan,
 * queried from qld_cadastre_address.
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

const UNIT_TYPE_LABELS: Record<string, string> = {
  U: "Unit",
  UNIT: "Unit",
  T: "Townhouse",
  V: "Villa",
  APT: "Apartment",
  FLAT: "Flat",
  SE: "Suite",
  SHOP: "Shop",
  OFFICE: "Office",
  STUDIO: "Studio",
  LOT: "Lot",
};

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const lot = searchParams.get("lot")?.trim() ?? "";
  const plan = searchParams.get("plan")?.trim() ?? "";

  if (!lot || !plan) {
    return NextResponse.json({ error: "lot and plan required" }, { status: 400 });
  }

  const result = await db.query<{
    unit_type: string | null;
    unit_number: string | null;
    unit_suffix: string | null;
    street_number: string | null;
    street_name: string | null;
    street_type: string | null;
    locality: string | null;
  }>(
    `SELECT unit_type, unit_number, unit_suffix, street_number, street_name, street_type, locality
     FROM qld_cadastre_address
     WHERE plan = $1 AND ($2 = 'COMPLEX' OR lot = $2)
     ORDER BY unit_number ASC NULLS LAST`,
    [plan, lot]
  );

  const addresses = result.rows.map((r) => {
    const typeLabel = UNIT_TYPE_LABELS[r.unit_type ?? ""] ?? r.unit_type ?? "";
    const unitNum = [r.unit_number, r.unit_suffix].filter(Boolean).join("");
    const streetLine = [r.street_number, r.street_name, r.street_type].filter(Boolean).join(" ");
    const full = [streetLine, r.locality].filter(Boolean).join(", ");
    if (typeLabel && unitNum) return `${typeLabel} ${unitNum}, ${full}`;
    return full;
  });

  return NextResponse.json({ addresses });
}
