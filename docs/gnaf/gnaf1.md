# Australia G-NAF

**Copyright**

All copyright and other rights in this manual and the licensed programs described in this manual are the property of Experian Ltd save for copyright in data in respect of which the copyright belongs to the relevant data provider.

No part of this manual may be copied, reproduced, translated or reduced to any electronic medium or machine-readable form without the written consent of Experian Ltd.

Microsoft, Word and Windows are trademarks of Microsoft Corporation. © Experian Ltd. 2025

---

## Contacts and Support

For resolutions to common issues, answers to frequently asked questions and hints and tips for using our products: https://docs.experienaperture.io/more/contact-us/

For information about data expiry, data vintage and how to keep your data up to date: www.edq.com/documentation/data

For more information about us and to get in touch: www.edq.com

*Revised March 2025*

---

## Contents

- Introduction
  - Australia G-NAF Address Data Information
  - AUG Address Dataset
- About This Data
  - Area Covered
  - Address Elements
  - Address Element Definitions
    - Abbreviations
    - Postal Code Structure
  - Address Formatting
  - Default Address Format
  - Forms Of Address
    - G-NAF Layout
    - G-NAF Layout AS4590 (NAMF)
  - About DataPlus Information
    - DataPlus Sets for AUG Address Data
      - G-NAF Geocode Level and Type
      - G-NAF Address-Level Geocode Information
      - G-NAF Street-Level Geocode Information
      - G-NAF Locality-Level Geocode Information
      - G-NAF Highest-Level Geocode Information
      - G-NAF Persistent Identifier
      - G-NAF Address Type
      - G-NAF Street Persistent Identifier
      - G-NAF Locality Persistent Identifier
      - G-NAF Confidence Level
      - G-NAF Complex Addresses
      - G-NAF Legal Parcel Identifier
      - Administrative Boundaries Collector Districts
      - Administrative Boundaries Commonwealth Electoral Boundaries
      - Administrative Boundaries Local Government Areas
      - Administrative Boundaries Statistical Local Areas
      - Administrative Boundaries State Electoral Boundaries
      - Mosaic Group and Type
      - Mosaic Segments
      - Mosaic Factor 1–5
      - Length of Residence and Housing Tenure
      - Head of Household Age
      - Children at Address
      - Adults at Address
      - Household Composition
      - Lifestage
      - Household Income and Wealth
      - Affluence
      - Risk Insight
      - Credit Demand
- Using This Data
  - With Pro
    - Address Elements
      - Sub-Premises Formatting
      - Bordering Localities
    - Search Examples: Typedown
    - Search Examples: Single Line
    - Search Constraints
  - With Pro Web
    - Scenarios
      - Search Examples: Verification
  - With Batch
    - Subset Functionality
    - Bordering Localities
    - Secondary Information
    - Address Cleaning Modes
    - Postal Delivery Addresses
    - AUG-Specific Information Bits
    - Configuration Settings
      - FormatSecondaryInfo={boolean}
      - RetainBorderingLocality={boolean}

---

## Introduction

### Australia G-NAF Address Data Information

This chapter provides an overview of the Australia Geocoded National Address File (G-NAF) dataset.

### AUG Address Dataset

| Field | Value |
|---|---|
| Dataset Code | AUG |
| Approximate Data Size | 600Mb |
| Data Source | G-NAF: © PSMA Australia Limited: Spatial Data; G-NAF DataPlus: © PSMA Australia Limited: Spatial Data; Administrative Boundaries DataPlus: © PSMA Australia Limited: Spatial Data |
| Update Frequency | Quarterly |
| Expiry | March, June, September, December. Data files will expire approximately 6 months after receipt. For example, March data will expire in September of the same year. Ensure every data update is applied promptly, otherwise the data may expire and the product will become unusable. |

---

## About This Data

### Area Covered

The Australia G-NAF (AUG) dataset covers all postal addresses within eight states and territories of the Commonwealth of Australia.

### Address Elements

The following address elements are stored within the AUG data files:

| Address Element | Example | Element Code |
|---|---|---|
| Building name | Treasury Building | P12 |
| Flat/Unit name | Flat 2 | P31 |
| Flat/Unit type | Flat | P311 |
| Flat/Unit number | 2 | P312 |
| Sub-building number | 5a | P32 |
| Sub-building number (number) | 5 | P321 |
| Sub-building number (alpha) | a | P322 |
| Building Level | Level 7 | P21 |
| Building Level type | Level | P211 |
| Building Level number | 7 | P212 |
| Building number | 1-131 | P11 |
| Building number (first) | 1 | P111 |
| Building number (last) | 131 | P112 |
| Allotment number | Lot 16 | P13 |
| Allotment lot | Lot | P131 |
| Allotment number | 16 | P132 |
| Street | Tudor Court East | S11 |
| Street name | Tudor | S111 |
| Street type | Court | S112 |
| Street type suffix | East | S113 |
| Private Street | Private Street | S12 |
| Locality | Ayr | L21 |
| Bordering Locality | Mt Kelly | L22 |
| State Code | QLD | L11 |
| State name | Queensland | |
| Postcode | 4807 | C11 |
| Country name | Australia | X11 |
| Two Character Country Code | AU | X12 |
| Three Character Country Code | AUS | X13 |

### Address Element Definitions

#### Abbreviations

