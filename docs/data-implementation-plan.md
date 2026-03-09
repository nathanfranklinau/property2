# Data Implementation Plan — Actionable Attributes from Datasets

This document maps every useful-but-currently-unused data attribute from the QLD Cadastre, GNAF, and Admin Boundaries datasets to concrete implementation steps. Each attribute includes: what it is, how it's useful, and exactly how to add it.

**Current state of the app:** The app currently uses cadastre `lot`, `plan`, `lot_area`, and `geometry` for spatial lookup; LGA name from `gnaf_admin_lga`; zone code/name from `qld_planning_zones`; and pool suburb-level counts from `qld_pools_registered`. There is NO GNAF address table usage.

---

## Priority 1 — High Impact, Low Effort

These attributes unlock major features with minimal code changes.

---

### 1.1 Plan Prefix Classification (Subdivision Eligibility Gate)

**What it is:** The prefix of `cadastre_plan` (e.g. `RP`, `SP`, `BUP`, `GTP`, `CP`) indicates the registration type of the property. `RP`/`SP` = freehold land, `BUP` = building units plan (strata), `GTP` = group title plan, `CP` = Crown land.

**How it's useful:** This is an instant pass/fail gate for subdivision potential. BUP/GTP properties are *already subdivided strata* — they cannot be further subdivided in the traditional sense. CP/NR/AG properties are government/special land. Only RP/SP properties are candidates. Currently the app blindly calculates subdivision potential for all properties, including units.

**How to add it:**

1. **Parse the prefix in the lookup API** — no migration needed, derive it from existing `plan` column:

```typescript
// web/app/api/properties/lookup/route.ts — add to the response
const planPrefix = parcel.plan.replace(/[0-9].*/g, '').toUpperCase();

// Classification logic
type PropertyRegistration = 'freehold' | 'strata' | 'government' | 'special';
function classifyPlan(prefix: string): PropertyRegistration {
  if (['RP', 'SP'].includes(prefix)) return 'freehold';
  if (['BUP', 'GTP'].includes(prefix)) return 'strata';
  if (['CP'].includes(prefix)) return 'government';
  return 'special'; // AP, NR, AG, MPH, MCH, etc.
}
```

2. **Add `plan_prefix` and `property_type` to the lookup response** — extend the return JSON with `plan_prefix` and `registration_type`.

3. **Display in the analysis page sidebar** — add a row under "Property Rights" showing the registration type. For strata properties, replace the "Subdivision Potential" section with an "Already Strata" badge explaining the property is a unit/townhouse in a body corporate.

4. **Guard the subdivision estimate** — skip the "Estimated new lots" calculation for non-freehold properties.

**Files to modify:**
- [web/app/api/properties/lookup/route.ts](../web/app/api/properties/lookup/route.ts) — add `plan_prefix`, `registration_type` to response
- [web/app/api/analysis/request/route.ts](../web/app/api/analysis/request/route.ts) — pass through to parcels table (optional: add column)
- [web/app/analysis/[id]/page.tsx](../web/app/analysis/[id]/page.tsx) — conditionally render subdivision section

**Complexity:** Very low. No migration, no new queries. Pure string parsing.

---

### 1.2 Excluded Area / Easements

**What it is:** The `excl_area` column on `qld_cadastre_parcels` represents land within the parcel boundary that is excluded from the usable area — typically easements, drainage reserves, or encumbrances. 6,455 QLD parcels have `excl_area > 0`.

**How it's useful:** Currently the app uses raw `lot_area` for all space calculations. Properties with significant easements have *less usable land* than `lot_area` suggests. A parcel showing 800 m² might only have 500 m² usable if 37% is a creek easement. This directly affects subdivision potential accuracy.

**How to add it:**

1. **Migration** — add `excl_area_sqm` to `parcels` table:

```sql
-- db/migrations/013_add_excl_area.sql
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS excl_area_sqm NUMERIC(12,2) DEFAULT 0;
```

2. **Update lookup query** — fetch `excl_area` alongside `lot_area`:

```sql
-- In properties/lookup/route.ts, add to the SELECT
SELECT lot, plan, lot_area, COALESCE(excl_area, 0) AS excl_area, ...
```

3. **Pass through the analysis pipeline** — store in parcels table, return from status endpoint.

4. **Display in the analysis page** — add an "Easements" row under Property Rights when `excl_area_sqm > 0`. Show as a warning badge when easement ratio exceeds 10%.

