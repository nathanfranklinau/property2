# G-NAF Data Dictionary

**Source:** Geoscape Geocoded National Address File (G-NAF), February 2026 release
**Schema reference:** https://docs.geoscape.com.au/projects/gnaf_desc/en/stable/appendix_c.html

---

## Overview

G-NAF is Australia's authoritative geocoded address file. This project loads it in full into PostgreSQL via `data-layer/import/import_gnaf_full.py`.

**Naming conventions:**
- Official table names are `UPPER_SNAKE_CASE` with no prefix (e.g. `ADDRESS_DETAIL`)
- Our tables use the prefix `gnaf_data_` in `lower_snake_case` (e.g. `gnaf_data_address_detail`)
- Official column names are `UPPER_SNAKE_CASE`; ours are the direct `snake_case` equivalents
- Authority/lookup tables have the suffix `_aut`

**Spatial data:**
- `geometry geometry(Point, 7844)` columns on geocode tables are **our addition** — not present in the source PSV files. Populated post-import from `longitude`/`latitude` using SRID 7844 (GDA2020).

**Immutability:** All `gnaf_data_*` tables are truncated and reloaded by the import script. Do not add custom columns or modify data.

---

## Table Index

### Standard Tables (19)

| Official Name | Internal Table | Description |
|---|---|---|
| STATE | gnaf_data_state | Australian states and territories |
| LOCALITY | gnaf_data_locality | Suburbs and localities |
| LOCALITY_ALIAS | gnaf_data_locality_alias | Alternative locality names |
| LOCALITY_NEIGHBOUR | gnaf_data_locality_neighbour | Adjacent locality pairs |
| LOCALITY_POINT | gnaf_data_locality_point | Gazetted locality centroid coordinates |
| MB_2016 | gnaf_data_mb_2016 | 2016 ABS census mesh block definitions |
| MB_2021 | gnaf_data_mb_2021 | 2021 ABS census mesh block definitions |
| STREET_LOCALITY | gnaf_data_street_locality | Streets within localities |
| STREET_LOCALITY_ALIAS | gnaf_data_street_locality_alias | Alternative street names |
| STREET_LOCALITY_POINT | gnaf_data_street_locality_point | Street segment centroid coordinates |
| ADDRESS_SITE | gnaf_data_address_site | Physical site metadata |
| ADDRESS_DETAIL | gnaf_data_address_detail | Core address records — primary table |
| ADDRESS_SITE_GEOCODE | gnaf_data_address_site_geocode | Site-level geocode points |
| ADDRESS_DEFAULT_GEOCODE | gnaf_data_address_default_geocode | Default geocode per address |
| ADDRESS_ALIAS | gnaf_data_address_alias | Links between principal and alias addresses |
| ADDRESS_FEATURE | gnaf_data_address_feature | Address change history records |
| ADDRESS_MESH_BLOCK_2016 | gnaf_data_address_mesh_block_2016 | Address-to-2016 mesh block links |
| ADDRESS_MESH_BLOCK_2021 | gnaf_data_address_mesh_block_2021 | Address-to-2021 mesh block links |
| PRIMARY_SECONDARY | gnaf_data_primary_secondary | Address hierarchy links (e.g. unit to complex) |

### Authority / Lookup Tables (16)

| Official Name | Internal Table | Rows |
|---|---|---|
| ADDRESS_ALIAS_TYPE_AUT | gnaf_data_address_alias_type_aut | 8 |
| ADDRESS_CHANGE_TYPE_AUT | gnaf_data_address_change_type_aut | 511 |
| ADDRESS_TYPE_AUT | gnaf_data_address_type_aut | 3 |
| FLAT_TYPE_AUT | gnaf_data_flat_type_aut | 54 |
| GEOCODED_LEVEL_TYPE_AUT | gnaf_data_geocoded_level_type_aut | 8 |
| GEOCODE_RELIABILITY_AUT | gnaf_data_geocode_reliability_aut | 6 |
| GEOCODE_TYPE_AUT | gnaf_data_geocode_type_aut | 30 |
| LEVEL_TYPE_AUT | gnaf_data_level_type_aut | 16 |
| LOCALITY_ALIAS_TYPE_AUT | gnaf_data_locality_alias_type_aut | 2 |
| LOCALITY_CLASS_AUT | gnaf_data_locality_class_aut | 9 |
| MB_MATCH_CODE_AUT | gnaf_data_mb_match_code_aut | 5 |
| PS_JOIN_TYPE_AUT | gnaf_data_ps_join_type_aut | 2 |
| STREET_CLASS_AUT | gnaf_data_street_class_aut | 2 |
| STREET_LOCALITY_ALIAS_TYPE_AUT | gnaf_data_street_locality_alias_type_aut | 2 |
| STREET_SUFFIX_AUT | gnaf_data_street_suffix_aut | 19 |
| STREET_TYPE_AUT | gnaf_data_street_type_aut | 276 |

---

## Key Field Reference

| Field | Table | Notes |
|---|---|---|
| `confidence` | gnaf_data_address_detail | Reflects how many contributor databases this address appears in (0 = 1 database, 1 = 2 databases etc.). |
| `alias_principal` | gnaf_data_address_detail | A = Alias record, P = Principal record. Filter to `P` for most uses. |
| `level_geocoded_code` | gnaf_data_address_detail | Binary indicator of the level of geocoding this address has. See `gnaf_data_geocoded_level_type_aut`. |
| `legal_parcel_id` | gnaf_data_address_detail | Generic parcel id field derived from the Geoscape Australia's Cadastre parcel where available. Used to join against cadastre data. |
| `primary_secondary` | gnaf_data_address_detail | Indicator that identifies if the address is P (Primary) or S (secondary). |
| `reliability_code` | gnaf_data_address_site_geocode | Spatial precision of the geocode expressed as number in the range, 1 (unique identification of feature) to 6 (feature associated to region i.e. postcode). |
| `geometry` | gnaf_data_address_site_geocode, gnaf_data_address_default_geocode | Point geometry – calculated by the longitude/latitude of record (not part of the product). Added by our import script; absent from source PSV files. SRID 7844 (GDA2020). |

