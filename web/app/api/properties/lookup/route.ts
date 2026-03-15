/**
 * GET /api/properties/lookup?address=...&lat=...&lon=...
 *
 * Resolves a Google Places address to a cadastre parcel.
 *
 * Flow:
 *   1. Google Address Validation API (cached in address_validation_cache)
 *      — gates on possibleNextAction === "ACCEPT", rejects non-QLD addresses
 *   2. Spatial cadastre lookup — ST_Contains(geometry, point) using the validated
 *      lat/lon to find the parcel directly, bypassing GNAF entirely.
 *      - If no parcel contains the point, falls back to nearest parcel within 50m.
 *   2b. Address refinement — cross-checks the spatial result against
 *       qld_cadastre_address using the street number from validation, so adjacent
 *       lots (e.g. 67/67A duplex) resolve to the correct individual parcel.
 *   2c. Common property handling — if the matched lot is 0/00000 (body corporate
 *       common property), unions all lots on that plan for the full building footprint.
 *   3. Parallel enrichment: LGA, zoning, address info, complex boundary
 *
 * Query params:
 *   address  - formatted address string from Google Places Autocomplete (required)
 *   lat      - latitude from Google Places (unused — we use the validated geocode)
 *   lon      - longitude from Google Places (unused — we use the validated geocode)
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { classifyProperty, extractPlanPrefix } from "@/lib/property-type";
import { validateAddress } from "@/lib/address-validation";

const COMMON_PROPERTY_LOTS = ["0", "00000"];

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const address = searchParams.get("address")?.trim() ?? "";

  if (!address) {
    return NextResponse.json({ error: "address query parameter is required" }, { status: 400 });
  }

  try {
    // ── Step 1: Address Validation ───────────────────────────────────────────
    const validation = await validateAddress(address);

    if (!validation) {
      return NextResponse.json(
        { error: "Could not validate address. Please try again." },
        { status: 422 }
      );
    }

    if (validation.possibleNextAction !== "ACCEPT") {
      return NextResponse.json(
        {
          error:
            "Address could not be confirmed. Please select a full street address from the suggestions.",
          detail: `Validation result: ${validation.possibleNextAction ?? "unknown"}`,
        },
        { status: 422 }
      );
    }

    if (validation.administrativeArea !== "QLD") {
      return NextResponse.json(
        { error: "Only Queensland properties are currently supported." },
        { status: 422 }
      );
    }

    const geocodeLat = validation.latitude;
    const geocodeLon = validation.longitude;

    // ── Step 2: Spatial cadastre lookup ─────────────────────────────────────
    // Find the parcel whose geometry contains the validated geocode point.
    // Order by lot_area ASC so individual strata lots (small) are preferred
    // over overlapping common property lots (large).
    let parcelResult = await db.query<{
      lot: string;
      plan: string;
      lot_area: number;
      geometry_json: string;
      centroid_lat: number;
      centroid_lon: number;
    }>(
      `SELECT
         lot, plan, lot_area,
         ST_AsGeoJSON(geometry)      AS geometry_json,
         ST_Y(ST_Centroid(geometry)) AS centroid_lat,
         ST_X(ST_Centroid(geometry)) AS centroid_lon
       FROM qld_cadastre_parcels
       WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint($1, $2), 7844))
         AND parcel_typ = 'Lot Type Parcel'
       ORDER BY lot_area ASC
       LIMIT 1`,
      [geocodeLon, geocodeLat]
    );

    // Fallback: nearest parcel within ~50m if point doesn't land inside any parcel
    if (parcelResult.rows.length === 0) {
      parcelResult = await db.query<{
        lot: string;
        plan: string;
        lot_area: number;
        geometry_json: string;
        centroid_lat: number;
        centroid_lon: number;
      }>(
        `SELECT
           lot, plan, lot_area,
           ST_AsGeoJSON(geometry)      AS geometry_json,
           ST_Y(ST_Centroid(geometry)) AS centroid_lat,
           ST_X(ST_Centroid(geometry)) AS centroid_lon
         FROM qld_cadastre_parcels
         WHERE ST_DWithin(geometry, ST_SetSRID(ST_MakePoint($1, $2), 7844), 0.0005)
           AND parcel_typ = 'Lot Type Parcel'
         ORDER BY ST_Distance(geometry, ST_SetSRID(ST_MakePoint($1, $2), 7844)) ASC
         LIMIT 1`,
        [geocodeLon, geocodeLat]
      );
    }

    if (parcelResult.rows.length === 0) {
      return NextResponse.json(
        { error: "No cadastre parcel found near this address. The property may not yet be in the Queensland cadastre dataset." },
        { status: 404 }
      );
    }

    let parcelRow = parcelResult.rows[0];

    // ── Address refinement ────────────────────────────────────────────────
    // The spatial lookup may land on the wrong lot when adjacent lots are
    // very close (e.g. duplex 67/67A). Cross-check against qld_cadastre_address
    // using the street number to pick the correct lot.
    //
    // IMPORTANT: Google Address Validation strips letter suffixes — it returns
    // streetNumber="67" for both "67 Joseph St" and "67A Joseph St". So we
    // extract the house number directly from the raw input address instead,
    // which preserves the suffix (e.g. "67A").
    //
    // Unit prefix detection: if the address starts with a unit prefix like
    // "U1/31", "Unit 1/31", "1/31", extract the unit number for precise lot
    // resolution. Without it, "U1/" and "U2/" at the same street number are
    // indistinguishable by street_number alone.
    const unitPrefixMatch = address.match(/^(?:[A-Za-z]+\s*)?(\d+)\s*\//i);
    const inputUnitNumber = unitPrefixMatch?.[1] ?? null;

    if (validation.route) {
      // Extract leading house number (e.g. "67A" from "67A Joseph Street, ...")
      const rawNumberMatch = address.match(/^(\d+[A-Za-z]?)\s/i);
      const refinementNumber = rawNumberMatch?.[1]?.toUpperCase() ?? validation.streetNumber;
      const streetNameOnly = validation.route.split(" ").slice(0, -1).join(" ") || validation.route;

      if (refinementNumber) {
        // If a unit number was extracted from the address, filter by it so that
        // "U1/31 Brier Cr" resolves to Lot 1 and "U2/31 Brier Cr" to Lot 2.
        const unitFilter = inputUnitNumber ? `AND ca.unit_number = $4` : "";
        const params: (string | number)[] = [parcelRow.plan, refinementNumber, streetNameOnly];
        if (inputUnitNumber) params.push(inputUnitNumber);

        const refinement = await db.query<{
          lot: string;
          plan: string;
          lot_area: number;
          geometry_json: string;
          centroid_lat: number;
          centroid_lon: number;
        }>(
          `SELECT
             cp.lot, cp.plan, cp.lot_area,
             ST_AsGeoJSON(cp.geometry)      AS geometry_json,
             ST_Y(ST_Centroid(cp.geometry)) AS centroid_lat,
             ST_X(ST_Centroid(cp.geometry)) AS centroid_lon
           FROM qld_cadastre_address ca
           JOIN qld_cadastre_parcels cp
             ON cp.lot = ca.lot AND cp.plan = ca.plan AND cp.parcel_typ = 'Lot Type Parcel'
           WHERE ca.plan = $1
             AND ca.street_number = $2
             AND UPPER(ca.street_name) = UPPER($3)
             ${unitFilter}
           LIMIT 1`,
          params
        );

        if (refinement.rows.length > 0) {
          parcelRow = refinement.rows[0];
        }
      }
    }

    // ── SP community titles: show full site when no unit specified ────────────
    // SP plans can be community titles schemes (duplex, triplex) with a common
    // property Lot 0. The code above resolves to an individual unit lot (e.g.
    // Lot 1, 83m²) which produces a tiny boundary. When the searched address
    // has no unit prefix, treat the plan as common property so the existing
    // union logic below returns the full site outline.
    // Only SP plans can be community titles schemes — skip this check for RP and others
    if (inputUnitNumber === null && !COMMON_PROPERTY_LOTS.includes(parcelRow.lot) && /^SP\d/i.test(parcelRow.plan)) {
      const cpCheck = await db.query<{ has_cp: boolean }>(
        `SELECT EXISTS(
           SELECT 1 FROM qld_cadastre_parcels
           WHERE plan = $1 AND lot = '0' AND parcel_typ = 'Lot Type Parcel'
         ) AS has_cp`,
        [parcelRow.plan]
      );
      if (cpCheck.rows[0]?.has_cp) {
        parcelRow = { ...parcelRow, lot: "0" };
      }
    }

    // ── BUP/GTP: show full complex when no unit prefix specified ─────────────
    // BUP (Building Unit Plan) and GTP (Group Titles Plan) are multi-unit
    // complexes. When no unit number is given, show the whole site rather than
    // a single unit lot. Trigger the union pathway the same way SP does (lot "0"
    // acts as the trigger; the actual union query doesn't require lot 0 to exist).
    if (inputUnitNumber === null && !COMMON_PROPERTY_LOTS.includes(parcelRow.lot) && /^(BUP|GTP)\d/i.test(parcelRow.plan)) {
      parcelRow = { ...parcelRow, lot: "0" };
    }

    const isCommonProperty = COMMON_PROPERTY_LOTS.includes(parcelRow.lot);

    // If the point landed on a common property lot (e.g. strata building lobby),
    // union all lots on that plan to produce the full building footprint.
    if (isCommonProperty) {
      const unionResult = await db.query<{
        lot: string;
        plan: string;
        lot_area: number;
        geometry_json: string;
        centroid_lat: number;
        centroid_lon: number;
      }>(
        `SELECT
           'COMPLEX'                                  AS lot,
           plan,
           SUM(lot_area)                             AS lot_area,
           ST_AsGeoJSON(ST_Multi(ST_Union(geometry))) AS geometry_json,
           ST_Y(ST_Centroid(ST_Union(geometry)))      AS centroid_lat,
           ST_X(ST_Centroid(ST_Union(geometry)))      AS centroid_lon
         FROM qld_cadastre_parcels
         WHERE plan = $1
           AND parcel_typ = 'Lot Type Parcel'
         GROUP BY plan`,
        [parcelRow.plan]
      );
      if (unionResult.rows.length > 0) {
        parcelRow = unionResult.rows[0];
      }
    }

    const planPrefix = extractPlanPrefix(parcelRow.plan);
    // Only fetch the complex overlay for individual BUP/GTP lots — when the
    // main boundary is already the full COMPLEX union, the overlay is redundant.
    const needsComplexBoundary = !isCommonProperty && (planPrefix === "BUP" || planPrefix === "GTP");

    // ── Step 3: Parallel enrichment ──────────────────────────────────────────
    const [lgaResult, zoneResult, complexResult, addressResult] = await Promise.all([
      db
        .query<{ lga_name: string }>(
          `SELECT lga_name FROM gnaf_admin_lga
           WHERE ST_Within(ST_SetSRID(ST_MakePoint($1, $2), 7844), geom)
           LIMIT 1`,
          [geocodeLon, geocodeLat]
        )
        .catch(() => ({ rows: [] as { lga_name: string }[] })),

      db
        .query<{ zone_code: string; zone_name: string }>(
          `SELECT zone_code, zone_name FROM qld_planning_zones
           WHERE ST_Intersects(ST_SetSRID(ST_MakePoint($1, $2), 7844), geometry)
           LIMIT 1`,
          [geocodeLon, geocodeLat]
        )
        .catch(() => ({ rows: [] as { zone_code: string; zone_name: string }[] })),

      needsComplexBoundary
        ? db.query<{ complex_geometry_json: string | null; complex_lot_count: string }>(
            `SELECT
               ST_AsGeoJSON(ST_Multi(ST_Union(geometry))) AS complex_geometry_json,
               COUNT(*)::text AS complex_lot_count
             FROM qld_cadastre_parcels
             WHERE plan = $1
               AND parcel_typ = 'Lot Type Parcel'`,
            [parcelRow.plan]
          )
        : Promise.resolve({ rows: [{ complex_geometry_json: null, complex_lot_count: "0" }] }),

      // Address enrichment from qld_cadastre_address
      db
        .query<{
          address_count: string;
          flat_types: string[] | null;
          building_name: string | null;
        }>(
          `SELECT
             COUNT(*)::text AS address_count,
             ARRAY_AGG(DISTINCT unit_type)
               FILTER (WHERE unit_type IS NOT NULL AND unit_type <> '') AS flat_types,
             MAX(property_name)
               FILTER (WHERE property_name IS NOT NULL AND property_name <> '') AS building_name
           FROM qld_cadastre_address
           WHERE plan = $1
             AND ($2 = 'COMPLEX' OR lot = $2)`,
          [parcelRow.plan, parcelRow.lot]
        )
        .catch(() => ({
          rows: [{ address_count: "1", flat_types: null, building_name: null }],
        })),
    ]);

    const complex = complexResult.rows[0];
    const addrInfo = addressResult.rows[0];
    const addressCount = parseInt(addrInfo?.address_count ?? "1", 10) || 1;
    const typeInfo = classifyProperty(planPrefix, addressCount);

    return NextResponse.json({
      lot: parcelRow.lot,
      plan: parcelRow.plan,
      lot_area_sqm: parcelRow.lot_area,
      display_address: validation.formattedAddress || address,
      lat: parseFloat(parcelRow.centroid_lat as unknown as string),
      lon: parseFloat(parcelRow.centroid_lon as unknown as string),
      geometry: JSON.parse(parcelRow.geometry_json),
      lga_name: lgaResult.rows[0]?.lga_name ?? null,
      zone_code: zoneResult.rows[0]?.zone_code ?? null,
      zone_name: zoneResult.rows[0]?.zone_name ?? null,
      // Property type
      property_type: typeInfo.type,
      plan_prefix: planPrefix,
      address_count: addressCount,
      flat_types: addrInfo?.flat_types ?? [],
      building_name: addrInfo?.building_name ?? null,
      complex_geometry: complex.complex_geometry_json
        ? JSON.parse(complex.complex_geometry_json)
        : null,
      complex_lot_count: parseInt(complex.complex_lot_count, 10) || 0,
      tenure_type: typeInfo.tenure,
      // Debug metadata
      _validation_from_cache: validation.fromCache,
      _lookup_method: "spatial",
    });
  } catch (err) {
    console.error("Property lookup error:", err);
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: "Lookup failed", detail: message }, { status: 500 });
  }
}
