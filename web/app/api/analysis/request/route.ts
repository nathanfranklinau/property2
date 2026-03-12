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
 *     lot, plan, lot_area_sqm, display_address, lat, lon, geometry,
 *     lga_name, zone_code, zone_name,
 *     property_type, plan_prefix, address_count, flat_types, building_name,
 *     complex_geometry, complex_lot_count, tenure_type
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
    lga_name: string | null;
    zone_code: string | null;
    zone_name: string | null;
    property_type: string | null;
    plan_prefix: string | null;
    address_count: number | null;
    flat_types: string[] | null;
    building_name: string | null;
    complex_geometry: object | null;
    complex_lot_count: number | null;
    tenure_type: string | null;
  };

  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const {
    lot, plan, lot_area_sqm, display_address, lat, lon, geometry,
    lga_name, zone_code, zone_name,
    property_type, plan_prefix, address_count, flat_types, building_name,
    complex_geometry, complex_lot_count, tenure_type,
  } = body;

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

      // Complete result → update display_address then return from cache
      if (cached.analysis_status === "complete") {
        await db.query(
          `UPDATE parcels SET display_address = $1 WHERE id = $2`,
          [display_address, cached.parcel_id]
        );
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
    const complexGeoJson = complex_geometry ? JSON.stringify(complex_geometry) : null;
    const parcelInsert = await db.query<{ id: string }>(
      `INSERT INTO parcels (
         cadastre_lot, cadastre_plan, lot_area_sqm, display_address, geometry,
         lga_name, zone_code, zone_name,
         property_type, plan_prefix, address_count, flat_types, building_name,
         complex_geometry, complex_lot_count, tenure_type
       )
       VALUES (
         $1, $2, $3, $4, ST_SetSRID(ST_GeomFromGeoJSON($5), 7844),
         $6, $7, $8,
         $9, $10, $11, $12, $13,
         CASE WHEN $14::text IS NOT NULL THEN ST_SetSRID(ST_GeomFromGeoJSON($14), 7844) ELSE NULL END,
         $15, $16
       )
       ON CONFLICT (cadastre_lot, cadastre_plan) DO UPDATE
         SET display_address = EXCLUDED.display_address,
             lga_name = COALESCE(EXCLUDED.lga_name, parcels.lga_name),
             zone_code = COALESCE(EXCLUDED.zone_code, parcels.zone_code),
             zone_name = COALESCE(EXCLUDED.zone_name, parcels.zone_name),
             property_type = EXCLUDED.property_type,
             plan_prefix = EXCLUDED.plan_prefix,
             address_count = EXCLUDED.address_count,
             flat_types = EXCLUDED.flat_types,
             building_name = EXCLUDED.building_name,
             complex_geometry = EXCLUDED.complex_geometry,
             complex_lot_count = EXCLUDED.complex_lot_count,
             tenure_type = EXCLUDED.tenure_type
       RETURNING id`,
      [
        lot, plan, lot_area_sqm, display_address, JSON.stringify(geometry),
        lga_name ?? null, zone_code ?? null, zone_name ?? null,
        property_type ?? null, plan_prefix ?? null, address_count ?? null,
        flat_types ?? null, building_name ?? null,
        complexGeoJson,
        complex_lot_count ?? null, tenure_type ?? null,
      ]
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
        property_type: property_type ?? null,
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
