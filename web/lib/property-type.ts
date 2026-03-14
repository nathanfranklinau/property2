/**
 * Property type classification based on cadastre plan prefix and GNAF address data.
 *
 * Plan prefix meanings:
 *   RP/SP  = Registered/Survey Plan (freehold)
 *   BUP    = Building Units Plan (strata apartments/units)
 *   GTP    = Group Title Plan (townhouses/villas)
 *   CP     = Crown Plan (government land)
 *   AP/AG  = Agricultural Plan
 *   MPH/MCH = Mining Purpose/Claim Homestead
 */

export type PropertyType =
  | "house"
  | "multi_dwelling"
  | "unit"
  | "townhouse"
  | "special_tenure";

export type PropertyTypeInfo = {
  type: PropertyType;
  label: string;
  tenure: string;
  allowDrawingTools: boolean;
  allowSubdivision: boolean;
  showComplexBoundary: boolean;
};

const SPECIAL_PREFIXES: Record<string, { label: string; tenure: string }> = {
  CP: { label: "Crown Land", tenure: "crown" },
  AP: { label: "Agricultural Land", tenure: "agricultural" },
  AG: { label: "Agricultural Land", tenure: "agricultural" },
  MPH: { label: "Mining Homestead", tenure: "mining" },
  MCH: { label: "Mining Homestead", tenure: "mining" },
};

export function classifyProperty(
  planPrefix: string | null,
  addressCount: number
): PropertyTypeInfo {
  const prefix = (planPrefix ?? "").toUpperCase();

  // Special tenure (crown, agricultural, mining)
  if (prefix in SPECIAL_PREFIXES) {
    const { label, tenure } = SPECIAL_PREFIXES[prefix];
    return {
      type: "special_tenure",
      label,
      tenure,
      allowDrawingTools: false,
      allowSubdivision: false,
      showComplexBoundary: false,
    };
  }

  // Strata units (BUP)
  if (prefix === "BUP") {
    return {
      type: "unit",
      label: "Unit / Apartment",
      tenure: "strata",
      allowDrawingTools: false,
      allowSubdivision: false,
      showComplexBoundary: true,
    };
  }

  // Group title (GTP) — townhouses, villas
  if (prefix === "GTP") {
    return {
      type: "townhouse",
      label: "Townhouse / Villa",
      tenure: "group_title",
      allowDrawingTools: true,
      allowSubdivision: false,
      showComplexBoundary: true,
    };
  }

  // Freehold with multiple addresses — duplex/dual-occ
  if (addressCount >= 2) {
    return {
      type: "multi_dwelling",
      label: "Multi-Dwelling",
      tenure: "freehold",
      allowDrawingTools: true,
      allowSubdivision: true,
      showComplexBoundary: false,
    };
  }

  // Default — standard house
  return {
    type: "house",
    label: "House",
    tenure: "freehold",
    allowDrawingTools: true,
    allowSubdivision: true,
    showComplexBoundary: false,
  };
}

/** Extract plan prefix (letters before digits) from a plan string like "SP123456" */
export function extractPlanPrefix(plan: string): string | null {
  const match = plan.match(/^[A-Z]+/i);
  return match ? match[0].toUpperCase() : null;
}

/** Badge colour for each property type — aligned with plan-prefix colours on the map (SP=emerald, BUP=indigo, GTP=amber) */
export const PROPERTY_TYPE_COLORS: Record<PropertyType, string> = {
  house: "bg-emerald-500/20 text-emerald-400",        // SP/RP freehold → emerald
  multi_dwelling: "bg-emerald-500/20 text-emerald-400", // SP/RP freehold → emerald
  unit: "bg-indigo-500/20 text-indigo-400",           // BUP → indigo
  townhouse: "bg-amber-500/20 text-amber-400",        // GTP → amber
  special_tenure: "bg-amber-500/20 text-amber-400",
};