In an output address, the Building Level Type, Flat/Unit Type, Street Type, or Street Type Suffix address elements are returned in an abbreviated or expanded form, depending on your address formatting settings.

| Element | Abbreviated Form | Expanded Form |
|---|---|---|
| Building Level Type | Fl 2 | Floor 2 |
| | L7 | Level 7 |
| Flat/Unit Type | F 10 | Flat 10 |
| | U3 | Unit 3 |
| | Dupl 13 | Duplex 13 |
| | Fcty 4 | Factory 4 |
| | Mbth 18 | Marine Berth 18 |
| | Offc 9 | Office 9 |
| | Stll 12 | Stall 12 |
| | Whse 51 | Warehouse 51 |
| Street Type | Acacia Ave / Acacia Av | Acacia Avenue |
| | High St | High Street |
| | Tomlinson Arty | Tomlinson Artery |
| | Henley Br | Henley Brace |
| | Royal Cswy | Royal Causeway |
| | Durham Cr | Durham Crescent |
| | Summerdown Csac | Summerdown Cul-De-Sac |
| | Southern Cutt | Southern Cutting |
| | Morbury Dvwy | Morbury Driveway |
| | Grays Ex | Grays Extension |
| | Bright Glde | Bright Glade |
| | Tomlinson Hird | Tomlinson Highroad |
| | Pacific Mtwy | Pacific Motorway |
| | Queens Pde | Queens Parade |
| | Didcot Pwy | Didcot Parkway |
| | Matherson Pway | Matherson Pathway |
| | Downlands Thfr | Downlands Thorough |
| | Victorian Viad | Victorian Viaduct |
| Street Suffix Type | River Rd W | River Road West |
| | Lr Queens St | Lower Queens Street |
| | Up Queens St | Upper Queens Street |

#### Postal Code Structure

Australian postal codes consist of four numbers. The first two numbers represent a zone within a State/Territory. The full four digits represent a specific delivery office. PO Box installations have separate postal codes to street addresses, and large volume receivers may have their own postal code.

| State/Territory | State Code | Postal Code Ranges |
|---|---|---|
| Australian Capital Territory | ACT | 0200-0299, 2600-2620, 2900-2921 |
| New South Wales | NSW | 1000-2599, 2620-2899, 2921-2999 |
| Northern Territory | NT | 0800-0899 |
| Queensland | QLD | 4000-4999, 9000-9799 |
| South Australia | SA | 5000-5999 |
| Tasmania | TAS | 7000-7999 |
| Victoria | VIC | 3000-3999, 8000-8999 |
| Western Australia | WA | 6000-6999 |

### Address Formatting

There are four different types of addresses in Australia:

| Address Format | Layout |
|---|---|
| Routine Street Address | `<Building Number> <Street Name>` / `<Locality> <State Code> (<Postcode>)` — e.g. `16 Banjo Street` / `OLD ADAMINABY NSW 2629` |
| Flat or Unit Address | `<Flat/Unit Number> <Building Number> <Street Name>` / `<Locality> <State Code> (<Postcode>)` — e.g. `Flat 9 8 Trenerry Crescent` / `ABBOTSFORD VIC 3067` |
| Multi-Storey Building | `<Flat/Unit Address> <Level Number> <Building Number> <Street Name>` — e.g. `Flat 4 Level 1 51 Rhyll-Newhaven Road` / `RHYLL VIC 3923` |
| Allotment Address | `<Lot Number> <Street Name>` / `<Locality> <State Code> (<Postcode>)` — e.g. `Lot 2556 Daisy Hill Road` / `BUCKAJO NSW 2550` |

### Default Address Format

Australian addresses are defined upwards from the last line. The last line is displayed in block capitals and contains the locality name, state code and postal code, each separated by two spaces. The line above contains premises and street information.

The building number is shown before the street name. If the address contains sub-premises information, it is shown immediately in front of the building number, separated from it by a forward slash (`/`).

Any building level or flat/unit information is displayed before the sub-premises information. If both items are populated, the flat/unit information is written on the line above. Any building names are given on the next line up. If premises information has not been allocated, an allotment number appears in place of the building number.

If the output address line count is fixed to four, the output will be presented as:

```
Address Line 1: 16 Banjo Street
Address Line 2: <Blank>
Address Line 3: <Blank>
Address Line 4: OLD ADAMINABY NSW 2629
```

### Forms Of Address

There are two Forms of Address stored in the AUG data files:

#### G-NAF Layout

Using this layout, only G-NAF address elements and the common address elements can be returned.

| Address Layout | Elements Returned | Default Element |
|---|---|---|
| `<auto>` | Flat, Building level, Building number, Allotment and Street information are returned on the first three lines. | P41, P31, P42, P11, P13, S11 |
| Locality, State code, Postcode | Locality, State code, Postcode are fixed on the last line. | L21, L11, C11 |

#### G-NAF Layout AS4590 (NAMF)

The G-NAF Layout AS4590 (NAMF) is almost identical in content to the G-NAF layout above, however it directly complies with the address interoperability NAMF standard, with variations for AS4590:2006 compliance. More information about the National Address Management Framework: http://www.finance.gov.au

### About DataPlus Information

Each DataPlus set (`.dap`) is divided into one or more elements. You can configure Products to use any of the DataPlus sets available for AUG data.

### DataPlus Sets for AUG Address Data