---

## Standard Tables

### gnaf_data_state

Australian states and territories.

| Column | Official Name | Type | Description |
|---|---|---|---|
| state_pid | STATE_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| state_name | STATE_NAME | varchar(50) | The state or territory name. All in uppercase. E.g. TASMANIA. |
| state_abbreviation | STATE_ABBREVIATION | varchar(3) | The state or territory abbreviation. |

---

### gnaf_data_locality

Suburbs and localities. Each locality belongs to a state.

| Column | Official Name | Type | Description |
|---|---|---|---|
| locality_pid | LOCALITY_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| locality_name | LOCALITY_NAME | varchar(100) | The name of the locality or suburb. |
| primary_postcode | PRIMARY_POSTCODE | varchar(4) | Required to differentiate localities of the same name within a state. |
| locality_class_code | LOCALITY_CLASS_CODE | char(1) | Describes the class of locality (e.g. Gazetted, topographic feature etc.). FK → gnaf_data_locality_class_aut |
| state_pid | STATE_PID | varchar(15) | State persistent identifier. FK → gnaf_data_state |
| gnaf_locality_pid | GNAF_LOCALITY_PID | varchar(15) | Internal identifier used in the management of G-NAF. |
| gnaf_reliability_code | GNAF_RELIABILITY_CODE | numeric(1) | = 5 if suburb locality, else = 6. Spatial precision of the geocode expressed as number in the range, 1 (unique identification of feature) to 6 (feature associated to region i.e. postcode). |

---

### gnaf_data_locality_alias

Alternative names for localities.

| Column | Official Name | Type | Description |
|---|---|---|---|
| locality_alias_pid | LOCALITY_ALIAS_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| locality_pid | LOCALITY_PID | varchar(15) | Locality persistent identifier. FK → gnaf_data_locality |
| name | NAME | varchar(100) | The alias name for the locality or suburb. |
| postcode | POSTCODE | varchar(4) | Postcode. |
| alias_type_code | ALIAS_TYPE_CODE | varchar(10) | Alias type code for the locality. FK → gnaf_data_locality_alias_type_aut |
| state_pid | STATE_PID | varchar(15) | State persistent identifier. FK → gnaf_data_state |

---

### gnaf_data_locality_neighbour

Records which localities share a boundary.

| Column | Official Name | Type | Description |
|---|---|---|---|
| locality_neighbour_pid | LOCALITY_NEIGHBOUR_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| locality_pid | LOCALITY_PID | varchar(15) | Locality persistent identifier. FK → gnaf_data_locality |
| neighbour_locality_pid | NEIGHBOUR_LOCALITY_PID | varchar(15) | The neighbour locality persistent identifier. FK → gnaf_data_locality |

---

### gnaf_data_locality_point

Gazetted centroid coordinates for each locality.

| Column | Official Name | Type | Description |
|---|---|---|---|
| locality_point_pid | LOCALITY_POINT_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| locality_pid | LOCALITY_PID | varchar(15) | Locality persistent identifier. FK → gnaf_data_locality |
| planimetric_accuracy | PLANIMETRIC_ACCURACY | numeric(12) | Planimetric accuracy of geocode (if known). |
| longitude | LONGITUDE | numeric(11,8) | Longitude of calculated geocode of gazetted locality. |
| latitude | LATITUDE | numeric(10,8) | Latitude of calculated geocode of gazetted locality. |

---

### gnaf_data_mb_2016 / gnaf_data_mb_2021

ABS Census mesh block definitions. One row per mesh block, for 2016 and 2021 censuses respectively.

| Column | Official Name | Type | Description |
|---|---|---|---|
| mb_2016_pid / mb_2021_pid | MB_[YEAR]_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| mb_2016_code | MB_2016_CODE | varchar(15) | The 2016 mesh block code. |
| mb_2021_code | MB_2021_CODE | varchar(15) | The 2021 mesh block code. |

---

### gnaf_data_street_locality

Streets defined within a specific locality. A single physical street may have multiple rows if it spans locality boundaries.

| Column | Official Name | Type | Description |
|---|---|---|---|
| street_locality_pid | STREET_LOCALITY_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| street_class_code | STREET_CLASS_CODE | char(1) | Defines whether this street represents a confirmed or unconfirmed street. FK → gnaf_data_street_class_aut |
| street_name | STREET_NAME | varchar(100) | Street name. e.g. "POPLAR". |
| street_type_code | STREET_TYPE_CODE | varchar(15) | The street type code. e.g. "PLACE". FK → gnaf_data_street_type_aut |
| street_suffix_code | STREET_SUFFIX_CODE | varchar(15) | The street suffix code. e.g. "WEST". FK → gnaf_data_street_suffix_aut |
| locality_pid | LOCALITY_PID | varchar(15) | The locality persistent identifier. FK → gnaf_data_locality |
| gnaf_street_pid | GNAF_STREET_PID | varchar(15) | Internal identifier used in the management of G-NAF. |
| gnaf_street_confidence | GNAF_STREET_CONFIDENCE | numeric(1) | The street confidence level. |
| gnaf_reliability_code | GNAF_RELIABILITY_CODE | numeric(1) | Always = 4. Spatial precision of the geocode expressed as number in the range, 1 (unique identification of feature) to 6 (feature associated to region i.e. postcode). |

---

### gnaf_data_street_locality_alias

Alternative names for streets (e.g. former names, unofficial names).

| Column | Official Name | Type | Description |
|---|---|---|---|
| street_locality_alias_pid | STREET_LOCALITY_ALIAS_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| street_locality_pid | STREET_LOCALITY_PID | varchar(15) | Street locality persistent identifier. FK → gnaf_data_street_locality |
| street_name | STREET_NAME | varchar(100) | The street alias name. e.g. "POPLAR". |
| street_type_code | STREET_TYPE_CODE | varchar(15) | The street type code. e.g. "PLACE". FK → gnaf_data_street_type_aut |
| street_suffix_code | STREET_SUFFIX_CODE | varchar(15) | The street suffix code. e.g. "WEST". FK → gnaf_data_street_suffix_aut |
| alias_type_code | ALIAS_TYPE_CODE | varchar(10) | The alias type code. FK → gnaf_data_street_locality_alias_type_aut |

