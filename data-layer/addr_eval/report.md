
# Address Parser Benchmark Report

Generated: 2026-03-24 18:05:03

## Parser Availability

| Parser | Status | Notes |
| -------------------- | --------------- | ---------------------------------------- |
| custom_regex | ✅ Available | Custom regex — GC (ePathway) + Brisbane (Development.i) formats |
| au_address_parser | ✅ Available | au-address-parser — standard AU format; requires state code in address |
| deepparse_bpemb | ✅ Available | deepparse bpemb — neural model; PyTorch 2.2+ works despite transformers warning |
| address_net | ❌ Unavailable | address-net — GNAF-trained neural model, requires TensorFlow (archived Feb 2025) |

## Accuracy on Labeled Test Cases (Ground Truth)

_These 33 GC + 13 Brisbane cases were manually verified._


### Gold Coast ePathway format

_n = 33 cases_

| Parser | Overall | street_number | street_name | street_type | unit_type | unit_number | suburb | postcode |
| -------------------- | --------- | ------------- | ----------- | ----------- | --------- | ----------- | -------- | --------- |
| custom_regex | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| au_address_parser | 39.8% | 39.4% | 39.4% | 39.4% | 0.0% | 0.0% | 87.5% | 87.5% |
| deepparse_bpemb | 72.2% | 60.6% | 60.6% | 84.8% | 100.0% | 88.9% | 37.5% | 100.0% |
| address_net | ❌ N/A | — | — | — | — | — | — | — |

### Brisbane Development.i format

_n = 13 cases_

| Parser | Overall | street_number | street_name | street_type | unit_type | unit_number | suburb | postcode |
| -------------------- | --------- | ------------- | ----------- | ----------- | --------- | ----------- | -------- | --------- |
| custom_regex | 100.0% | 100.0% | 100.0% | 100.0% | — | — | 100.0% | 100.0% |
| au_address_parser | 88.5% | 92.3% | 92.3% | 84.6% | — | — | 81.8% | 90.9% |
| deepparse_bpemb | 98.4% | 100.0% | 100.0% | 100.0% | — | — | 90.9% | 100.0% |
| address_net | ❌ N/A | — | — | — | — | — | — | — |

## Labeled Test: Parse Errors (first 5 per parser)


### Gold Coast

**custom_regex**: all labeled cases correct ✅

**au_address_parser**:

  - `7 Mornington Court` → field `street_number`: expected `'7'`, got `None`
  - `7 Mornington Court` → field `street_name`: expected `'Mornington'`, got `None`
  - `7 Mornington Court` → field `street_type`: expected `'Court'`, got `None`
  - `635 Gold Coast Springbrook Road` → field `street_number`: expected `'635'`, got `None`
  - `635 Gold Coast Springbrook Road` → field `street_name`: expected `'Gold Coast Springbrook'`, got `None`

**deepparse_bpemb**:

  - `Lot 58 Gold Coast Highway` → field `street_number`: expected `'58'`, got `'gold'`
  - `Lot 58 Gold Coast Highway` → field `street_name`: expected `'Gold Coast'`, got `'Coast'`
  - `Lot 2 Hope Island Road` → field `street_number`: expected `'2'`, got `'hope'`
  - `Lot 2 Hope Island Road` → field `street_name`: expected `'Hope Island'`, got `'Island'`
  - `Lot 600 Ross Street` → field `street_number`: expected `'600'`, got `'ross'`

**address_net**: ❌ unavailable — skipped


### Brisbane

**custom_regex**: all labeled cases correct ✅

**au_address_parser**:

  - `184 COOPERS CAMP RD ASHGROVE  QLD  4060` → field `street_type`: expected `'Road'`, got `None`
  - `184 COOPERS CAMP RD ASHGROVE  QLD  4060` → field `suburb`: expected `'Ashgrove'`, got `'Rd Ashgrove'`
  - `115 NEWNHAM RD MOUNT GRAVATT EAST  QLD  4122` → field `street_number`: expected `'115'`, got `None`
  - `115 NEWNHAM RD MOUNT GRAVATT EAST  QLD  4122` → field `street_name`: expected `'Newnham'`, got `None`
  - `115 NEWNHAM RD MOUNT GRAVATT EAST  QLD  4122` → field `street_type`: expected `'Road'`, got `None`