The following DataPlus sets are available with Australia G-NAF data:

- G-NAF Geocode Level and Type
- G-NAF Address-Level Geocode
- G-NAF Street-Level Geocode
- G-NAF Locality-Level Geocode
- G-NAF Highest-Level Geocode
- G-NAF Persistent Identifier
- G-NAF Address Type
- G-NAF Street Persistent Identifier
- G-NAF Locality Persistent Identifier
- G-NAF Confidence Level Type
- G-NAF Complex Address
- G-NAF Legal Parcel Identifier
- Administrative Boundaries Collector Districts
- Administrative Boundaries Commonwealth Electoral Boundaries
- Administrative Boundaries Local Government Areas
- Administrative Boundaries Statistical Local Areas
- Administrative Boundaries State Electoral Boundaries
- Mosaic Group and Type
- Mosaic Segments
- Mosaic Factor 1–5
- Length of Residence and Housing Tenure
- Head of Household Age
- Children at Address
- Adults at Address
- Household Composition
- Lifestage
- Household Income and Wealth
- Affluence
- Risk Insight
- Credit Demand

---

#### G-NAF Geocode Level and Type

**Identifier:** AUGGLT

Returns the geocode level and type of the address. Every principal address must have at least a locality level geocode; it may also have a street level geocode and a parcel level geocode.

| Element | Code | Description |
|---|---|---|
| Geocode Level Code | GeocodeLvlCode | Geocode level code, a number between 0 and 7; e.g. "2". |
| Geocode Level Description | GeocodeLvlDesc | Geocode level description; e.g. "Street level geocode only". |
| Geocode Type Code | GeocodeTypeCode | 2–4 uppercase alphabetic characters; e.g. "LB". |
| Geocode Type Description | GeocodeTypeDesc | Geocode type description; e.g. "Letterbox". |

**Geocode levels:**

| Code | Description |
|---|---|
| 0 | No geocode information |
| 1 | Parcel level geocode only |
| 2 | Street level geocode only |
| 3 | Street and parcel level geocodes |
| 4 | Locality level geocode only |
| 5 | Locality and parcel level geocode |
| 6 | Locality and street level geocodes |
| 7 | Locality, street and parcel level geocodes |

**Geocode types:**

| Code | Description |
|---|---|
| BAP | Building access point |
| B | Building centroid |
| CDF | Centre-line dropped frontage |
| DF | Driveway frontage |
| EA | Emergency access |
| EAS | Emergency access secondary |
| ECP | Electricity connection point |
| EM | Electricity meter |
| FC | Frontage centre |
| FCS | Frontage centre setback |
| FDA | Front door access |
| GCP | Gas connection point |
| GG | Gap geocode |
| GM | Gas meter |
| ICP | Internet connection point |
| LB | Letterbox |
| PAP | Property access point |
| PAPS | Property access point setback |
| PC | Property centroid |
| PCM | Property centroid manual |
| SCP | Sewerage connection point |
| TCP | Telephone connection point |
| UC | Unit centroid |
| UCM | Unit centroid manual |
| UNK | Unknown |
| WCP | Water connection point |
| WM | Water meter |

---

#### G-NAF Address-Level Geocode Information

**Identifier:** AUGGAD

Returns address-level geocode information. Not all addresses have geocode information to address-level detail.

| Element | Code | Description |
|---|---|---|
| Address-Level Longitude | Longitude | The address-level longitude in degrees. |
| Address-Level Latitude | Latitude | The address-level latitude in degrees. |
| Address-Level Elevation | Elevation | The address-level elevation. |
| Address-Level Planimetric Accuracy | PlanimetricAccuracy | The address-level planimetric accuracy. |
| Address-Level Boundary Extent | BoundaryExtent | The address-level boundary extent. |
| Address-Level Geocode Reliability Code | GeocodeReliabilityCode | E.g. "2". See reliability table. |
| Address-Level Geocode Reliability Description | GeocodeReliabilityDesc | E.g. "Geocode accuracy sufficient to place centroid within address site boundary". |

**Geocode reliability codes:**

| Code | Description |
|---|---|
| 1 | Geocode accuracy recorded to appropriate surveying standard |
| 2 | Geocode accuracy sufficient to place centroid within address site boundary |
| 3 | Geocode accuracy sufficient to place centroid near (or possibly within) address site boundary |
| 4 | Geocode accuracy sufficient to associate address site with a unique road feature |
| 5 | Geocode accuracy sufficient to associate address site with a unique locality or neighbourhood |
| 6 | Geocode accuracy sufficient to associate address site with a unique region |

---

#### G-NAF Street-Level Geocode Information

**Identifier:** AUGGST

Returns street-level geocode information. Not all addresses have geocode information to street-level detail.

| Element | Code | Description |
|---|---|---|
| Street-Level Longitude | Longitude | The street-level longitude in degrees. |
| Street-Level Latitude | Latitude | The street-level latitude in degrees. |
| Street-Level Planimetric Accuracy | PlanimetricAccuracy | The street-level planimetric accuracy. |
| Street-Level Boundary Extent | BoundaryExtent | The street-level boundary extent. |
| Street-Level Geocode Reliability Code | GeocodeReliabilityCode | Either "4" or blank. |
| Street-Level Geocode Reliability Description | GeocodeReliabilityDesc | If code is "4": "Geocode accuracy sufficient to associate address site with a unique road feature". |