5. **Adjust space calculations** — use `lot_area_sqm - excl_area_sqm` as the effective lot size in the subdivision potential calculation.

**Files to modify:**
- New: `db/migrations/013_add_excl_area.sql`
- [web/app/api/properties/lookup/route.ts](../web/app/api/properties/lookup/route.ts) — fetch & return excl_area
- [web/app/api/analysis/request/route.ts](../web/app/api/analysis/request/route.ts) — store in parcels
- [web/app/api/analysis/status/route.ts](../web/app/api/analysis/status/route.ts) — return excl_area_sqm
- [web/app/analysis/[id]/page.tsx](../web/app/analysis/[id]/page.tsx) — display & adjust calculations

**Complexity:** Low. One ALTER TABLE, minor query changes.

---

### 1.3 Zone Rules Integration (Already Built, Not Wired Up)

**What it is:** `web/lib/zone-rules.ts` contains a `getZoneRules()` function that maps zone names to structured rules: `minLotSizeSqm`, `maxStoreys`, `permittedUses[]`, and `subdivisionNotes`. This code exists but is **never called** anywhere.

**How it's useful:** The app already fetches `zone_name` for every property but only displays it as a static badge. The zone rules would:
- Show the minimum lot size required for subdivision (critical information)
- Tell the user what they can and can't build
- Provide subdivision-specific notes per zone
- Replace the hardcoded `400` in the estimated new lots calculation with the actual minimum from the zone

**How to add it:**

1. **No migration needed** — everything is already in the codebase.

2. **Import and call in the analysis page:**

```typescript
// web/app/analysis/[id]/page.tsx
import { getZoneRules, type ZoneRules } from "@/lib/zone-rules";

// Inside the component:
const zoneRules = status?.zone_name ? getZoneRules(status.zone_name) : null;

// Replace hardcoded 400 in subdivision estimate:
const minLotSize = zoneRules?.minLotSizeSqm ?? 400;
const estimatedLots = Math.max(1, Math.floor(freeSpace / minLotSize));
```

3. **Add a "Zone Rules" section to the sidebar:**

```tsx
{zoneRules && (
  <SidebarSection title="Zone Rules">
    <SidebarRow label="Min Lot Size" value={sqm(zoneRules.minLotSizeSqm)} />
    <SidebarRow label="Max Storeys" value={String(zoneRules.maxStoreys ?? '—')} />
    <SidebarRow label="Permitted Uses" value={zoneRules.permittedUses.join(', ')} />
    <p className="text-xs text-zinc-500 px-3 py-2">{zoneRules.subdivisionNotes}</p>
  </SidebarSection>
)}
```

**Files to modify:**
- [web/app/analysis/[id]/page.tsx](../web/app/analysis/[id]/page.tsx) — import zone-rules, render zone details, fix estimated lots calculation

**Complexity:** Very low. The code is already written. Just import and use it.

---

### 1.4 Multi-Dwelling Detection (Address Count per Parcel)

**What it is:** By querying `gnaf_data_address_detail` grouped by `legal_parcel_id`, you can count how many addresses are registered at a parcel. A single address = single dwelling. Multiple addresses with `flat_type_code` = multi-dwelling (units, townhouses, duplexes).

**How it's useful:** This is one of the most powerful signals for property analysis:
- **Single-address parcels on RP/SP plans ≥ 600 m²** = ideal subdivision candidates
- **2 addresses** = likely duplex / dual occupancy (already partially developed)
- **3–20 addresses** = townhouse complex
- **20+ addresses** = apartment building
- Instantly tells the user whether the property is a standalone house or part of a complex

**How to add it:**

1. **Migration** — add columns to `parcels`:

```sql
-- db/migrations/013_add_gnaf_attributes.sql  (or combine with other changes)
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS address_count INTEGER;
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS dwelling_type VARCHAR(50);
```

2. **Query GNAF during lookup** — add to the lookup route:

```sql
SELECT
  COUNT(*) AS address_count,
  COUNT(CASE WHEN flat_type_code IS NOT NULL THEN 1 END) AS unit_count,
  MAX(flat_type_code) AS sample_flat_type,
  MAX(building_name) AS building_name
FROM gnaf_data_address_detail
WHERE legal_parcel_id = $1 || '/' || $2   -- lot/plan format
  AND date_retired IS NULL
```

