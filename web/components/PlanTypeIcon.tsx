/**
 * Plan type icons and helpers for QLD cadastre plan prefix classification.
 *
 * The plan prefix (letters before the digits in a plan number) tells you
 * what kind of land registration the lot has — which directly determines
 * subdivision eligibility.
 *
 * Prefix reference:
 *   RP / SP  → Registered Plan / Survey Plan  → Freehold, subdivisible
 *   BUP      → Building Units Plan            → Body corporate strata, NOT subdivisible
 *   GTP      → Group Title Plan               → Townhouse/group title, NOT subdivisible
 *   CP       → Crown Plan                     → Government/Crown land
 *   AP / AG  → Agricultural Plan / Holding    → Rural/agricultural land
 *   NR       → Nature Refuge                  → Protected land
 *   MPH/MCH  → Mining homesteads              → Special mining tenure
 *
 * ── Named exports ───────────────────────────────────────────────────────────
 *
 * Types / data:
 *   PlanRegistration         — union type of all registration categories
 *   IconProps                — { className?: string } shared by every icon
 *   getPlanRegistration()    — parse a raw plan string → PlanRegistration
 *   PLAN_REGISTRATION_INFO   — labels, descriptions, colours, subdivisibility
 *   ICON_MAP                 — map PlanRegistration → icon component
 *
 * Individual icons (use when you need a specific icon without a plan string):
 *   FreeholdIcon             — RP / SP  — detached house on lot
 *   StrataUnitsIcon          — BUP      — apartment block
 *   GroupTitleIcon           — GTP      — terraced townhouses
 *   CrownIcon                — CP       — three-pointed crown
 *   RuralIcon                — AP/NR/AG — farm paddock fence
 *   UnknownIcon              — ?        — diamond with question mark
 *
 * Smart wrapper (resolves icon from a raw plan string automatically):
 *   PlanTypeIcon             — <PlanTypeIcon plan="RP79217" className="w-5 h-5" />
 */

export type PlanRegistration =
  | "freehold"
  | "strata_units"
  | "group_title"
  | "crown"
  | "rural"
  | "unknown";

/** Extract the plan type registration from a plan string like "RP79217" or "BUP100650". */
export function getPlanRegistration(plan: string): PlanRegistration {
  const prefix = plan.replace(/[0-9].*$/, "").toUpperCase();
  switch (prefix) {
    case "RP":
    case "SP":
      return "freehold";
    case "BUP":
      return "strata_units";
    case "GTP":
      return "group_title";
    case "CP":
      return "crown";
    case "AP":
    case "AG":
    case "NR":
    case "MPH":
    case "MCH":
      return "rural";
    default:
      return "unknown";
  }
}

export const PLAN_REGISTRATION_INFO: Record<
  PlanRegistration,
  {
    label: string;
    shortLabel: string;
    description: string;
    subdivisible: boolean;
    color: string; // tailwind text color
  }
> = {
  freehold: {
    label: "Freehold Land",
    shortLabel: "RP / SP",
    description:
      "Individually owned lot on a registered or survey plan. Primary candidate for subdivision.",
    subdivisible: true,
    color: "text-emerald-400",
  },
  strata_units: {
    label: "Building Units Plan",
    shortLabel: "BUP",
    description:
      "Body corporate strata title — a unit in an apartment block or multi-dwelling complex. Cannot be further subdivided.",
    subdivisible: false,
    color: "text-indigo-400",
  },
  group_title: {
    label: "Group Title Plan",
    shortLabel: "GTP",
    description:
      "Group title — townhouses or villas sharing common property under a body corporate. Not individually subdivisible.",
    subdivisible: false,
    color: "text-amber-400",
  },
  crown: {
    label: "Crown Land",
    shortLabel: "CP",
    description:
      "State government (Crown) land. Cannot be subdivided by private owners.",
    subdivisible: false,
    color: "text-sky-400",
  },
  rural: {
    label: "Rural / Agricultural",
    shortLabel: "AP / NR",
    description:
      "Agricultural, nature refuge, or mining tenure land. Subdivision rules vary significantly — consult the local planning scheme.",
    subdivisible: false, // not in the typical residential sense
    color: "text-lime-400",
  },
  unknown: {
    label: "Unknown Plan Type",
    shortLabel: "—",
    description:
      "Unrecognised plan prefix. Verify property type with your council or a property solicitor.",
    subdivisible: false,
    color: "text-zinc-400",
  },
};

// ─── Icon components ──────────────────────────────────────────────────────

/**
 * Props shared by every plan type icon.
 *
 * @example
 * <FreeholdIcon className="w-5 h-5 text-emerald-400" />
 */
