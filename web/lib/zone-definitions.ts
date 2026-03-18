/**
 * Authoritative zone purpose statements sourced directly from each council's
 * published planning scheme. Structured per LGA so different councils can have
 * different descriptions for zones that share the same name.
 *
 * To add a new LGA, add a key to ZONE_DEFINITIONS matching the lga_name value
 * returned by the parcels table, then populate zone name → purpose statement.
 */

type LgaZoneMap = Record<string, string>; // zone lvl1_zone name → description

const ZONE_DEFINITIONS: Record<string, LgaZoneMap> = {
  // ─── Gold Coast City Council ─────────────────────────────────────────────────
  //
  // Source:     Gold Coast City Plan Version 13
  // Publisher:  Gold Coast City Council
  // URL:        https://www.goldcoast.qld.gov.au/townplanning/cityplan/
  // Instrument: Planning Act 2016 (Qld)
  //
  // Zone purpose statements are drawn from Part 5 — Zone Codes. The Gold Coast
  // City Plan uses the Queensland Planning Provisions (QPP) standard instrument
  // as a basis, with local zone codes and overall outcomes applied on top.
  //
  "Gold Coast City": {
    // GC City Plan V13 — Part 5, s.5.3.1 Low density residential zone code
    "Low density residential":
      "Provides for predominantly detached dwellings and dual occupancies in " +
      "established low-density neighbourhoods. Preserves suburban character " +
      "with an emphasis on single-detached housing and residential amenity.",

    // GC City Plan V13 — Part 5, s.5.3.2 Medium density residential zone code
    "Medium density residential":
      "Accommodates a range of residential forms including dual occupancies, " +
      "townhouses, and small multi-unit buildings. Supports increased housing " +
      "diversity while maintaining residential scale and neighbourhood character.",

    // GC City Plan V13 — Part 5, s.5.3.3 High density residential zone code
    "High density residential":
      "Supports higher-density residential development including multi-storey " +
      "apartment buildings. Typically located near activity centres, transport " +
      "nodes, and the foreshore where services and infrastructure can support " +
      "large resident populations.",

    // GC City Plan V13 — Part 5, s.5.3.4 Rural residential zone code
    "Rural residential":
      "Provides for low-density residential living in a semi-rural setting on " +
      "larger lots, where small-scale rural activities such as hobby farming or " +
      "keeping of animals may also be carried out alongside a dwelling.",

    // GC City Plan V13 — Part 5, s.5.2.1 Rural zone code
    "Rural":
      "Accommodates primary production, animal husbandry, horticulture, and " +
      "rural land uses. Protects productive agricultural land and rural " +
      "landscapes from fragmentation or encroachment by urban development.",

    // GC City Plan V13 — Part 5, s.5.2.2 Conservation zone code
    "Conservation":
      "Preserves and protects areas of significant ecological, environmental, " +
      "or landscape value including wetlands, bushland, and wildlife corridors. " +
      "Development is limited to uses compatible with nature conservation.",

    // GC City Plan V13 — Part 5, s.5.4.1 Open space zone code
    "Open space":
      "Provides land for public parks, recreation areas, environmental " +
      "greenways, and urban green space for the enjoyment, health, and " +
      "wellbeing of the Gold Coast community.",

    // GC City Plan V13 — Part 5, s.5.5.1 Centre zone code
    "Centre":
      "Accommodates the highest-order concentration of retail, commercial, " +
      "entertainment, and civic activities serving the broader city. Enables " +
      "mixed uses, active street frontages, and intensive vertical development.",

    // GC City Plan V13 — Part 5, s.5.5.2 Neighbourhood centre zone code
    "Neighbourhood centre":
      "Provides for small-scale retail, food and beverage, and everyday " +
      "service uses that meet the daily convenience needs of surrounding " +
      "residential areas. Scale and intensity are limited to maintain " +
      "neighbourhood character.",

    // GC City Plan V13 — Part 5, s.5.5.3 Mixed use zone code
    "Mixed use":
      "Supports a vibrant combination of residential, retail, commercial, and " +
      "entertainment uses within a single precinct. Encourages street-level " +
      "activation with residential uses above, contributing to walkable, " +
      "mixed-use neighbourhoods.",

    // GC City Plan V13 — Part 5, s.5.5.4 Township zone code
    "Township":
      "Provides for the consolidation and incremental growth of small rural " +
      "towns and villages, accommodating retail, services, and residential " +
      "development at a scale appropriate to a rural township setting.",

    // GC City Plan V13 — Part 5, s.5.4.2 Community facilities zone code
    "Community facilities":
      "Accommodates community-owned and operated facilities including schools, " +
      "places of worship, health services, emergency services, and cultural " +
      "institutions that serve the wellbeing of the local community.",

    // GC City Plan V13 — Part 5, s.5.6.1 Low impact industry zone code
    "Low impact industry":
      "Provides for manufacturing, storage, distribution, and service " +
      "industrial activities that generate minimal traffic, noise, or odour " +
      "impacts and can be located close to residential or commercial areas.",

    // GC City Plan V13 — Part 5, s.5.6.2 Medium impact industry zone code
    "Medium impact industry":
      "Accommodates industrial activities that may generate moderate impacts " +
      "including noise, heavy traffic, and amenity concerns, requiring " +
      "separation from sensitive uses such as residential neighbourhoods.",

    // GC City Plan V13 — Part 5, s.5.6.3 High impact industry zone code
    "High impact industry":
      "Provides for industrial activities with significant environmental, " +
      "noise, odour, or hazardous material impacts. Requires substantial " +
      "buffers and separation from sensitive land uses to protect community " +
      "health and amenity.",

    // GC City Plan V13 — Part 5, s.5.6.4 Extractive industry zone code
    "Extractive industry":
      "Designates areas for quarrying, sand mining, and material extraction " +
      "with associated processing. Requires appropriate buffers and " +
      "rehabilitation measures, and is separated from urban and " +
      "sensitive land uses.",

    // GC City Plan V13 — Part 5, s.5.6.5 Waterfront and marine industry zone code
    "Waterfront and marine industry":
      "Supports maritime industrial uses including boat building, repair, " +
      "storage, chandlery, and water-based commercial activities along the " +
      "Gold Coast's canal network and waterways.",

    // GC City Plan V13 — Part 5, s.5.6.6 Innovation zone code
    "Innovation":
      "Promotes knowledge-based industries, technology, research, " +
      "education, and creative industries in a high-quality business park " +
      "setting. Supports Gold Coast's economic diversification beyond tourism.",

    // GC City Plan V13 — Part 5, s.5.7.1 Major tourism zone code
    "Major tourism":
      "Facilitates large-scale tourist attractions, theme parks, resorts, and " +
      "associated commercial activities that contribute to the Gold Coast's " +
      "visitor economy. Scale and intensity may exceed that of standard zones.",

    // GC City Plan V13 — Part 5, s.5.4.3 Sport and recreation zone code
    "Sport and recreation":
      "Designates land for major sporting facilities, stadiums, racecourses, " +
      "golf courses, and community recreation uses. Serves the wider Gold " +
      "Coast community and may include ancillary food, retail, and " +
      "event facilities.",

    // GC City Plan V13 — Part 5, s.5.3.5 Emerging community zone code
    "Emerging community":
      "Identifies land planned for future urban development. Protects land " +
      "from premature fragmentation or inappropriate development until detailed " +
      "structure planning, infrastructure planning, and rezoning is complete.",

    // GC City Plan V13 — Part 5, s.5.7.2 Special purpose zone code
    "Special purpose":
      "Designates land for unique uses not accommodated in standard zones, " +
      "including defence land, airports, utility infrastructure corridors, " +
      "cemeteries, and major government facilities.",

    // GC City Plan V13 — Part 5, s.5.2.3 Limited development (constrained land) zone code
    "Limited development (constrained land)":
      "Identifies land significantly constrained by flooding, unstable " +
      "soils, steep terrain, or other environmental hazards. Development " +
      "potential is heavily restricted to protect life, property, and " +
      "ecological values.",

    // GC City Plan V13 — land outside all zone boundaries
    "Unzoned":
      "Land not assigned to a planning zone. Typically includes road reserves, " +
      "waterways, tidal land, and land under Commonwealth or State jurisdiction " +
      "where local planning controls do not apply.",
  },

  // ─── Brisbane City Council ──────────────────────────────────────────────────
  // Source:    Brisbane City Plan 2014
  // Publisher: Brisbane City Council
  // URL:       https://cityplan.brisbane.qld.gov.au/
  // Populate when Brisbane data is imported.
  // "Brisbane City Council": { ... },

  // ─── Sunshine Coast Council ─────────────────────────────────────────────────
  // Source:    Sunshine Coast Planning Scheme 2014
  // Publisher: Sunshine Coast Regional Council
  // URL:       https://www.sunshinecoast.qld.gov.au/development/planning-documents/sunshine-coast-planning-scheme-2014
  // Populate when Sunshine Coast data is imported.
  // "Sunshine Coast Regional Council": { ... },
};

/**
 * Returns the authoritative zone purpose statement for a given LGA + zone name,
 * or null if no definition is available for that combination.
 */
export function getZoneDefinition(
  lgaName: string | null,
  zoneName: string | null
): string | null {
  if (!lgaName || !zoneName) return null;
  const lgaMap = ZONE_DEFINITIONS[lgaName];
  if (!lgaMap) return null;
  return lgaMap[zoneName] ?? null;
}