---

#### G-NAF Locality-Level Geocode Information

**Identifier:** AUGGLC

| Element | Code | Description |
|---|---|---|
| Locality-Level Longitude | Longitude | The locality-level longitude in degrees. |
| Locality-Level Latitude | Latitude | The locality-level latitude in degrees. |
| Locality-Level Planimetric Accuracy | PlanimetricAccuracy | The locality-level planimetric accuracy. |
| Locality-Level Geocode Reliability Code | GeocodeReliabilityCode | Either "5", "6", or blank. |
| Locality-Level Geocode Reliability Description | GeocodeReliabilityDesc | E.g. "Geocode accuracy sufficient to associate address site with a unique locality or neighbourhood". |

---

#### G-NAF Highest-Level Geocode Information

**Identifier:** AUGGHL

Contains the highest-level geocode information for a particular address. The level of detail depends on the `GeocodeLvlCode` in AUGGLT.

| Element | Code | Description |
|---|---|---|
| Longitude | Longitude | The highest-level longitude in degrees. |
| Latitude | Latitude | The highest-level latitude in degrees. |
| Elevation | Elevation | The highest-level elevation. |
| Planimetric Accuracy | PlanimetricAccuracy | The highest-level planimetric accuracy. |
| Boundary Extent | BoundaryExtent | The highest-level boundary extent. |
| Geocode Reliability Code | GeocodeReliabilityCode | The highest-level geocode reliability code. |
| Geocode Reliability Description | GeocodeReliabilityDesc | The highest-level geocode reliability description. |

---

#### G-NAF Persistent Identifier

**Identifier:** AUGGID

| Element | Code | Description |
|---|---|---|
| G-NAF PID | GNAFPID | Unique 14-character alphanumeric identifier; e.g. "GANSW716798454". |

---

#### G-NAF Address Type

**Identifier:** AUGADT

| Element | Code | Description |
|---|---|---|
| Address Type Code | AddrTypeCode | E.g. "R/RMB". |
| Address Type Description | AddrTypeDesc | E.g. "Rural Roadside Mail Box". |

**Address type codes:**

| Code | Description |
|---|---|
| R | Rural |
| R/BLOCK | Rural Block |
| R/CABIN | Rural Cabin |
| R/FLAT | Rural Flat |
| R/HOUSE | Rural House |
| R/LOT | Rural Lot |
| R/RES | Rural Reserve |
| R/RMB | Rural Roadside Mail Box |
| R/ROOM | Rural Room |
| R/RSD | Rural Roadside Mail Delivery |
| R/RSM | Rural Roadside Mail Service |
| R/SEC | Rural Section |
| R/SITE | Rural Site |
| R/UNIT | Rural Unit |
| UN | Unknown |
| UN/APT | Unknown Apartment |
| UN/BLOCK | Unknown Block |
| UN/CABIN | Unknown Cabin |
| UN/CTGE | Unknown Cottage |
| UN/CVAN | Unknown Caravan |
| UN/FARM | Unknown Farm |
| UN/FLAT | Unknown Flat |
| UN/GD | Unknown Ground Floor |
| UN/HOUSE | Unknown House |
| UN/LOC | Unknown Location |
| UN/LOT | Unknown Lot |
| UN/LWR | Unknown Lower |
| UN/POR | Unknown Portion |
| UN/PTHS | Unknown Penthouse |
| UN/REAR | Unknown Rear |
| UN/RES | Unknown Reserve |
| UN/RMB | Unknown Roadside Mail Box |
| UN/RMS | Unknown Roadside Mail Service |
| UN/ROOM | Unknown Room |
| UN/RSD | Unknown Roadside Mail Delivery |
| UN/RSM | Unknown Roadside Mail Service |
| UN/SEC | Unknown Section |
| UN/SITE | Unknown Site |
| UN/TNHS | Unknown Townhouse |
| UN/UNIT | Unknown Unit |
| UN/VILLA | Unknown Villa |
| UR | Urban |
| UR/BLOCK | Urban Block |
| UR/CABIN | Urban Cabin |
| UR/FLAT | Urban Flat |
| UR/HOUSE | Urban House |
| UR/LOT | Urban Lot |
| UR/RES | Urban Reserve |
| UR/RMB | Urban Roadside Mail Box |
| UR/RMS | Urban Roadside Mail Service |
| UR/ROOM | Urban Room |
| UR/RSD | Urban Roadside Mail Delivery |
| UR/RSM | Urban Roadside Mail Service |
| UR/SEC | Urban Section |
| UR/SITE | Urban Site |
| UR/UNIT | Urban Unit |

---

#### G-NAF Street Persistent Identifier

**Identifier:** AUGSID

| Element | Code | Description |
|---|---|---|
| Street PID | StreetPID | Unique street persistent identifier. |

---

#### G-NAF Locality Persistent Identifier

**Identifier:** AUGLID

| Element | Code | Description |
|---|---|---|
| Locality PID | LocalityPID | Unique locality persistent identifier. |

---

#### G-NAF Confidence Level

**Identifier:** AUGCFL

G-NAF consists of addresses provided by all States and Territories (Jurisdictions), the Australian Electoral Commission (AEC) and Australia Post. Validated addresses are merged into G-NAF, producing a single occurrence of each unique address.