Where `$1` = lot number, `$2` = plan number (need to construct "lot/plan" format matching GNAF's `legal_parcel_id`).

3. **Derive dwelling_type** from the results:

```typescript
function getDwellingType(addressCount: number, unitCount: number, flatType: string | null): string {
  if (addressCount <= 1) return 'House';
  if (addressCount === 2) return 'Dual Occupancy';
  if (flatType === 'TNHS' || (addressCount >= 3 && addressCount <= 20)) return 'Townhouse Complex';
  if (addressCount > 20) return 'Apartment Building';
  return 'Multi-Dwelling';
}
```

4. **Display in analysis page** — show dwelling type badge and address count. For multi-dwelling properties, explain that the land already has multiple residences.

**The key query to link GNAF → Cadastre:**
```sql
-- GNAF stores legal_parcel_id as "lot/plan" (e.g. "2/RP20457")
-- Cadastre stores lotplan as concatenated (e.g. "2RP20457")
WHERE REPLACE(legal_parcel_id, '/', '') = $1 || $2  -- lot || plan
```

**Files to modify:**
- New migration for `address_count`, `dwelling_type` columns
- [web/app/api/properties/lookup/route.ts](../web/app/api/properties/lookup/route.ts) — add GNAF query
- [web/app/api/analysis/request/route.ts](../web/app/api/analysis/request/route.ts) — pass through to parcels
- [web/app/analysis/[id]/page.tsx](../web/app/analysis/[id]/page.tsx) — display dwelling type

**Complexity:** Medium. Requires a new SQL query against a 3.5M-row table (needs index on `legal_parcel_id` — check if one exists).

---

### 1.5 Building Name Display

**What it is:** 345,467 QLD addresses in GNAF have a `building_name` — named complexes like "Palm Lake Resort", "Gemlife", shopping centres, hospitals, etc.

**How it's useful:** When a user searches for a property in a named complex, showing the building name immediately contextualises the result. A user looking up an address in "Palm Lake Resort" instantly knows it's a retirement village. This affects subdivision potential (retirement villages are already body-corporate developments).

**How to add it:**

This is fetched as part of the Multi-Dwelling Detection query (1.4 above) — the `MAX(building_name)` result. Store it in a `building_name` column on parcels and display it below the address in the sidebar when present.

```sql
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS building_name VARCHAR(200);
```

**Files to modify:** Same as 1.4. Include in the same migration and query.

**Complexity:** Very low (bundled with 1.4).

---

## Priority 2 — Medium Impact, Medium Effort

These require new queries or minor schema changes but unlock significant insights.

---

### 2.1 GNAF Address Confidence & Geocode Quality

**What it is:** Two quality indicators on every GNAF address:
- `confidence` (-1, 0, 1, 2): How well-validated the address is. 57.5% are level 2 (high), 6.4% are -1 (unvalidated).
- `level_geocoded_code` (4–7): How precisely the lat/lon is positioned. 94.4% are level 7 (full address), 0.7% are level 4 (locality only).

**How it's useful:** When the app displays analysis results for a poorly-geocoded or low-confidence address, the user should see a data quality warning. A level-4 geocoded address means the lat/lon is only suburb-accurate — the building detection may have run on the wrong location entirely.

**How to add it:**

1. **Query during lookup** — add to the GNAF query from 1.4:

```sql
SELECT confidence, level_geocoded_code
FROM gnaf_data_address_detail
WHERE legal_parcel_id = ... AND date_retired IS NULL
ORDER BY confidence DESC
LIMIT 1
```

2. **Display a quality badge** — show a small indicator on the analysis page:
   - Confidence ≥ 2 + geocode 7: no badge (default, most properties)
   - Confidence 0–1 or geocode 5–6: amber "Limited data quality" notice
   - Confidence -1 or geocode 4: red "Data quality warning — verify with council"

**Files to modify:**
- [web/app/api/properties/lookup/route.ts](../web/app/api/properties/lookup/route.ts) — fetch from GNAF
- [web/app/analysis/[id]/page.tsx](../web/app/analysis/[id]/page.tsx) — render quality badge

**Complexity:** Low. Minor addition to the GNAF query from 1.4.

---

### 2.2 Urban/Rural Classification

**What it is:** `gnaf_data_address_site` has an `address_type` field: `UR` (urban, 6.6M addresses nationally), `R` (rural, 439K), `UN` (unknown, 9.7M).

**How it's useful:** Rural properties have fundamentally different subdivision rules — much larger minimum lot sizes (often 100+ hectares), different council requirements, and different infrastructure needs (septic, bore water, etc.). Currently the app treats all properties the same.

**How to add it:**

1. **Join via `address_site_pid`** — the address_detail row links to address_site:

```sql
SELECT
  CASE s.address_type
    WHEN 'UR' THEN 'Urban'
    WHEN 'R' THEN 'Rural'
    ELSE NULL
  END AS site_classification
FROM gnaf_data_address_detail d
JOIN gnaf_data_address_site s ON d.address_site_pid = s.address_site_pid
WHERE d.legal_parcel_id = ...
```

2. **Display in analysis** — show "Urban" or "Rural" classification. For rural properties, show a note that rural subdivision rules apply (different minimum sizes, infrastructure requirements).

3. **Adjust zone rules** — when `site_classification = 'Rural'` and no matching zone was found in `qld_planning_zones`, default to rural subdivision rules instead of the standard 400 m² minimum.

**Files to modify:**
- [web/app/api/properties/lookup/route.ts](../web/app/api/properties/lookup/route.ts) — add join
- [web/app/analysis/[id]/page.tsx](../web/app/analysis/[id]/page.tsx) — display classification

**Complexity:** Low-medium. Straightforward join but `address_type = 'UN'` for 58% of addresses limits usefulness.

---

### 2.3 Pool Registration Enhancement

**What it is:** Currently the Python analyser matches pools by suburb name (suburb-level count, not property-level). The `qld_pools_registered` table has a `site_name` column in the format `lot/plan_type/plan_number` which can be parsed to match specific parcels.

**How it's useful:** Instead of "there are 150 registered pools in your suburb" (current behaviour), you get "this property has a registered pool" — a definitive property-level match.

**How to add it:**

1. **Parse site_name to extract lot/plan** in the Python analyser:

```python
# data-layer/service/analyser.py — replace get_registered_pool_count
def get_registered_pool_count(conn, cadastre_lot: str, cadastre_plan: str) -> int:
    """Match by parsing site_name = 'lot/plan_type/plan_number'."""
    with conn.cursor() as cur:
        # site_name format: "2/RP/20457" → lot=2, plan=RP20457
        # Build the pattern: lot + '/' + first letters of plan + '/' + digits of plan
        plan_prefix = ''.join(c for c in cadastre_plan if c.isalpha())
        plan_number = ''.join(c for c in cadastre_plan if c.isdigit())
        site_pattern = f"{cadastre_lot}/{plan_prefix}/{plan_number}"

        cur.execute(
            "SELECT COALESCE(SUM(number_of_pools), 0) FROM qld_pools_registered WHERE site_name = %s",
            (site_pattern,),
        )
        row = cur.fetchone()
        return row[0] if row else 0
```

2. **Fallback to suburb match** if no direct match:

```python
    if count == 0:
        # Fall back to original suburb-level count
        ...
```

Note: Validate the `site_name` format against actual data first — run:
```sql
SELECT site_name FROM qld_pools_registered LIMIT 20;
```

**Files to modify:**
- [data-layer/service/analyser.py](../data-layer/service/analyser.py) — rewrite `get_registered_pool_count`

**Complexity:** Low. Single function rewrite. Need to verify `site_name` format first.

---

### 2.4 Suburb Name from GNAF Locality (Independent of Google)

**What it is:** Currently the display address comes entirely from Google Places. The GNAF `locality` table provides the official gazetted suburb name for the property via `locality_pid` on the address_detail record.

**How it's useful:** 
- Show the official suburb name independently of Google's formatting
- Use for suburb-level statistics ("other properties in this suburb")  
- More reliable than parsing the Google-formatted address
- Enables the SEO-friendly URLs like `/analysis/paddington-qld/lot-2-rp20457`

**How to add it:**

Fetched as part of the GNAF query in 1.4:

```sql
SELECT l.locality_name AS suburb
FROM gnaf_data_address_detail d
JOIN gnaf_data_locality l ON d.locality_pid = l.locality_pid
WHERE d.legal_parcel_id = ...
  AND d.date_retired IS NULL
  AND l.locality_class_code = 'G'  -- gazetted only
```

Store in parcels: `ALTER TABLE parcels ADD COLUMN IF NOT EXISTS suburb VARCHAR(100);`

**Complexity:** Very low (bundled with 1.4).

---

### 2.5 Postcode

**What it is:** The `postcode` column on `gnaf_data_address_detail`. Almost all QLD addresses have this populated.

**How it's useful:**
- Display alongside the address
- Use for postcode-level filtering/search in Phase 2
- Link to external data (ABS, property market data) that is often indexed by postcode

**How to add it:**

Fetched as part of the GNAF query in 1.4. Add `d.postcode` to the SELECT.

Store in parcels: `ALTER TABLE parcels ADD COLUMN IF NOT EXISTS postcode VARCHAR(4);`

**Complexity:** Very low (bundled with 1.4).

---

## Priority 3 — High Value, Higher Effort

These require more complex implementation but provide distinctive features.

---

### 3.1 Subdivision Potential Score

**What it is:** A composite score computed from multiple data attributes that quantifies how suitable a property is for subdivision.

**How it's useful:** Instead of just showing "Estimated 2 lots", provide a 0–100 score with a breakdown showing which factors help and which hinder. This is the app's core value proposition.

**How to add it:**

1. **Define the scoring model** — all inputs are already available or being added:

```typescript
type SubdivisionFactors = {
  lotAreaSqm: number;           // from cadastre
  registrationType: string;     // from plan prefix (1.1)
  exclAreaSqm: number;          // from cadastre (1.2)
  zoneMinLotSqm: number | null; // from zone-rules.ts (1.3)
  addressCount: number;         // from GNAF (1.4)
  dwellingType: string;         // derived (1.4)
  siteClassification: string;   // urban/rural (2.2)
  confidence: number;           // GNAF quality (2.1)
  freeSpaceSqm: number;         // from analysis pipeline
};

function computeSubdivisionScore(f: SubdivisionFactors): { score: number; factors: Factor[] } {
  let score = 50; // baseline
  const factors: Factor[] = [];

  // Registration type gate
  if (f.registrationType === 'strata') {
    return { score: 0, factors: [{ label: 'Already strata-titled', impact: -50, type: 'blocker' }] };
  }
  if (f.registrationType === 'government') {
    return { score: 0, factors: [{ label: 'Government/Crown land', impact: -50, type: 'blocker' }] };
  }

  // Lot size scoring
  const usableArea = f.lotAreaSqm - f.exclAreaSqm;
  const minLot = f.zoneMinLotSqm ?? 400;
  if (usableArea >= minLot * 3) { score += 20; factors.push({ label: `Large lot (${sqm(usableArea)})`, impact: 20, type: 'positive' }); }
  else if (usableArea >= minLot * 2) { score += 10; factors.push({ label: 'Adequate lot size', impact: 10, type: 'positive' }); }
  else { score -= 20; factors.push({ label: 'Lot too small for subdivision', impact: -20, type: 'negative' }); }

  // Dwelling count penalty
  if (f.addressCount === 1) { score += 10; factors.push({ label: 'Single dwelling', impact: 10, type: 'positive' }); }
  else if (f.addressCount >= 3) { score -= 15; factors.push({ label: 'Multiple dwellings already', impact: -15, type: 'negative' }); }

  // Easement penalty
  const easementRatio = f.exclAreaSqm / f.lotAreaSqm;
  if (easementRatio > 0.1) { score -= 10; factors.push({ label: `${Math.round(easementRatio * 100)}% easement`, impact: -10, type: 'negative' }); }

  // etc.

  return { score: Math.max(0, Math.min(100, score)), factors };
}
```

2. **Display as a visual score card** in the Subdivision Potential section.

**Files to modify:**
- New: `web/lib/subdivision-score.ts` — scoring logic
- [web/app/analysis/[id]/page.tsx](../web/app/analysis/[id]/page.tsx) — render score with factor breakdown

**Complexity:** Medium. Logic itself is straightforward; visual design of the score card is the main effort.

---

### 3.2 Nearby Suburb Properties (Locality Neighbours)

**What it is:** `gnaf_data_locality_neighbour` maps every suburb to its adjacent suburbs (89,460 bidirectional records). Brisbane City's neighbours: Fortitude Valley, Kangaroo Point, Milton, Petrie Terrace, South Brisbane, Spring Hill.

**How it's useful:** "See similar properties in neighbouring suburbs" — a discovery feature that keeps users engaged and helps them understand the broader market. Can show suburb-level stats (average lot size, subdivision activity).

**How to add it:**

1. **New API route:**

```typescript
// web/app/api/properties/nearby/route.ts
// GET /api/properties/nearby?locality_pid=QLD1234
export async function GET(req: NextRequest) {
  const localityPid = req.nextUrl.searchParams.get('locality_pid');

  const result = await db.query(`
    SELECT l.locality_name, l.locality_pid
    FROM gnaf_data_locality_neighbour n
    JOIN gnaf_data_locality l ON n.neighbour_locality_pid = l.locality_pid
    WHERE n.locality_pid = $1
    AND l.locality_class_code = 'G'
  `, [localityPid]);

  return NextResponse.json(result.rows);
}
```

2. **Display in sidebar** — "Nearby suburbs: Paddington, Milton, Auchenflower" with links to browse properties in those areas.

**Files to modify:**
- New: `web/app/api/properties/nearby/route.ts`
- [web/app/analysis/[id]/page.tsx](../web/app/analysis/[id]/page.tsx) — render nearby suburbs section

**Complexity:** Medium. New endpoint + UI section. Need to store `locality_pid` in the parcel record (from the GNAF query in 1.4).

---

### 3.3 Address History / Development Trend Detection

**What it is:** `date_created` on `gnaf_data_address_detail` records when each address was added to the national register. New addresses appearing on a parcel or in a suburb indicate recent development/subdivision activity.

**How it's useful:** 
- Show "This address was created in 2015" — indicates the property is from a recent subdivision
- Show "12 new addresses created in this suburb since 2020" — indicates active development area
- Find recent subdivisions nearby (new address clusters on the same plan number)

**How to add it:**

1. **Fetch address creation date** — from the GNAF query in 1.4, add `d.date_created`.

2. **Suburb trend query:**

```sql
SELECT
  COUNT(*) AS new_addresses_since_2020,
  DATE_TRUNC('year', date_created)::date AS year
FROM gnaf_data_address_detail
WHERE locality_pid = $1
  AND date_created >= '2020-01-01'
  AND date_retired IS NULL
GROUP BY year
ORDER BY year
```

3. **Display** — add a "Development Activity" section showing recent address creation trends in the suburb.

**Complexity:** Medium. The queries are simple but may be slow on 3.5M rows without proper indexing. An index on `(locality_pid, date_created)` would be needed.

---

### 3.4 Primary/Secondary Address Relationships

**What it is:** `gnaf_data_primary_secondary` links secondary addresses (unit 1, shop 2, etc.) to their primary address (the main building). 4.9M records nationally.

**How it's useful:** Given a property, find all units/secondary addresses at the site. Shows the complete picture of how many dwellings exist on the lot — more reliable than just counting addresses, because it shows the parent-child relationship.

**How to add it:**

```sql
-- Find all secondary addresses for a primary address
SELECT
  d.flat_type_code, d.flat_number, d.number_first,
  d.building_name, d.date_created
FROM gnaf_data_primary_secondary ps
JOIN gnaf_data_address_detail d ON d.address_detail_pid = ps.secondary_pid
WHERE ps.primary_pid = $1  -- primary address PID
  AND d.date_retired IS NULL
ORDER BY d.flat_number
```

Display as an expandable list: "5 registered units at this address" → expand to see Unit 1, Unit 2, etc.

**Complexity:** Medium. Need to first identify the primary address PID from the GNAF query, then run a second query.

---

### 3.5 Full GNAF Address Construction (Independent of Google)

**What it is:** GNAF stores all address components separately: `number_first`, `number_first_suffix`, `flat_type_code`, `flat_number` + street name from `gnaf_data_street_locality` + suburb from `gnaf_data_locality` + `postcode`.

**How it's useful:**
- Construct a complete address without relying on Google Places
- Used for SEO metadata, structured data, and display when Google address is unavailable
- Enables searching by lot/plan and seeing the address result

**How to add it:**

```sql
SELECT
  CASE WHEN d.flat_type_code IS NOT NULL
    THEN d.flat_type_code || ' ' || COALESCE(CAST(d.flat_number AS TEXT), '') || '/'
    ELSE ''
  END
  || COALESCE(CAST(d.number_first AS TEXT), '')
  || COALESCE(d.number_first_suffix, '')
  || CASE WHEN d.number_last IS NOT NULL
    THEN '-' || CAST(d.number_last AS TEXT) || COALESCE(d.number_last_suffix, '')
    ELSE ''
  END
  || ' ' || s.street_name
  || ' ' || COALESCE(s.street_type_code, '')
  || COALESCE(' ' || s.street_suffix_code, '')
  || ', ' || l.locality_name
  || ' QLD ' || COALESCE(d.postcode, '') AS gnaf_address
FROM gnaf_data_address_detail d
JOIN gnaf_data_street_locality s ON d.street_locality_pid = s.street_locality_pid
JOIN gnaf_data_locality l ON d.locality_pid = l.locality_pid
WHERE REPLACE(d.legal_parcel_id, '/', '') = $1
  AND d.date_retired IS NULL
  AND d.alias_principal = 'P'
ORDER BY d.confidence DESC
LIMIT 1
```

**Complexity:** Medium. The join works; formatting edge cases are the challenge.

---

## Priority 4 — Future Features (Phase 2+)

These are valuable but better suited for later development phases.

---

### 4.1 ABS Census Data via Mesh Blocks

**What it is:** `gnaf_data_address_mesh_block_2021` links every address to an ABS 2021 Census mesh block. Mesh blocks are the smallest geographic unit for Census data.

**How it's useful:** Link to demographic data (population density, median income, household composition, age distribution) for suburb-level market profiling. Enables "neighbourhood profile" features.

**How to add it:** The GNAF link exists in the database. The missing piece is loading actual Census mesh block statistics (a separate ABS dataset, not currently imported). Once that's loaded, join via `mb_2021_pid`.

**Complexity:** High. Requires importing ABS Census data (separate dataset). The GNAF linkage is already in place.

---

### 4.2 Address/Locality Aliases (Search Enhancement)

**What it is:** 
- `gnaf_data_locality_alias` maps old/alternative suburb names to current official names
- `gnaf_data_address_alias` maps alternative address representations (ranged addresses "10–12 Smith St", synonyms, formatting variants) — 879,018 records

**How it's useful:** Search improvement — a user typing "North Booval" should find results in the current official suburb "East Ipswich". A user searching "10-12 Smith St" should match the canonical "10 Smith St".

**How to add it:** This will matter when implementing a custom address search (Phase 2). Currently the app uses Google Places Autocomplete, which handles this internally.

**Complexity:** Low to implement when needed, but not needed while Google Places handles search.

---

### 4.3 Street Character Analysis

**What it is:** `gnaf_data_street_locality` has `street_type_code` which indicates the type of road: Court, Close, Place = quiet residential cul-de-sacs; Road, Highway = arterial/noisy.

**How it's useful:** Street character affects property desirability and subdivision potential. A property on a quiet court is ideal for subdivision (no traffic noise, safe for families). A property on a highway has traffic noise concerns but may have commercial potential.

**How to add it:** Fetched from the street_locality join in 3.5. Classify into:
- `quiet_residential`: Court, Close, Place, Lane, Mews
- `standard_residential`: Street, Crescent, Drive, Way, Terrace
- `arterial`: Road, Highway, Boulevard, Parade

**Complexity:** Very low classification logic; useful primarily as a display attribute.

---

### 4.4 Comparable Subdivisions on Same Plan

**What it is:** Find other lots registered on the same `plan` number. If plan RP79217 has lots 1–20 all under 600 m², that's a completed subdivision — shows what the subdivision result looks like.

**How it's useful:** "See 15 other lots on the same plan" — shows the user what happened when this land was previously subdivided (or what a nearby subdivision looks like).

```sql
SELECT lot, lot_area, excl_area
FROM qld_cadastre_parcels
WHERE plan = $1  -- same plan as the searched property
  AND lot != $2  -- exclude the searched property itself
ORDER BY CAST(lot AS INTEGER) NULLS LAST
```

**Complexity:** Low query, medium UI effort.

---

### 4.5 Locality Boundary Display on Map

**What it is:** `gnaf_admin_localities` has polygon geometries for all 3,304 QLD suburbs.

**How it's useful:** Draw the suburb boundary on the property map as a faint overlay, giving the user geographic context. Shows where the suburb ends and neighbours begin.

**How to add it:** Fetch the suburb boundary geometry as GeoJSON, pass to the PropertyMap component and render as a polygon overlay with low opacity.

**Complexity:** Medium. The geometry fetch is simple, but GeoJSON rendering on Google Maps requires client-side polygon handling (which `PropertyMap` already does for parcel boundaries, so the pattern exists).

---

### 4.6 Address Feature History

**What it is:** `gnaf_data_address_feature` (239,845 records) tracks what changed about an address over time — locality changes, street renumbering, lot changes.

**How it's useful:** "This address was renumbered in 2015" or "This property's suburb was reclassified in 2020". Interesting historical context but not critical for analysis.

**Complexity:** Low query, minimal value for Phase 1.

---

## Implementation Order (Recommended)

### Sprint 1 — Core Data Enrichment
1. **1.1 Plan Prefix Classification** — 1 hour. Zero dependencies. Instant value.
2. **1.3 Zone Rules Integration** — 30 min. Code already exists. Just wire it up.
3. **1.2 Excluded Area** — 1 hour. One migration, simple query change.

### Sprint 2 — GNAF Integration
4. **1.4 + 1.5 + 2.4 + 2.5 Multi-Dwelling Detection bundle** — 3 hours. Single GNAF query fetches address count, building name, suburb, postcode, dwelling type. One migration adds all columns. This is the big unlock.
5. **2.1 Address Confidence** — 30 min. Added to the same GNAF query.
6. **2.3 Pool Registration Enhancement** — 1 hour. Isolated function rewrite.

### Sprint 3 — Scoring & Insights
7. **3.1 Subdivision Potential Score** — 3 hours. Requires outputs from Sprint 1+2.
8. **3.5 GNAF Address Construction** — 1 hour. Useful for SEO and display.

### Sprint 4 — Discovery Features
9. **3.2 Nearby Suburbs** — 2 hours.
10. **3.3 Development Trends** — 2 hours.
11. **3.4 Primary/Secondary Addresses** — 2 hours.

---

## Combined Migration

All "parcels" table additions can be combined into a single migration:

```sql
-- db/migrations/013_parcels_gnaf_enrichment.sql

-- From 1.2: Excluded area
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS excl_area_sqm NUMERIC(12,2) DEFAULT 0;

-- From 1.4: Multi-dwelling detection
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS address_count INTEGER;
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS dwelling_type VARCHAR(50);

-- From 1.5: Building name
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS building_name VARCHAR(200);

-- From 2.4: Official suburb
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS suburb VARCHAR(100);

-- From 2.5: Postcode
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS postcode VARCHAR(4);

-- From 2.1: GNAF data quality
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS gnaf_confidence INTEGER;

-- From 2.2: Urban/Rural
ALTER TABLE parcels ADD COLUMN IF NOT EXISTS site_classification VARCHAR(10);

-- Plan prefix (1.1) is derived from cadastre_plan at query time — no column needed.
-- Zone rules (1.3) use existing zone_name — no schema change.
```

---

## Combined GNAF Lookup Query

All GNAF data can be fetched in a **single query** during property lookup:

```sql
SELECT
  COUNT(*) OVER () AS address_count,
  d.building_name,
  d.confidence,
  d.level_geocoded_code,
  d.flat_type_code,
  d.date_created,
  d.postcode,
  l.locality_name AS suburb,
  l.locality_pid,
  s.address_type AS site_classification
FROM gnaf_data_address_detail d
JOIN gnaf_data_locality l ON d.locality_pid = l.locality_pid
LEFT JOIN gnaf_data_address_site s ON d.address_site_pid = s.address_site_pid
WHERE REPLACE(d.legal_parcel_id, '/', '') = $1  -- lotplan
  AND d.date_retired IS NULL
  AND d.state_pid LIKE '%QLD%'
ORDER BY d.confidence DESC, d.alias_principal ASC
LIMIT 1
```

And for the address count (which needs all rows):

```sql
SELECT
  COUNT(*) AS total_addresses,
  COUNT(CASE WHEN flat_type_code IS NOT NULL THEN 1 END) AS unit_addresses,
  MAX(building_name) AS building_name,
  MAX(confidence) AS best_confidence
FROM gnaf_data_address_detail
WHERE REPLACE(legal_parcel_id, '/', '') = $1
  AND date_retired IS NULL
```

**Important:** Check if an index exists on `legal_parcel_id`. If not, create one:

```sql
CREATE INDEX IF NOT EXISTS idx_gnaf_address_legal_parcel
  ON gnaf_data_address_detail (legal_parcel_id)
  WHERE date_retired IS NULL;
```

This index is critical — without it, the GNAF lookup will table-scan 3.5M rows per request.
