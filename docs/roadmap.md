# ProductProfiler — Product Roadmap

## Vision

PropertyProfiler is a property intelligence platform for Australian homeowners and property professionals. It answers the questions homeowners actually have about their land — what they can build, where the boundaries are, what the rules say, and what their options are — using authoritative government datasets and automated analysis.

The starting hook is subdivision potential, but the platform is designed to grow into a comprehensive property profile tool covering zoning, constraints, renovation planning, and regulatory workflows.

---

## Audiences

### Primary (Phase 1): Homeowners
Single property view. A homeowner wants to understand what they can do with their land — can they subdivide? Can they add a granny flat? What zone are they in? What council rules apply?

### Secondary (Phase 2): Property Professionals
Multi-property tracking. Planners, surveyors, builders, and real estate agents who work across multiple sites and need to track properties through various stages of assessment and approval.

---

## Product Goals

These are the high-level capabilities the platform is being built toward:

### 1. Property Insights and Attributes
Surface key facts about a property from authoritative sources: lot size, boundaries, lot and plan number, survey plan history, ownership type (freehold vs strata), and cadastral metadata.

### 2. Property Markup and Annotation
Allow users to mark up a property map with callouts — pool locations, building footprints, unusable land, proposed changes. The underlying map supports polygon drawing, editing, rotation, buffer zones, and measurement labels.

### 3. LGA and Zoning Intelligence
Show the council (LGA) a property sits within, the planning scheme zone, minimum lot sizes, setback requirements, and what uses are permitted. Sourced from the QLD Planning Scheme Zones dataset (state-wide authoritative) and LGA boundary data.

### 4. Blog and Educational Content
SEO-driven blog covering subdivision guides, zoning explainers, council-specific guides, and property tips. Helps users understand the landscape before and after running an analysis. Built with MDX (no external CMS).

### 5. Regulatory Workflow Guidance
Step-by-step guidance for specific activities: subdivision (Reconfiguration of a Lot), development applications, pre-lodgement processes. Tracks which steps a user has completed and what comes next. (Phase 2+)

### 6. Public Analysis — No Login Required (Phase 1)
Unauthenticated users can run a full property analysis and see all results. This is intentional for the Phase 1 proof of concept — lower friction = more validation data. A subset of features will eventually move behind auth.

### 7. Authenticated Markup Saving (Phase 2)
Logged-in users can save their property markups, annotations, and analysis results. No login required in Phase 1 — markups exist only for the session.

### 8. Contours, Slope, and Dead Space
Show contour lines and relief shading on the property. Identify areas where nothing can practically be built — steep slopes, easements, setback zones, flood-prone land. Uses Google Elevation API (on-demand, no bulk DEM hosting).

### 9. Floor Plan Template Positioning
Drag standard floor plan templates (small/medium/large house, granny flat, garage) onto the property map to mock up subdivision scenarios and visualise where an additional dwelling could go. Uses the existing PropertyMap polygon system.

### 10. Subdivision Rules and Zoning Explainers
Surface property-specific rules: is subdivision permitted? What is the minimum lot size? What is the assessment pathway (code vs impact)? Show the council's planning scheme URL and pre-lodgement contact. Initially from a static lookup; later from live data.

### 11. Neighbourhood Subdivision Statistics
Show how many properties in the same postcode and surrounding postcodes have been subdivided, what types of subdivisions were done, and what the typical lot sizes are. Derived from QLD cadastre data (SP-prefixed plans = subdivisions).

---

## Phase Structure

### Phase 1 — Unauthenticated Proof of Concept

**Goal:** Validate market demand. Ship something real that homeowners can use and that generates organic traffic via the blog.

**Access model:** Fully public, no login required.

#### Completed

- [x] Address search via Google Places Autocomplete
- [x] Cadastre parcel lookup (PostGIS spatial join, QLD only)
- [x] Automated property analysis pipeline: satellite imagery, building detection (OpenCV), pool detection (YOLO), space calculation
- [x] Interactive property map: boundary outline, building footprint polygons, polygon drawing/editing, rotation, buffer zones, measurement labels
- [x] Analysis caching by lot/plan (shared across users)
- [x] Status polling with progress UI
- [x] LGA (council) lookup via spatial join on QLD LGA boundaries
- [x] Zoning lookup via spatial join on QLD Planning Scheme Zones
- [x] Council and zone display in analysis sidebar
- [x] Blog system (MDX, SSG, category filtering, sitemap)
- [x] 4 seed blog posts covering subdivision, zoning, cadastral surveys, ROL applications
- [x] Rebrand to PropertyProfiler
- [x] Shared site header/footer on public pages

#### In Progress / Next