| Element | Code | Description |
|---|---|---|
| Confidence Level Code | ConfLvlCode | Numerical; e.g. "2". |
| Confidence Level Description | ConfLvlDesc | E.g. "All three contributors have supplied an identical address". |

**Confidence level codes:**

| Code | Description |
|---|---|
| 0 | Only a single contributor holds this address. |
| 1 | A match has been achieved between only two contributors. |
| 2 | All three contributors have supplied an identical address. |

---

#### G-NAF Complex Addresses

**Identifier:** AUGCPX

Indicates if there is a link between Primary and Secondary addresses, and the PID of the Primary address if it exists.

| Element | Code | Description |
|---|---|---|
| Address Type Code | AddressTypeCode | Blank if no relationship exists; otherwise `P` (Primary) or `S` (Secondary). |
| Primary Address PID | PrimaryAddressPID | Only populated if the input address is a Secondary address. Contains the PID of the primary address. |
| Address Join Type Code | JoinType | `1`: Both parent and child have the same root address. `2`: Parent and child may or may not have the same root address. |

---

#### G-NAF Legal Parcel Identifier

**Identifier:** AUGLPI

Provides cadastral information captured from the address supplied by the jurisdiction.

| Element | Code | Description |
|---|---|---|
| G-NAF Legal Parcel Identifier | LPIPID | Populated with cadastral information using the same concatenations as adopted for the Jurisdiction Id in the Cadastre theme (CAD table) of the CadLite product. |

---

#### Administrative Boundaries Collector Districts

**Identifier:** AUGCLD

| Element | Code | Description |
|---|---|---|
| Collector District ID | CollectorDistrictPID | Unique Collector District persistent identifier. |
| Collector District Code | CollectorDistrictCode | The Collector District Code. |

---

#### Administrative Boundaries Commonwealth Electoral Boundaries

**Identifier:** AUGCWE

| Element | Code | Description |
|---|---|---|
| Commonwealth Electoral Boundary ID | CommonWealthElectoralPID | Unique Commonwealth Electoral Boundary persistent identifier. |
| Commonwealth Electoral Boundary Name | CommonWealthElectoralName | The Commonwealth Electoral Boundary name. |

---

#### Administrative Boundaries Local Government Areas

**Identifier:** AUGLGA

| Element | Code | Description |
|---|---|---|
| Local Government Area ID | LGAPID | Local Government Area persistent identifier. |
| Local Government Area Name | LGAName | Local Government Area name. |

---

#### Administrative Boundaries Statistical Local Areas

**Identifier:** AUGSLA

| Element | Code | Description |
|---|---|---|
| Statistical Local Area ID | SLAPID | Statistical Local Area persistent identifier. |
| Statistical Local Area Code | SLACode | Statistical Local Area code. |
| Statistical Local Area Name | SLAName | Statistical Local Area name. |

---

#### Administrative Boundaries State Electoral Boundaries

**Identifier:** AUGSTE

| Element | Code | Description |
|---|---|---|
| State Electoral Boundary ID | StateElectoralPID | State Electoral Boundary persistent identifier. |
| State Electoral Boundary Name | StateElectoralName | State Electoral Boundary name. |
| State Electoral Effective Start | StateElectoralEffectiveStart | Date the electorate becomes effective. |
| State Electoral Effective End | StateElectoralEffectiveEnd | End date when electorate is no longer in effect. |
| State Electoral New Boundary ID | StateElectoralNewPID | Identifier for the new electorate that will be in effect. |
| State Electoral New Boundary Name | StateElectoralNewName | Name for the new electorate that will be in effect. |
| State Electoral New Effective Start | StateElectoralNewEffectiveStart | Start date the new electorate will become effective. |
| State Electoral New Effective End | StateElectoralNewEffectiveEnd | End date when the new electorate will no longer be in effect. |

---

#### Mosaic Group and Type

**Identifier:** AUGMOS

Mosaic classifies all Australian households into unique Types and overarching Groups. For more information: http://www.experian.com.au/business/solutions/marketing-services/mosaic

| Element | Code | Description |
|---|---|---|
| Mosaic Group | Group | Mosaic Group; e.g. "K". |
| Mosaic Type | Type | Mosaic Group and Type; e.g. "K39". |

---

#### Mosaic Segments

**Identifier:** AUGMS

Mosaic Segments offer the next level of discrimination from Mosaic Types. Available at the household and Meshblock level.

| Element | Code | Description |
|---|---|---|
| Mosaic Segment Code | Code | Mosaic Segment; e.g. "A01_3". |

---

#### Mosaic Factor 1

**Identifier:** AUGFC1

Returns geodemographic Factor values for Cultural Diversity. Average score is zero, standard deviation is 10,000 (68% of meshblocks score between -10,000 and 10,000). Each percentile contains 1% of Australian households (0–99).

| Element | Code | Description |
|---|---|---|
| F1 Score - Cultural Diversity | Score | Mosaic 2024: Factor 1 scores representing levels of cultural diversity from traditional to multicultural. |
| F1 Percentile - Cultural Diversity | Percentile | Mosaic 2024: Factor 1 percentiles representing levels of cultural diversity from traditional to multicultural. |

---

#### Mosaic Factor 2

**Identifier:** AUGFC2

Returns geodemographic Factor values for Household Composition.