**deepparse_bpemb**:

  - `115 NEWNHAM RD MOUNT GRAVATT EAST  QLD  4122` → field `suburb`: expected `'Mount Gravatt East'`, got `'Gravatt East'`

**address_net**: ❌ unavailable — skipped


## Full Dataset Statistics


### Gold Coast DA (8,107 distinct addresses)

| Parser | Available | Total Rows | Real Street Addrs | Parse Rate (real) | Bare Lot Correct | Elapsed |
| -------------------- | --------- | ---------- | ----------------- | ----------------- | ---------------- | --------- |
| custom_regex | ✅ | 8107 | 7133 | 100.0% | 100.0% | 0.1s |
| au_address_parser | ✅ | 8107 | 7133 | 0.0% | 100.0% | 0.1s |
| deepparse_bpemb | ✅ | 8107 | 7133 | 99.3% | 22.5% | 64.0s |
| address_net | ❌ | — | — | — | — | — |

### Brisbane DA (18 addresses)

| Parser | Available | Total Rows | Real Street Addrs | Parse Rate (real) | Bare Lot Correct | Elapsed |
| -------------------- | --------- | ---------- | ----------------- | ----------------- | ---------------- | --------- |
| custom_regex | ✅ | 18 | 17 | 100.0% | 100.0% | 0.0s |
| au_address_parser | ✅ | 18 | 17 | 94.1% | 100.0% | 0.0s |
| deepparse_bpemb | ✅ | 18 | 17 | 100.0% | 0.0% | 0.3s |
| address_net | ❌ | — | — | — | — | — |

## Field Extraction Rates (Full Dataset)

_% of addresses where each field was populated in parser output_


### Gold Coast

| Parser | street_number | street_name | street_type | unit_type | unit_number | suburb | postcode |
| -------------------- | ------------- | ----------- | ----------- | --------- | ----------- | -------- | --------- |
| custom_regex | 88.3% | 88.0% | 88.3% | 13.6% | 13.6% | 0.0% | 0.0% |
| au_address_parser | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| deepparse_bpemb | 96.9% | 97.9% | 84.5% | 15.8% | 15.8% | 2.5% | 8.1% |
| address_net | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### Brisbane

| Parser | street_number | street_name | street_type | unit_type | unit_number | suburb | postcode |
| -------------------- | ------------- | ----------- | ----------- | --------- | ----------- | -------- | --------- |
| custom_regex | 94.4% | 94.4% | 94.4% | 0.0% | 0.0% | 94.4% | 100.0% |
| au_address_parser | 88.9% | 88.9% | 77.8% | 0.0% | 0.0% | 88.9% | 88.9% |
| deepparse_bpemb | 100.0% | 100.0% | 88.9% | 5.6% | 5.6% | 100.0% | 100.0% |
| address_net | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Summary & Recommendation


| Parser | Strengths | Weaknesses |
|--------|-----------|-----------|
| **custom_regex** | Handles all GC-specific formats (bare lot refs, Lot+plan+address, ePathway variants); fast | Brittle to new formats; manual maintenance |
| **au_address_parser** | Clean AU standard addresses; no deps | Requires state code; fails on GC bare-format addresses |
| **deepparse_bpemb** | Neural approach; handles varied formats; suburb/postcode extraction | Street type folded into StreetName (needs post-processing split); heavy model download |
| **address_net** | Separate street_type field; trained on GNAF AU data | Archived (2025); TensorFlow dependency; old architecture |

**Recommendation:** For the GC DA use case, the custom_regex parser is best suited — it handles the GC-specific lot/plan formats, ePathway summary format, and the unit-prefix patterns that external libraries don't see. For a complementary "clean address" fallback (standard suburb+state+postcode format), au_address_parser adds value.