---

### gnaf_data_street_locality_point

Programmatically calculated centroid for a street within a locality.

| Column | Official Name | Type | Description |
|---|---|---|---|
| street_locality_point_pid | STREET_LOCALITY_POINT_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| street_locality_pid | STREET_LOCALITY_PID | varchar(15) | Street locality persistent identifier. FK → gnaf_data_street_locality |
| boundary_extent | BOUNDARY_EXTENT | numeric(7) | Boundary extent is defined as the straight-line distance from the street centroid to the furthest centreline point on the street segment. The value of the street boundary extent will be expressed in km. |
| planimetric_accuracy | PLANIMETRIC_ACCURACY | numeric(12) | Planimetric accuracy of geocode (if known). |
| longitude | LONGITUDE | numeric(11,8) | Longitude of programmatically calculated centroid of street centreline within the gazetted locality. |
| latitude | LATITUDE | numeric(10,8) | Latitude of programmatically calculated centroid of street centreline within the gazetted locality. |

---

### gnaf_data_address_site

Physical site-level metadata. Represents the site independent of individual address records.

| Column | Official Name | Type | Description |
|---|---|---|---|
| address_site_pid | ADDRESS_SITE_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| address_type | ADDRESS_TYPE | varchar(8) | Address type (e.g. 'Postal', 'Physical'). FK → gnaf_data_address_type_aut |
| address_site_name | ADDRESS_SITE_NAME | varchar(200) | Address site name. Field length: 200 alphanumeric characters. |

---

### gnaf_data_address_detail

**Primary table.** One row per address. Contains all parsed address components. Join to `gnaf_data_address_default_geocode` for coordinates.

| Column | Official Name | Type | Description |
|---|---|---|---|
| address_detail_pid | ADDRESS_DETAIL_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_last_modified | DATE_LAST_MODIFIED | date | Date this record was last modified (not retired/recreated in line with ICSM standard). |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| building_name | BUILDING_NAME | varchar(200) | Combines both building/property name fields. Field length: up to 200 alphanumeric characters (AS4590:2006 5.7). |
| lot_number_prefix | LOT_NUMBER_PREFIX | varchar(2) | Lot number prefix. Field length: up to two alphanumeric characters (AS4590:2006 5.8.1). |
| lot_number | LOT_NUMBER | varchar(5) | Lot number. Field length: up to five alphanumeric characters (AS4590:2006 5.8.1). |
| lot_number_suffix | LOT_NUMBER_SUFFIX | varchar(2) | Lot number suffix. Field length: up to two alphanumeric characters (AS4590:2006 5.8.1). |
| flat_type_code | FLAT_TYPE_CODE | varchar(7) | Specification of the type of a separately identifiable portion within a building/complex. Field Length: up to seven upper case alpha characters (AS4590:2006 5.5.1.1). FK → gnaf_data_flat_type_aut |
| flat_number_prefix | FLAT_NUMBER_PREFIX | varchar(2) | Flat/unit number prefix. Field length: up to two alphanumeric characters (AS4590:2006 5.5.1.2). |
| flat_number | FLAT_NUMBER | numeric(5) | Flat/unit number. Field length: up to five numeric characters (AS4590:2006 5.5.1.2). |
| flat_number_suffix | FLAT_NUMBER_SUFFIX | varchar(2) | Flat/unit number suffix Field length: up to two alphanumeric characters (AS4590:2006 5.5.1.2). |
| level_type_code | LEVEL_TYPE_CODE | varchar(4) | Level type. Field length: up to four alphanumeric characters (AS4590:2006 5.5.2.1). FK → gnaf_data_level_type_aut |
| level_number_prefix | LEVEL_NUMBER_PREFIX | varchar(2) | Level number prefix. Field length: up to two alphanumeric characters (AS4590:2006 5.5.2.2). |
| level_number | LEVEL_NUMBER | numeric(3) | Level number. Field length: up to three numeric characters (AS4590:2006 5.5.2.2). |
| level_number_suffix | LEVEL_NUMBER_SUFFIX | varchar(2) | Level number suffix. Field length: up to two alphanumeric characters (AS4590:2006 5.5.2.2). |
| number_first_prefix | NUMBER_FIRST_PREFIX | varchar(3) | Prefix for the first (or only) number in range. Field length: up to three uppercase alphanumeric characters (AS4590:2006 5.5.3.1). |
| number_first | NUMBER_FIRST | numeric(6) | Identifies first (or only) street number in range. Field length: up to six numeric characters (AS4590:2006 5.5.3.1). |
| number_first_suffix | NUMBER_FIRST_SUFFIX | varchar(2) | Suffix for the first (or only) number in range. Field length: up to two uppercase alphanumeric characters (AS4590:2006 5.5.3.1). |
| number_last_prefix | NUMBER_LAST_PREFIX | varchar(3) | Prefix for the last number in range. Field length: up to three uppercase alphanumeric characters (AS4590:2006 5.5.3.2). |
| number_last | NUMBER_LAST | numeric(6) | Identifies last number in range. Field length: up to six numeric characters (AS4590:2006 5.5.3.2). |
| number_last_suffix | NUMBER_LAST_SUFFIX | varchar(2) | Suffix for the last number in range. Field length: up to two uppercase alphanumeric characters (AS4590:2006 5.5.3.2). |
| street_locality_pid | STREET_LOCALITY_PID | varchar(15) | Street/Locality of this address - not mandatory as some records in G-NAF may not require street (e.g. remote rural property). FK → gnaf_data_street_locality |
| location_description | LOCATION_DESCRIPTION | varchar(45) | A general field to capture various references to address locations alongside another physical location. Field length: up to 45 alphanumeric characters (AS4590:2006 5.16). |
| locality_pid | LOCALITY_PID | varchar(15) | The unique identifier for the locality. FK → gnaf_data_locality |
| alias_principal | ALIAS_PRINCIPAL | char(1) | A = Alias record, P = Principal record. |
| postcode | POSTCODE | varchar(4) | Postcodes are optional as prescribed by AS4819 and AS4590:2006 5.13. |
| private_street | PRIVATE_STREET | varchar(75) | Private street information. This is not broken up into name/type/suffix. Field length: up to 75 alphanumeric characters. This is not currently populated. |
| legal_parcel_id | LEGAL_PARCEL_ID | varchar(20) | Generic parcel id field derived from the Geoscape Australia's Cadastre parcel where available. |
| confidence | CONFIDENCE | numeric(1) | Reflects how many contributor databases this address appears in (0 = 1 database, 1 = 2 database etc.). |
| address_site_pid | ADDRESS_SITE_PID | varchar(15) | Address site Persistent Identifier. FK → gnaf_data_address_site |
| level_geocoded_code | LEVEL_GEOCODED_CODE | numeric(2) | Binary indicator of the level of geocoding this address has. e.g. 0 = 000 = (No geocode), 1 = 001 = (No Locality geocode, No Street geocode, Address geocode), etc. FK → gnaf_data_geocoded_level_type_aut |
| property_pid | PROPERTY_PID | varchar(15) | Property persistent identifier referenced to relevant cadastral model. This field is not currently populated. |
| gnaf_property_pid | GNAF_PROPERTY_PID | varchar(15) | This field stores the property identifier provided by the jurisdiction for the property associated with the address. This identifier is the same as the CONTRIBUTOR_ID in the Property product. |
| primary_secondary | PRIMARY_SECONDARY | varchar(1) | Indicator that identifies if the address is P (Primary) or S (secondary). |