| Element | Code | Description |
|---|---|---|
| F2 Score - Household Composition | Score | Mosaic 2024: Factor 2 scores representing household composition from singles in units/apartments to families in detached houses. |
| F2 Percentile - Household Composition | Percentile | Mosaic 2024: Factor 2 percentiles representing household composition. |

---

#### Mosaic Factor 3

**Identifier:** AUGFC3

Returns geodemographic Factor values for Workforce Participation.

| Element | Code | Description |
|---|---|---|
| F3 Score - Workforce Maturity | Score | Mosaic 2024: Factor 3 scores representing levels of workforce maturity from low to high. |
| F3 Percentile - Workforce Maturity | Percentile | Mosaic 2024: Factor 3 percentiles representing levels of workforce maturity. |

---

#### Mosaic Factor 4

**Identifier:** AUGFC4

Returns geodemographic Factor values for Wealth.

| Element | Code | Description |
|---|---|---|
| F4 Score - Socioeconomic Status | Score | Mosaic 2024: Factor 4 scores representing levels of socioeconomic status from less to more access to socioeconomic resources. |
| F4 Percentile - Socioeconomic Status | Percentile | Mosaic 2024: Factor 4 percentiles representing socioeconomic status. |

---

#### Mosaic Factor 5

**Identifier:** AUGFC5

Returns geodemographic Factor scores for Rurality.

| Element | Code | Description |
|---|---|---|
| F5 Score - Rurality | Score | Mosaic 2024: Factor 5 scores representing levels of rurality from urban to rural. |
| F5 Percentile - Rurality | Percentile | Mosaic 2024: Factor 5 percentiles representing levels of rurality. |

---

#### Length of Residence and Housing Tenure

**Identifier:** AUGRLN

Returns an estimate of the length of time a person or family has lived at an address. Length of residency is divided into 15 bands.

| Element | Code | Description |
|---|---|---|
| Maximum Length of Residence | ResLenCodeHH | Mosaic 2024: Code for length of residence band of a household; e.g. "14". |
| | ResLenCodeMB | Mosaic 2024: Code for dominant length of residence band for households in a meshblock; e.g. "14". |
| | TenureCodeHH | Mosaic 2024: Single digit code for property tenure; e.g. "2". |
| | TenureCodeMB | Mosaic 2024: Single digit code for dominant tenure of properties in a meshblock; e.g. "2". |

---

#### Head of Household Age

**Identifier:** AUGAGE

Returns a predictor of age for the likely head of household. Ages returned in one of 15 bands, or marked as unclassified.

| Element | Code | Description |
|---|---|---|
| Head of Household Age | CodeHH | Mosaic 2024: Code for head of household age band for the property; e.g. "11". |
| | CodeMB | Mosaic 2024: Code for dominant head of household age band for properties in the meshblock; e.g. "11". |
| | Code | Deprecated element, always blank. |

---

#### Children at Address

**Identifier:** AUGCAD

Returns a predictor of the presence of children. Grouped into 10 bands, or marked as unclassified.

| Element | Code | Description |
|---|---|---|
| Propensity for Children 0-5 years | Cld05Code | Mosaic 2024: Likelihood of children aged 0-5 in the meshblock, as a decile; e.g. "10". |
| Propensity for Children 6-12 years | Cld612Code | Mosaic 2024: Likelihood of children aged 6-12, as a decile. |
| Propensity for Children 13-17 years | Cld1317Code | Mosaic 2024: Likelihood of children aged 13-17, as a decile. |

---

#### Adults at Address

**Identifier:** AUGAAD

Returns an estimate of the number of people aged 18 and over in a household.

| Element | Code | Description |
|---|---|---|
| Adults at Address | NumAdultsHH | Mosaic 2024: Estimated number of adults at an address; e.g. "3". |
| | NumAdultsMB | Mosaic 2024: Dominant estimated number of adults in a meshblock; e.g. "3". |
| | YoungAdultsDecileHH | Mosaic 2024: Likelihood of adults aged 18-24 at the property, as a decile; e.g. "10". |
| | YoungAdultsDecileMB | Mosaic 2024: Likelihood of adults aged 18-24 at a meshblock, as a decile. |

---

#### Household Composition

**Identifier:** AUGCMP

Provides an indication of the type of household. Grouped into one of 6 categories, or marked as unclassified.

| Element | Code | Description |
|---|---|---|
| Relations | CodeHH | Mosaic 2024: Single digit code for household composition of a property; e.g. "3". |
| | CodeMB | Mosaic 2024: Single digit code for dominant household composition in a meshblock; e.g. "3". |

---

#### Lifestage

**Identifier:** AUGLST

Returns an indication of the stage of life of household occupants. Returned in one of 10 bands.

| Element | Code | Description |
|---|---|---|
| Lifestage | CodeHH | Mosaic 2024: Code for life stage of property occupants; e.g. "10". |
| | CodeMB | Mosaic 2024: Code for dominant lifestage of households in a meshblock; e.g. "10". |

---

#### Household Income and Wealth

**Identifier:** AUGEIN

Household Income predicts the annual income of every Australian household, classified into one of 7 income bands.

| Element | Code | Description |
|---|---|---|
| Household Income | EINCodeHH | Mosaic 2024: Single digit code for income band of the household; e.g. "5". |
| | EINCodeMB | Mosaic 2024: Single digit code for dominant household income band of the meshblock; e.g. "5". |
| | WealthDecileHH | Mosaic 2024: Level of wealth of a household, as a decile; e.g. "5". |
| | WealthDecileMB | Mosaic 2024: Level of wealth of households in a meshblock, as a decile; e.g. "5". |

