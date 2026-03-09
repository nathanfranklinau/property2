# Dataset Analysis — QLD Cadastre, GNAF & Admin Boundaries

Comprehensive analysis of the three authoritative Australian datasets in this database, covering what each field means, data quality/reliability, and how to apply them in PropertyProfiler.

---

## 1. QLD Cadastre Parcels (`qld_cadastre_parcels`)

### What It Is
The Queensland Digital Cadastral Database (DCDB) — the official spatial register of all land parcels in Queensland. Published by the QLD Department of Resources. This is the **legal definition of property boundaries**.

**3,445,706 total parcel records** (including multipart polygons for the same lot/plan).

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | integer | Auto-increment primary key |
| `lot` | varchar(5) | Lot number (e.g. "1", "42", "A") |
| `plan` | varchar(10) | Plan number (e.g. "RP79217", "SP133707", "BUP100650") |
| `lotplan` | varchar(15) | Concatenated lot+plan identifier (e.g. "8RP79217") |
| `lot_area` | numeric | Total parcel area in **square metres** |
| `excl_area` | numeric | Excluded area in sqm (easements, reserves within parcel) |
| `geometry` | MultiPolygon (SRID 7844) | Parcel boundary polygon |

### Key Data Points

#### Plan Prefix Types (Critical for Property Classification)
The plan prefix tells you what **type of property registration** a lot has:

| Prefix | Full Name | Count | Median Area | Meaning for App |
|--------|-----------|-------|-------------|-----------------|
| **RP** | Registered Plan | 1,268,054 | 755 sqm | Standard freehold land — **primary target for subdivision** |
| **SP** | Survey Plan | 1,088,400 | 576 sqm | Modern survey plans (post-1997) — also freehold, **primary target** |
| **BUP** | Building Units Plan | 83,560 | 204 sqm | Body corporate units — **NOT subdivisible** (already strata) |
| **GTP** | Group Title Plan | 63,208 | 203 sqm | Group title units/townhouses — **NOT subdivisible** (already strata) |
| **MPH** | Mining Purpose Homestead | 24,430 | 1,098 sqm | Mining lease land — special rules |
| **CP** | Crown Plan | 11,730 | 4,421 sqm | Crown (government) land — not privately subdivisible |
| **AP** | Agricultural Plan | 11,701 | 29,916 sqm | Large agricultural lots |
| **NR** | Nature Refuge | 4,486 | 58,025 sqm | Protected land |
| **AG** | Agricultural | 3,277 | 230,671 sqm | Agricultural holdings |
| **MCH** | Mining Claim Homestead | 3,478 | 10,120 sqm | Mining-related |

**App Usage:** Use plan prefix to immediately classify whether a property is:
- **Subdivisible candidate** (RP, SP with sufficient area)
- **Already strata/units** (BUP, GTP — show "already subdivided" message)
- **Government/special land** (CP, AP, NR, AG — not applicable)

#### Area Distribution (Understanding the Market)

| Range | Count | % | Interpretation |
|-------|-------|---|---------------|
| 0–200 sqm | 1,068,785 | 31.0% | Units, carparks, small lots (includes BUP/GTP zero-lot parcels) |
| 201–400 sqm | 188,922 | 5.5% | Small lots, townhouse lots |
| 401–600 sqm | 401,407 | 11.7% | **Standard residential** |
| 601–800 sqm | 586,263 | 17.0% | **Prime subdivision candidates** |
| 801–1000 sqm | 266,572 | 7.7% | **Excellent subdivision candidates** |
| 1001–2000 sqm | 265,111 | 7.7% | **High-value subdivision candidates** |
| 2001–5000 sqm | 185,149 | 5.4% | Large residential / acreage edge |
| 5001 sqm – 10 ha | 273,502 | 7.9% | Rural residential / farms |
| >10 ha | 209,994 | 6.1% | Rural, agricultural, pastoral |

**App Usage:** Filter properties by area to highlight subdivision potential. Properties 600–2000 sqm on RP/SP plans are the sweet spot.