- [ ] Install CV pipeline dependencies (OpenCV, NumPy, YOLO) so analysis runs end-to-end
- [ ] Source and import QLD LGA boundary data (download from QLD Spatial Catalogue, run `import_qld_lga.py`)
- [ ] Source and import QLD Planning Scheme Zones data (download from QLD Spatial Catalogue, run `import_qld_zones.py`)
- [ ] Council rules reference — static lookup of setbacks, min lot sizes, contacts for top 5 QLD councils
- [ ] Subdivision statistics — SP/RP plan analysis per postcode from cadastre data
- [ ] Static guide pages (`/guides/subdivision-qld`, `/how-it-works`, `/about`)
- [ ] Image display on results page (satellite, styled map, mask overlay)
- [ ] Retry button for failed analyses
- [ ] Elevation / slope analysis (Google Elevation API)
- [ ] Floor plan template positioning (extends existing PropertyMap system)

---

### Phase 2 — Authentication and Saved State

**Goal:** Convert interested users into registered users. Enable professionals to track multiple properties.

**Access model:** Auth required for saving. Core analysis still public.

#### Scope

- NextAuth.js authentication (Google + email)
- User profiles and saved properties
- Save and reload markup annotations (footprints, custom polygons)
- Multi-property dashboard for professionals
- Subdivision journey tracker (step-by-step workflow with completion tracking)
- Property comparison views
- Email notifications for analysis completion
- Paywall design — decide which features require a paid tier

#### Schema already prepared

The Phase 2 tables are defined in `db/migrations/002_application_tables.sql` (commented out): `users`, `user_properties`, `subdivision_assessments`, `subdivision_journeys`, `journey_steps`, `journey_step_completions`.

---

### Phase 3 — Multi-State Expansion

**Goal:** Expand beyond Queensland to NSW, VIC, and other states.

**Approach:** The database schema already has `state` and `jurisdiction` columns throughout. Import scripts are named with `qld_` prefix by convention — NSW/VIC equivalents slot in without schema changes.

**Data required per new state:**
- Cadastre parcel data (equivalent of DCDB)
- Planning scheme zones (state-wide or council-by-council)
- LGA boundaries
- Pool registry (if available)
- State-specific subdivision process documentation

---

## Feature Prioritisation Rationale

### Why blog first?
SEO takes time to compound. Getting content indexed early means organic traffic by the time the paid features are ready. Blog posts also act as top-of-funnel for the analysis tool.

### Why no auth in Phase 1?
Lower friction = more usage = more validation. Every step a user must take before seeing value (sign up, verify email, fill a profile) is a drop-off point. The Phase 1 goal is to learn whether people find the analysis useful, not to build a user database.

### Why QLD only?
Data availability and consistency. QLD government publishes excellent open data: DCDB cadastre, pool registry, planning zones, LGA boundaries — all free and machine-readable. Other states vary significantly in data quality and availability. Starting with QLD lets the analysis pipeline be well-tuned before expanding.

### Why keep elevation/floor plans for later?
These features require working analysis infrastructure first (so CV pipeline must run end-to-end). They also carry higher implementation risk (Google Elevation API costs per request; floor plan templates require UX iteration). Better to ship core value first.

### Why derive subdivision stats from cadastre rather than buying data?
Historical survey plan lodgements (SP-prefixed plans = subdivisions, RP-prefixed = original surveys) are already in the cadastre data loaded into the database. This gives a free, always-current proxy for subdivision density without needing to pay for or licence title registry data.

---

## What This Is Not

- **Not an investment tool.** No rental yield estimates, capital growth projections, or buy/sell recommendations. Audience is homeowners making decisions about their own land.
- **Not a legal or planning advice service.** All analysis includes disclaimers. Users are directed to consult their council and licensed professionals before acting.
- **Not a real estate search platform.** No listing data, no sale prices, no auction results.

---

## Key Data Sources

| Dataset | Source | License | Coverage |
|---|---|---|---|
| GNAF (addresses) | data.gov.au | CC BY 4.0 | All states |
| QLD Cadastre (DCDB) | data.qld.gov.au | CC BY 4.0 | QLD |
| QLD Pool Registry | data.qld.gov.au | CC BY 4.0 | QLD |
| QLD LGA Boundaries | qldspatial.information.qld.gov.au | CC BY 4.0 | QLD |
| QLD Planning Scheme Zones | qldspatial.information.qld.gov.au | CC BY 4.0 | QLD |
| Satellite imagery | Google Maps Static API | Paid per request | Global |
| Elevation | Google Maps Elevation API | Paid per request | Global |
| Street View | Google Maps Street View API | Paid per request | Global |