---

#### Affluence

**Identifier:** AUGAFF

An indicator of household level wealth based on income, assets and investments, differing from Household Income in that it offers an indication of disposable income. Returned in one of seven bands.

| Element | Code | Description |
|---|---|---|
| Affluence | CodeHH | Mosaic 2024: Single digit code for affluence band of the household; e.g. "3". |
| | CodeMB | Mosaic 2024: Single digit code for affluence band of the meshblock; e.g. "3". |

---

#### Risk Insight

**Identifier:** AUGRSK

Provides an indicator of risk at the sub meshblock level. Bureau data is aggregated to a geographical region for privacy. Returned in one of 12 bands, plus one category for households in a sub-meshblock with no presence on the bureau.

| Element | Code | Description |
|---|---|---|
| Risk Insight | Code | Code representing the Risk Insight band; e.g. "7". |

---

#### Credit Demand

**Identifier:** AUGCRD

Provides an indicator of demand for credit at the sub meshblock level. Credit data is aggregated to a geographical region for privacy. Categorised into 12 distinct bands.

| Element | Code | Description |
|---|---|---|
| Credit Demand | Code | Code representing the Credit Demand band; e.g. "7". |

---

## Using This Data

> These searches are accurate at the time of data release. Search results may differ depending on the data release you are using.

### With Pro

#### Address Elements

##### Sub-Premises Formatting

The default sort order in Australia is for sub-premises to appear after the premises (i.e. all primary points are grouped together). This allows refinement on both premises and sub-premises information.

For an example, do a Single Line search on `trinity avenue,sydney`.

##### Bordering Localities

When you search for a street, you may not know the correct postal locality. Pro and Pro Web search for the street in all localities which border the input locality and/or postal code.

For example, searching `banks street,parramatta` returns matches in Parramatta and its bordering localities (including Mays Hill). Matches from bordering localities are marked as aliases in the picklist.

#### Search Examples: Typedown

| Search type | Example |
|---|---|
| Full address known | 1. Type `2303` + Enter. 2. Type `brid` + Enter (uniquely identifies Bridge Street in 2303). 3. Type `18` + Enter. → `18 Bridge St, HAMILTON NSW 2303` |
| Post code unknown | 1. Type `bears` + Enter (uniquely identifies Bears Lagoon). 2. Type `dalz` + Enter. 3. Type `146` + Enter. → `146 Dalziels Road, BEARS LAGOON VIC 3517` |
| Full sub-premises address known | 1. Type `4000` + Enter. 2. Type `ad` + Enter (Adelaide Street). 3. Type `15` + Enter. 4. Type `9` + Enter. 5. Press Enter to accept. → `L 9 15 Adelaide St, BRISBANE QLD 4000` |

#### Search Examples: Single Line

| Search type | Example |
|---|---|
| Full address known | `40 roma st,4000` → `40 Roma Street, BRISBANE QLD 4000` |
| Full sub-premises address known | `9/18 ridge st,north sydney` → `9/18 Ridge Street, NORTH SYDNEY NSW 2060` |
| Postcode unknown | `8 fuller st,melrose` → `8 Fuller St, MELROSE SA 5483` |
| Street name known | Type `fairfield st` to view a list of every street of that name in the country. |
| Character missing | `12 ?arden rd,hope valley` → `12 Garden Road, HOPE VALLEY WA 6165` |
| Spelling mistake | `10 perhaw st,castlemaine` → `10 Preshaw Street, CASTLEMAINE VIC 3450` |
| Only partial info known | `high street, strat*` → picklist of High Streets in all places beginning with "Strat". Tag example: `king@s,nsw` restricts to streets containing "King" in NSW. |

#### Search Constraints

| Constraint | Elements Restricted to | Example Search |
|---|---|---|
| @C | State code/name | `victoria@c` |
| @L/@T | Locality | `King*@l, nsw` |
| @P | Premises information | `20@p, brighton` |
| @S | Street | `grove*@s,qld` |
| @X | Postal code | `1 mckay st, 08*@x` |

---

### With Pro Web

#### Scenarios

| Scenario | Search engine | For search examples, see |
|---|---|---|
| Address Capture on the Intranet | Single Line hierarchical | Single Line search examples |
| Address Capture on the Web | Single Line flattened | Single Line search examples |
| Address Capture | Single Line flattened | Single Line search examples |
| Single Line | Single Line hierarchical | Single Line search examples |
| Standard | Typedown / Single Line hierarchical | Typedown / Single Line search examples |
| Address Verification on the Web | Verification | Verification Search examples |

#### Search Examples: Verification

| Verify level | Example |
|---|---|
| Verified | `11 Dalgleish Close, Spence, ACT, 2615` → returns "Verified". |
| Multiple | `27 Alma Street, VIC, 3012` → returns "Multiple" as the street and number match in more than one city (Maidstone and West Footscray). Requires further user interaction. |
| None | `12 Raymount Way, Mayfield, NSW, 2304` → returns "None" as not enough information was provided. |
| StreetPartial | `Hickson Place, West Hobart, TAS, 7000` → returns "StreetPartial" as no property number was defined. |
| InteractionRequired | `16-18, Alfreds Gdn, KINGSTON, TAS, 7050` → returns "InteractionRequired" as the premise number has been changed (will match to 16 Alfreds Gdn), requiring verification from the user. |