export interface IconProps {
  /** Any Tailwind (or other) class string — typically a size + colour utility. */
  className?: string;
}

/**
 * RP / SP — Freehold detached house on its own lot.
 *
 * Design: gabled roof + walls + door, sitting on a ground line with
 * corner ticks at the edges — the ticks indicate the lot boundary
 * extends beyond the house footprint (free space either side).
 *
 * @example
 * // Standalone
 * <FreeholdIcon className="w-6 h-6 text-emerald-400" />
 * // Via smart wrapper
 * <PlanTypeIcon plan="RP79217" className="w-6 h-6" />
 */
export function FreeholdIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/* Gabled roof */}
      <path d="M2 12L12 3l10 9" />
      {/* Walls — open at base (ground line acts as the floor) */}
      <path d="M4 12v9h16v-9" />
      {/* Door — open at bottom so it meets the ground line */}
      <path d="M10 21v-5.5h4V21" />
      {/* Ground line — extends wider than the house (shows the full lot width) */}
      <line x1="1" y1="21" x2="23" y2="21" />
      {/* Corner boundary markers — ticks down from the ground line */}
      <line x1="1" y1="21" x2="1" y2="23.5" />
      <line x1="23" y1="21" x2="23" y2="23.5" />
    </svg>
  );
}

/**
 * BUP — Building Units Plan (body corporate apartment block).
 *
 * Design: flat-topped multi-storey rectangular building (no gabled roof —
 * the flat top distinguishes it instantly from the freehold house).
 * Three floors with a 2-column window grid; centre door at ground level.
 *
 * @example
 * // Standalone
 * <StrataUnitsIcon className="w-6 h-6 text-amber-400" />
 * // Via smart wrapper
 * <PlanTypeIcon plan="BUP100650" className="w-6 h-6" />
 */
export function StrataUnitsIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/* Building outline — flat top */}
      <rect x="3" y="2.5" width="18" height="19" rx="1" />
      {/* Horizontal floor dividers */}
      <line x1="3" y1="9" x2="21" y2="9" />
      <line x1="3" y1="15.5" x2="21" y2="15.5" />
      {/* Top-floor windows: 2 side by side */}
      <rect x="5.5" y="4.5" width="4" height="3" rx="0.5" />
      <rect x="14.5" y="4.5" width="4" height="3" rx="0.5" />
      {/* Mid-floor windows: same layout */}
      <rect x="5.5" y="11" width="4" height="3" rx="0.5" />
      <rect x="14.5" y="11" width="4" height="3" rx="0.5" />
      {/* Ground floor: central door (open at base) */}
      <path d="M10.5 21.5V18H13.5V21.5" />
    </svg>
  );
}

/**
 * GTP — Group Title Plan (terraced townhouses).
 *
 * Design: three connected peaked roofs sharing walls — the classic
 * row-house / terraced-house silhouette. Shared interior party walls
 * run vertically between the three units.
 *
 * @example
 * // Standalone
 * <GroupTitleIcon className="w-6 h-6 text-amber-400" />
 * // Via smart wrapper
 * <PlanTypeIcon plan="GTP11204" className="w-6 h-6" />
 */
export function GroupTitleIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/*
       * Three connected townhouse peaks as one continuous outer profile.
       * Peaks at x=5, x=12, x=19 (y=6); valley points at x=9, x=15 (y=12).
       * Left outer wall from (1,20) rises to peak at (5,6) then descends.
       */}
      <path d="M1 20V12L5 6L9 12L12 6L15 12L19 6L23 12V20H1Z" />
      {/* Interior party walls (shared) — mark unit boundaries */}
      <line x1="9" y1="12" x2="9" y2="20" />
      <line x1="15" y1="12" x2="15" y2="20" />
      {/* Doors — one per unit */}
      <path d="M3.5 20v-5h3v5" />
      <path d="M10.5 20v-5h3v5" />
      <path d="M17.5 20v-5h3v5" />
    </svg>
  );
}

/**
 * CP — Crown Plan (government / Crown land).
 *
 * Design: a classic three-pointed crown sitting on a rectangular band/base.
 * The crown is universally understood as a government/state emblem.
 * Three jewel circles mark the tip of each crown point.
 *
 * @example
 * // Standalone
 * <CrownIcon className="w-6 h-6 text-sky-400" />
 * // Via smart wrapper
 * <PlanTypeIcon plan="CP123456" className="w-6 h-6" />
 */