---

### gnaf_data_address_default_geocode

The single best geocode for each address. This is the geocode used in `ADDRESS_VIEW` and for most spatial queries.

| Column | Official Name | Type | Description |
|---|---|---|---|
| address_default_geocode_pid | ADDRESS_DEFAULT_GEOCODE_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| address_detail_pid | ADDRESS_DETAIL_PID | varchar(15) | Persistent identifier from the ADDRESS_DETAIL table. FK → gnaf_data_address_detail |
| geocode_type_code | GEOCODE_TYPE_CODE | varchar(4) | Unique abbreviation for the geocode type. FK → gnaf_data_geocode_type_aut |
| longitude | LONGITUDE | numeric(11,8) | Longitude. |
| latitude | LATITUDE | numeric(10,8) | Latitude. |
| geometry | GEOMETRY | geometry(Point, 7844) | Point geometry – calculated by the longitude/latitude of record (not part of the product). Added by our import script. |

**Geocode priority:** Geoscape applies a 29-level priority hierarchy to select the default geocode, from Building Access Point (highest) to locality-level generalisation (lowest).

---

### gnaf_data_address_site_geocode

All geocode points for a site, not just the default. Richer than `address_default_geocode` — includes reliability, accuracy, and site name metadata.

| Column | Official Name | Type | Description |
|---|---|---|---|
| address_site_geocode_pid | ADDRESS_SITE_GEOCODE_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| address_site_pid | ADDRESS_SITE_PID | varchar(15) | Address site Persistent Identifier. FK → gnaf_data_address_site |
| geocode_site_name | GEOCODE_SITE_NAME | varchar(200) | An identifier that relates to this specific geocoded site (e.g. 'Transformer 75658'). |
| geocode_site_description | GEOCODE_SITE_DESCRIPTION | varchar(45) | Additional textual data e.g. "Warning: Access to water riser is located at rear of building via SMITH LANE". |
| geocode_type_code | GEOCODE_TYPE_CODE | varchar(4) | Unique abbreviation for geocode feature. (e.g. 'PRCL'). FK → gnaf_data_geocode_type_aut |
| reliability_code | RELIABILITY_CODE | numeric(1) | Spatial precision of the geocode expressed as number in the range, 1 (unique identification of feature) to 6 (feature associated to region i.e. postcode). FK → gnaf_data_geocode_reliability_aut |
| boundary_extent | BOUNDARY_EXTENT | numeric(7) | Measurement (metres) of a geocode from other geocodes associated with the same address persistent identifier. |
| planimetric_accuracy | PLANIMETRIC_ACCURACY | numeric(12) | Planimetric accuracy. |
| elevation | ELEVATION | numeric(7) | Elevation. This field is not currently populated. |
| longitude | LONGITUDE | numeric(11,8) | Longitude. |
| latitude | LATITUDE | numeric(10,8) | Latitude. |
| geometry | GEOMETRY | geometry(Point, 7844) | Point geometry – calculated by the longitude/latitude of record (not part of the product). Added by our import script. |

---

### gnaf_data_address_alias

Links between principal and alias address records.

| Column | Official Name | Type | Description |
|---|---|---|---|
| address_alias_pid | ADDRESS_ALIAS_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| principal_pid | PRINCIPAL_PID | varchar(15) | Persistent identifier (i.e. ADDRESS_DETAIL_PID) of the principal address. FK → gnaf_data_address_detail |
| alias_pid | ALIAS_PID | varchar(15) | Persistent identifier (i.e. ADDRESS_DETAIL_PID) of the alias address. FK → gnaf_data_address_detail |
| alias_type_code | ALIAS_TYPE_CODE | varchar(10) | Alias type (e.g. 'Synonym'). FK → gnaf_data_address_alias_type_aut |
| alias_comment | ALIAS_COMMENT | varchar(200) | Comment about the alias (e.g. Corner address). |

---

### gnaf_data_address_feature

Tracks changes to address records over time.