#### Excluded Area (Easements)
- **6,455 parcels** have `excl_area > 0`
- Represents easements, drainage reserves, or other encumbrances
- Some have up to 73% excluded area (e.g. waterway easements)
- **Usable area = lot_area - excl_area**

**App Usage:** Always subtract `excl_area` when calculating usable/developable area. Flag properties with >10% excluded area as having significant encumbrances.

#### Duplicate Lotplans
Many lotplans have multiple geometry records (same lot/plan, different polygon parts). The parcel "3SP263939" has up to 108 geometry records — this is a multipart parcel where the same legal lot has discontinuous geographic extents.

**App Usage:** When querying by lotplan, be aware you may get multiple rows. Use `ST_Union()` to merge the geometries, or pick the largest polygon for display.

#### Null Records
- **604,918 records** (17.5%) have null lot/plan/lotplan — these are typically road parcels, waterways, or other non-titled land
- All 3,445,706 records have geometry (no null geometries)

**Reliability: HIGH.** This is the authoritative legal register. Data is refreshed by the QLD government. Boundary positions are surveyed and legally defined.

---

## 2. GNAF (Geocoded National Address File)

### What It Is
Australia's authoritative national address database, maintained by Geoscape Australia (previously PSMA). Contains **every known address in Australia** — 16.8M+ nationally, 3.55M in QLD alone.

### Core Tables

#### 2a. `gnaf_data_address_detail` — The Central Table
**16,836,365 records nationally | 3,550,178 QLD records**

This is the **master address register**. Every physical address in Australia has a record here.

| Column | Type | Description | App Value |
|--------|------|-------------|-----------|
| `address_detail_pid` | varchar(15) | Unique address ID (e.g. "GAQLD162877994") | Primary key for address lookup |
| `building_name` | varchar(200) | Named building/complex (e.g. "PALM LAKE RESORT") | Display on property page |
| `lot_number` | varchar(5) | Lot number from address registration | Cross-ref with cadastre |
| `flat_type_code` | varchar(7) | Unit type: UNIT, SHOP, APT, VLLA, SHED, TNHS, etc. | **Multi-dwelling detection** |
| `flat_number` | numeric(5) | Unit/flat number | Display in address |
| `number_first` | numeric(6) | Street number | Address display |
| `number_first_suffix` | varchar(2) | Suffix like "A", "B" | Address display |
| `number_last` | numeric(6) | End of street number range (e.g. "10–12") | Range address display |
| `street_locality_pid` | varchar(15) | FK to street_locality table | Join for street name |
| `locality_pid` | varchar(15) | FK to locality (suburb) table | Join for suburb name |
| `postcode` | varchar(4) | Postcode | Display, search, filtering |
| **`legal_parcel_id`** | varchar(20) | **Lot/Plan in "lot/plan" format** (e.g. "2/RP20457") | **Critical: links to cadastre** |
| `confidence` | numeric(1) | Address confidence: -1, 0, 1, 2 | Data quality indicator |
| `level_geocoded_code` | numeric(2) | Geocoding precision level (0–7) | Quality indicator |
| `alias_principal` | char(1) | "P" for principal, "A" for alias | Filter to principal only |
| `primary_secondary` | varchar(1) | NULL=standalone, "S"=secondary to a primary | Multi-dwelling detection |
| `date_created` | date | When address was added | Detect new developments |
| `date_retired` | date | When address was decommissioned | Filter to active only |
| `address_site_pid` | varchar(15) | FK to address_site | Join for site type |
| `property_pid` | varchar(15) | Property identifier | Group addresses by property |
| `gnaf_property_pid` | varchar(15) | GNAF-assigned property ID | Alternative property grouping |

##### Confidence Levels
| Value | Count (QLD) | % | Meaning |
|-------|------------|---|---------|
| 2 | 2,040,173 | 57.5% | **High** — address is well validated |
| 1 | 496,746 | 14.0% | **Medium** — reasonable confidence |
| 0 | 784,901 | 22.1% | **Low** — limited validation |
| -1 | 228,358 | 6.4% | **Unvalidated** — address contributed but not confirmed |

**App Usage:** Prefer confidence ≥ 1 for display. Flag confidence 0 and -1 addresses with a quality warning.

