/**
 * Google Address Validation API — cache-backed lookup.
 *
 * Flow:
 *   1. Check address_validation_cache (keyed by lowercased input address)
 *   2. If fresh hit → return cached result
 *   3. If miss or stale → call Google Address Validation API → upsert cache → return
 *
 * Staleness window is controlled by STALENESS_MONTHS below.
 */

import { db } from "@/lib/db";

// ─── Configuration ────────────────────────────────────────────────────────────

/** How many months before a cached address validation result is considered stale. */
export const STALENESS_MONTHS = 18;

// ─── Types ────────────────────────────────────────────────────────────────────

export type AddressValidationResult = {
  /** Canonical formatted address from Google. */
  formattedAddress: string;
  placeId: string | null;

  /** Parsed address components. */
  streetNumber: string | null;
  route: string | null;       // e.g. "Trinity Street"
  locality: string | null;    // e.g. "Fortitude Valley"
  administrativeArea: string | null; // e.g. "QLD"
  postalCode: string | null;

  /** Geocode point. */
  latitude: number;
  longitude: number;

  /** Geocode bounding box of the premise. */
  boundsLowLat: number | null;
  boundsLowLng: number | null;
  boundsHighLat: number | null;
  boundsHighLng: number | null;

  /** Approximate size of the feature in metres. */
  featureSizeMeters: number | null;

  /** Verdict fields. */
  validationGranularity: string | null;
  addressComplete: boolean;
  possibleNextAction: string | null;  // "ACCEPT" | "CONFIRM" | "FIX"

  /** Property metadata. */
  isResidential: boolean | null;
  isBusiness: boolean | null;

  /** Whether this result came from the cache. */
  fromCache: boolean;
};

// ─── Internal helpers ─────────────────────────────────────────────────────────

function cacheKey(address: string): string {
  return address.trim().toLowerCase();
}

function extractComponent(
  components: Array<{ componentName: { text: string }; componentType: string }>,
  type: string
): string | null {
  return components.find((c) => c.componentType === type)?.componentName.text ?? null;
}

// ─── Cache read ───────────────────────────────────────────────────────────────

async function readCache(address: string): Promise<AddressValidationResult | null> {
  const result = await db.query<{
    formatted_address: string;
    place_id: string | null;
    street_number: string | null;
    route: string | null;
    locality: string | null;
    administrative_area: string | null;
    postal_code: string | null;
    latitude: string;
    longitude: string;
    bounds_low_lat: string | null;
    bounds_low_lng: string | null;
    bounds_high_lat: string | null;
    bounds_high_lng: string | null;
    feature_size_meters: string | null;
    validation_granularity: string | null;
    address_complete: boolean;
    possible_next_action: string | null;
    is_residential: boolean | null;
    is_business: boolean | null;
  }>(
    `SELECT
       formatted_address, place_id,
       street_number, route, locality, administrative_area, postal_code,
       latitude, longitude,
       bounds_low_lat, bounds_low_lng, bounds_high_lat, bounds_high_lng,
       feature_size_meters,
       validation_granularity, address_complete, possible_next_action,
       is_residential, is_business
     FROM address_validation_cache
     WHERE input_address = $1
       AND queried_at > now() - ($2 || ' months')::interval`,
    [cacheKey(address), STALENESS_MONTHS]
  );

  if (result.rows.length === 0) return null;
  const r = result.rows[0];

  return {
    formattedAddress: r.formatted_address,
    placeId: r.place_id,
    streetNumber: r.street_number,
    route: r.route,
    locality: r.locality,
    administrativeArea: r.administrative_area,
    postalCode: r.postal_code,
    latitude: parseFloat(r.latitude),
    longitude: parseFloat(r.longitude),
    boundsLowLat: r.bounds_low_lat ? parseFloat(r.bounds_low_lat) : null,
    boundsLowLng: r.bounds_low_lng ? parseFloat(r.bounds_low_lng) : null,
    boundsHighLat: r.bounds_high_lat ? parseFloat(r.bounds_high_lat) : null,
    boundsHighLng: r.bounds_high_lng ? parseFloat(r.bounds_high_lng) : null,
    featureSizeMeters: r.feature_size_meters ? parseFloat(r.feature_size_meters) : null,
    validationGranularity: r.validation_granularity,
    addressComplete: r.address_complete,
    possibleNextAction: r.possible_next_action,
    isResidential: r.is_residential,
    isBusiness: r.is_business,
    fromCache: true,
  };
}

// ─── API call ─────────────────────────────────────────────────────────────────

