/**
 * GET /api/debug/lookup?address=...
 *
 * Read-only debug endpoint. Returns ALL available data from every source.
 * Each section is independently try/caught so one failure doesn't kill the rest.
 * Does NOT write to any database tables.
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

// ── Gold Coast overlay queries (lot/plan based) ──────────────────────────────

async function fetchGoldCoastOverlays(lot: string, plan: string): Promise<Record<string, unknown>> {
  const parcelUnion = `(SELECT ST_Union(geometry) FROM qld_cadastre_parcels WHERE lot = $1 AND plan = $2)`;

  const gcQuery = (table: string, cols: string) =>
    db.query(`SELECT ${cols} FROM ${table} WHERE ST_Intersects(geometry, ${parcelUnion})`, [lot, plan])
      .catch(() => ({ rows: [] as Record<string, unknown>[] }));

  const [
    zones, buildingHeight, flood, bushfire, minLotSize,
    residentialDensity, heritage, heritageProximity, environmental,
    bufferArea, dwellingHouseOverlay, partyHouse, airportNoise,
  ] = await Promise.all([
    gcQuery("qld_goldcoast_zones", "id, zone_precinct, lvl1_zone, zone, building_height, bh_category"),
    gcQuery("qld_goldcoast_building_height", "id, cat_desc, ovl_cat, ovl2_desc, ovl2_cat, height_in_metres, storey_number, label, height_label"),
    gcQuery("qld_goldcoast_flood", "id, cat_desc, ovl_cat, ovl2_desc, ovl2_cat"),
    gcQuery("qld_goldcoast_bushfire_hazard", "id, cat_desc, ovl_cat, ovl2_desc, ovl2_cat"),
    gcQuery("qld_goldcoast_minimum_lot_size", "id, cat_desc, ovl_cat, ovl2_desc, ovl2_cat, mls"),
    gcQuery("qld_goldcoast_residential_density", "id, cat_desc, ovl_cat, ovl2_desc, ovl2_cat, residential_density"),
    gcQuery("qld_goldcoast_heritage", "id, cat_desc, ovl_cat, ovl2_desc, ovl2_cat, lhr_id, place_name, assessment_id, register_status, qld_heritage_register, heritage_protection_boundary, adjoining_allotments"),
    db.query(
      `SELECT id, cat_desc, ovl_cat, ovl2_desc, ovl2_cat, lhr_id, lot_plan, assessment_id, place_name, qld_heritage_register
       FROM qld_goldcoast_heritage_proximity
       WHERE lot_plan = $1 OR ST_Intersects(geometry, ${parcelUnion})`,
      [`${lot}/${plan}`, lot, plan]
    ).catch(() => ({ rows: [] as Record<string, unknown>[] })),
    gcQuery("qld_goldcoast_environmental", "id, category, cat_desc, ovl_cat, ovl2_desc, ovl2_cat"),
    gcQuery("qld_goldcoast_buffer_area", "id"),
    gcQuery("qld_goldcoast_dwelling_house_overlay", "id, cat_desc, ovl_cat, ovl2_desc, ovl2_cat"),
    gcQuery("qld_goldcoast_party_house", "id, cat_desc, ovl_cat, ovl2_desc, ovl2_cat"),
    gcQuery("qld_goldcoast_airport_noise", "id, cat_desc, ovl_cat, ovl2_desc, ovl2_cat, sensitive_use_type, buffer_source, buffer_distance"),
  ]);

  return {
    zones: zones.rows,
    buildingHeight: buildingHeight.rows,
    flood: flood.rows,
    bushfireHazard: bushfire.rows,
    minimumLotSize: minLotSize.rows,
    residentialDensity: residentialDensity.rows,
    heritage: heritage.rows,
    heritageProximity: heritageProximity.rows,
    environmental: environmental.rows,
    bufferArea: { intersects: bufferArea.rows.length > 0 },
    dwellingHouseOverlay: dwellingHouseOverlay.rows,
    partyHouse: partyHouse.rows,
    airportNoise: airportNoise.rows,
  };
}

async function fetchDevApplications(lot: string, plan: string): Promise<Record<string, unknown>[]> {
  const lotplan = `${lot}${plan}`;
  const result = await db.query(
    `SELECT application_number, description, application_type, lodgement_date, status,
            suburb, location_address, lot_on_plan, lot_plan,
            pre_assessment_started, pre_assessment_completed,
            confirmation_notice_started, confirmation_notice_completed,
            decision_started, decision_completed,
            decision_type, decision_date, decision_authority,
            responsible_officer,
            decision_approved_started, decision_approved_completed,
            issue_decision_started, issue_decision_completed,
            appeal_period_started, appeal_period_completed,
            workflow_events, documents_summary,
            first_scraped_at, last_scraped_at, detail_scraped_at
     FROM goldcoast_dev_applications
     WHERE lot_plan = $1
     ORDER BY lodgement_date DESC`,
    [lotplan]
  );
  return result.rows;
}

async function handleLotPlanLookup(lot: string, plan: string): Promise<NextResponse> {
  const debug: Record<string, unknown> = { input: `${lot}/${plan}`, mode: "lot_plan" };

  // All parcels for this lot/plan
  try {
    const allPieces = await db.query(
      `SELECT id, lot, plan, lotplan, lot_area, excl_area,
         seg_num, par_num, segpar, par_ind, lot_volume,
         surv_ind, tenure, prc, parish, county, lac,
         shire_name, feat_name, alias_name, loc, locality,
         parcel_typ, cover_typ, acc_code, ca_area_sqm, smis_map,
         ST_AsGeoJSON(geometry) AS geometry_json,
         ST_Y(ST_Centroid(geometry)) AS centroid_lat,
         ST_X(ST_Centroid(geometry)) AS centroid_lon,
         ST_Area(geometry::geography) AS area_m2_calc
       FROM qld_cadastre_parcels
       WHERE lot = $1 AND plan = $2
       ORDER BY id`,
      [lot, plan]
    );

    debug.allPiecesForMatchedLot = allPieces.rows.map((r) => ({ ...r, geometry_json: undefined }));
    debug.allPiecesForMatchedLotGeometries = allPieces.rows.map((r) => ({
      lot: r.lot,
      plan: r.plan,
      id: r.id,
      geometry: r.geometry_json ? JSON.parse(r.geometry_json as string) : null,
      centroid_lat: r.centroid_lat,
      centroid_lon: r.centroid_lon,
    }));

    if (allPieces.rows.length > 0) {
      const unionResult = await db.query(
        `SELECT ST_AsGeoJSON(ST_Union(geometry)) AS union_geometry_json
         FROM qld_cadastre_parcels WHERE lot = $1 AND plan = $2`,
        [lot, plan]
      );
      const unionJson = unionResult.rows[0]?.union_geometry_json;
      debug.allPiecesUnionGeometry = unionJson ? JSON.parse(unionJson) : null;

      // Centroid of first piece for LGA/zoning
      const firstRow = allPieces.rows[0];
      const centroidLat = parseFloat(firstRow.centroid_lat as string);
      const centroidLng = parseFloat(firstRow.centroid_lon as string);

      const [lgaResult, zoneResult] = await Promise.all([
        db.query(
          `SELECT id, lga_name FROM gnaf_admin_lga
           WHERE ST_Within(ST_SetSRID(ST_MakePoint($1, $2), 7844), geom) LIMIT 1`,
          [centroidLng, centroidLat]
        ).catch(() => ({ rows: [] as Record<string, unknown>[] })),
        db.query(
          `SELECT id, zone_code, zone_name FROM qld_planning_zones
           WHERE ST_Intersects(ST_SetSRID(ST_MakePoint($1, $2), 7844), geometry) LIMIT 1`,
          [centroidLng, centroidLat]
        ).catch(() => ({ rows: [] as Record<string, unknown>[] })),
      ]);
      debug.lga = lgaResult.rows[0] ?? null;
      debug.zoning = zoneResult.rows[0] ?? null;

      const lgaName = (debug.lga as Record<string, unknown> | null)?.lga_name as string | undefined;
      if (lgaName?.toLowerCase().includes("gold coast")) {
        debug.goldCoast = await fetchGoldCoastOverlays(lot, plan).catch((err) => ({ error: String(err) }));
      }
    } else {
      debug.error = `No parcels found for lot ${lot} / plan ${plan}`;
    }
  } catch (err) {
    debug.error = err instanceof Error ? err.message : String(err);
  }

  // Dev applications
  try {
    debug.devApplications = await fetchDevApplications(lot, plan);
  } catch (err) {
    debug.devApplicationsError = err instanceof Error ? err.message : String(err);
  }

  // All addresses on this plan
  try {
    const allAddrs = await db.query(
      `SELECT id, lot, plan, lotplan,
         unit_type, unit_number, unit_suffix,
         floor_type, floor_number, floor_suffix,
         property_name,
         street_no_1, street_no_1_suffix, street_no_2, street_no_2_suffix,
         street_number, street_name, street_type, street_suffix, street_full,
         locality, local_authority, state,
         address, address_status, address_standard,
         lotplan_status, address_pid, geocode_type,
         latitude, longitude
       FROM qld_cadastre_address
       WHERE plan = $1
       ORDER BY lot, street_number`,
      [plan]
    );
    debug.allAddressesOnPlan = allAddrs.rows;
  } catch (err) {
    debug.allAddressesOnPlanError = err instanceof Error ? err.message : String(err);
  }

  return NextResponse.json(debug);
}

async function handlePlanSearch(plan: string): Promise<NextResponse> {
  try {
    const result = await db.query(
      `SELECT
         p.lot,
         p.plan,
         p.parcel_typ,
         p.locality,
         ROUND(ST_Area(ST_Union(p.geometry)::geography)::numeric, 0) AS lot_area_sqm,
         MIN(a.address) AS sample_address,
         ST_AsGeoJSON(ST_Union(p.geometry)) AS geometry_json,
         ST_Y(ST_Centroid(ST_Union(p.geometry))) AS centroid_lat,
         ST_X(ST_Centroid(ST_Union(p.geometry))) AS centroid_lon
       FROM qld_cadastre_parcels p
       LEFT JOIN qld_cadastre_address a ON a.lot = p.lot AND a.plan = p.plan
       WHERE p.plan = $1
       GROUP BY p.lot, p.plan, p.parcel_typ, p.locality
       ORDER BY p.lot`,
      [plan]
    );
    const results = result.rows.map((r) => ({
      lot: r.lot,
      plan: r.plan,
      parcel_typ: r.parcel_typ,
      locality: r.locality,
      lot_area_sqm: r.lot_area_sqm,
      sample_address: r.sample_address,
      centroid_lat: r.centroid_lat,
      centroid_lon: r.centroid_lon,
      geometry: r.geometry_json ? JSON.parse(r.geometry_json as string) : null,
    }));
    return NextResponse.json({ mode: "plan_search", plan, results });
  } catch (err) {
    return NextResponse.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  const address = req.nextUrl.searchParams.get("address")?.trim() ?? "";
  const lotParam = req.nextUrl.searchParams.get("lot")?.trim() ?? "";
  const planParam = req.nextUrl.searchParams.get("plan")?.trim().toUpperCase() ?? "";

  // ── Plan-only search mode ────────────────────────────────────────────
  if (!lotParam && planParam) {
    return handlePlanSearch(planParam);
  }

  // ── Lot/plan direct lookup mode ──────────────────────────────────────
  if (lotParam && planParam) {
    return handleLotPlanLookup(lotParam, planParam);
  }

  if (!address) {
    return NextResponse.json({ error: "address or lot+plan params required" }, { status: 400 });
  }

  const debug: Record<string, unknown> = { input: address };

  // ── 1. Google Address Validation (direct call, no cache) ──────────────
  const apiKey = process.env.GOOGLE_MAPS_API_KEY;
  if (!apiKey) {
    debug.error = "GOOGLE_MAPS_API_KEY not set";
    return NextResponse.json(debug, { status: 500 });
  }

  let parsed: {
    formattedAddress: string;
    streetNumber: string | null;
    route: string | null;
    locality: string | null;
    administrativeArea: string | null;
    postalCode: string | null;
    lat: number | null;
    lng: number | null;
    boundsLow: { latitude: number; longitude: number } | null;
    boundsHigh: { latitude: number; longitude: number } | null;
    featureSizeMeters: number | null;
    validationGranularity: string | null;
    addressComplete: boolean;
    possibleNextAction: string | null;
  };

  try {
    const valRes = await fetch(
      `https://addressvalidation.googleapis.com/v1:validateAddress?key=${apiKey}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address: { addressLines: [address] } }),
      }
    );
    const valJson = await valRes.json();
    debug.addressValidation = valJson;

    const r = valJson.result;
    const components: Array<{ componentName: { text: string }; componentType: string }> =
      r?.address?.addressComponents ?? [];
    const geocode = r?.geocode ?? {};
    const verdict = r?.verdict ?? {};
    const bounds = geocode?.bounds ?? {};

    const extract = (type: string) =>
      components.find((c) => c.componentType === type)?.componentName.text ?? null;

    parsed = {
      formattedAddress: r?.address?.formattedAddress ?? address,
      streetNumber: extract("street_number"),
      route: extract("route"),
      locality: extract("locality"),
      administrativeArea: extract("administrative_area_level_1"),
      postalCode: extract("postal_code"),
      lat: geocode?.location?.latitude ?? null,
      lng: geocode?.location?.longitude ?? null,
      boundsLow: bounds?.low ?? null,
      boundsHigh: bounds?.high ?? null,
      featureSizeMeters: geocode?.featureSizeMeters ?? null,
      validationGranularity: verdict?.validationGranularity ?? null,
      addressComplete: verdict?.addressComplete ?? false,
      possibleNextAction: verdict?.possibleNextAction ?? null,
    };
    debug.parsed = parsed;
  } catch (err) {
    debug.error = "Address validation failed: " + (err instanceof Error ? err.message : String(err));
    return NextResponse.json(debug, { status: 500 });
  }

  const geocodeLat = parsed.lat;
  const geocodeLng = parsed.lng;
  if (!geocodeLat || !geocodeLng) {
    debug.error = "No geocode returned";
    return NextResponse.json(debug);
  }

  // ── 2. GNAF — full address detail + geocode point ───────────────────
  try {
    if (parsed.streetNumber && parsed.route && parsed.locality && parsed.administrativeArea) {
      const numberFirst = parseInt(parsed.streetNumber.replace(/\D/g, ""), 10);
      const numberFirstSuffix = parsed.streetNumber.replace(/^\d+/, "").toUpperCase() || null;

      // All columns from address_detail + joined street/locality/state + geocode point
      const gnafResult = await db.query(
        `SELECT
           ad.address_detail_pid,
           ad.date_created, ad.date_last_modified, ad.date_retired,
           ad.building_name,
           ad.lot_number_prefix, ad.lot_number, ad.lot_number_suffix,
           ad.flat_type_code, ad.flat_number_prefix, ad.flat_number, ad.flat_number_suffix,
           ad.level_type_code, ad.level_number_prefix, ad.level_number, ad.level_number_suffix,
           ad.number_first_prefix, ad.number_first, ad.number_first_suffix,
           ad.number_last_prefix, ad.number_last, ad.number_last_suffix,
           ad.location_description,
           ad.alias_principal, ad.postcode, ad.private_street,
           ad.legal_parcel_id, ad.confidence, ad.level_geocoded_code,
           ad.property_pid, ad.gnaf_property_pid, ad.primary_secondary,
           sl.street_locality_pid, sl.street_name, sl.street_type_code,
           l.locality_pid, l.locality_name,
           s.state_abbreviation,
           -- Geocode point from address_default_geocode
           geo.geocode_type_code AS geo_type,
           geo.latitude AS geo_lat, geo.longitude AS geo_lng
         FROM gnaf_data_address_detail ad
         JOIN gnaf_data_street_locality sl ON sl.street_locality_pid = ad.street_locality_pid
         JOIN gnaf_data_locality l ON l.locality_pid = ad.locality_pid
         JOIN gnaf_data_state s ON s.state_pid = l.state_pid
         LEFT JOIN gnaf_data_address_default_geocode geo
           ON geo.address_detail_pid = ad.address_detail_pid AND geo.date_retired IS NULL
         WHERE ad.number_first = $1
           AND (COALESCE(ad.number_first_suffix, '') = COALESCE($6, ''))
           AND UPPER(sl.street_name || CASE WHEN sl.street_type_code IS NOT NULL THEN ' ' || sl.street_type_code ELSE '' END) = UPPER($2)
           AND UPPER(l.locality_name) = UPPER($3)
           AND ad.postcode = $4
           AND s.state_abbreviation = UPPER($5)
           AND ad.date_retired IS NULL
         LIMIT 20`,
        [numberFirst, parsed.route, parsed.locality, parsed.postalCode, parsed.administrativeArea, numberFirstSuffix]
      );
      debug.gnaf = gnafResult.rows;

      // Extract GNAF geocode point for map
      const firstWithGeo = gnafResult.rows.find((r) => r.geo_lat != null);
      if (firstWithGeo) {
        debug.gnafPoint = {
          lat: parseFloat(firstWithGeo.geo_lat),
          lng: parseFloat(firstWithGeo.geo_lng),
        };
      }

      // All geocode points for matched addresses (all geocode types)
      const pids = gnafResult.rows.map((r) => r.address_detail_pid);
      if (pids.length > 0) {
        const geocodesResult = await db.query(
          `SELECT
             asg.address_detail_pid,
             asg.geocode_type_code,
             gt.name AS geocode_type_name,
             asg.longitude, asg.latitude,
             asg.boundary_extent, asg.planimetric_accuracy, asg.elevation
           FROM gnaf_data_address_site_geocode asg
           LEFT JOIN gnaf_data_geocode_type_aut gt ON gt.code = asg.geocode_type_code
           WHERE asg.address_detail_pid = ANY($1)
             AND asg.date_retired IS NULL
           ORDER BY asg.address_detail_pid, asg.geocode_type_code`,
          [pids]
        );
        debug.gnafGeocodes = geocodesResult.rows;
      }
    } else {
      debug.gnaf = null;
      debug.gnafSkipReason = "Missing street components";
    }
  } catch (err) {
    debug.gnaf = null;
    debug.gnafError = err instanceof Error ? err.message : String(err);
  }

  // ── 3. Spatial cadastre lookup (ST_Contains) — all parcel columns ───
  let spatialPrimaryRows: Record<string, unknown>[] = [];
  try {
    const spatialPrimary = await db.query(
      `SELECT
         id, lot, plan, lotplan, lot_area, excl_area,
         seg_num, par_num, segpar, par_ind, lot_volume,
         surv_ind, tenure, prc, parish, county, lac,
         shire_name, feat_name, alias_name, loc, locality,
         parcel_typ, cover_typ, acc_code, ca_area_sqm, smis_map,
         ST_AsGeoJSON(geometry) AS geometry_json,
         ST_Y(ST_Centroid(geometry)) AS centroid_lat,
         ST_X(ST_Centroid(geometry)) AS centroid_lon,
         ST_Area(geometry::geography) AS area_m2_calc
       FROM qld_cadastre_parcels
       WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint($1, $2), 7844))
       ORDER BY lot_area ASC
       LIMIT 10`,
      [geocodeLng, geocodeLat]
    );
    spatialPrimaryRows = spatialPrimary.rows;
    debug.cadastreSpatialContains = spatialPrimary.rows.map((r) => ({
      ...r, geometry_json: undefined,
    }));
    debug.cadastreSpatialContainsGeometries = spatialPrimary.rows.map((r) => ({
      lot: r.lot,
      plan: r.plan,
      geometry: r.geometry_json ? JSON.parse(r.geometry_json as string) : null,
      centroid_lat: r.centroid_lat,
      centroid_lon: r.centroid_lon,
    }));
    // All geometry rows for the matched lot/plan (multi-piece lots)
    if (spatialPrimaryRows.length > 0) {
      const topLotType = spatialPrimaryRows.find((r) => r.parcel_typ === "Lot Type Parcel") ?? spatialPrimaryRows[0];
      const allPieces = await db.query(
        `SELECT id, lot, plan, lotplan,
           ST_AsGeoJSON(geometry) AS geometry_json,
           ST_Y(ST_Centroid(geometry)) AS centroid_lat,
           ST_X(ST_Centroid(geometry)) AS centroid_lon
         FROM qld_cadastre_parcels
         WHERE lot = $1 AND plan = $2
         ORDER BY id`,
        [topLotType.lot, topLotType.plan]
      );
      debug.allPiecesForMatchedLot = allPieces.rows.map((r) => ({ ...r, geometry_json: undefined }));
      debug.allPiecesForMatchedLotGeometries = allPieces.rows.map((r) => ({
        lot: r.lot,
        plan: r.plan,
        id: r.id,
        geometry: r.geometry_json ? JSON.parse(r.geometry_json as string) : null,
        centroid_lat: r.centroid_lat,
        centroid_lon: r.centroid_lon,
      }));

      // Union of all pieces — outer boundary
      const unionResult = await db.query(
        `SELECT ST_AsGeoJSON(ST_Union(geometry)) AS union_geometry_json
         FROM qld_cadastre_parcels
         WHERE lot = $1 AND plan = $2`,
        [topLotType.lot, topLotType.plan]
      );
      const unionJson = unionResult.rows[0]?.union_geometry_json;
      debug.allPiecesUnionGeometry = unionJson ? JSON.parse(unionJson) : null;
    }
  } catch (err) {
    debug.cadastreSpatialContainsError = err instanceof Error ? err.message : String(err);
  }

  // ── 3b. Fallback: ST_DWithin — all parcel columns ──────────────────
  try {
    const spatialFallback = await db.query(
      `SELECT
         id, lot, plan, lotplan, lot_area, excl_area,
         seg_num, par_num, segpar, par_ind, lot_volume,
         surv_ind, tenure, prc, parish, county, lac,
         shire_name, feat_name, alias_name, loc, locality,
         parcel_typ, cover_typ, acc_code, ca_area_sqm, smis_map,
         ST_AsGeoJSON(geometry) AS geometry_json,
         ST_Y(ST_Centroid(geometry)) AS centroid_lat,
         ST_X(ST_Centroid(geometry)) AS centroid_lon,
         ST_Distance(geometry, ST_SetSRID(ST_MakePoint($1, $2), 7844)) AS distance
       FROM qld_cadastre_parcels
       WHERE ST_DWithin(geometry, ST_SetSRID(ST_MakePoint($1, $2), 7844), 0.0005)
         AND parcel_typ = 'Lot Type Parcel'
       ORDER BY distance ASC
       LIMIT 5`,
      [geocodeLng, geocodeLat]
    );
    debug.cadastreDWithin = spatialFallback.rows.map((r) => ({
      ...r, geometry_json: undefined,
    }));
    debug.cadastreDWithinGeometries = spatialFallback.rows.map((r) => ({
      lot: r.lot,
      plan: r.plan,
      distance: r.distance,
      geometry: r.geometry_json ? JSON.parse(r.geometry_json as string) : null,
      centroid_lat: r.centroid_lat,
      centroid_lon: r.centroid_lon,
    }));
  } catch (err) {
    debug.cadastreDWithinError = err instanceof Error ? err.message : String(err);
  }

  // ── 4. Address refinement — all qld_cadastre_address columns ────────
  try {
    const topParcel = spatialPrimaryRows.find(
      (r) => r.parcel_typ === "Lot Type Parcel"
    ) ?? spatialPrimaryRows[0];

    if (topParcel && parsed.route) {
      const rawNumberMatch = address.match(/^(\d+[A-Za-z]?)\s/i);
      const refinementNumber = rawNumberMatch?.[1]?.toUpperCase() ?? parsed.streetNumber;
      const streetNameOnly = parsed.route.split(" ").slice(0, -1).join(" ") || parsed.route;

      debug.refinementInput = { refinementNumber, streetNameOnly, plan: topParcel.plan };

      // All cadastre_address columns + joined parcel geometry
      const refinement = await db.query(
        `SELECT
           ca.id, ca.lot, ca.plan, ca.lotplan,
           ca.unit_type, ca.unit_number, ca.unit_suffix,
           ca.floor_type, ca.floor_number, ca.floor_suffix,
           ca.property_name,
           ca.street_no_1, ca.street_no_1_suffix, ca.street_no_2, ca.street_no_2_suffix,
           ca.street_number, ca.street_name, ca.street_type, ca.street_suffix, ca.street_full,
           ca.locality, ca.local_authority, ca.state,
           ca.address, ca.address_status, ca.address_standard,
           ca.lotplan_status, ca.address_pid, ca.geocode_type,
           ca.latitude AS addr_lat, ca.longitude AS addr_lng,
           ST_AsGeoJSON(ca.geometry) AS addr_geometry_json,
           cp.lot_area, cp.tenure, cp.parish, cp.county, cp.shire_name,
           ST_AsGeoJSON(cp.geometry) AS parcel_geometry_json,
           ST_Y(ST_Centroid(cp.geometry)) AS centroid_lat,
           ST_X(ST_Centroid(cp.geometry)) AS centroid_lon
         FROM qld_cadastre_address ca
         LEFT JOIN qld_cadastre_parcels cp
           ON cp.lot = ca.lot AND cp.plan = ca.plan AND cp.parcel_typ = 'Lot Type Parcel'
         WHERE ca.plan = $1
           AND ca.street_number = $2
           AND UPPER(ca.street_name) = UPPER($3)
         LIMIT 10`,
        [topParcel.plan, refinementNumber, streetNameOnly]
      );
      debug.addressRefinement = refinement.rows.map((r) => ({
        ...r, addr_geometry_json: undefined, parcel_geometry_json: undefined,
      }));
      debug.addressRefinementGeometries = refinement.rows.map((r) => ({
        lot: r.lot,
        plan: r.plan,
        parcelGeometry: r.parcel_geometry_json ? JSON.parse(r.parcel_geometry_json as string) : null,
        addrPoint: r.addr_lat ? { lat: parseFloat(r.addr_lat), lng: parseFloat(r.addr_lng) } : null,
        centroid_lat: r.centroid_lat,
        centroid_lon: r.centroid_lon,
      }));

      // All addresses on this plan — all columns
      const allAddrs = await db.query(
        `SELECT
           id, lot, plan, lotplan,
           unit_type, unit_number, unit_suffix,
           floor_type, floor_number, floor_suffix,
           property_name,
           street_no_1, street_no_1_suffix, street_no_2, street_no_2_suffix,
           street_number, street_name, street_type, street_suffix, street_full,
           locality, local_authority, state,
           address, address_status, address_standard,
           lotplan_status, address_pid, geocode_type,
           latitude, longitude
         FROM qld_cadastre_address
         WHERE plan = $1
         ORDER BY lot, street_number`,
        [topParcel.plan]
      );
      debug.allAddressesOnPlan = allAddrs.rows;
    }
  } catch (err) {
    debug.addressRefinementError = err instanceof Error ? err.message : String(err);
  }

  // ── 5. Direct qld_cadastre_address lookup by address components ─────
  try {
    if (parsed.streetNumber && parsed.route) {
      const rawNumberMatch = address.match(/^(\d+[A-Za-z]?)\s/i);
      const refinementNumber = rawNumberMatch?.[1]?.toUpperCase() ?? parsed.streetNumber;
      const streetNameOnly = parsed.route.split(" ").slice(0, -1).join(" ") || parsed.route;

      const cadastreAddrDirect = await db.query(
        `SELECT
           ca.id, ca.lot, ca.plan, ca.lotplan,
           ca.unit_type, ca.unit_number,
           ca.property_name,
           ca.street_no_1, ca.street_no_1_suffix,
           ca.street_number, ca.street_name, ca.street_type, ca.street_full,
           ca.locality, ca.local_authority, ca.state,
           ca.address, ca.address_status,
           ca.address_pid, ca.geocode_type,
           ca.latitude, ca.longitude,
           cp.lot_area, cp.tenure, cp.parcel_typ, cp.shire_name,
           ST_AsGeoJSON(cp.geometry) AS parcel_geometry_json,
           ST_Y(ST_Centroid(cp.geometry)) AS centroid_lat,
           ST_X(ST_Centroid(cp.geometry)) AS centroid_lon
         FROM qld_cadastre_address ca
         LEFT JOIN qld_cadastre_parcels cp
           ON cp.lot = ca.lot AND cp.plan = ca.plan AND cp.parcel_typ = 'Lot Type Parcel'
         WHERE ca.street_number = $1
           AND UPPER(ca.street_name) = UPPER($2)
           AND ($3::text IS NULL OR UPPER(ca.locality) = UPPER($3))
         ORDER BY ca.plan, ca.lot
         LIMIT 20`,
        [refinementNumber, streetNameOnly, parsed.locality]
      );
      debug.cadastreAddressDirect = cadastreAddrDirect.rows.map((r) => ({
        ...r, parcel_geometry_json: undefined,
      }));
      debug.cadastreAddressDirectGeometries = cadastreAddrDirect.rows
        .filter((r) => r.parcel_geometry_json)
        .map((r) => ({
          lot: r.lot,
          plan: r.plan,
          geometry: JSON.parse(r.parcel_geometry_json as string),
          centroid_lat: r.centroid_lat,
          centroid_lon: r.centroid_lon,
        }));
    }
  } catch (err) {
    debug.cadastreAddressDirectError = err instanceof Error ? err.message : String(err);
  }

  // ── 6. LGA + Zoning ─────────────────────────────────────────────────
  try {
    const [lgaResult, zoneResult] = await Promise.all([
      db.query(
        `SELECT id, lga_name FROM gnaf_admin_lga
         WHERE ST_Within(ST_SetSRID(ST_MakePoint($1, $2), 7844), geom)
         LIMIT 1`,
        [geocodeLng, geocodeLat]
      ).catch(() => ({ rows: [] as Record<string, unknown>[] })),
      db.query(
        `SELECT id, zone_code, zone_name FROM qld_planning_zones
         WHERE ST_Intersects(ST_SetSRID(ST_MakePoint($1, $2), 7844), geometry)
         LIMIT 1`,
        [geocodeLng, geocodeLat]
      ).catch(() => ({ rows: [] as Record<string, unknown>[] })),
    ]);
    debug.lga = lgaResult.rows[0] ?? null;
    debug.zoning = zoneResult.rows[0] ?? null;
  } catch (err) {
    debug.lgaZoningError = err instanceof Error ? err.message : String(err);
  }

  // ── 7. Gold Coast overlays (only when LGA is Gold Coast) ────────────
  const lgaName = (debug.lga as Record<string, unknown> | null)?.lga_name as string | undefined;
  if (lgaName?.toLowerCase().includes("gold coast")) {
    const topLot = spatialPrimaryRows.find((r) => r.parcel_typ === "Lot Type Parcel") ?? spatialPrimaryRows[0];
    const lot = topLot?.lot as string | undefined;
    const plan = topLot?.plan as string | undefined;
    if (lot && plan) {
      debug.goldCoast = await fetchGoldCoastOverlays(lot, plan).catch((err) => ({ error: String(err) }));
    }
  }

  // ── 8. Dev applications ──────────────────────────────────────────────
  const topLotForDA = spatialPrimaryRows.find((r) => r.parcel_typ === "Lot Type Parcel") ?? spatialPrimaryRows[0];
  if (topLotForDA?.lot && topLotForDA?.plan) {
    try {
      debug.devApplications = await fetchDevApplications(topLotForDA.lot as string, topLotForDA.plan as string);
    } catch (err) {
      debug.devApplicationsError = err instanceof Error ? err.message : String(err);
    }
  }

  return NextResponse.json(debug);
}