##### Level Geocoded Code (How good is the position)
| Code | Meaning | Count (QLD) | % |
|------|---------|------------|---|
| 7 | LOCALITY + STREET + ADDRESS | 3,350,826 | 94.4% | **Best** — geocoded to full address |
| 6 | LOCALITY + STREET, no address | 117,661 | 3.3% | Geocoded to street but not specific property |
| 5 | LOCALITY, no street, has address | 57,286 | 1.6% | Rural/remote with lot but no street |
| 4 | LOCALITY only | 24,405 | 0.7% | Only placed to suburb level |

##### Flat Type Codes (Multi-Dwelling Detection)
| Code | Full Name | Count (QLD) | Significance |
|------|-----------|------------|-------------|
| UNIT | Unit | 957,035 | Standard unit/apartment |
| SHOP | Shop | 57,755 | Commercial tenancy |
| SE | Suite | 8,200 | Office suite |
| VLLA | Villa | 7,656 | Villa in retirement/complex |
| APT | Apartment | 6,691 | Apartment |
| SHED | Shed | 5,470 | Rural/industrial shed |
| SITE | Site | 4,238 | Caravan/mobile home site |
| TNHS | Townhouse | 4,134 | Townhouse |
| ROOM | Room | 3,207 | Hotel/boarding room |
| OFFC | Office | 2,765 | Office |
| HSE | House | 2,314 | House within a group title |
| DUPL | Duplex | 2,066 | Duplex half |
| FLAT | Flat | 1,783 | Flat/bedsit |

**App Usage:** If a property's lotplan has addresses with `flat_type_code IS NOT NULL`, it's already multi-dwelling. Critical for subdivision analysis — tells you whether the land is already developed with multiple dwellings.

##### `legal_parcel_id` — The Critical Link
- Format: "lot/plan" (e.g. "2/RP20457")
- **3,248,784 QLD addresses** (91.5%) have a legal_parcel_id
- When you strip the "/" it matches the cadastre `lotplan` column
- **86.3% match rate** between distinct GNAF parcel IDs and cadastre lotplans
- The 13.7% that don't match are typically historical/superceded plans

**App Usage:** This is how you link an address to its land parcel. `REPLACE(legal_parcel_id, '/', '') = qld_cadastre_parcels.lotplan`

##### Multi-Dwelling Detection via Address Counts
By counting addresses per `legal_parcel_id`:

| Addresses per Parcel | Parcel Count | Interpretation |
|---------------------|-------------|----------------|
| 1 | 2,236,482 | Single dwelling — **subdivision candidate** |
| 2–5 | 297,260 | Small multi-dwelling (duplex, dual occ) |
| 6–20 | 12,591 | Townhouse/small apartment complex |
| 21–100 | 2,294 | Medium apartment building |
| 100+ | 512 | Large apartment/commercial complex |

**App Usage:** Single-address parcels on RP/SP plans with area ≥ 600 sqm are the **ideal subdivision targets**.

##### Building Names
- **345,467 QLD addresses** have a building name
- Top names: Palm Lake Resort (3,427), Gemlife (1,128), Carlyle Gardens (1,048)
- These are predominantly retirement villages, shopping centres, and large complexes

**App Usage:** Display building name prominently when available. Useful for identifying property type (retirement village, shopping centre, etc.).

##### State Coverage
| State | Total Addresses | With Parcel ID |
|-------|----------------|----------------|
| NSW | 5,190,134 | 4,716,170 |
| VIC | 4,376,696 | 4,136,554 |
| **QLD** | **3,550,178** | **3,248,784** |
| WA | 1,666,702 | 1,520,651 |
| SA | 1,276,707 | 1,153,186 |
| TAS | 374,851 | 339,940 |
| ACT | 281,460 | 254,183 |
| NT | 119,183 | 109,057 |

**Reliability: HIGH.** GNAF is the authoritative national standard.

---

#### 2b. `gnaf_data_address_default_geocode` — Coordinates
**16,836,811 records** — one per address, giving the **best available coordinate**.

