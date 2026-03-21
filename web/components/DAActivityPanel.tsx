"use client";

import { useState } from "react";
import type { DevelopmentApplication } from "@/app/api/analysis/das/route";
import type { NearbyDA } from "@/app/api/analysis/nearby-das/route";

// ─── Type helpers ────────────────────────────────────────────────────────────

/** Normalised status bucket */
function statusBucket(status: string | null): "approved" | "current" | "refused" | "withdrawn" | "lapsed" | "other" {
  if (!status) return "other";
  const s = status.toLowerCase();
  if (s.includes("approved") || s.includes("decision made")) return "approved";
  if (s.includes("refused")) return "refused";
  if (s.includes("withdrawn")) return "withdrawn";
  if (s.includes("lapsed")) return "lapsed";
  if (s.includes("current") || s.includes("pending") || s.includes("assessment") || s.includes("lodged")) return "current";
  return "other";
}

function statusLabel(status: string | null): string {
  return status ?? "Unknown";
}

const STATUS_STYLES: Record<string, string> = {
  approved:   "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25",
  current:    "bg-amber-500/15 text-amber-400 border border-amber-500/25",
  refused:    "bg-red-500/15 text-red-400 border border-red-500/25",
  withdrawn:  "bg-zinc-600/30 text-zinc-400 border border-zinc-600/30",
  lapsed:     "bg-zinc-600/30 text-zinc-400 border border-zinc-600/30",
  other:      "bg-zinc-600/20 text-zinc-400 border border-zinc-600/25",
};

const STATUS_DOT: Record<string, string> = {
  approved:  "bg-emerald-400",
  current:   "bg-amber-400 animate-pulse",
  refused:   "bg-red-400",
  withdrawn: "bg-zinc-500",
  lapsed:    "bg-zinc-500",
  other:     "bg-zinc-500",
};

// ─── DA type metadata ─────────────────────────────────────────────────────────

type DATypeMeta = {
  label: string;
  shortLabel: string;
  color: string;          // Tailwind text colour
  mapColor: string;       // Hex for Google Maps marker
  icon: React.ReactNode;
  tooltip: string;
};

