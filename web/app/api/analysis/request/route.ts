/**
 * POST /api/analysis/request
 *
 * The main entry point for on-demand analysis.
 *
 * 1. Checks if a cached analysis already exists for this parcel (lot/plan).
 *    If complete → returns the cached result immediately (no Python call).
 * 2. If no cache → creates a parcels row + property_analysis row,
 *    then calls the Python analysis service to start analysis in the background.
 *
 * Body:
 *   {
 *     lot:            string   // from cadastre
 *     plan:           string
 *     lot_area_sqm:   number
 *     locality:       string
 *     shire_name:     string
 *     display_address: string
 *     lat:            number   // centroid of the parcel
 *     lon:            number
 *     geometry:       GeoJSON  // parcel boundary (for display)
 *   }
 *
 * Returns:
 *   { parcel_id, analysis_id, status, cached: boolean, ...analysis_fields }
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

const ANALYSIS_SERVICE_URL = process.env.ANALYSIS_SERVICE_URL ?? "http://localhost:8001";

export async function POST(req: NextRequest) {
  let body: {
    lot: string;
    plan: string;
    lot_area_sqm: number;
    locality: string;
    shire_name: string;
    display_address: string;
    lat: number;
    lon: number;
    geometry: object;
  };

  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { lot, plan, lot_area_sqm, display_address, lat, lon, geometry } = body;

  if (!lot || !plan || !lat || !lon) {
    return NextResponse.json(
      { error: "lot, plan, lat, and lon are required" },
      { status: 400 }
    );
  }

  try {
    // ── 1. Check for existing cached analysis ───────────────────────────
    const cacheCheck = await db.query<{
      parcel_id: string;
      analysis_id: string;
      image_status: string;
      analysis_status: string;
      main_house_size_sqm: number | null;
      building_count: number | null;
      available_space_sqm: number | null;
      pool_count_detected: number | null;
      pool_count_registered: number | null;
      pool_area_sqm: number | null;
    }>(
      `SELECT
         p.id AS parcel_id,
         pa.id AS analysis_id,
         pa.image_status,
         pa.analysis_status,
         pa.main_house_size_sqm,
         pa.building_count,
         pa.available_space_sqm,
         pa.pool_count_detected,
         pa.pool_count_registered,
         pa.pool_area_sqm
       FROM parcels p
       JOIN property_analysis pa ON pa.parcel_id = p.id
       WHERE p.cadastre_lot = $1 AND p.cadastre_plan = $2`,
      [lot, plan]
    );

    if (cacheCheck.rows.length > 0) {
      const cached = cacheCheck.rows[0];

      // Complete result → return from cache immediately
      if (cached.analysis_status === "complete") {
        return NextResponse.json({ ...cached, cached: true });
      }

      // In-progress → let the client poll; no need to re-trigger
      if (cached.analysis_status === "pending" || cached.analysis_status === "detecting") {
        return NextResponse.json({
          parcel_id: cached.parcel_id,
          analysis_id: cached.analysis_id,
          image_status: cached.image_status,
          analysis_status: cached.analysis_status,
          cached: false,
        });
      }

      // Failed → fall through to re-trigger below (reset status first)
      if (cached.analysis_status === "failed") {
        await db.query(
          `UPDATE property_analysis
           SET image_status = 'pending', analysis_status = 'pending', error_message = NULL, updated_at = NOW()
           WHERE parcel_id = $1`,
          [cached.parcel_id]
        );
      }
    }

    // ── 2. Create parcel record ─────────────────────────────────────────
    const parcelInsert = await db.query<{ id: string }>(
      `INSERT INTO parcels (cadastre_lot, cadastre_plan, lot_area_sqm, display_address, geometry)
       VALUES ($1, $2, $3, $4, ST_SetSRID(ST_GeomFromGeoJSON($5), 7844))
       ON CONFLICT (cadastre_lot, cadastre_plan) DO UPDATE
         SET display_address = EXCLUDED.display_address
       RETURNING id`,
      [lot, plan, lot_area_sqm, display_address, JSON.stringify(geometry)]
    );
    const parcelId = parcelInsert.rows[0].id;

    // ── 3. Create property_analysis record (status = pending) ───────────
    const analysisInsert = await db.query<{ id: string }>(
      `INSERT INTO property_analysis (parcel_id)
       VALUES ($1)
       ON CONFLICT (parcel_id) DO NOTHING
       RETURNING id`,
      [parcelId]
    );

    // If ON CONFLICT fired (race condition), fetch existing
    let analysisId: string;
    if (analysisInsert.rows.length > 0) {
      analysisId = analysisInsert.rows[0].id;
    } else {
      const existing = await db.query<{ id: string }>(
        "SELECT id FROM property_analysis WHERE parcel_id = $1",
        [parcelId]
      );
      analysisId = existing.rows[0].id;
    }

    // ── 4. Call Python analysis service ────────────────────────────────
    const serviceResponse = await fetch(`${ANALYSIS_SERVICE_URL}/analyse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        parcel_id: parcelId,
        cadastre_lot: lot,
        cadastre_plan: plan,
        lat,
        lon,
        lot_area_sqm,
      }),
    });

    if (!serviceResponse.ok) {
      const errText = await serviceResponse.text();
      console.error("Analysis service error:", errText);
      // Don't fail the request — the client can still poll for status
    }

    return NextResponse.json({
      parcel_id: parcelId,
      analysis_id: analysisId,
      image_status: "pending",
      analysis_status: "pending",
      cached: false,
    });
  } catch (err) {
    console.error("Analysis request error:", err);
    return NextResponse.json({ error: "Failed to start analysis" }, { status: 500 });
  }
}