| Column | Type | Description |
|--------|------|-------------|
| `address_detail_pid` | varchar(15) | FK to address_detail |
| `geocode_type_code` | varchar(4) | Type of geocode (see below) |
| `longitude` | numeric(11,8) | Longitude (GDA2020) |
| `latitude` | numeric(10,8) | Latitude (GDA2020) |
| `geometry` | Point (SRID 7844) | PostGIS point geometry |

##### Geocode Type Distribution (QLD)
| Code | Name | Count | Precision |
|------|------|-------|-----------|
| **PC** | Property Centroid | 3,329,295 | **Best** — centre of the property boundary |
| STL | Street Locality | 117,661 | Medium — placed on street centreline |
| GG | Gap Geocode | 42,036 | Medium — interpolated between neighbours |
| BC | Building Centroid | 34,032 | **Best** — centre of actual building |
| LOC | Locality | 24,405 | Low — placed at suburb centroid |
| UC | Unit Centroid | 1,465 | Best — specific unit location |

**App Usage:** 93.8% of QLD addresses have Property Centroid or better geocoding. Use `longitude`/`latitude` directly for map display. The `geometry` column enables spatial queries (point-in-polygon for LGA/zone lookup).

**Reliability: HIGH** for PC/BC types (93.8%). STL/GG/LOC are progressively less precise.

---

#### 2c. `gnaf_data_address_site_geocode` — Multiple Geocode Points
**20,788,314 records** — can have **multiple geocode points per address site** (e.g. property centroid + driveway frontage + letterbox).

Contains the same coordinate fields plus:
- `geocode_site_name` — named location within the site
- `geocode_site_description` — description of the point
- `boundary_extent` — size of property boundary in metres
- `planimetric_accuracy` — accuracy in metres
- `elevation` — height above datum

**App Usage:** Use for enhanced property display — show property centroid for map pin, but use driveway frontage for Street View camera positioning.

---

#### 2d. `gnaf_data_street_locality` — Street Names
**764,241 records** — every named street in Australia.

| Column | Description |
|--------|-------------|
| `street_name` | Street name (e.g. "QUEEN") |
| `street_type_code` | Street type (e.g. "STREET", "ROAD", "COURT") |
| `street_suffix_code` | Direction suffix (e.g. "NORTH", "EAST") |
| `street_class_code` | "C" (confirmed) or "U" (unconfirmed) |
| `gnaf_street_confidence` | 0–2 confidence score |

QLD Street Types (top 10):
1. ROAD (50,177)
2. STREET (44,820)
3. COURT (15,164)
4. DRIVE (7,927)
5. PLACE (5,867)
6. LANE (4,905)
7. AVENUE (4,881)
8. CLOSE (4,272)
9. CRESCENT (3,568)
10. ACCESS (3,465)

**App Usage:** Join via `street_locality_pid` to build full addresses. Street type tells you about neighbourhood character (courts/closes = residential cul-de-sacs, roads = arterials).

---

#### 2e. `gnaf_data_locality` — Suburbs/Localities
**17,578 records** — every suburb, town, district, and locality in Australia.

| Column | Description |
|--------|-------------|
| `locality_name` | Suburb/locality name (e.g. "PADDINGTON") |
| `primary_postcode` | Main postcode (often NULL — use address postcode instead) |
| `locality_class_code` | Classification (see below) |
| `state_pid` | FK to state table |

##### Locality Classes
| Code | Name | Meaning |
|------|------|---------|
| **G** | Gazetted Locality | Official suburb/town — **use these** |
| A | Alias Only | Alternative name only |
| D | District | Larger region |
| T | Topographic | Geographic feature |
| U | Unofficial Suburb | Common usage but not official |
| I | Indigenous Location | AGIL-identified location |

Top QLD Localities by Address Count:
1. Surfers Paradise (43,067)
2. Southport (31,985)
3. Brisbane City (23,213)
4. Maroochydore (21,745)
5. Caboolture (19,374)

**App Usage:** Filter `locality_class_code = 'G'` for official suburbs. Use for suburb-level stats and search.

---

#### 2f. `gnaf_data_locality_neighbour` — Adjacent Suburbs
**89,460 records** — bidirectional neighbour relationships between localities.

