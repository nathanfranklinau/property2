/**
 * GNAF address lookup — resolves validated address components to a cadastre lot/plan.
 *
 * Uses gnaf_data_address_detail joined to gnaf_data_street_locality,
 * gnaf_data_locality, and gnaf_data_state.
 *
 * Two cases:
 *   - Single lot  → returns { lot, plan, isComplex: false }
 *   - Multi-unit building (many distinct lots on same plan) → returns { plan, isComplex: true }
 *     The caller is responsible for doing a plan-level cadastre lookup in this case.
 */

import { db } from "@/lib/db";
import type { AddressValidationResult } from "@/lib/address-validation";

export type GnafMatch = {
  /** Always present. */
  plan: string;
  /**
   * Present for single-lot matches. Absent when isComplex = true (building-level search
   * where no single lot can be identified without a unit number).
   */
  lot: string | null;
  legalParcelId: string | null;
  /** True when multiple distinct lots share this plan — i.e. a strata building searched without a unit number. */
  isComplex: boolean;
  /** Total active GNAF address records matching this plan at this street number. */
  addressCount: number;
  flatTypes: string[] | null;
  buildingName: string | null;
};

/**
 * Look up a cadastre lot/plan from validated address components via GNAF.
 *
 * Matching strategy:
 *   - number_first   ← streetNumber
 *   - street_name + street_type_code (full name, e.g. "TRINITY STREET")
 *   - locality_name  ← locality
 *   - postcode       ← postalCode
 *   - state          ← administrativeArea
 *
 * Groups by the plan extracted from legal_parcel_id.
 * If multiple distinct lots share the same plan → isComplex = true (building-level).
 * If a single lot → isComplex = false (standard parcel).
 *
 * Returns null if no match found.
 */
export async function gnafLookup(
  validation: AddressValidationResult
): Promise<GnafMatch | null> {
  const { streetNumber, route, locality, administrativeArea, postalCode } = validation;

  if (!streetNumber || !route || !locality || !administrativeArea) return null;

  // GNAF stores number_first as numeric(6) and number_first_suffix as varchar(2).
  // e.g. "67A" → numberFirst=67, numberFirstSuffix="A"
  const numberFirst = parseInt(streetNumber.replace(/\D/g, ""), 10);
  if (isNaN(numberFirst)) return null;
  const numberFirstSuffix = streetNumber.replace(/^\d+/, "").toUpperCase() || null;

  // Group by the plan portion of legal_parcel_id.
  // street_locality.street_type_code stores the full type name (e.g. "STREET", "PLACE")
  // which matches what Google returns in the route component — do NOT join through
  // street_type_aut.name which is the abbreviation (e.g. "ST", "PL").
  const result = await db.query<{
    plan: string;
    lot_count: string;
    address_count: string;
    sample_lot: string;
    flat_types: string[] | null;
    building_name: string | null;
  }>(
    `SELECT
       SUBSTRING(ad.legal_parcel_id FROM POSITION('/' IN ad.legal_parcel_id) + 1) AS plan,
       COUNT(DISTINCT ad.legal_parcel_id)::text                                    AS lot_count,
       COUNT(*)::text                                                               AS address_count,
       MIN(ad.legal_parcel_id)                                                     AS sample_lot,
       ARRAY_AGG(DISTINCT ad.flat_type_code)
         FILTER (WHERE ad.flat_type_code IS NOT NULL)                              AS flat_types,
       MAX(ad.building_name)                                                        AS building_name
     FROM gnaf_data_address_detail ad
     JOIN gnaf_data_street_locality sl
       ON sl.street_locality_pid = ad.street_locality_pid
     JOIN gnaf_data_locality l
       ON l.locality_pid = ad.locality_pid
     JOIN gnaf_data_state s
       ON s.state_pid = l.state_pid
     WHERE ad.number_first = $1
       AND (COALESCE(ad.number_first_suffix, '') = COALESCE($6, ''))
       AND UPPER(
             sl.street_name
             || CASE WHEN sl.street_type_code IS NOT NULL THEN ' ' || sl.street_type_code ELSE '' END
           ) = UPPER($2)
       AND UPPER(l.locality_name) = UPPER($3)
       AND ad.postcode            = $4
       AND s.state_abbreviation   = UPPER($5)
       AND ad.date_retired IS NULL
       AND ad.legal_parcel_id IS NOT NULL
       AND ad.legal_parcel_id <> ''
       AND POSITION('/' IN ad.legal_parcel_id) > 0
     GROUP BY plan
     ORDER BY COUNT(*) DESC
     LIMIT 1`,
    [numberFirst, route, locality, postalCode, administrativeArea, numberFirstSuffix]
  );

  if (result.rows.length === 0) return null;

  const row = result.rows[0];
  const plan = row.plan;
  const lotCount = parseInt(row.lot_count, 10) || 1;
  // Only treat as complex (strata/multi-unit) when the addresses include unit/flat designations.
  // Two lots on the same plan without flat types = dual occupancy or duplex — pick the first lot.
  const hasUnits = row.flat_types !== null && row.flat_types.length > 0;
  const isComplex = lotCount > 1 && hasUnits;

  if (isComplex) {
    return {
      plan,
      lot: null,
      legalParcelId: null,
      isComplex: true,
      addressCount: parseInt(row.address_count, 10) || lotCount,
      flatTypes: row.flat_types ?? null,
      buildingName: row.building_name ?? null,
    };
  }

  // Single lot — extract from the sample_lot (which equals the only legal_parcel_id)
  const legalParcelId = row.sample_lot;
  const slashIdx = legalParcelId.indexOf("/");
  if (slashIdx === -1) return null;
  const lot = legalParcelId.substring(0, slashIdx);
  if (!lot) return null;

  return {
    plan,
    lot,
    legalParcelId,
    isComplex: false,
    addressCount: parseInt(row.address_count, 10) || 1,
    flatTypes: row.flat_types ?? null,
    buildingName: row.building_name ?? null,
  };
}