---

### With Batch

#### Subset Functionality

The subset functionality is used to licence the Australia Enhanced data. It contains an additional secure subset file defining parameters for your subset of the AUG dataset so that metered searches within your subset do not incur royalty charges. Searches outside the subset parameters are subject to royalty charges.

The key configuration parameter is "State Code" for state administration area awareness, and "LGA Code" for local administration area awareness. This version of Batch includes two counters: one for addresses within your administrative area (no royalty charges), one for addresses outside (royalty charges apply).

Use of subset functionality requires a special licence key.

#### Bordering Localities

Batch can be configured to search against an input locality and all bordering localities. By default, Batch changes the supplied locality to the correct postal locality for the matched address. To retain a supplied bordering locality in the formatted return address, set `RetainBorderingLocality=True`.

#### Secondary Information

Batch enables you to retain unmatched secondary information not existing in the G-NAF data. For example, for `Suite 5/12 Ann St, NSW`, by default Batch would not retain "Suite 5". To retain it, set `FormatSecondaryInfo=True`.

#### Address Cleaning Modes

Three available modes:
- **Whole Address** (recommended for AUG data)
- **Enhanced Address**
- **Postal Code Only**

The Whole Address mode retains any unmatched premises info and formats it according to AUG rules.

Example — `14th Floor 61 Mary Street, Brisbane`:
- **Enhanced Mode** (without comma separator): `61 Mary Street, Brisbane QLD 4000` (sub-premises not retained)
- **Enhanced Mode** (with comma: `14th Floor, 61 Mary Street, Brisbane`): `14th Floor, 61 Mary Street, Brisbane QLD 4000`
- **Whole Address Mode**: `Floor 14 61 Mary Street, Brisbane QLD 4000` (sub-premises retained and formatted)

#### Postal Delivery Addresses

If a valid Postal Delivery Address type is supplied, Batch will automatically categorise it as unmatched (K) and set information bit `00100000`.

| Expanded PO Box Type | Abbreviated PO Box Type |
|---|---|
| Care of Post Office | Care PO |
| Community Mail Agent | CMA |
| Community Mail Bag | CMB |
| General Post Office Box | GPO Box |
| Locked Mail Bag Service | Locked Bag |
| Mail Service | MS |
| Post Office Box | PO Box |
| Poste Restante | Care PO |
| Private Mail Bag Service | Private Bag |
| Roadside Delivery | RSD |
| Roadside Mail Bag | RMB |
| Roadside Mail Box | RMB |
| Roadside Mail Service | RMS |
| Community Postal Agent | CPA |

#### AUG-Specific Information Bits

- For Standalone users: returned as the first 8 digits of the 16-digit extended match result in Interactive.
- For API users: returned by `QABatchWV_GetMatchInfo` as `rlCountryInfo1`, and from `QABatchWV_Clean` in `rsReturnCode` characters 13–20.

| Information Bit | Description |
|---|---|
| 10000000 | A street alias has been matched (may be retained if the street alias output item is fixed during configuration). |
| 20000000 | A locality alias has been matched (may be retained if the locality alias output item is fixed during configuration). |
| 40000000 | A bordering locality has been matched (may be retained if `RetainBorderingLocality` is enabled). |
| 01000000 | A match has been made to building number only. No sub-premises item has been matched. |
| 02000000 | No additional valid secondary information supplied. A building number has been supplied and matched. |
| 04000000 | A building number and valid secondary information were supplied but neither matched. The unmatched secondary information may be retained if `FormatSecondaryInfo=True`. |
| 00100000 | A valid PO Box type has been supplied in the input address. |

#### Configuration Settings

Configuration settings are held in the `[AUG]` section of the `qaworld.ini` file. The `AUG` prefix is optional:

```ini
FormatSecondaryInfo=True
```

or:

```ini
AUGFormatSecondaryInfo=True
```

---

#### FormatSecondaryInfo={boolean}

**Default:** `True`

Determines whether Batch retains supplied unmatched secondary information within a formatted return address.

**Example:**

Supplied address:
```
Kiosk 3 39 Nicholson St
Bairnsdale VIC 3875
```

Address in data:
```
39 Nicholson St
Bairnsdale VIC 3875
```

- Default (`True`): Output includes input descriptor → `Kiosk 3 39 Nicholson St, Bairnsdale VIC 3875`
- `False`: Output excludes input descriptor → `39 Nicholson St, Bairnsdale VIC 3875`

---

#### RetainBorderingLocality={boolean}

**Default:** `False`

Determines whether Batch retains supplied bordering locality information within a formatted return address. By default, when Batch matches via bordering locality data, the supplied locality is changed to the correct postal locality.

> Note: Due to the lack of bordering postcode information in G-NAF, postcode will not be returned if the bordering locality is retained, to avoid returning an incorrect locality/postcode combination.

**Example:**

Supplied address:
```
1 Coombs St
EDMONTON QLD 4869
```

- `RetainBorderingLocality=True`: `1 Coombs St, EDMONTON QLD` (no postcode)
- `RetainBorderingLocality=False`: `1 Coombs St, WHITE ROCK QLD 4868`