Example: Brisbane City neighbours = Fortitude Valley, Kangaroo Point, Milton, Petrie Terrace, South Brisbane, Spring Hill, Kelvin Grove.

**App Usage:** "See nearby properties in adjacent suburbs" feature. Also useful for showing subdivision potential in a broader neighbourhood context.

---

#### 2g. `gnaf_data_locality_alias` — Alternative Suburb Names
Maps old/alternative suburb names to current official names. Essential for search — users might search for a historical suburb name.

**App Usage:** Include in address search to handle old suburb names. E.g., someone searching "North Booval" should find results in "East Ipswich".

---

#### 2h. `gnaf_data_address_alias` — Alternative Address Representations
**879,018 records** — alternative ways to express the same address.

Alias Types:
| Code | Name | Count | Meaning |
|------|------|-------|---------|
| RA | Ranged Address | 396,015 | "10–12 Smith St" is alias for "10 Smith St" |
| SYN | Synonym | 294,945 | Same address in different locality/street name |
| LD | Level Duplication | 135,139 | Level-based duplicate |
| FNNFS | Flat Number – No First Suffix | 25,272 | Formatting variant |
| FPS | Flat Prefix – Suffix De-duplication | 15,162 | Formatting variant |
| CD | Contributor Defined | 12,485 | Custom alias |

**App Usage:** Use in address search to match user input to any known representation. Critical for "did you mean?" functionality.

---

#### 2i. `gnaf_data_address_site` — Site Classification
**16,845,123 records**

| Address Type | Count | Meaning |
|-------------|-------|---------|
| UN | 9,732,992 | Unknown site type |
| UR | 6,669,457 | Urban |
| R | 438,648 | Rural |

**App Usage:** Urban vs Rural classification affects subdivision rules. Rural properties have different minimum lot sizes and council requirements.

---

#### 2j. `gnaf_data_primary_secondary` — Address Relationships
**4,926,016 records** — links secondary addresses (units, shops) to their primary address (the building/property).

**App Usage:** Given a property address, find all units/secondary addresses at that site. Shows how many dwellings exist on the property.

---

#### 2k. `gnaf_data_address_mesh_block_2021` — ABS Mesh Blocks
**16,843,029 records** — links every address to an ABS 2021 Census mesh block.

Mesh Block Match Codes:
| Code | Match Level | Confidence |
|------|------------|-----------|
| 1 | Parcel level | Very high |
| 2 | Gap geocoded | High |
| 3 | Street level (single match) | High |
| 4 | Street level (multiple match) | Low |
| 5 | Locality level (multiple match) | Very low |

**App Usage:** Link to ABS Census data via mesh block codes for demographic information (population density, income levels, household composition). Valuable for market analysis.

---

#### 2l. `gnaf_data_address_feature` — Change History
**239,845 records** — tracks what changed about an address over time.

Change Types: LOC (locality change), NOF (number first change), STN (street name change), STT (street type change), LOT (lot number change), etc.

**App Usage:** Show property history — "This address was renumbered in 2015" or "This property's suburb was reclassified in 2020".

---

#### 2m. `gnaf_data_street_locality_point` — Street Midpoints
**717,857 records** — lat/lng for streets (typically the midpoint of the street).

**App Usage:** Centre map on street centroid when user searches by street name. Useful for street-level views.

---

#### 2n. `gnaf_data_locality_point` — Suburb Centres
**17,578 records** — lat/lng centroid for each locality.

**App Usage:** Centre map on suburb when user searches by suburb name more efficiently than computing from addresses.

---

## 3. GNAF Admin Boundaries

### 3a. `gnaf_admin_lga` — Local Government Areas
**209 QLD LGAs** (78 unique names — duplicates are multi-polygon parts of the same LGA).

All 78 QLD councils are represented, from Brisbane City to remote Indigenous shires.

| Column | Description |
|--------|-------------|
| `lga_name` | Full council name (e.g. "Brisbane City") |
| `abb_name` | Abbreviated name (e.g. "Brisbane") |
| `state` | State code ("QLD") |
| `geom` | MultiPolygon boundary (SRID 7844) |