export function CrownIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/* Crown band / base rectangle */}
      <rect x="2.5" y="18" width="19" height="3.5" rx="0.5" />
      {/*
       * Crown points:
       *   Left to right — outer left at (3,18), rises to left-side jewel at (4,13),
       *   descends to inner-left valley (8,17), rises to centre jewel at (12,8),
       *   descends to inner-right valley (16,17), rises to right-side jewel at (20,13),
       *   descends to outer right at (21,18).
       */}
      <path d="M3 18L4 13L8 17L12 8L16 17L20 13L21 18" />
      {/* Jewel at centre-top (largest) */}
      <circle cx="12" cy="8" r="1.25" fill="currentColor" stroke="none" />
      {/* Jewels at left and right points */}
      <circle cx="4" cy="13" r="1" fill="currentColor" stroke="none" />
      <circle cx="20" cy="13" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

/**
 * AP / NR / AG — Rural, agricultural, or nature refuge land.
 *
 * Design: three wooden fence posts (vertical lines with T-cap crosspieces)
 * with two horizontal rails running between them — the classic farm paddock
 * fence silhouette. A ground line extends to property boundary corner markers
 * (survey pegs) wider than the fence itself, indicating open land beyond.
 * Three posts give enough detail to read as "fence" without crowding.
 *
 * @example
 * // Standalone
 * <RuralIcon className="w-6 h-6 text-lime-400" />
 * // Via smart wrapper
 * <PlanTypeIcon plan="AP12345" className="w-6 h-6" />
 */
export function RuralIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/* Fence posts — left, centre, right */}
      <line x1="4"  y1="6" x2="4"  y2="19" />
      <line x1="12" y1="6" x2="12" y2="19" />
      <line x1="20" y1="6" x2="20" y2="19" />
      {/* T-cap crosspieces at the top of each post */}
      <line x1="2"  y1="6" x2="6"  y2="6" />
      <line x1="10" y1="6" x2="14" y2="6" />
      <line x1="18" y1="6" x2="22" y2="6" />
      {/* Two horizontal rails spanning all three posts */}
      <line x1="4" y1="11.5" x2="20" y2="11.5" />
      <line x1="4" y1="17"   x2="20" y2="17"   />
      {/* Ground / horizon line — wider than the fence to suggest open paddock */}
      <line x1="1" y1="21" x2="23" y2="21" />
      {/* Corner survey-peg markers */}
      <line x1="1" y1="19" x2="1" y2="23" />
      <line x1="23" y1="19" x2="23" y2="23" />
    </svg>
  );
}

/**
 * Unknown — unrecognised plan prefix.
 *
 * Design: a diamond/lozenge with a question mark — the standard
 * "unknown / caution" symbol. Used when the prefix doesn't match
 * any known QLD plan type.
 *
 * @example
 * // Standalone
 * <UnknownIcon className="w-6 h-6 text-zinc-400" />
 * // Via smart wrapper (any unrecognised prefix)
 * <PlanTypeIcon plan="XY0001" className="w-6 h-6" />
 */
export function UnknownIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/* Diamond outline */}
      <path d="M12 2L22 12L12 22L2 12L12 2Z" />
      {/* Question mark stem */}
      <path d="M12 16v.5" strokeWidth={2} />
      {/* Question mark arc */}
      <path d="M9.5 9.5a2.5 2.5 0 014.9.8c0 2-2.9 2.5-2.9 4.2" />
    </svg>
  );
}

// ─── Map from registration type to icon component ─────────────────────────

/**
 * Lookup table from registration category to its icon component.
 * Useful when you already know the registration type and don't want
 * to go through the `PlanTypeIcon` wrapper.
 *
 * @example
 * const Icon = ICON_MAP['freehold'];
 * return <Icon className="w-5 h-5 text-emerald-400" />;
 */
export const ICON_MAP: Record<PlanRegistration, React.ComponentType<IconProps>> = {
  freehold: FreeholdIcon,
  strata_units: StrataUnitsIcon,
  group_title: GroupTitleIcon,
  crown: CrownIcon,
  rural: RuralIcon,
  unknown: UnknownIcon,
};

// ─── Public component ─────────────────────────────────────────────────────

interface PlanTypeIconProps {
  /** The raw plan string from the cadastre, e.g. "RP79217" or "BUP100650". */
  plan: string;
  /** Tailwind size class passed to the svg. Defaults to "w-4 h-4". */
  className?: string;
}

/**
 * Renders an icon representing the plan registration type for a given
 * cadastral plan string. Parses the prefix automatically.
 *
 * @example
 * <PlanTypeIcon plan="RP79217" className="w-5 h-5" />
 * <PlanTypeIcon plan="BUP100650" className="w-3.5 h-3.5 text-amber-400" />
 */
export function PlanTypeIcon({ plan, className = "w-4 h-4" }: PlanTypeIconProps) {
  const registration = getPlanRegistration(plan);
  const Icon = ICON_MAP[registration];
  return <Icon className={className} />;
}