| Column | Official Name | Type | Description |
|---|---|---|---|
| address_feature_id | ADDRESS_FEATURE_ID | varchar(16) PK | The Identifier is unique to the record within the table. The ID is prefixed with the state or territory abbreviation, e.g. NSW123456 |
| address_feature_pid | ADDRESS_FEATURE_PID | varchar(16) | The Persistent Identifier is the unique identifier for the addressable object this record represents. The PID allows for tracking change to the ADDRESS_DETAIL_PID associated with an addressable object over time. The PID is prefixed with AF and the state or territory abbreviation, e.g. AFNSW123456 |
| address_detail_pid | ADDRESS_DETAIL_PID | varchar(15) | The Persistent Identifier that is unique to the real world feature this record represents. FK → gnaf_data_address_detail |
| date_address_detail_created | DATE_ADDRESS_DETAIL_CREATED | date | Date the address (ADDRESS_DETAIL) record was created. |
| date_address_detail_retired | DATE_ADDRESS_DETAIL_RETIRED | date | Date the address (ADDRESS_DETAIL) record was retired. |
| address_change_type_code | ADDRESS_CHANGE_TYPE_CODE | varchar(50) | The code indicating the type of change, for example, LOC-STN for locality name and street name change. FK → gnaf_data_address_change_type_aut |

---

### gnaf_data_address_mesh_block_2016 / gnaf_data_address_mesh_block_2021

Links each address to its ABS census mesh block for 2016 and 2021 respectively.

| Column | Official Name | Type | Description |
|---|---|---|---|
| address_mesh_block_2016_pid / address_mesh_block_2021_pid | ADDRESS_MESH_BLOCK_[YEAR]_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| address_detail_pid | ADDRESS_DETAIL_PID | varchar(15) | Persistent identifier (i.e. ADDRESS_DETAIL_PID) of the principal address. FK → gnaf_data_address_detail |
| mb_match_code | MB_MATCH_CODE | varchar(15) | Code for mesh block match e.g. 1. FK → gnaf_data_mb_match_code_aut |
| mb_2016_pid / mb_2021_pid | MB_[YEAR]_PID | varchar(15) | Mesh block 2016/2021 Persistent Identifier. FK → gnaf_data_mb_2016 / gnaf_data_mb_2021 |

---

### gnaf_data_primary_secondary

Links parent/primary addresses to their child/secondary addresses (e.g. a complex address to its unit addresses).

| Column | Official Name | Type | Description |
|---|---|---|---|
| primary_secondary_pid | PRIMARY_SECONDARY_PID | varchar(15) PK | The Persistent Identifier is unique to the real world feature this record represents. |
| date_created | DATE_CREATED | date | Date this record was created. |
| date_retired | DATE_RETIRED | date | Date this record was retired. |
| primary_pid | PRIMARY_PID | varchar(15) | Persistent identifier for the primary address. Defined as a principal address which does not have a flat number or level number but which matches the secondary address in all other respects OR is designated as owning secondary addresses by Geoscape (e.g. involves private road in complex development). FK → gnaf_data_address_detail |
| secondary_pid | SECONDARY_PID | varchar(15) | Secondary persistent identifier for the Secondary address - defined as any address where flat number or level number information is not null, i.e. includes PREFIX, NUMBER or SUFFIX, OR is designated as being linked to a primary address by Geoscape (e.g. involves private road in complex development). FK → gnaf_data_address_detail |
| ps_join_type_code | PS_JOIN_TYPE_CODE | numeric(2) | Code of 1 OR 2 when the root address:- Code 1: Automatically generated when the primary and secondary addresses share the same street number, street name (and type) and locality name components. Code 2: Manually generated where the primary and secondary addresses MAY or MAY NOT share the same street number, street name (and type) and locality name components. FK → gnaf_data_ps_join_type_aut |
| ps_join_comment | PS_JOIN_COMMENT | varchar(500) | Details of join type can be given. |

---

## Authority Tables

All authority tables share the same column structure: `code` (PK), `name`, `description`.

---

### gnaf_data_address_alias_type_aut

| code | name | description |
|---|---|---|
| AL | ALTERNATIVE LOCALITY | ALTERNATIVE LOCALITY |
| CD | CONTRIBUTOR DEFINED | CONTRIBUTOR DEFINED |
| FNNFS | FLAT NUMBER - NO FIRST SUFFIX CORRELATION | FL NO-ST NO SUFF CORRELATION |
| FPS | FLAT PREFIX - SUFFIX DE-DUPLICATION | FLAT PREFIX - SUFFIX DE-DUP |
| LD | LEVEL DUPLICATION | LEVEL DUPLICATION |
| MR | MAINTENANCE REFERENCE | MAINTENANCE REFERENCE |
| RA | RANGED ADDRESS | RANGED ADDRESS |
| SYN | SYNONYM | SYNONYM |

---

### gnaf_data_address_change_type_aut

511 rows. Codes are hyphen-separated abbreviations of the address components that changed (e.g. `LOC-STN` = locality name and street name changed). Each combination is a distinct code. Used in `gnaf_data_address_feature.address_change_type_code`.

---

### gnaf_data_address_type_aut

| code | name | description |
|---|---|---|
| R | RURAL | RURAL |
| UN | UNKNOWN | UNKNOWN |
| UR | URBAN | URBAN |

---

### gnaf_data_flat_type_aut

Unit/flat type codes used in `gnaf_data_address_detail.flat_type_code`.

| code | name |
|---|---|
| ANT | ANTENNA |
| APT | APARTMENT |
| ATM | AUTOMATED TELLER MACHINE |
| BBQ | BARBECUE |
| BLCK | BLOCK |
| BLDG | BUILDING |
| BNGW | BUNGALOW |
| BTSD | BOATSHED |
| CAGE | CAGE |
| CARP | CARPARK |
| CARS | CARSPACE |
| CLUB | CLUB |
| COOL | COOLROOM |
| CTGE | COTTAGE |
| DUPL | DUPLEX |
| FCTY | FACTORY |
| FLAT | FLAT |
| GRGE | GARAGE |
| HALL | HALL |
| HSE | HOUSE |
| KSK | KIOSK |
| LBBY | LOBBY |
| LOFT | LOFT |
| LOT | LOT |
| LSE | LEASE |
| MBTH | MARINE BERTH |
| MSNT | MAISONETTE |
| OFFC | OFFICE |
| PTHS | PENTHOUSE |
| REAR | REAR |
| RESV | RESERVE |
| ROOM | ROOM |
| RTCE | ROOF TERRACE |
| SE | SUITE |
| SEC | SECTION |
| SHED | SHED |
| SHOP | SHOP |
| SHRM | SHOWROOM |
| SIGN | SIGN |
| SITE | SITE |
| STLL | STALL |
| STOR | STORE |
| STR | STRATA UNIT |
| STU | STUDIO |
| SUBS | SUBSTATION |
| TNCY | TENANCY |
| TNHS | TOWNHOUSE |
| TWR | TOWER |
| UNIT | UNIT |
| VLLA | VILLA |
| VLT | VAULT |
| WARD | WARD |
| WHSE | WAREHOUSE |
| WKSH | WORKSHOP |