**App Usage:** Spatial lookup — `ST_Contains(lga.geom, address_point)` tells you which council governs a property. This determines:
- Development assessment authority
- Council fees and charges
- Local planning scheme
- Minimum lot sizes and frontage requirements

**Reliability: HIGH.** Official PSMA boundaries, updated regularly.

---

### 3b. `gnaf_admin_localities` — Suburb Boundaries
**3,304 QLD localities** with polygon boundaries.

| Column | Description |
|--------|-------------|
| `loc_name` | Locality name |
| `loc_class` | Classification (same as locality_class_aut) |
| `geom` | MultiPolygon boundary |

**App Usage:** Draw suburb boundaries on map, determine which suburb a property is in via spatial query. More reliable than relying on address postcode (which can span multiple suburbs).

**Reliability: HIGH.** Official gazetted boundaries.

---

### 3c. `gnaf_admin_state_boundaries` — State Borders
**12,844 records** — state boundary polygons (complex coastlines = many polygon parts).

**App Usage:** Filter to QLD-only results. Useful for future multi-state expansion.

---

### 3d. `gnaf_admin_wards` — Electoral Wards
**No QLD wards in this dataset** — only NT, VIC, WA, SA have wards loaded.

**App Usage:** Not applicable for QLD currently. Brisbane City Council has 26 wards but they're not in this GNAF admin dataset. Would need to source separately if ward-level analysis is needed.

---

## 4. QLD Pools Registered (`qld_pools_registered`)

### What It Is
QLD government register of swimming pools — **18,285 registered pool sites** with 18,489 pools across 1,772 suburbs, 86 LGAs.

| Column | Description |
|--------|-------------|
| `site_name` | Registration ID (format: "lot/plan_type/plan_number") |
| `street_number`, `street_name`, `street_type` | Address components |
| `suburb`, `postcode` | Location |
| `number_of_pools` | Pools at this site |
| `lga` | Council name |
| `shared_pool_property` | Whether pool is shared (body corporate etc.) |

- **833 shared pool properties** (body corporate / community title)
- Most sites have 1 pool; some have multiple

**App Usage:** 
- Display "Registered pool on property" indicator
- The `site_name` format often encodes the lot/plan which can link to cadastre
- Pool presence affects property value and development constraints
- Shared pools indicate body corporate properties

**Reliability: MEDIUM.** Only covers registered pools; unregistered pools won't appear. Some records lack postcodes.

---

## 5. Cross-Reference & Joining Strategy

### The Master Join: Address → Parcel → Boundary

```sql
-- Complete property profile query
SELECT 
  d.number_first || COALESCE(d.number_first_suffix, '') AS street_number,
  s.street_name,
  s.street_type_code AS street_type,
  l.locality_name AS suburb,
  d.postcode,
  d.legal_parcel_id,
  d.confidence,
  d.building_name,
  g.longitude,
  g.latitude,
  g.geocode_type_code,
  c.lot_area,
  c.excl_area,
  c.lot_area - c.excl_area AS usable_area,
  UPPER(regexp_replace(c.plan, '[0-9].*', '')) AS plan_type
FROM gnaf_data_address_detail d
JOIN gnaf_data_street_locality s ON d.street_locality_pid = s.street_locality_pid
JOIN gnaf_data_locality l ON d.locality_pid = l.locality_pid
LEFT JOIN gnaf_data_address_default_geocode g ON d.address_detail_pid = g.address_detail_pid
LEFT JOIN qld_cadastre_parcels c ON c.lotplan = REPLACE(d.legal_parcel_id, '/', '')
WHERE d.address_detail_pid LIKE 'GAQLD%'
  AND d.date_retired IS NULL;
```