async function callApi(address: string): Promise<AddressValidationResult> {
  const apiKey = process.env.GOOGLE_MAPS_API_KEY;
  if (!apiKey) throw new Error("GOOGLE_MAPS_API_KEY is not set");

  const res = await fetch(
    `https://addressvalidation.googleapis.com/v1:validateAddress?key=${apiKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address: { addressLines: [address] } }),
    }
  );

  if (!res.ok) {
    throw new Error(`Address Validation API error: ${res.status} ${res.statusText}`);
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const json: any = await res.json();
  const r = json.result;
  const components: Array<{ componentName: { text: string }; componentType: string }> =
    r?.address?.addressComponents ?? [];
  const geocode = r?.geocode ?? {};
  const verdict = r?.verdict ?? {};
  const metadata = r?.metadata ?? {};
  const bounds = geocode?.bounds ?? {};

  const result: AddressValidationResult = {
    formattedAddress: r?.address?.formattedAddress ?? address,
    placeId: geocode?.placeId ?? null,
    streetNumber: extractComponent(components, "street_number"),
    route: extractComponent(components, "route"),
    locality: extractComponent(components, "locality"),
    administrativeArea: extractComponent(components, "administrative_area_level_1"),
    postalCode: extractComponent(components, "postal_code"),
    latitude: geocode?.location?.latitude ?? 0,
    longitude: geocode?.location?.longitude ?? 0,
    boundsLowLat: bounds?.low?.latitude ?? null,
    boundsLowLng: bounds?.low?.longitude ?? null,
    boundsHighLat: bounds?.high?.latitude ?? null,
    boundsHighLng: bounds?.high?.longitude ?? null,
    featureSizeMeters: geocode?.featureSizeMeters ?? null,
    validationGranularity: verdict?.validationGranularity ?? null,
    addressComplete: verdict?.addressComplete ?? false,
    possibleNextAction: verdict?.possibleNextAction ?? null,
    isResidential: metadata?.residential ?? null,
    isBusiness: metadata?.business ?? null,
    fromCache: false,
  };

  // Upsert into cache
  await db.query(
    `INSERT INTO address_validation_cache (
       input_address, place_id, formatted_address,
       street_number, route, locality, administrative_area, postal_code,
       latitude, longitude,
       bounds_low_lat, bounds_low_lng, bounds_high_lat, bounds_high_lng,
       feature_size_meters,
       validation_granularity, address_complete, possible_next_action,
       is_residential, is_business,
       raw_response, queried_at, updated_at
     ) VALUES (
       $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
       $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
       $21, now(), now()
     )
     ON CONFLICT (input_address) DO UPDATE SET
       place_id                = EXCLUDED.place_id,
       formatted_address       = EXCLUDED.formatted_address,
       street_number           = EXCLUDED.street_number,
       route                   = EXCLUDED.route,
       locality                = EXCLUDED.locality,
       administrative_area     = EXCLUDED.administrative_area,
       postal_code             = EXCLUDED.postal_code,
       latitude                = EXCLUDED.latitude,
       longitude               = EXCLUDED.longitude,
       bounds_low_lat          = EXCLUDED.bounds_low_lat,
       bounds_low_lng          = EXCLUDED.bounds_low_lng,
       bounds_high_lat         = EXCLUDED.bounds_high_lat,
       bounds_high_lng         = EXCLUDED.bounds_high_lng,
       feature_size_meters     = EXCLUDED.feature_size_meters,
       validation_granularity  = EXCLUDED.validation_granularity,
       address_complete        = EXCLUDED.address_complete,
       possible_next_action    = EXCLUDED.possible_next_action,
       is_residential          = EXCLUDED.is_residential,
       is_business             = EXCLUDED.is_business,
       raw_response            = EXCLUDED.raw_response,
       queried_at              = now(),
       updated_at              = now()`,
    [
      cacheKey(address),
      result.placeId,
      result.formattedAddress,
      result.streetNumber,
      result.route,
      result.locality,
      result.administrativeArea,
      result.postalCode,
      result.latitude,
      result.longitude,
      result.boundsLowLat,
      result.boundsLowLng,
      result.boundsHighLat,
      result.boundsHighLng,
      result.featureSizeMeters,
      result.validationGranularity,
      result.addressComplete,
      result.possibleNextAction,
      result.isResidential,
      result.isBusiness,
      JSON.stringify(json),
    ]
  );

  return result;
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Validate an address via Google Address Validation API, with DB caching.
 * Returns null if the address cannot be validated (API error, no result).
 */
export async function validateAddress(
  address: string
): Promise<AddressValidationResult | null> {
  try {
    const cached = await readCache(address);
    if (cached) return cached;
    return await callApi(address);
  } catch (err) {
    console.error("Address validation error:", err);
    return null;
  }
}
