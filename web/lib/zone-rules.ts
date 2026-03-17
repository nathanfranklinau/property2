/**
 * Static lookup of common QLD residential zone rules.
 *
 * Zone codes vary between councils but follow similar patterns.
 * This maps common zone name patterns to human-readable implications.
 * Values are approximate — always verify against the specific council's planning scheme.
 */

export type ZoneRules = {
  description: string;
  minLotSizeSqm: number | null;
  maxStoreys: number | null;
  maxSiteCover: number | null; // fraction, e.g. 0.50 = 50%
  permittedUses: string[];
  subdivisionNotes: string;
};

/**
 * Match a zone name (from qld_planning_zones) to rules.
 * Uses substring matching since exact names vary between councils.
 */
export function getZoneRules(zoneName: string | null): ZoneRules | null {
  if (!zoneName) return null;
  const lower = zoneName.toLowerCase();

  for (const [pattern, rules] of ZONE_PATTERNS) {
    if (lower.includes(pattern)) return rules;
  }

  return null;
}

const ZONE_PATTERNS: [string, ZoneRules][] = [
  [
    "low density residential",
    {
      description:
        "Suburban residential areas with detached houses on individual lots.",
      minLotSizeSqm: 400,
      maxStoreys: 2,
      maxSiteCover: 0.50,
      permittedUses: [
        "Dwelling house",
        "Home-based business",
        "Secondary dwelling (some councils)",
      ],
      subdivisionNotes:
        "Subdivision generally code-assessable. Both new and remaining lots must meet minimum lot size (typically 400-600 m\u00B2).",
    },
  ],
  [
    "medium density residential",
    {
      description:
        "Areas for townhouses, duplexes, and small unit blocks at higher density.",
      minLotSizeSqm: 300,
      maxStoreys: 3,
      maxSiteCover: 0.50,
      permittedUses: [
        "Dwelling house",
        "Dual occupancy",
        "Multiple dwelling",
        "Townhouses",
      ],
      subdivisionNotes:
        "Smaller minimum lot sizes apply. Higher density development generally encouraged.",
    },
  ],
  [
    "character residential",
    {
      description:
        "Older suburbs with heritage or character value. Stricter building controls.",
      minLotSizeSqm: 600,
      maxStoreys: 2,
      maxSiteCover: 0.50,
      permittedUses: ["Dwelling house", "Home-based business"],
      subdivisionNotes:
        "Subdivision may be restricted to preserve neighbourhood character. Often requires impact assessment.",
    },
  ],
  [
    "rural residential",
    {
      description:
        "Large lot residential on the urban fringe. Limited subdivision potential.",
      minLotSizeSqm: 2000,
      maxStoreys: 2,
      maxSiteCover: 0.25,
      permittedUses: [
        "Dwelling house",
        "Home-based business",
        "Rural activity",
      ],
      subdivisionNotes:
        "Very large minimum lot sizes (2,000-4,000+ m\u00B2). Subdivision potential is limited.",
    },
  ],
  [
    "emerging community",
    {
      description:
        "Land earmarked for future urban development. Not yet zoned for residential.",
      minLotSizeSqm: null,
      maxStoreys: null,
      maxSiteCover: null,
      permittedUses: ["Existing lawful use"],
      subdivisionNotes:
        "Subdivision generally not permitted until a detailed structure plan is approved.",
    },
  ],
  [
    "general residential",
    {
      description:
        "Standard residential zone allowing a range of housing types.",
      minLotSizeSqm: 400,
      maxStoreys: 3,
      maxSiteCover: 0.50,
      permittedUses: [
        "Dwelling house",
        "Dual occupancy",
        "Multiple dwelling",
      ],
      subdivisionNotes:
        "Code-assessable subdivision typically available. Check minimum lot size for your specific council.",
    },
  ],
  [
    "high density residential",
    {
      description:
        "Areas designated for apartment buildings and high-rise residential.",
      minLotSizeSqm: 800,
      maxStoreys: 8,
      maxSiteCover: 0.50,
      permittedUses: [
        "Multiple dwelling",
        "Short-term accommodation",
        "Residential care facility",
      ],
      subdivisionNotes:
        "Subdivision for individual lots is uncommon. Typically used for strata/community title development.",
    },
  ],
];
