/**
 * GET /api/properties/encumbrances?lot=&plan=
 *
 * Returns all cadastre parcels that intersect the given lot/plan and are NOT
 * themselves a Lot Type Parcel (i.e. easements, roads, watercourses, covenants
 * etc.). Only the portion of each intersecting parcel that falls inside the
 * base parcel is returned (ST_Intersection).
 *
 * Query params:
 *   lot   - lot identifier (e.g. "1")
 *   plan  - plan identifier (e.g. "RP123456")
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export type Encumbrance = {
  lotplan: string | null;
  parcel_typ: string;
  tenure: string | null;
  label: string;
  area_sqm: number;
  /** [[lat, lon], ...] — intersection polygon clipped to base parcel */
  coords: [number, number][][];
};

/** Map raw parcel_typ values to friendly labels. */
function typeLabel(parcel_typ: string, tenure: string | null): string {
  if (parcel_typ === "Easement") return "Easement";
  if (parcel_typ === "Road Type Parcel") return "Road";
  if (parcel_typ === "Watercourse") return "Watercourse";
  if (parcel_typ === "Transport Route") return "Transport Route";
  if (tenure === "Covenant") return "Covenant";
  if (tenure === "Profit à Prendre") return "Profit à Prendre";
  return parcel_typ;
}

/**
 * Convert a GeoJSON geometry (Polygon or MultiPolygon) from PostGIS into an
 * array of rings, each ring being [[lat, lon], ...].
 * GeoJSON uses [lon, lat] — we flip to [lat, lon] for consistency with the
 * rest of the app.
 */
function geoJsonToCoords(geojson: string): [number, number][][] {
  try {
    const geom = JSON.parse(geojson) as {
      type: string;
      coordinates: number[][][] | number[][][][];
    };

    if (geom.type === "Polygon") {
      const rings = geom.coordinates as number[][][];
      // Return only the outer ring
      return [rings[0].map(([lon, lat]) => [lat, lon] as [number, number])];
    }

    if (geom.type === "MultiPolygon") {
      const polys = geom.coordinates as number[][][][];
      // Return outer ring of each sub-polygon
      return polys.map((rings) =>
        rings[0].map(([lon, lat]) => [lat, lon] as [number, number])
      );
    }
  } catch {
    // ignore parse errors
  }
  return [];
}

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const lot = searchParams.get("lot");
  const plan = searchParams.get("plan");

  if (!lot || !plan) {
    return NextResponse.json(
      { error: "lot and plan query parameters are required" },
      { status: 400 }
    );
  }

  try {
    const result = await db.query<{
      lotplan: string | null;
      parcel_typ: string;
      tenure: string | null;
      overlap_area_sqm: number;
      intersection_geojson: string;
    }>(
      `WITH base AS (
         SELECT id, geometry
         FROM qld_cadastre_parcels
         WHERE lot = $1 AND plan = $2
         LIMIT 1
       )
       SELECT
         o.lotplan,
         o.parcel_typ,
         o.tenure,
         ST_Area(ST_Intersection(b.geometry, o.geometry)::geography) AS overlap_area_sqm,
         ST_AsGeoJSON(ST_Transform(ST_Intersection(b.geometry, o.geometry), 4283)) AS intersection_geojson
       FROM base b
       JOIN qld_cadastre_parcels o ON ST_Intersects(b.geometry, o.geometry)
       WHERE o.id != b.id
         AND o.parcel_typ IS DISTINCT FROM 'Lot Type Parcel'
         AND ST_Area(ST_Intersection(b.geometry, o.geometry)::geography) > 1
       ORDER BY overlap_area_sqm DESC
       LIMIT 50`,
      [lot, plan]
    );

    const encumbrances: Encumbrance[] = result.rows.map((row) => ({
      lotplan: row.lotplan,
      parcel_typ: row.parcel_typ,
      tenure: row.tenure,
      label: typeLabel(row.parcel_typ, row.tenure),
      area_sqm: parseFloat(row.overlap_area_sqm as unknown as string),
      coords: geoJsonToCoords(row.intersection_geojson),
    }));

    return NextResponse.json({ encumbrances });
  } catch (err) {
    console.error("Encumbrances lookup error:", err);
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: "Lookup failed", detail: message },
      { status: 500 }
    );
  }
}