---

### gnaf_data_geocoded_level_type_aut

Binary indicator of the level of geocoding an address has. Used in `gnaf_data_address_detail.level_geocoded_code`.

| code | name |
|---|---|
| 0 | NO GEOCODE |
| 1 | NO LOCALITY, NO STREET, ADDRESS |
| 2 | NO LOCALITY, STREET, NO ADDRESS |
| 3 | NO LOCALITY, STREET, ADDRESS |
| 4 | LOCALITY, NO STREET, NO ADDRESS |
| 5 | LOCALITY, NO STREET, ADDRESS |
| 6 | LOCALITY, STREET, NO ADDRESS |
| 7 | LOCALITY, STREET, ADDRESS |

---

### gnaf_data_geocode_reliability_aut

Spatial precision of geocode points. Used in `gnaf_data_address_site_geocode.reliability_code`.

| code | name | description |
|---|---|---|
| 1 | SURVEYING STANDARD | GEOCODE ACCURACY RECORDED TO APPROPRIATE SURVEYING STANDARD |
| 2 | WITHIN ADDRESS SITE BOUNDARY OR ACCESS POINT | GEOCODE ACCURACY SUFFICIENT TO PLACE CENTROID WITHIN ADDRESS SITE BOUNDARY OR ACCESS POINT |
| 3 | NEAR (OR POSSIBLY WITHIN) ADDRESS SITE BOUNDARY | GEOCODE ACCURACY SUFFICIENT TO PLACE CENTROID NEAR (OR POSSIBLY WITHIN) ADDRESS SITE BOUNDARY |
| 4 | UNIQUE ROAD FEATURE | GEOCODE ACCURACY SUFFICIENT TO ASSOCIATE ADDRESS SITE WITH A UNIQUE ROAD FEATURE |
| 5 | UNIQUE LOCALITY OR NEIGHBOURHOOD | GEOCODE ACCURACY SUFFICIENT TO ASSOCIATE ADDRESS SITE WITH A UNIQUE LOCALITY OR NEIGHBOURHOOD |
| 6 | UNIQUE REGION | GEOCODE ACCURACY SUFFICIENT TO ASSOCIATE ADDRESS SITE WITH A UNIQUE REGION |

---

### gnaf_data_geocode_type_aut

Describes the real-world feature a geocode point represents. Used in `gnaf_data_address_site_geocode.geocode_type_code` and `gnaf_data_address_default_geocode.geocode_type_code`.

| code | name | description |
|---|---|---|
| BAP | BUILDING ACCESS POINT | POINT OF ACCESS TO THE BUILDING. |
| BC | BUILDING CENTROID | POINT AS CENTRE OF BUILDING AND LYING WITHIN ITS BOUNDS (E.G. FOR U-SHAPED BUILDING). |
| BCM | BUILDING CENTROID MANUAL | POINT MANUALLY PLACED APPROXIMATELY AT CENTRE OF BUILDING AND LYING WITHIN ITS BOUNDS (E.G. FOR U-SHAPED BUILDING). |
| CDF | CENTRE-LINE DROPPED FRONTAGE | A POINT ON THE ROAD CENTRE-LINE OPPOSITE THE CENTRE OF THE ROAD FRONTAGE OF AN ADDRESS SITE. |
| DF | DRIVEWAY FRONTAGE | CENTRE OF DRIVEWAY ON ADDRESS SITE FRONTAGE. |
| EA | EMERGENCY ACCESS | SPECIFIC BUILDING OR PROPERTY ACCESS POINT FOR EMERGENCY SERVICES. |
| EAS | EMERGENCY ACCESS SECONDARY | SPECIFIC BUILDING OR PROPERTY SECONDARY ACCESS POINT FOR EMERGENCY SERVICES. |
| ECP | ELECTRICITY CONNECTION POINT | ELECTRICITY CONNECTION POINT (E.G. BOX, OR UNDERGROUND CHAMBER). |
| EM | ELECTRICITY METER | ELECTRICITY METER POINT (E.G. BOX, OR UNDERGROUND CHAMBER). |
| FC | FRONTAGE CENTRE | POINT ON THE CENTRE OF THE ADDRESS SITE FRONTAGE. |
| FCS | FRONTAGE CENTRE SETBACK | A POINT SET BACK FROM THE CENTRE OF THE ROAD FRONTAGE WITHIN AN ADDRESS SITE. |
| FDA | FRONT DOOR ACCESS | FRONT DOOR OF BUILDING. |
| GCP | GAS CONNECTION POINT | GAS CONNECTION POINT (E.G. BOX, OR UNDERGROUND CHAMBER). |
| GG | GAP GEOCODE | POINT PROGRAMMATICALLY ALLOCATED DURING G-NAF PRODUCTION PROPORTIONALLY BETWEEN ADJACENT ADDRESS LOCATIONS (BASED ON NUMBER_FIRST). |
| GM | GAS METER | GAS METER POINT (E.G. BOX, OR UNDERGROUND CHAMBER). |
| ICP | INTERNET CONNECTION POINT | INTERNET CONNECTION POINT (E.G. BOX, OR UNDERGROUND CHAMBER). |
| LB | LETTERBOX | PLACE WHERE MAIL IS DEPOSITED. |
| LOC | LOCALITY | POINT REPRESENTING A LOCALITY. |
| PAP | PROPERTY ACCESS POINT | ACCESS POINT (CENTRE OF) AT THE ROAD FRONTAGE OF THE PROPERTY. |
| PAPS | PROPERTY ACCESS POINT SETBACK | A POINT SET BACK FROM THE (CENTRE OF THE) ACCESS POINT AT THE ROAD FRONTAGE OF THE PROPERTY. |
| PC | PROPERTY CENTROID | POINT OF CENTRE OF PARCELS MAKING UP A PROPERTY AND LYING WITHIN ITS BOUNDARIES. |
| PCM | PROPERTY CENTROID MANUAL | POINT MANUALLY PLACED APPROXIMATELY AT CENTRE OF PARCELS MAKING UP A PROPERTY AND LYING WITHIN ITS BOUNDARIES. |
| SCP | SEWERAGE CONNECTION POINT | SEWERAGE CONNECTION POINT (E.G. BOX, OR UNDERGROUND CHAMBER). |
| STL | STREET LOCALITY | POINT REPRESENTING THE EXTENT OF A STREET WITHIN A LOCALITY. |
| TCP | TELEPHONE CONNECTION POINT | TELEPHONE CONNECTION POINT (E.G. BOX, OR UNDERGROUND CHAMBER). |
| UC | UNIT CENTROID | POINT AT CENTRE OF UNIT AND LYING WITHIN ITS BOUNDS. |
| UCM | UNIT CENTROID MANUAL | POINT MANUALLY PLACED APPROXIMATELY AT CENTRE OF UNIT AND LYING WITHIN ITS BOUNDS. |
| UNK | UNKNOWN | THE TYPE OF REAL WORLD FEATURE THE POINT REPRESENTS IS NOT KNOWN. |
| WCP | WATER CONNECTION POINT | WATER CONNECTION POINT (E.G. BOX, OR UNDERGROUND CHAMBER). |
| WM | WATER METER | WATER METER POINT (E.G. BOX, OR UNDERGROUND CHAMBER). |

