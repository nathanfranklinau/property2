# Subdivision Process — Queensland

This document captures the actual steps a homeowner must complete to subdivide their land in Queensland. This is the content that drives the `journey_steps` table and the guided workflow in the app.

**Status: DRAFT — needs verification against current QLD planning legislation**

Primary references:
- Planning Act 2016 (Qld)
- Development Assessment Rules (DAR)
- Standard Building Regulation 2021
- Local Government (Planning and Environment) Act 1990 (historical context)

---

## Overview

Subdividing land in Queensland typically involves:
1. Confirming eligibility (lot size, zoning, frontage)
2. Pre-lodgement consultation with council
3. Lodging a development application (DA)
4. Council assessment and approval (possibly with conditions)
5. Survey and plan sealing
6. Infrastructure contributions and connections
7. Titles registration (Titles Queensland)

Timeframe: typically 6–18 months depending on council and complexity.

---

## Step Categories

Steps are grouped into categories for the UI:

- **Eligibility** — checks the user must do before starting
- **Professional** — surveys, reports, plans commissioned from licensed professionals
- **Council** — applications, approvals, responses to conditions
- **Infrastructure** — connections to water, sewer, electricity, roads
- **Legal** — contracts, easements, title transfers
- **Finance** — costs, contributions, levies

---

## Steps (Queensland — Standard Residential Subdivision)

### Stage 1: Eligibility Assessment

**Step 1.1 — Confirm minimum lot size**
- Check your local council's planning scheme for the minimum lot size in your zone
- Typical residential zones require 400–600m² per new lot (varies by council)
- Both the proposed new lot AND the remaining land must meet minimums
- *Required documents:* Current rate notice (confirms lot/plan), council planning scheme extract

**Step 1.2 — Confirm zoning permits subdivision**
- Identify property zoning in council's planning scheme
- Not all zones permit subdivision as of right — some require impact assessment
- *Tool:* QLD Government PD Hub (https://pdonline.dsdmip.qld.gov.au)

**Step 1.3 — Confirm adequate frontage**
- Minimum road frontage required for each new lot (typically 6–10m for battle-axe, 15m+ for standard)
- Check if existing driveway/access arrangement allows subdivision

**Step 1.4 — Check for overlays and constraints**
- Flood overlay, bushfire overlay, heritage overlay, character residential overlay
- Easements (drainage, overhead lines, sewerage)
- Registered encumbrances on title

---

### Stage 2: Pre-Lodgement

**Step 2.1 — Engage a town planner or private certifier** (recommended)
- Not legally required but strongly recommended for first-time applicants
- They advise on whether code-assessable or impact-assessable pathway

**Step 2.2 — Pre-lodgement meeting with council** (optional but recommended)
- Most councils offer a pre-lodgement consultation service
- Identify likely conditions before spending money on plans
- *Cost:* Typically $100–$500 depending on council

**Step 2.3 — Engage a licensed surveyor**
- Required to prepare the Survey Plan (SP) and subdivision plans
- Surveyor will also identify boundary pegs and easements

---

### Stage 3: Development Application

**Step 3.1 — Prepare development application (DA)**
- Completed by town planner or owner
- Submitted via PD Hub (Queensland's online planning portal)
- Application types: Code Assessment (faster) vs Impact Assessment

**Step 3.2 — Prepare supporting documents**
Required documents typically include:
- Site plan showing proposed lot boundaries and dimensions
- Statement of proposal / town planning report
- Survey plan (or draft)
- Stormwater management plan (if required)
- Services plan (water, sewer, electricity connection points)
- *Cost:* Council application fee (varies — typically $500–$5,000 for residential)

**Step 3.3 — Lodge DA via PD Hub**
- Lodgement triggers the statutory timeframe for council decision
- Code assessment: 20 business days
- Impact assessment: longer (includes public notification period)

---

### Stage 4: Council Assessment

**Step 4.1 — Council acknowledges application**
- Council issues an Acknowledgement Notice
- May issue an Information Request (IR) for additional information
- Clock stops while IR is being responded to

**Step 4.2 — Respond to Information Request (if issued)**
- Provide requested information within the specified timeframe
- Failure to respond may result in lapsing of the application

**Step 4.3 — Receive Decision Notice**
- Approval with conditions, or refusal
- Conditions typically cover: infrastructure contributions, works required, easements to be created

---

### Stage 5: Post-Approval Works

**Step 5.1 — Pay infrastructure charges notice (ICN)**
- Council issues an Infrastructure Charges Notice
- Covers network infrastructure (water, sewer, transport, parks)
- Must be paid before survey plan is sealed or at specific trigger

**Step 5.2 — Complete works required by conditions**
- May include: kerb and channel, stormwater connections, driveway upgrades, landscaping
- Works typically require a Building Development Approval (BDA) separately

**Step 5.3 — Connect new lot to services**
- Water and sewer connection (via local water authority — often council or Unitywater/SEQ Water)
- Electricity connection (energex/ergon)
- Each utility may have its own application and fee

---

### Stage 6: Survey Plan Sealing

**Step 6.1 — Surveyor prepares final Survey Plan**
- Based on approved conditions
- Submitted to council for sealing

**Step 6.2 — Council seals the Survey Plan**
- Council confirms all conditions have been met before sealing
- Signed copy returned to surveyor

---

### Stage 7: Title Registration

**Step 7.1 — Lodge Survey Plan with Titles Queensland**
- Survey plan + Form 5 (Request to Register Survey Plan)
- Completed by surveyor or solicitor
- *Cost:* Titles Queensland registration fee

**Step 7.2 — New titles issued**
- Each new lot receives its own Certificate of Title
- Process complete

---

## Costs Summary (approximate, QLD residential)

| Item | Typical range |
|---|---|
| Town planner | $2,000–$8,000 |
| Licensed surveyor | $3,000–$8,000 |
| Council DA fee | $500–$5,000 |
| Infrastructure charges | $20,000–$60,000+ (varies significantly by council) |
| Civil works | $10,000–$50,000+ (depending on conditions) |
| Utility connections | $5,000–$20,000 |
| Titles registration | ~$800 |
| **Total** | **~$50,000–$150,000+** |

---

## Notes for App Implementation

- The steps above need to be seeded into `journey_steps` for `jurisdiction = 'QLD'`
- Each step needs: title, description, category, is_required, typical_cost_low, typical_cost_high, reference_url
- Some steps are conditional (e.g., Information Request response only appears if council issues one)
- Council-specific variations (e.g., Brisbane City Council vs Sunshine Coast Council) may require council-level overrides of generic QLD steps in future
- Step order matters — the app should enforce that users can't mark Stage 4 steps complete before Stage 3

---

## References to Verify

- [ ] Confirm current minimum lot sizes for major QLD councils (BCC, Gold Coast, Sunshine Coast, Logan, Ipswich)
- [ ] Confirm current infrastructure charge rates (vary by council and financial year)
- [ ] Confirm PD Hub as the current lodgement portal
- [ ] Add links to current council planning scheme lookups
- [ ] Verify code assessment vs impact assessment thresholds