function daTypeMeta(appType: string | null): DATypeMeta {
  const t = (appType ?? "").toUpperCase().trim();

  // MCU — Material Change of Use
  if (t.includes("MATERIAL CHANGE") || t === "MCU") return {
    label: "Material Change of Use",
    shortLabel: "MCU",
    color: "text-blue-400",
    mapColor: "#3b82f6",
    icon: <MCUIcon />,
    tooltip: "A DA required when starting a new land use, restarting an abandoned use, or significantly increasing the scale of an existing use. Planning Act 2016 (Qld), Schedule 2.",
  };

  // ROL — Reconfiguring a Lot
  if (t.includes("RECONFIGUR") || t === "ROL") return {
    label: "Reconfiguring a Lot",
    shortLabel: "ROL",
    color: "text-purple-400",
    mapColor: "#a855f7",
    icon: <ROLIcon />,
    tooltip: "Covers subdividing land into new lots, combining lots, realigning boundaries, or creating a new access easement. Planning Act 2016 (Qld), Schedule 2.",
  };

  // OPW — Operational Works (and subtypes)
  if (t.includes("OPERATIONAL") || t === "OPW" || t.includes("GROUND ANCHOR") || t.includes("VEHICLE") || t.includes("VXO") || t.includes("TREE WORK")) return {
    label: "Operational Works",
    shortLabel: t.includes("VEHICLE") || t.includes("VXO") ? "VXO" : t.includes("GROUND ANCHOR") ? "Ground Anchors" : "OPW",
    color: "text-orange-400",
    mapColor: "#f97316",
    icon: <OPWIcon />,
    tooltip: "Physical changes to land not covered by building or plumbing approvals — earthworks, tree clearing, driveways, landscaping, infrastructure. Planning Act 2016 (Qld), Schedule 2.",
  };

  // Tidal / Pontoon
  if (t.includes("TIDAL") || t.includes("PONTOON") || t.includes("SEAWALL") || t.includes("JETTY") || t.includes("MARINA")) return {
    label: "Prescribed Tidal Works",
    shortLabel: "Tidal",
    color: "text-cyan-400",
    mapColor: "#06b6d4",
    icon: <TidalIcon />,
    tooltip: "Works built or demolished in tidal water — jetties, pontoons, seawalls, boat ramps — assessed under the Coastal Protection and Management Regulation 2017.",
  };

  // Minor Change
  if (t.includes("MINOR CHANGE") || t.includes("MINOR CHANGE TO APPROVAL")) return {
    label: "Minor Change",
    shortLabel: "Minor Change",
    color: "text-teal-400",
    mapColor: "#14b8a6",
    icon: <MinorChangeIcon />,
    tooltip: "A modest modification to an existing development approval that does not result in substantially different development. No public notification required. Planning Act 2016 (Qld), s.78.",
  };

  // Extension of Approval
  if (t.includes("EXTENSION") || t.includes("CURRENCY")) return {
    label: "Extension of Approval",
    shortLabel: "Extension",
    color: "text-zinc-400",
    mapColor: "#71717a",
    icon: <ExtensionIcon />,
    tooltip: "An application to extend the period within which a development approval must be acted on before it lapses. Planning Act 2016 (Qld), s.86.",
  };

  // Combined Application
  if (t.includes("COMBINED")) return {
    label: "Combined Application",
    shortLabel: "Combined",
    color: "text-indigo-400",
    mapColor: "#6366f1",
    icon: <CombinedIcon />,
    tooltip: "A single DA covering two or more development types assessed together in one process. Planning Act 2016 (Qld), s.51.",
  };

  // Express DA
  if (t.includes("EXPRESS")) return {
    label: "Express DA",
    shortLabel: "Express",
    color: "text-yellow-400",
    mapColor: "#eab308",
    icon: <ExpressIcon />,
    tooltip: "A fast-track council process for simple, code-assessable DAs decided within 10–15 business days instead of the standard 45.",
  };

  // PDA
  if (t.includes("PRIORITY DEVELOPMENT") || t.includes("PDA") || t.includes("ROBINA")) return {
    label: "Priority Development Area",
    shortLabel: "PDA",
    color: "text-violet-400",
    mapColor: "#8b5cf6",
    icon: <PDAIcon />,
    tooltip: "Development assessed under a State-declared Priority Development Area scheme, administered by Economic Development Queensland rather than council.",
  };

  // Superseded
  if (t.includes("SUPERSEDED")) return {
    label: "Superseded Planning Scheme",
    shortLabel: "Superseded",
    color: "text-zinc-400",
    mapColor: "#71717a",
    icon: <ExtensionIcon />,
    tooltip: "Application to have a DA assessed under the previous planning scheme if it was recently replaced or amended. Planning Act 2016 (Qld), s.29.",
  };

  // Fallback
  return {
    label: appType ?? "Development Application",
    shortLabel: appType ?? "DA",
    color: "text-zinc-400",
    mapColor: "#71717a",
    icon: <GenericDAIcon />,
    tooltip: "A development application lodged with Gold Coast City Council.",
  };
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function MCUIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 21h18M3 7l9-4 9 4M4 21V7M20 21V7" />
      <rect x="9" y="13" width="6" height="8" />
      <path d="M14 9.5l3 3-3 3" /><path d="M7 12.5h7.5" />
    </svg>
  );
}

function ROLIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="2" y="3" width="20" height="18" rx="1" />
      <line x1="12" y1="3" x2="12" y2="21" />
      <line x1="2" y1="12" x2="22" y2="12" />
    </svg>
  );
}

function OPWIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

function TidalIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 18c2-2 4-2 6 0s4 2 6 0 4-2 6 0" />
      <path d="M3 13c2-2 4-2 6 0s4 2 6 0 4-2 6 0" />
      <path d="M12 3v6" /><path d="M9 6l3-3 3 3" />
    </svg>
  );
}

function MinorChangeIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z" />
    </svg>
  );
}

function ExtensionIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function CombinedIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="2" y="3" width="8" height="8" rx="1" /><rect x="14" y="3" width="8" height="8" rx="1" />
      <rect x="2" y="13" width="8" height="8" rx="1" /><rect x="14" y="13" width="8" height="8" rx="1" />
    </svg>
  );
}

function ExpressIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />
    </svg>
  );
}

function PDAIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

function GenericDAIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
      <path d="M9 12h6M9 16h4" />
    </svg>
  );
}

// ─── Utility ──────────────────────────────────────────────────────────────────

function formatDate(d: string | null): string {
  if (!d) return "—";
  const dt = new Date(d);
  if (isNaN(dt.getTime())) return d;
  return dt.toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}

function formatYear(d: string | null): string {
  if (!d) return "—";
  return new Date(d).getFullYear().toString();
}

function epathwayUrl(epathwayId: number | null, applicationNumber: string | null): string | null {
  if (epathwayId) return `https://epathway.goldcoast.qld.gov.au/epathway/Index.aspx?app=73&appId=${epathwayId}`;
  if (applicationNumber) return `https://epathway.goldcoast.qld.gov.au/epathway/Index.aspx?app=73`;
  return null;
}

// ─── DA detail row (expandable) ───────────────────────────────────────────────

function DARow({ da }: { da: DevelopmentApplication }) {
  const [expanded, setExpanded] = useState(false);
  const meta = daTypeMeta(da.application_type);
  const bucket = statusBucket(da.status);
  const link = epathwayUrl(da.epathway_id, da.application_number);

  // Build description summary
  const descParts: string[] = [];
  if (da.dwelling_type) descParts.push(da.dwelling_type);
  if (da.unit_count && da.unit_count > 1) descParts.push(`${da.unit_count} units`);
  if (da.lot_split_from && da.lot_split_to) descParts.push(`${da.lot_split_from}→${da.lot_split_to} lots`);
  const summaryText = descParts.length > 0
    ? descParts.join(" · ")
    : (da.description ?? da.location_address ?? "—");

  return (
    <div className="border border-zinc-800 rounded-lg overflow-hidden">
      {/* Header row — always visible */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-3 py-2.5 flex items-start gap-2.5 hover:bg-zinc-800/50 transition-colors"
      >
        {/* Type icon */}
        <span className={`mt-0.5 flex-shrink-0 ${meta.color}`}>{meta.icon}</span>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className={`text-[10px] font-semibold tracking-wide uppercase ${meta.color}`}>
              {meta.shortLabel}
            </span>
            {da.assessment_level && (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-700/60 text-zinc-400 uppercase tracking-wide">
                {da.assessment_level}
              </span>
            )}
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium flex items-center gap-1 ${STATUS_STYLES[bucket]}`}>
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${STATUS_DOT[bucket]}`} />
              {statusLabel(da.status)}
            </span>
            <span className="ml-auto text-[10px] text-zinc-500 flex-shrink-0">{formatYear(da.lodgement_date)}</span>
          </div>
          <p className="text-xs text-zinc-300 mt-1 line-clamp-1 leading-tight">{summaryText}</p>
        </div>

        {/* Expand chevron */}
        <span className={`mt-1 flex-shrink-0 text-zinc-600 transition-transform ${expanded ? "rotate-180" : ""}`}>
          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </span>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-zinc-800 px-3 py-2.5 space-y-2 bg-zinc-900/50">
          {/* Full description */}
          {da.description && (
            <p className="text-[11px] text-zinc-300 leading-relaxed">{da.description}</p>
          )}

          {/* Key-value grid */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            <DetailRow label="Application" value={da.application_number} mono />
            <DetailRow label="Lodged" value={formatDate(da.lodgement_date)} />
            {da.decision_date && <DetailRow label="Decision" value={formatDate(da.decision_date)} />}
            {da.decision_type && <DetailRow label="Decision type" value={da.decision_type} />}
            {da.decision_authority && <DetailRow label="Authority" value={da.decision_authority} />}
            {da.responsible_officer && <DetailRow label="Officer" value={da.responsible_officer} />}
            {da.suburb && <DetailRow label="Suburb" value={da.suburb} />}
            {da.location_address && <DetailRow label="Address" value={da.location_address} />}
          </div>

          {/* Milestone timeline */}
          <MilestoneTimeline da={da} />

          {/* ePathway link */}
          {link && (
            <a
              href={link}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 flex items-center gap-1.5 text-[11px] text-emerald-400 hover:text-emerald-300 transition-colors"
            >
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
              </svg>
              View on ePathway
            </a>
          )}
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="text-[9px] text-zinc-600 uppercase tracking-wider leading-none mb-0.5">{label}</p>
      <p className={`text-[11px] text-zinc-300 leading-tight ${mono ? "font-mono" : ""}`}>{value}</p>
    </div>
  );
}

function MilestoneTimeline({ da }: { da: DevelopmentApplication }) {
  const milestones: { label: string; date: string | null }[] = [
    { label: "Pre-assessment", date: da.pre_assessment_completed },
    { label: "Confirmation notice", date: da.confirmation_notice_completed },
    { label: "Decision", date: da.decision_completed ?? da.decision_date },
    { label: "Decision issued", date: da.issue_decision_completed },
    { label: "Appeal period", date: da.appeal_period_completed },
  ].filter((m) => m.date);

  if (milestones.length < 2) return null;

  return (
    <div className="mt-1">
      <p className="text-[9px] text-zinc-600 uppercase tracking-wider mb-1.5">Timeline</p>
      <div className="flex items-center gap-0 overflow-x-auto">
        {milestones.map((m, i) => (
          <div key={i} className="flex items-center">
            {i > 0 && <div className="w-4 h-px bg-zinc-700 flex-shrink-0" />}
            <div className="flex-shrink-0 text-center">
              <div className="w-2 h-2 rounded-full bg-emerald-500/80 mx-auto mb-0.5" />
              <p className="text-[8px] text-zinc-500 whitespace-nowrap">{m.label}</p>
              <p className="text-[8px] text-zinc-400 whitespace-nowrap">{formatDate(m.date)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Nearby summary chips ─────────────────────────────────────────────────────

function TypeChip({ type, count, color }: { type: string; count: number; color: string }) {
  const meta = daTypeMeta(type);
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 ${meta.color}`}>
      {meta.icon}
      <span className="font-medium">{meta.shortLabel}</span>
      <span className="text-zinc-500">{count}</span>
    </span>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

type Props = {
  parcelDAs: DevelopmentApplication[] | null;
  nearbyDAs: NearbyDA[] | null;
  nearbyTotal: number;
  nearbySummary: { by_type: Record<string, number>; by_category: Record<string, number>; by_status: Record<string, number> } | null;
  nearbyRadius: number;
  onNearbyRadiusChange: (r: number) => void;
  showOnMap: boolean;
  onShowOnMapChange: (v: boolean) => void;
  loading: boolean;
  nearbyLoading: boolean;
};

const RADIUS_OPTIONS = [
  { value: 500,  label: "500m" },
  { value: 1000, label: "1 km" },
  { value: 2000, label: "2 km" },
  { value: 5000, label: "5 km" },
];

export function DAActivityPanel({
  parcelDAs,
  nearbyDAs,
  nearbyTotal,
  nearbySummary,
  nearbyRadius,
  onNearbyRadiusChange,
  showOnMap,
  onShowOnMapChange,
  loading,
  nearbyLoading,
}: Props) {
  const [nearbyExpanded, setNearbyExpanded] = useState(false);
  const [filterTypes, setFilterTypes] = useState<string[]>([]);
  const [filterStatuses, setFilterStatuses] = useState<string[]>([]);
  const [filterTimeRange, setFilterTimeRange] = useState<"6m" | "1y" | "2y" | "all">("all");

  const isGoldCoast = parcelDAs !== null;
  if (!isGoldCoast) return null;

  // Compute unique types present in nearby DAs for filter chips
  const availableTypes = nearbyDAs
    ? Array.from(new Set(nearbyDAs.map((da) => daTypeMeta(da.application_type).shortLabel)))
    : [];

  // Time range cutoff
  function timeRangeCutoff(range: string): Date | null {
    const now = new Date();
    if (range === "6m") return new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
    if (range === "1y") return new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
    if (range === "2y") return new Date(now.getFullYear() - 2, now.getMonth(), now.getDate());
    return null;
  }

  // Apply filters to nearby DAs
  const filteredNearbyDAs = (nearbyDAs ?? []).filter((da) => {
    if (filterTypes.length > 0 && !filterTypes.includes(daTypeMeta(da.application_type).shortLabel)) return false;
    if (filterStatuses.length > 0 && !filterStatuses.includes(statusBucket(da.status))) return false;
    if (filterTimeRange !== "all") {
      const cutoff = timeRangeCutoff(filterTimeRange);
      if (cutoff && da.lodgement_date && new Date(da.lodgement_date) < cutoff) return false;
    }
    return true;
  });

  const filteredCount = filteredNearbyDAs.length;
  const hasActiveFilters = filterTypes.length > 0 || filterStatuses.length > 0 || filterTimeRange !== "all";

  function toggleType(label: string) {
    setFilterTypes((prev) => prev.includes(label) ? prev.filter((t) => t !== label) : [...prev, label]);
  }
  function toggleStatus(bucket: string) {
    setFilterStatuses((prev) => prev.includes(bucket) ? prev.filter((s) => s !== bucket) : [...prev, bucket]);
  }

  return (
    <div>
      {/* ── Panel header — matches SidebarSection layout ── */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-zinc-200">
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
            <rect x="9" y="3" width="6" height="4" rx="1" />
            <path d="M9 12h6M9 16h4" />
          </svg>
        </span>
        <span className="text-xs font-semibold text-zinc-200 tracking-wide flex-1">Development Activity</span>

        {/* Map toggle */}
        <button
          onClick={() => onShowOnMapChange(!showOnMap)}
          className={`flex items-center gap-1.5 text-[10px] px-2 py-1 rounded-md transition-all ${
            showOnMap
              ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
              : "text-zinc-500 hover:text-zinc-300 border border-zinc-700 hover:border-zinc-600"
          }`}
          title={showOnMap ? "Hide DAs on map" : "Show nearby DAs on map"}
        >
          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21" />
            <line x1="9" y1="3" x2="9" y2="18" /><line x1="15" y1="6" x2="15" y2="21" />
          </svg>
          {showOnMap ? "Showing on map" : "Show on map"}
        </button>
      </div>
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02]">

      {/* ── Nearby DAs ── */}
      <div className="px-3 py-2.5">
        <div className="flex items-center justify-between mb-2.5">
          {/* Radius selector */}
          <div className="flex items-center gap-0.5">
            {RADIUS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => onNearbyRadiusChange(opt.value)}
                className={`text-[9px] px-1.5 py-0.5 rounded transition-colors ${
                  nearbyRadius === opt.value
                    ? "bg-zinc-700 text-zinc-200"
                    : "text-zinc-500 hover:text-zinc-400"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {hasActiveFilters && (
            <button
              onClick={() => { setFilterTypes([]); setFilterStatuses([]); setFilterTimeRange("all"); }}
              className="text-[9px] text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>

        {nearbyLoading && (
          <div className="flex items-center gap-2 py-1">
            <div className="w-3 h-3 rounded-full border border-zinc-600 border-t-zinc-300 animate-spin" />
            <span className="text-[10px] text-zinc-500">Finding nearby applications…</span>
          </div>
        )}

        {!nearbyLoading && nearbyDAs !== null && nearbyTotal > 0 && (
          <>
            {/* ── Filters ── */}
            <div className="rounded-lg border border-zinc-700/60 bg-zinc-900/80 mb-3">
              {/* Filter header */}
              <div className="flex items-center justify-between px-2.5 py-1.5 border-b border-zinc-800/80 bg-zinc-800/40">
                <div className="flex items-center gap-1.5 text-zinc-400">
                  <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
                  </svg>
                  <span className="text-[10px] font-semibold tracking-wide">Filters</span>
                </div>
                {hasActiveFilters && (
                  <button
                    onClick={() => { setFilterTypes([]); setFilterStatuses([]); setFilterTimeRange("all"); }}
                    className="text-[9px] text-zinc-500 hover:text-zinc-200 transition-colors flex items-center gap-1"
                  >
                    <svg className="w-2.5 h-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                    Clear all
                  </button>
                )}
              </div>

              {/* Time range */}
              <div className="flex items-center gap-1.5 px-2.5 py-2 border-b border-zinc-800/60">
                <span className="text-[9px] font-medium text-zinc-500 uppercase tracking-widest w-10 flex-shrink-0">Period</span>
                <div className="flex gap-1 flex-wrap">
                  {(["all", "6m", "1y", "2y"] as const).map((range) => (
                    <button
                      key={range}
                      onClick={() => setFilterTimeRange(range)}
                      className={`text-[10px] px-2 py-0.5 rounded-md font-medium transition-all ${
                        filterTimeRange === range
                          ? "bg-zinc-600 text-white shadow-sm"
                          : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                      }`}
                    >
                      {range === "all" ? "All" : range === "6m" ? "6 mo" : range === "1y" ? "1 yr" : "2 yr"}
                    </button>
                  ))}
                </div>
              </div>

              {/* Type filter chips with tooltips */}
              {availableTypes.length > 1 && (
                <div className="flex items-start gap-1.5 px-2.5 py-2 border-b border-zinc-800/60">
                  <span className="text-[9px] font-medium text-zinc-500 uppercase tracking-widest w-10 flex-shrink-0 mt-0.5">Type</span>
                  <div className="flex gap-1 flex-wrap">
                    {availableTypes.map((label) => {
                      const meta = daTypeMeta(nearbyDAs.find((d) => daTypeMeta(d.application_type).shortLabel === label)?.application_type ?? null);
                      const active = filterTypes.includes(label);
                      return (
                        <div key={label} className="relative group">
                          <button
                            onClick={() => toggleType(label)}
                            className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md font-medium transition-all ${
                              active
                                ? `bg-zinc-600 ${meta.color} shadow-sm ring-1 ring-inset ring-white/10`
                                : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                            }`}
                          >
                            <span className={active ? meta.color : "text-zinc-600"}>{meta.icon}</span>
                            {label}
                          </button>
                          <div className="absolute top-full left-0 mt-1.5 z-50 hidden group-hover:block w-56 bg-zinc-900 border border-white/10 rounded-lg shadow-xl p-2.5 text-[10px] text-zinc-300 leading-relaxed pointer-events-none">
                            <p className={`font-semibold mb-1 ${meta.color}`}>{meta.label}</p>
                            <p className="text-zinc-400">{meta.tooltip}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Status filter */}
              <div className="flex items-center gap-1.5 px-2.5 py-2">
                <span className="text-[9px] font-medium text-zinc-500 uppercase tracking-widest w-10 flex-shrink-0">Status</span>
                <div className="flex gap-1 flex-wrap">
                  {(["approved", "current", "refused", "withdrawn"] as const).map((bucket) => {
                    const active = filterStatuses.includes(bucket);
                    const label = bucket.charAt(0).toUpperCase() + bucket.slice(1);
                    return (
                      <button
                        key={bucket}
                        onClick={() => toggleStatus(bucket)}
                        className={`inline-flex items-center gap-1.5 text-[10px] px-2 py-0.5 rounded-md font-medium transition-all ${
                          active ? `${STATUS_STYLES[bucket]} shadow-sm` : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                        }`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${active ? STATUS_DOT[bucket] : "bg-zinc-700"}`} />
                        {label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Count summary */}
            <div className="flex items-center justify-between mb-2">
              <span className={`text-[11px] font-semibold ${filteredCount > 0 ? "text-zinc-200" : "text-zinc-500"}`}>
                {filteredCount === 0
                  ? "No matching applications"
                  : hasActiveFilters
                    ? `${filteredCount} of ${nearbyTotal} within ${nearbyRadius >= 1000 ? `${nearbyRadius / 1000} km` : `${nearbyRadius}m`}`
                    : `${nearbyTotal} application${nearbyTotal !== 1 ? "s" : ""} within ${nearbyRadius >= 1000 ? `${nearbyRadius / 1000} km` : `${nearbyRadius}m`}`}
              </span>
            </div>

            {/* Nearby DA list (collapsed by default) */}
            {filteredCount > 0 && (
              <button
                onClick={() => setNearbyExpanded((v) => !v)}
                className="flex items-center gap-1.5 text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                <svg
                  className={`w-3 h-3 transition-transform ${nearbyExpanded ? "rotate-180" : ""}`}
                  viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}
                >
                  <polyline points="6 9 12 15 18 9" />
                </svg>
                {nearbyExpanded ? "Hide list" : `Browse ${filteredCount} application${filteredCount !== 1 ? "s" : ""}`}
              </button>
            )}

            {nearbyExpanded && filteredNearbyDAs.length > 0 && (
              <div className="mt-2 space-y-1.5 max-h-80 overflow-y-auto pr-0.5">
                {filteredNearbyDAs.map((da) => (
                  <NearbyDARow key={da.application_number} da={da} />
                ))}
              </div>
            )}
          </>
        )}

        {!nearbyLoading && nearbyDAs !== null && nearbyTotal === 0 && (
          <p className="text-[11px] text-zinc-600 italic">No nearby applications found within {nearbyRadius >= 1000 ? `${nearbyRadius / 1000} km` : `${nearbyRadius}m`}.</p>
        )}

      </div>

      {/* ── Data coverage notice ── */}
      <div className="border-t border-white/[0.04] px-3 py-2.5">
        <div className="flex items-start gap-1.5 text-[10px] text-zinc-600 bg-zinc-800/30 rounded px-2 py-1.5">
          <svg className="w-3 h-3 mt-0.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" />
          </svg>
          <span>Data covers 2017–2019 and 2025–2026. Applications from 2020–2024 are mostly absent.</span>
        </div>
      </div>
    </div>
    </div>
  );
}

// ─── Compact nearby DA row ────────────────────────────────────────────────────

function NearbyDARow({ da }: { da: NearbyDA }) {
  const meta = daTypeMeta(da.application_type);
  const bucket = statusBucket(da.status);
  const link = epathwayUrl(da.epathway_id, da.application_number);

  const dist = da.distance_m < 1000
    ? `${Math.round(da.distance_m)}m`
    : `${(da.distance_m / 1000).toFixed(1)} km`;

  const descParts: string[] = [];
  if (da.dwelling_type) descParts.push(da.dwelling_type);
  if (da.unit_count && da.unit_count > 1) descParts.push(`${da.unit_count} units`);
  if (da.lot_split_from && da.lot_split_to) descParts.push(`${da.lot_split_from}→${da.lot_split_to} lots`);
  const summaryText = descParts.length > 0
    ? descParts.join(" · ")
    : (da.description ?? da.location_address ?? da.suburb ?? "—");

  return (
    <div className="flex items-start gap-2 px-2 py-1.5 rounded-md bg-zinc-800/30 hover:bg-zinc-800/60 transition-colors group">
      <span className={`mt-0.5 flex-shrink-0 ${meta.color}`}>{meta.icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className={`text-[10px] font-semibold ${meta.color}`}>{meta.shortLabel}</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${STATUS_STYLES[bucket]}`}>
            {statusLabel(da.status)}
          </span>
          <span className="ml-auto text-[9px] text-zinc-600">{dist} · {formatYear(da.lodgement_date)}</span>
        </div>
        <p className="text-[10px] text-zinc-400 line-clamp-1 mt-0.5">{summaryText}</p>
      </div>
      {link && (
        <a
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="mt-0.5 text-zinc-700 hover:text-emerald-400 transition-colors flex-shrink-0 opacity-0 group-hover:opacity-100"
          title="View on ePathway"
        >
          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
          </svg>
        </a>
      )}
    </div>
  );
}

// ─── Map marker data extractor ────────────────────────────────────────────────

export type DAMapMarker = {
  lat: number;
  lng: number;
  applicationNumber: string;
  applicationTypeLong: string;
  shortLabel: string;
  status: string | null;
  description: string | null;
  lodgementDate: string | null;
  mapColor: string;
  epathwayId: number | null;
};

export function buildDAMapMarkers(das: NearbyDA[]): DAMapMarker[] {
  return das.map((da) => {
    const meta = daTypeMeta(da.application_type);
    return {
      lat: da.lat,
      lng: da.lng,
      applicationNumber: da.application_number,
      applicationTypeLong: meta.label,
      shortLabel: meta.shortLabel,
      status: da.status,
      description: da.description,
      lodgementDate: da.lodgement_date,
      mapColor: meta.mapColor,
      epathwayId: da.epathway_id,
    };
  });
}