---

### gnaf_data_level_type_aut

Floor/level type codes used in `gnaf_data_address_detail.level_type_code`.

| code | name |
|---|---|
| B | BASEMENT |
| FL | FLOOR |
| G | GROUND |
| L | LEVEL |
| LB | LOBBY |
| LG | LOWER GROUND FLOOR |
| M | MEZZANINE |
| OD | OBSERVATION DECK |
| P | PARKING |
| PDM | PODIUM |
| PLF | PLATFORM |
| PTHS | PENTHOUSE |
| RT | ROOFTOP |
| SB | SUB-BASEMENT |
| UG | UPPER GROUND FLOOR |
| UNGD | UNDERGROUND |

---

### gnaf_data_locality_alias_type_aut

| code | name |
|---|---|
| SR | SPATIALLY RELATED |
| SYN | SYNONYM |

---

### gnaf_data_locality_class_aut

| code | name | description |
|---|---|---|
| A | ALIAS ONLY LOCALITY | ALIAS ONLY LOCALITY |
| D | DISTRICT | DISTRICT |
| G | GAZETTED LOCALITY | GAZETTED LOCALITY |
| H | HUNDRED | HUNDRED |
| I | INDIGENOUS LOCATION | LOCATION IDENTIFIED IN THE AUSTRALIAN GOVERNMENT INDIGENOUS PROGRAMS AND POLICY LOCATIONS (AGIL) DATASET |
| M | MANUALLY VALIDATED | MANUALLY VALIDATED |
| T | TOPOGRAPHIC LOCALITY | TOPOGRAPHIC LOCALITY |
| U | UNOFFICIAL SUBURB | UNOFFICIAL SUBURB |
| V | UNOFFICIAL TOPOGRAPHIC FEATURE | UNOFFICIAL TOPOGRAPHIC FEATURE |

---

### gnaf_data_mb_match_code_aut

Match quality for address-to-mesh-block assignment. Used in `gnaf_data_address_mesh_block_2016/2021.mb_match_code`.

| code | name | description |
|---|---|---|
| 1 | PARCEL LEVEL MATCH | A parcel level geocode for the address has been applied and clearly within the boundaries of a single mesh block. The mesh block ID allocated to the address in most cases is at a very high level of confidence. |
| 2 | GAP GEOCODED ADDRESS LEVEL MATCH | A gap geocoded match for the address has been applied and clearly within the boundaries of a single mesh block. The mesh block ID allocated to the address in most cases is at a high level of confidence. |
| 3 | STREET LOCALITY LEVEL SINGLE MATCH | A street-locality level geocode for the address has been applied and clearly within the boundaries of a single mesh block. The mesh block ID allocated to the address in most cases is at a high level of confidence. |
| 4 | STREET LOCALITY LEVEL MULTIPLE MATCH | A street-locality level geocode for the address has been applied and is within the boundaries of multiple mesh blocks. The mesh block ID allocated to the address is at a low level of confidence. |
| 5 | LOCALITY LEVEL MULTIPLE MATCH | A locality level geocode for the address has been applied and is within the boundaries of multiple mesh blocks. The mesh block ID allocated to the address is at a very low level of confidence. |

---

### gnaf_data_ps_join_type_aut

| code | name | description |
|---|---|---|
| 1 | AUTO | AUTOMATICALLY MATCHED PRIMARY AND SECONDARY, BOTH PARENT AND CHILD HAVE THE SAME ROOT ADDRESS |
| 2 | MANUAL | MANUALLY GENERATED LINK, MAY OR MAY NOT HAVE THE SAME ROOT ADDRESS |

---

### gnaf_data_street_class_aut

| code | name | description |
|---|---|---|
| C | CONFIRMED | A confirmed street is present in the roads data of the PSMA Transport and Topography product for the same release. |
| U | UNCONFIRMED | An unconfirmed street is NOT present in the roads data of the PSMA Transport and Topography product for the same release and will not have a street locality geocode. |

---

### gnaf_data_street_locality_alias_type_aut

| code | name |
|---|---|
| ALT | ALTERNATIVE |
| SYN | SYNONYM |

---