### Join Keys Summary
| From | To | Join Column |
|------|-----|------------|
| address_detail → street | `street_locality_pid` | Get street name/type |
| address_detail → locality | `locality_pid` | Get suburb name |
| address_detail → geocode | `address_detail_pid` | Get coordinates |
| address_detail → cadastre | `REPLACE(legal_parcel_id, '/', '') = lotplan` | Get parcel geometry/area |
| address_detail → site | `address_site_pid` | Get urban/rural classification |
| address_detail → mesh_block | `address_detail_pid` | Link to Census data |
| address_detail → primary_secondary | via `primary_pid` or `secondary_pid` | Find related addresses |
| cadastre geometry → LGA boundary | `ST_Contains(lga.geom, ST_Centroid(c.geometry))` | Find governing council |
| cadastre geometry → locality boundary | `ST_Contains(loc.geom, ST_Centroid(c.geometry))` | Confirm suburb |

---

## 6. Application Opportunities

### Immediate Value (Phase 1)

1. **Subdivision Potential Score** — Combine lot_area, plan_type, address count per parcel, and zone to compute a subdivision potential score:
   - Area ≥ 600 sqm on RP/SP plan ✓
   - Single dwelling (1 address per parcel) ✓
   - Not BUP/GTP (already strata) ✓
   - Low excluded area ratio ✓
   - Confidence ≥ 1 ✓

2. **Property Type Classification** — Automatically classify from plan prefix + flat_type + address count:
   - House (RP/SP, no flat_type, 1 address)
   - Unit (BUP/GTP, or has flat_type)
   - Duplex/Dual Occ (2 addresses)
   - Townhouse complex (3–20 addresses, TNHS flat_type)
   - Apartment building (20+ addresses, APT/UNIT flat_type)
   - Rural (area > 1 ha)
   - Government/special (CP, NR plan types)

3. **Address Search Enhancement** — Use locality_alias and address_alias tables to handle:
   - Old suburb names → current names
   - Ranged addresses ("10–12" → "10")
   - Alternative street names

4. **Nearby Properties** — Use locality_neighbour to show properties in adjacent suburbs

5. **LGA Detection** — Spatial lookup to determine which council governs the property. Then link to council-specific subdivision rules.

6. **Pool Indicator** — Show whether property has a registered pool

7. **Encumbrance Warning** — Flag properties with significant excluded area (easements)

### Future Value (Phase 2+)

8. **ABS Census Integration** — Via mesh blocks, link to demographic data for suburb profiling

9. **Development Trend Detection** — Use `date_created` on address_detail to spot new subdivisions:
   - Find parcels where new addresses appeared recently (post-2020)
   - These indicate recent development activity in the area

10. **Multi-State Expansion** — GNAF already has all states. Only cadastre needs state-specific import.

11. **Street Character Analysis** — Street types indicate neighbourhood character:
    - Courts/Closes/Places = quiet residential
    - Roads/Highways = arterial/noisy
    - This affects property desirability

12. **Comparable Subdivisions** — Find other lots on the same plan to identify similar subdivisions nearby (same developer, similar lot sizes). A plan with 20+ lots under 600 sqm that was created recently is a recent subdivision development.

---

## 7. Data Quality Summary

| Dataset | Records (QLD) | Reliability | Refresh Cycle | Key Limitation |
|---------|--------------|-------------|---------------|----------------|
| QLD Cadastre | 3,445,706 | **Very High** | Quarterly | 17.5% null lotplans (roads/waterways) |
| GNAF Addresses | 3,550,178 | **Very High** | Quarterly | 8.5% without parcel link; 6.4% unvalidated |
| GNAF Geocodes | 3,550,178 | **High** | Quarterly | 5.6% geocoded only to street/locality level |
| Admin LGAs | 209 (78 unique) | **Very High** | Annual | Multi-polygon parts require ST_Union |
| Admin Localities | 3,304 | **Very High** | Annual | Includes unofficial/alias localities |
| Pool Register | 18,285 | **Medium** | Static snapshot | Only registered pools; Aug 2024 snapshot |

### Key Caveats
1. **lot_area is in square metres** — values can be huge (up to 12.9 billion sqm = massive rural leases)
2. **SRID 7844 (GDA2020)** used throughout — not WGS84 (4326). Don't mix coordinate systems.
3. **Duplicate geometry rows** per lotplan are normal — use DISTINCT or aggregate
4. **Some addresses have no parcel link** — these still have valid geocodes, just can't be linked to land boundaries
5. **Confidence -1** addresses should be treated with caution — may be historical or unverified
