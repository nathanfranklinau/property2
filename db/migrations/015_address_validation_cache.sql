-- Migration 015: Address validation cache
-- Stores results from the Google Address Validation API so we don't re-call it on every lookup.
-- Records are considered stale after STALENESS_MONTHS (configured in web/lib/address-validation.ts).

CREATE TABLE IF NOT EXISTS address_validation_cache (
    id                      serial          PRIMARY KEY,

    -- Cache key: the formatted address string returned by Google Places Autocomplete.
    -- Lowercased + trimmed before insert/lookup.
    input_address           text            NOT NULL UNIQUE,

    -- Google identifiers
    place_id                varchar(255),

    -- Canonical address returned by the API
    formatted_address       text,

    -- Parsed address components (from addressComponents[])
    street_number           varchar(20),
    route                   varchar(200),       -- e.g. "Trinity Street"
    locality                varchar(100),       -- e.g. "Fortitude Valley"
    administrative_area     varchar(10),        -- e.g. "QLD"
    postal_code             varchar(10),

    -- Geocode
    latitude                numeric(10, 8),
    longitude               numeric(11, 8),
    bounds_low_lat          numeric(10, 8),
    bounds_low_lng          numeric(11, 8),
    bounds_high_lat         numeric(10, 8),
    bounds_high_lng         numeric(11, 8),
    feature_size_meters     numeric(8, 2),

    -- Verdict
    validation_granularity  varchar(50),        -- e.g. "PREMISE", "ROUTE"
    address_complete        boolean,
    possible_next_action    varchar(20),        -- e.g. "ACCEPT", "CONFIRM", "FIX"

    -- Metadata
    is_residential          boolean,
    is_business             boolean,

    -- Full raw API response for forward compatibility
    raw_response            jsonb,

    -- Housekeeping
    queried_at              timestamptz     NOT NULL DEFAULT now(),
    updated_at              timestamptz     NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_address_validation_cache_input
    ON address_validation_cache (input_address);

CREATE INDEX IF NOT EXISTS idx_address_validation_cache_queried_at
    ON address_validation_cache (queried_at);

COMMENT ON TABLE address_validation_cache IS
    'Cache of Google Address Validation API responses. Staleness window configured in web/lib/address-validation.ts.';