### gnaf_data_street_suffix_aut

Directional and positional modifiers appended to street names. Used in `gnaf_data_street_locality.street_suffix_code`.

| code | name |
|---|---|
| CN | CENTRAL |
| DE | DEVIATION |
| E | EAST |
| EX | EXTENSION |
| IN | INNER |
| LR | LOWER |
| ML | MALL |
| N | NORTH |
| NE | NORTH EAST |
| NW | NORTH WEST |
| OF | OFF |
| ON | ON |
| OP | OVERPASS |
| OT | OUTER |
| S | SOUTH |
| SE | SOUTH EAST |
| SW | SOUTH WEST |
| UP | UPPER |
| W | WEST |

---

### gnaf_data_street_type_aut

276 rows. The `code` column holds the full street type name (e.g. `STREET`, `ROAD`, `AVENUE`). The `name` column holds the standard abbreviation (e.g. `ST`, `RD`, `AV`). The `description` column duplicates `name`.

Common examples:

| code (full name) | name (abbreviation) |
|---|---|
| AVENUE | AV |
| BOULEVARD | BVD |
| CLOSE | CL |
| COURT | CT |
| CRESCENT | CR |
| DRIVE | DR |
| HIGHWAY | HWY |
| LANE | LANE |
| PARADE | PDE |
| PLACE | PL |
| ROAD | RD |
| STREET | ST |
| TERRACE | TCE |
| WAY | WAY |

Full list: `SELECT code, name FROM gnaf_data_street_type_aut ORDER BY code;`

---

## ADDRESS_VIEW

A non-materialised view defined in `db/migrations/036_gnaf_address_view.sql`. Not part of the official G-NAF schema — created by this project for address autocomplete and GNAF-backed lookups.

**Filter:** `WHERE confidence > -1` (excludes addresses with no contributor data).

**Joins:** `address_detail` → `flat_type_aut`, `level_type_aut`, `street_locality`, `street_suffix_aut`, `street_class_aut`, `street_type_aut`, `locality`, `address_default_geocode`, `geocode_type_aut`, `geocoded_level_type_aut`, `state`.

| Column | Source | Description |
|---|---|---|
| ADDRESS_DETAIL_PID | address_detail.address_detail_pid | The Persistent Identifier is unique to the real world feature this record represents. |
| STREET_LOCALITY_PID | address_detail.street_locality_pid | Street/Locality of this address. |
| LOCALITY_PID | address_detail.locality_pid | The unique identifier for the locality. |
| BUILDING_NAME | address_detail.building_name | Combines both building/property name fields. |
| LOT_NUMBER_PREFIX | address_detail.lot_number_prefix | Lot number prefix. |
| LOT_NUMBER | address_detail.lot_number | Lot number. |
| LOT_NUMBER_SUFFIX | address_detail.lot_number_suffix | Lot number suffix. |
| FLAT_TYPE | flat_type_aut.name | Resolved flat/unit type name (e.g. UNIT, APARTMENT). |
| FLAT_NUMBER_PREFIX | address_detail.flat_number_prefix | Flat/unit number prefix. |
| FLAT_NUMBER | address_detail.flat_number | Flat/unit number. |
| FLAT_NUMBER_SUFFIX | address_detail.flat_number_suffix | Flat/unit number suffix. |
| LEVEL_TYPE | level_type_aut.name | Resolved floor type name (e.g. LEVEL, GROUND). |
| LEVEL_NUMBER_PREFIX | address_detail.level_number_prefix | Level number prefix. |
| LEVEL_NUMBER | address_detail.level_number | Level number. |
| LEVEL_NUMBER_SUFFIX | address_detail.level_number_suffix | Level number suffix. |
| NUMBER_FIRST_PREFIX | address_detail.number_first_prefix | Prefix for the first (or only) number in range. |
| NUMBER_FIRST | address_detail.number_first | Identifies first (or only) street number in range. |
| NUMBER_FIRST_SUFFIX | address_detail.number_first_suffix | Suffix for the first (or only) number in range. |
| NUMBER_LAST_PREFIX | address_detail.number_last_prefix | Prefix for the last number in range. |
| NUMBER_LAST | address_detail.number_last | Identifies last number in range. |
| NUMBER_LAST_SUFFIX | address_detail.number_last_suffix | Suffix for the last number in range. |
| STREET_NAME | street_locality.street_name | Street name. |
| STREET_CLASS_CODE | street_locality.street_class_code | Raw class code (C/U). |
| STREET_CLASS_TYPE | street_class_aut.name | Resolved class name (CONFIRMED / UNCONFIRMED). |
| STREET_TYPE_CODE | street_locality.street_type_code | Raw type code (e.g. ROAD). |
| STREET_SUFFIX_CODE | street_locality.street_suffix_code | Raw suffix code (e.g. N). |
| STREET_SUFFIX_TYPE | street_suffix_aut.name | Resolved suffix name (e.g. NORTH). |
| LOCALITY_NAME | locality.locality_name | The name of the locality or suburb. |
| STATE_ABBREVIATION | state.state_abbreviation | The state or territory abbreviation. |
| POSTCODE | address_detail.postcode | Postcodes are optional as prescribed by AS4819 and AS4590:2006 5.13. |
| LATITUDE | address_default_geocode.latitude | Latitude. |
| LONGITUDE | address_default_geocode.longitude | Longitude. |
| GEOCODE_TYPE | geocode_type_aut.name | Resolved geocode type name. |
| CONFIDENCE | address_detail.confidence | Reflects how many contributor databases this address appears in (0 = 1 database, 1 = 2 database etc.). |
| ALIAS_PRINCIPAL | address_detail.alias_principal | A = Alias record, P = Principal record. |
| PRIMARY_SECONDARY | address_detail.primary_secondary | Indicator that identifies if the address is P (Primary) or S (secondary). |
| LEGAL_PARCEL_ID | address_detail.legal_parcel_id | Generic parcel id field derived from the Geoscape Australia's Cadastre parcel where available. |
| DATE_CREATED | address_detail.date_created | Date this record was created. |
