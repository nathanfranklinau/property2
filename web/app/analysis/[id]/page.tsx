"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";

const PropertyMap = dynamic(() => import("@/components/PropertyMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-[#0d0d15] animate-pulse" />
  ),
});

import { simplifyFootprint, computeBufferCoords, type BuildingFootprint } from "@/components/PropertyMap";
import { classifyProperty, PROPERTY_TYPE_COLORS, type PropertyType, type PropertyTypeInfo } from "@/lib/property-type";
import { PlanTypeIcon } from "@/components/PlanTypeIcon";

type AnalysisStatus = {
  parcel_id: string;
  cadastre_lot: string;
  cadastre_plan: string;
  lot_area_sqm: number | null;
  display_address: string | null;
  image_status: string;
  analysis_status: string;
  main_house_size_sqm: number | null;
  building_count: number | null;
  available_space_sqm: number | null;
  pool_count_detected: number | null;
  pool_count_registered: number | null;
  pool_area_sqm: number | null;
  image_satellite_path: string | null;
  image_styled_map_path: string | null;
  image_mask2_path: string | null;
  image_street_view_path: string | null;
  error_message: string | null;
  building_footprints_geo: BuildingFootprint[] | null;
  boundary_coords_gda94: [number, number][] | null;
  centroid_lat: number | null;
  centroid_lon: number | null;
  lga_name: string | null;
  zone_code: string | null;
  zone_name: string | null;
  // Property type fields
  property_type: PropertyType | null;
  plan_prefix: string | null;
  address_count: number | null;
  flat_types: string[] | null;
  building_name: string | null;
  complex_geometry: object | null;
  complex_lot_count: number | null;
  tenure_type: string | null;
};

type NearbyPlan = {
  plan: string;
  addresses: string[];
  lot_count: number;
  total_area_sqm: number;
  distance_m: number;
  centroid: { lat: number; lng: number };
  boundary_coords: [number, number][][];
};

type Stage = "queuing" | "imagery" | "analysing" | "complete" | "failed";

function getStage(status: AnalysisStatus): Stage {
  if (status.analysis_status === "failed" || status.image_status === "failed") return "failed";
  if (status.analysis_status === "complete") return "complete";
  if (status.image_status === "complete" || status.analysis_status === "running") return "analysing";
  if (status.image_status === "downloading") return "imagery";
  return "queuing";
}

const STEPS: { id: Stage | "property"; label: string }[] = [
  { id: "property", label: "Property identified in cadastre" },
  { id: "imagery", label: "Downloading satellite imagery" },
  { id: "analysing", label: "Detecting buildings and structures" },
  { id: "complete", label: "Analysis complete" },
];

function stepDone(stepId: string, stage: Stage): boolean {
  const order = ["property", "imagery", "analysing", "complete"];
  const currentIdx = order.indexOf(stage === "failed" ? "analysing" : stage);
  const stepIdx = order.indexOf(stepId);
  return stepIdx < currentIdx || (stepId === stage && stage === "complete");
}

function stepActive(stepId: string, stage: Stage): boolean {
  if (stage === "failed") return false;
  if (stepId === "property") return stage === "queuing";
  if (stepId === "imagery") return stage === "imagery";
  if (stepId === "analysing") return stage === "analysing";
  if (stepId === "complete") return stage === "complete";
  return false;
}

function computeUnionAreaSqm(
  footprints: BuildingFootprint[],
  extraCoords: [number, number][][] = []
): number {
  const allCoordSets = [
    ...footprints.map((fp) => fp.coords),
    ...extraCoords,
  ];
  if (allCoordSets.length === 0) return 0;
  if (allCoordSets.length === 1 && extraCoords.length === 0) return footprints[0].area_sqm;

  const CANVAS_SIZE = 1024;
  let minLat = Infinity, maxLat = -Infinity, minLng = Infinity, maxLng = -Infinity;
  for (const coords of allCoordSets) {
    for (const [lat, lng] of coords) {
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
      if (lng < minLng) minLng = lng;
      if (lng > maxLng) maxLng = lng;
    }
  }

  const latRange = maxLat - minLat || 1e-6;
  const lngRange = maxLng - minLng || 1e-6;

  const canvas = document.createElement("canvas");
  canvas.width = CANVAS_SIZE;
  canvas.height = CANVAS_SIZE;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return footprints.reduce((sum, f) => sum + f.area_sqm, 0);
  }

  ctx.fillStyle = "white";
  for (const coords of allCoordSets) {
    if (coords.length < 3) continue;
    ctx.beginPath();
    for (let i = 0; i < coords.length; i++) {
      const [lat, lng] = coords[i];
      const x = ((lng - minLng) / lngRange) * (CANVAS_SIZE - 1);
      const y = ((maxLat - lat) / latRange) * (CANVAS_SIZE - 1);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fill();
  }

  const imageData = ctx.getImageData(0, 0, CANVAS_SIZE, CANVAS_SIZE);
  let filledPixels = 0;
  for (let i = 0; i < imageData.data.length; i += 4) {
    if (imageData.data[i] > 0) filledPixels++;
  }

  const centerLat = (minLat + maxLat) / 2;
  const mPerLat = 111320;
  const mPerLng = 111320 * Math.cos((centerLat * Math.PI) / 180);
  const bboxSqm = latRange * mPerLat * lngRange * mPerLng;

  return (filledPixels / (CANVAS_SIZE * CANVAS_SIZE)) * bboxSqm;
}

function sqm(value: number | null): string {
  if (value == null) return "—";
  return `${Math.round(value).toLocaleString()} m\u00B2`;
}

// ─── Tab definitions ──────────────────────────────────────────────────────

type TabId = "free-space" | "buildings" | "plots" | "easements" | "boundaries" | "subdivision";

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  {
    id: "free-space",
    label: "Free Space",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <path d="M3 9h18M9 3v18" />
      </svg>
    ),
  },
  {
    id: "buildings",
    label: "Buildings",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
        <path d="M3 21V7l9-4 9 4v14" />
        <path d="M9 21V13h6v8" />
      </svg>
    ),
  },
  {
    id: "plots",
    label: "Plots",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    id: "easements",
    label: "Easements",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
        <path d="M4 20L20 4" strokeDasharray="4 2" />
        <path d="M4 4v16h16" />
      </svg>
    ),
  },
  {
    id: "boundaries",
    label: "Boundaries",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
        <polygon points="12,2 22,8.5 22,15.5 12,22 2,15.5 2,8.5" />
      </svg>
    ),
  },
  {
    id: "subdivision",
    label: "Subdivision Potential",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
        <path d="M16 3h5v5M14 10l7-7M8 21H3v-5M10 14l-7 7" />
      </svg>
    ),
  },
];

// ─── Main page ────────────────────────────────────────────────────────────

export default function AnalysisPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const parcelId = params.id;

  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [footprints, setFootprints] = useState<BuildingFootprint[]>([]);
  const [footprintsInitialized, setFootprintsInitialized] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>("free-space");
  const [showNotice, setShowNotice] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [nearbyData, setNearbyData] = useState<{
    counts: { within_2km: number; within_5km: number; within_10km: number; within_20km: number };
    plans: NearbyPlan[];
  } | null>(null);
  const [nearbyLoading, setNearbyLoading] = useState(false);
  const [expandedBands, setExpandedBands] = useState<Set<string>>(new Set());
  const [visibleNearbyPlans, setVisibleNearbyPlans] = useState<Set<string>>(new Set());
  const [focusedNearbyPlan, setFocusedNearbyPlan] = useState<{ lat: number; lng: number } | null>(null);
  const [expandedPlanAddresses, setExpandedPlanAddresses] = useState<Set<string>>(new Set());
  const [nearbySearch, setNearbySearch] = useState("");
  const [bandPage, setBandPage] = useState<Record<string, number>>({});

  const bufferCoords = useMemo(() => {
    if (!status?.boundary_coords_gda94) return [];
    return footprints
      .filter((fp) => fp.hasBuffer)
      .map((fp) => computeBufferCoords(fp, status.boundary_coords_gda94!))
      .filter((c): c is [number, number][] => c !== null);
  }, [footprints, status?.boundary_coords_gda94]);

  const totalStructuresArea = useMemo(
    () => computeUnionAreaSqm(footprints, bufferCoords),
    [footprints, bufferCoords]
  );

  const freeSpace = useMemo(() => {
    if (status?.lot_area_sqm == null) return status?.available_space_sqm ?? null;
    return status.lot_area_sqm - totalStructuresArea - (Number(status.pool_area_sqm) || 0);
  }, [status?.lot_area_sqm, status?.available_space_sqm, status?.pool_area_sqm, totalStructuresArea]);

  // Property type classification — must be before any early returns (Rules of Hooks)
  const typeInfo: PropertyTypeInfo = useMemo(
    () => classifyProperty(status?.plan_prefix ?? null, status?.address_count ?? 0),
    [status?.plan_prefix, status?.address_count]
  );
  const propertyType = status?.property_type ?? typeInfo.type;
  const typeBadgeColor = PROPERTY_TYPE_COLORS[propertyType] ?? PROPERTY_TYPE_COLORS.house;

  const visibleTabs = useMemo(() => {
    switch (propertyType) {
      case "unit":
        return TABS.filter((t) => t.id === "boundaries" || t.id === "buildings");
      case "townhouse":
        return TABS.filter((t) => t.id === "boundaries" || t.id === "buildings" || t.id === "easements");
      case "special_tenure":
        return TABS.filter((t) => t.id === "boundaries");
      default:
        return TABS;
    }
  }, [propertyType]);

  const complexBoundaryRings = useMemo((): [number, number][][] | undefined => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const geo = status?.complex_geometry as any;
    if (!geo?.coordinates) return undefined;
    if (geo.type === "MultiPolygon") {
      return (geo.coordinates as number[][][][]).map((poly) =>
        poly[0].map(([lon, lat]) => [lat, lon] as [number, number])
      );
    }
    if (geo.type === "Polygon") {
      return [(geo.coordinates as number[][][])[0].map(([lon, lat]) => [lat, lon] as [number, number])];
    }
    return undefined;
  }, [status?.complex_geometry]);

  const nearbyBoundaries = useMemo(() => {
    if (!nearbyData || !nearbyData.plans) return [];
    return nearbyData.plans
      .filter((p) => visibleNearbyPlans.has(p.plan))
      .map((p) => ({
        plan: p.plan,
        rings: p.boundary_coords,
        addresses: p.addresses,
        lot_count: p.lot_count,
        total_area_sqm: p.total_area_sqm,
        distance_m: p.distance_m,
        centroid: p.centroid,
      }));
  }, [nearbyData, visibleNearbyPlans]);

  async function poll() {
    try {
      const res = await fetch(
        `/api/analysis/status?parcel_id=${encodeURIComponent(parcelId)}`
      );
      if (!res.ok) {
        if (res.status === 404) {
          setFetchError("Analysis not found. The page may have expired.");
          return;
        }
        throw new Error(`HTTP ${res.status}`);
      }
      const data: AnalysisStatus = await res.json();
      setStatus(data);

      if (!footprintsInitialized && data.building_footprints_geo) {
        setFootprints(data.building_footprints_geo.map((fp) => ({ ...simplifyFootprint(fp), hasBuffer: true })));
        setFootprintsInitialized(true);
      }

      const stage = getStage(data);
      if (stage === "complete" || stage === "failed") {
        if (intervalRef.current) clearInterval(intervalRef.current);
        if (stage === "complete") {
          setNearbyLoading(true);
          fetch(`/api/analysis/nearby-subdivisions?parcel_id=${encodeURIComponent(parcelId)}`)
            .then((r) => {
              if (!r.ok) {
                console.warn(`Nearby subdivisions API returned ${r.status}`);
                return { counts: { within_2km: 0, within_5km: 0, within_10km: 0, within_20km: 0 }, plans: [] };
              }
              return r.json();
            })
            .then((d) => {
              // Ensure the response has the expected structure
              if (d && typeof d === 'object') {
                setNearbyData({
                  counts: d.counts || { within_2km: 0, within_5km: 0, within_10km: 0, within_20km: 0 },
                  plans: d.plans || []
                });
              }
            })
            .catch((err) => {
              console.error("Nearby subdivisions error:", err);
              setNearbyData({
                counts: { within_2km: 0, within_5km: 0, within_10km: 0, within_20km: 0 },
                plans: []
              });
            })
            .finally(() => setNearbyLoading(false));
        }
      }
    } catch (err) {
      console.error("Poll error:", err);
    }
  }

  useEffect(() => {
    if (!parcelId) return;
    poll();
    intervalRef.current = setInterval(poll, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parcelId]);

  // ─── Error state ────────────────────────────────────────────────────────
  if (fetchError) {
    return (
      <DarkShell>
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <p className="text-zinc-400 mb-6">{fetchError}</p>
            <Link href="/" className="text-white font-medium underline underline-offset-4 hover:text-zinc-300">
              Start a new search
            </Link>
          </div>
        </div>
      </DarkShell>
    );
  }

  // ─── Loading state ──────────────────────────────────────────────────────
  if (!status) {
    return (
      <DarkShell>
        <div className="flex items-center justify-center h-full">
          <Spinner className="w-8 h-8 text-zinc-500" />
        </div>
      </DarkShell>
    );
  }

  const stage = getStage(status);

  // ─── In-progress / failed state ─────────────────────────────────────────
  if (stage !== "complete") {
    return (
      <DarkShell>
        <div className="flex items-center justify-center h-full">
          <div className="w-full max-w-md">
            <h1 className="text-lg font-semibold text-white mb-1">
              {status.display_address ?? `Lot ${status.cadastre_lot} on ${status.cadastre_plan}`}
            </h1>
            <p className="text-sm text-zinc-500 mb-8">
              Lot {status.cadastre_lot} on {status.cadastre_plan}
              {status.lot_area_sqm ? ` · ${Math.round(status.lot_area_sqm).toLocaleString()} m²` : ""}
            </p>

            {stage === "failed" ? (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-5 py-4">
                <p className="text-sm font-medium text-red-400">Analysis failed</p>
                {status.error_message && (
                  <p className="text-sm text-red-400/70 mt-1">{status.error_message}</p>
                )}
                <button
                  onClick={() => router.push("/")}
                  className="mt-3 text-sm text-red-400 underline underline-offset-4 hover:text-red-300"
                >
                  Try a different address
                </button>
              </div>
            ) : (
              <>
                <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-5">
                  Analysing your property
                </p>
                <ol className="space-y-3">
                  {STEPS.map((step) => {
                    const done = stepDone(step.id, stage);
                    const active = stepActive(step.id, stage);
                    return (
                      <li key={step.id} className="flex items-center gap-3">
                        <span
                          className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center ${
                            done
                              ? "bg-emerald-500"
                              : active
                              ? "border-2 border-white"
                              : "border-2 border-zinc-700"
                          }`}
                        >
                          {done && (
                            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                          {active && <span className="w-2.5 h-2.5 rounded-full bg-white animate-pulse" />}
                        </span>
                        <span className={`text-sm ${done ? "text-zinc-600 line-through" : active ? "text-white font-medium" : "text-zinc-600"}`}>
                          {step.label}
                        </span>
                        {active && <Spinner className="w-4 h-4 text-zinc-500 ml-auto" />}
                      </li>
                    );
                  })}
                </ol>
              </>
            )}
          </div>
        </div>
      </DarkShell>
    );
  }

  // ─── Complete state — full dashboard ────────────────────────────────────

  return (
    <div className="h-screen bg-[#111118] text-white flex flex-col overflow-hidden">
      {/* Top navigation bar */}
      <nav className="flex items-center gap-1 px-3 py-2 border-b border-white/[0.06] bg-[#111118]">
        <NavIcon href="/" tooltip="Home">
          <svg className="w-4.5 h-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M3 12l9-8 9 8" />
            <path d="M5 10v10a1 1 0 001 1h3a1 1 0 001-1v-5h4v5a1 1 0 001 1h3a1 1 0 001-1V10" />
          </svg>
        </NavIcon>
        <NavIcon tooltip="Refresh" onClick={() => poll()}>
          <svg className="w-4.5 h-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M4 12a8 8 0 0114.93-4M20 12a8 8 0 01-14.93 4" />
            <path d="M20 4v4h-4M4 20v-4h4" />
          </svg>
        </NavIcon>
        <NavIcon tooltip="Notifications" badge>
          <svg className="w-4.5 h-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 01-3.46 0" />
          </svg>
        </NavIcon>
        <div className="w-px h-5 bg-white/10 mx-1" />
        <NavIcon tooltip="Property" active>
          <svg className="w-4.5 h-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M12 22c1-4 6-7 6-12a6 6 0 10-12 0c0 5 5 8 6 12z" />
            <circle cx="12" cy="10" r="2" />
          </svg>
        </NavIcon>
        <div className="flex-1" />
        <NavIcon tooltip="Undo">
          <svg className="w-4.5 h-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M3 10h13a4 4 0 010 8H7" />
            <path d="M7 6L3 10l4 4" />
          </svg>
        </NavIcon>
        <NavIcon tooltip="Redo">
          <svg className="w-4.5 h-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M21 10H8a4 4 0 000 8h9" />
            <path d="M17 6l4 4-4 4" />
          </svg>
        </NavIcon>
        <NavIcon tooltip="Share">
          <svg className="w-4.5 h-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M5 12l14-7M5 12l14 7M5 12H3" />
            <circle cx="19" cy="5" r="2" />
            <circle cx="19" cy="19" r="2" />
          </svg>
        </NavIcon>
      </nav>

      {/* Main content area */}
      <div className="flex flex-1 min-h-0">
        {/* Left: Map + Tab bar */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Map */}
          <div className="flex-1 relative">
            {status.boundary_coords_gda94 &&
              status.centroid_lat != null &&
              status.centroid_lon != null && (
                <PropertyMap
                  apiKey={process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ?? ""}
                  boundaryCoords={status.boundary_coords_gda94}
                  centroid={{
                    lat: status.centroid_lat,
                    lng: status.centroid_lon,
                  }}
                  footprints={footprints}
                  onFootprintsChange={setFootprints}
                  readOnly={!typeInfo.allowDrawingTools}
                  complexBoundary={complexBoundaryRings}
                  nearbySubdivisions={nearbyBoundaries}
                  focusedNearbyPlan={focusedNearbyPlan}
                />
              )}
          </div>

          {/* Tab bar */}
          <div className="flex items-center gap-0.5 px-2 py-1.5 border-t border-white/[0.06] bg-[#111118] overflow-x-auto">
            {visibleTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  activeTab === tab.id
                    ? "bg-white/[0.08] text-white"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04]"
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
            <button className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04] whitespace-nowrap transition-all">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
              See More
            </button>
          </div>
        </div>

        {/* Right: Sidebar */}
        <aside className="w-[380px] flex-shrink-0 border-l border-white/[0.06] bg-[#15151e] flex flex-col">
          <div className="flex-1 overflow-y-auto">
            <div className="p-5 space-y-5">
              {/* Address + property type icon */}
              <div className="flex items-start gap-3">
                <div className={`flex-shrink-0 w-10 h-10 rounded flex items-center justify-center border border-current/20 ${typeBadgeColor}`}>
                  <PlanTypeIcon plan={status.cadastre_plan} className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <h1 className="text-sm font-semibold text-white leading-tight truncate">
                    {status.display_address ?? `Lot ${status.cadastre_lot} on ${status.cadastre_plan}`}
                  </h1>
                  <p className="text-xs text-zinc-500 mt-0.5">{typeInfo.label}</p>
                  {status.building_name && (
                    <p className="text-xs text-zinc-500">{status.building_name}</p>
                  )}
                </div>
              </div>

              {/* View mode tabs */}
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white">
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                    <circle cx="12" cy="12" r="3" />
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                  </svg>
                  Free Space
                </div>
              </div>

              {/* Zone badge */}
              {status.zone_name && (
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    {status.zone_name}
                  </span>
                </div>
              )}

              {/* Special tenure banner */}
              {propertyType === "special_tenure" && (
                <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 px-3 py-2.5">
                  <p className="text-xs font-semibold text-amber-400">{typeInfo.label}</p>
                  <p className="text-[11px] text-amber-400/70 mt-0.5">
                    This land is not standard freehold and has special tenure restrictions.
                  </p>
                </div>
              )}

              {/* Multi-dwelling banner */}
              {propertyType === "multi_dwelling" && (
                <div className="rounded-lg bg-blue-500/10 border border-blue-500/20 px-3 py-2.5">
                  <p className="text-xs font-semibold text-blue-400">
                    {status.address_count ?? 0} addresses on this lot
                  </p>
                  {status.flat_types && status.flat_types.length > 0 && (
                    <p className="text-[11px] text-blue-400/70 mt-0.5">
                      Types: {status.flat_types.join(", ")}
                    </p>
                  )}
                </div>
              )}

              {/* Big numbers — free space + covered */}
              {typeInfo.allowSubdivision && (
                <div className="flex items-end gap-4">
                  <div>
                    <p className="text-[11px] text-zinc-500 mb-0.5 uppercase tracking-wider font-medium">Free</p>
                    <p className="text-4xl font-bold tracking-tight tabular-nums leading-none">
                      {freeSpace != null ? Math.round(freeSpace).toLocaleString() : "—"}
                      <span className="text-lg font-medium text-zinc-400 ml-0.5">m²</span>
                    </p>
                  </div>
                  {status?.lot_area_sqm != null && !isNaN(totalStructuresArea) && (
                    <>
                      <div className="w-px h-8 bg-white/10 mb-1 flex-shrink-0" />
                      <div>
                        <p className="text-[11px] text-zinc-500 mb-0.5 uppercase tracking-wider font-medium">Covered</p>
                        <p className="text-2xl font-semibold tracking-tight tabular-nums leading-none text-zinc-300">
                          {Math.round(totalStructuresArea + (Number(status.pool_area_sqm) || 0)).toLocaleString()}
                          <span className="text-sm font-medium text-zinc-500 ml-0.5">m²</span>
                        </p>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Dismissible notice */}
              {showNotice && (
                <div className="flex items-start gap-2 rounded-lg bg-white/[0.04] border border-white/[0.06] px-3 py-2.5">
                  <p className="text-[11px] text-zinc-400 leading-relaxed flex-1">
                    Results are estimates based on satellite imagery and public data — verify with your local council before proceeding.
                  </p>
                  <button
                    onClick={() => setShowNotice(false)}
                    className="text-zinc-600 hover:text-zinc-400 transition-colors mt-0.5 flex-shrink-0"
                  >
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" d="M18 6L6 18M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              )}

              {/* Complex Info (BUP / GTP only) */}
              {(propertyType === "unit" || propertyType === "townhouse") && (
                <SidebarSection
                  title="Complex Info"
                  icon={
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                      <rect x="3" y="8" width="8" height="13" rx="1" />
                      <rect x="13" y="3" width="8" height="18" rx="1" />
                      <path d="M6 12h2M6 15h2M16 7h2M16 10h2M16 13h2" />
                    </svg>
                  }
                >
                  {status.building_name && (
                    <SidebarRow
                      icon={<BuildingCountIcon />}
                      label="Complex Name"
                      value={status.building_name}
                    />
                  )}
                  <SidebarRow
                    icon={<PlanIcon />}
                    label="Plan"
                    value={status.cadastre_plan}
                  />
                  {status.complex_lot_count != null && status.complex_lot_count > 0 && (
                    <SidebarRow
                      icon={<LotIcon />}
                      label={propertyType === "unit" ? "Units in Complex" : "Lots in Complex"}
                      value={String(status.complex_lot_count)}
                    />
                  )}
                  {status.address_count != null && status.address_count > 0 && (
                    <SidebarRow
                      icon={<AreaIcon />}
                      label="Addresses"
                      value={String(status.address_count)}
                    />
                  )}
                </SidebarSection>
              )}

              {/* Property Rights */}
              <SidebarSection
                title="Property Rights"
                icon={
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <path d="M3 9h18M9 3v18" />
                  </svg>
                }
              >
                <SidebarRow
                  icon={<LotIcon />}
                  label="Lot Size"
                  value={sqm(status.lot_area_sqm)}
                />
                <SidebarRow
                  icon={<PlanIcon />}
                  label="Lot / Plan"
                  value={`${status.cadastre_lot} / ${status.cadastre_plan}`}
                />
                <SidebarRow
                  icon={<CouncilIcon />}
                  label="Council"
                  value={status.lga_name ?? "—"}
                  valueColor={status.lga_name ? undefined : "text-zinc-500"}
                />
                {propertyType === "special_tenure" && (
                  <SidebarRow
                    icon={<ZoneIcon />}
                    label="Tenure"
                    value={typeInfo.label}
                  />
                )}
              </SidebarSection>

              {/* Space Analysis — only for house/multi_dwelling */}
              {(propertyType === "house" || propertyType === "multi_dwelling") && (
                <SidebarSection
                  title="Space Analysis"
                  icon={
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                      <path d="M21 12a9 9 0 11-9-9" />
                      <path d="M21 3v6h-6" />
                    </svg>
                  }
                >
                  <SidebarRow
                    icon={<FreeSpaceIcon />}
                    label="Free Space"
                    value={sqm(freeSpace)}
                    highlight
                  />
                  <SidebarRow
                    icon={<StructuresIcon />}
                    label="Total Structures"
                    value={sqm(totalStructuresArea)}
                  />
                  {status.pool_area_sqm != null && status.pool_area_sqm > 0 && (
                    <SidebarRow
                      icon={<PoolIcon />}
                      label="Pool Area"
                      value={sqm(status.pool_area_sqm)}
                    />
                  )}
                </SidebarSection>
              )}



              {/* Nearby Subdivision Activity */}
              {typeInfo.allowSubdivision && (nearbyLoading || nearbyData) && (
                <SidebarSection
                  title="Nearby Subdivisions"
                  icon={
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                      <circle cx="12" cy="12" r="3" />
                      <circle cx="12" cy="12" r="7" strokeDasharray="3 2" />
                      <circle cx="12" cy="12" r="11" strokeDasharray="3 2" />
                    </svg>
                  }
                  info={"Nearby properties where the land has been split into 2–6 separate lots — for example, a duplex, two homes built side by side, or a small group of townhouses.\n\nThese show what's already been approved in your area, which is a signal of what council may allow on similar land.\n\nNot included: large housing estates, apartment towers, commercial projects, or properties where multiple people simply share one building without the land being divided."}
                >
                  {nearbyLoading && !nearbyData ? (
                    <div className="flex items-center gap-2 px-3 py-3">
                      <svg className="w-3.5 h-3.5 text-zinc-500 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={2} opacity={0.25} />
                        <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
                      </svg>
                      <span className="text-[11px] text-zinc-500">Finding nearby subdivisions…</span>
                    </div>
                  ) : nearbyData ? (
                  <>
                  <div className="px-3 py-2 border-b border-white/[0.04]">
                    <div className="relative">
                      <svg className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        <circle cx="11" cy="11" r="8" />
                        <path d="M21 21l-4.35-4.35" />
                      </svg>
                      <input
                        type="text"
                        value={nearbySearch}
                        onChange={(e) => { setNearbySearch(e.target.value); setBandPage({}); }}
                        placeholder="Search addresses…"
                        className="w-full bg-white/[0.04] border border-white/[0.06] rounded text-[11px] text-zinc-300 placeholder-zinc-600 pl-6 pr-6 py-1.5 focus:outline-none focus:border-indigo-500/50 focus:bg-white/[0.06] transition-colors"
                      />
                      {nearbySearch && (
                        <button
                          onClick={() => setNearbySearch("")}
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400 transition-colors"
                        >
                          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                            <path d="M18 6L6 18M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                  {(
                    [
                      { label: "Within 2 km", key: "within_2km" as const, maxDist: 2000, minDist: 0 },
                      { label: "2 km – 5 km", key: "within_5km" as const, maxDist: 5000, minDist: 2000 },
                      { label: "5 km – 10 km", key: "within_10km" as const, maxDist: 10000, minDist: 5000 },
                      { label: "10 km – 20 km", key: "within_20km" as const, maxDist: 20000, minDist: 10000 },
                    ]
                  ).map(({ label, key, maxDist, minDist }) => {
                    const searchTerm = nearbySearch.trim().toLowerCase();
                    const bandPlans = (nearbyData.plans || []).filter(
                      (p) =>
                        p.distance_m <= maxDist &&
                        p.distance_m > minDist &&
                        (searchTerm === "" ||
                          p.plan.toLowerCase().includes(searchTerm) ||
                          p.addresses.some((a) => a.toLowerCase().includes(searchTerm)))
                    );
                    const isExpanded = expandedBands.has(key) || (searchTerm !== "" && bandPlans.length > 0);
                    const allBandVisible = bandPlans.length > 0 && bandPlans.every((p) => visibleNearbyPlans.has(p.plan));
                    const bandCount = nearbyData.counts?.[key] || 0;
                    return (
                      <div key={key}>
                        <div className="flex items-center">
                          <button
                            onClick={() =>
                              setExpandedBands((prev) => {
                                const next = new Set(prev);
                                next.has(key) ? next.delete(key) : next.add(key);
                                return next;
                              })
                            }
                            className="flex items-center justify-between flex-1 px-3 py-2.5 gap-3 hover:bg-white/[0.02] transition-colors min-w-0"
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="text-zinc-600 flex-shrink-0"><ActivityIcon /></span>
                              <span className="text-xs text-zinc-400">{label}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-semibold tabular-nums text-zinc-300">
                                {bandCount.toLocaleString()}
                              </span>
                              <svg
                                className={`w-3 h-3 text-zinc-600 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth={2}
                              >
                                <path d="M6 9l6 6 6-6" />
                              </svg>
                            </div>
                          </button>
                          {bandPlans.length > 0 && (
                            <button
                              onClick={() =>
                                setVisibleNearbyPlans((prev) => {
                                  const next = new Set(prev);
                                  if (allBandVisible) {
                                    bandPlans.forEach((p) => next.delete(p.plan));
                                  } else {
                                    bandPlans.forEach((p) => next.add(p.plan));
                                  }
                                  return next;
                                })
                              }
                              className={`px-2 py-1 mr-2 text-[10px] rounded transition-colors flex-shrink-0 ${
                                allBandVisible
                                  ? "text-indigo-400 hover:text-indigo-300"
                                  : "text-zinc-600 hover:text-zinc-400"
                              }`}
                              title={allBandVisible ? "Deselect all in this band" : "Select all in this band"}
                            >
                              {allBandVisible ? "Deselect all" : "Select all"}
                            </button>
                          )}
                        </div>
                        {isExpanded && bandPlans.length > 0 && (() => {
                          const PAGE_SIZE = 50;
                          const currentPage = bandPage[key] ?? 0;
                          const totalPages = Math.ceil(bandPlans.length / PAGE_SIZE);
                          const pagedPlans = bandPlans.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);
                          return (
                          <div className="border-t border-white/[0.03]">
                            {pagedPlans.map((plan) => {
                              const isVisible = visibleNearbyPlans.has(plan.plan);
                              const addressesExpanded = expandedPlanAddresses.has(plan.plan);
                              const extraAddresses = plan.addresses.slice(1);
                              return (
                                <div
                                  key={plan.plan}
                                  className={`flex items-start justify-between px-3 py-2 pl-8 gap-2 transition-colors ${
                                    isVisible
                                      ? "bg-indigo-500/[0.07] border-l-2 border-indigo-500/50"
                                      : "border-l-2 border-transparent"
                                  }`}
                                >
                                  <div className="min-w-0 flex-1">
                                    <p className={`text-[11px] font-medium truncate ${isVisible ? "text-indigo-200" : "text-zinc-300"}`}>
                                      {plan.addresses.length > 0 ? plan.addresses[0] : plan.plan}
                                    </p>
                                    {extraAddresses.length > 0 && (
                                      <>
                                        <button
                                          onClick={() =>
                                            setExpandedPlanAddresses((prev) => {
                                              const next = new Set(prev);
                                              next.has(plan.plan) ? next.delete(plan.plan) : next.add(plan.plan);
                                              return next;
                                            })
                                          }
                                          className="text-[10px] text-indigo-400/70 hover:text-indigo-300 transition-colors mt-0.5"
                                        >
                                          {addressesExpanded ? "▾ Hide addresses" : `▸ +${extraAddresses.length} more address${extraAddresses.length > 1 ? "es" : ""}`}
                                        </button>
                                        {addressesExpanded && (
                                          <ul className="mt-1 space-y-0.5">
                                            {extraAddresses.map((addr) => (
                                              <li key={addr} className="text-[10px] text-zinc-400 truncate">{addr}</li>
                                            ))}
                                          </ul>
                                        )}
                                      </>
                                    )}
                                    <p className={`text-[10px] mt-0.5 ${isVisible ? "text-indigo-400/60" : "text-zinc-600"}`}>
                                      {plan.plan} · {plan.lot_count} lots · {plan.total_area_sqm.toLocaleString()} m² · {(plan.distance_m / 1000).toFixed(1)} km
                                    </p>
                                  </div>
                                  <div className="flex items-center gap-0.5 flex-shrink-0 mt-0.5">
                                    <button
                                      onClick={() => {
                                        if (!isVisible) {
                                          setVisibleNearbyPlans((prev) => new Set(prev).add(plan.plan));
                                        }
                                        setFocusedNearbyPlan(plan.centroid);
                                      }}
                                      className={`p-1 rounded transition-colors ${isVisible ? "text-indigo-400/70 hover:text-indigo-300" : "text-zinc-700 hover:text-zinc-400"}`}
                                      title="Locate on map"
                                    >
                                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                                        <path d="M12 22c1-4 6-7 6-12a6 6 0 10-12 0c0 5 5 8 6 12z" />
                                        <circle cx="12" cy="10" r="2" />
                                      </svg>
                                    </button>
                                    <button
                                      onClick={() =>
                                        setVisibleNearbyPlans((prev) => {
                                          const next = new Set(prev);
                                          next.has(plan.plan) ? next.delete(plan.plan) : next.add(plan.plan);
                                          return next;
                                        })
                                      }
                                      className={`p-1 rounded transition-colors ${
                                        isVisible
                                          ? "text-indigo-400 hover:text-indigo-300"
                                          : "text-zinc-700 hover:text-zinc-500"
                                      }`}
                                      title={isVisible ? "Hide on map" : "Show on map"}
                                    >
                                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                                        {isVisible ? (
                                          <>
                                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z" />
                                            <circle cx="12" cy="12" r="3" />
                                          </>
                                        ) : (
                                          <>
                                            <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94" />
                                            <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19" />
                                            <line x1="1" y1="1" x2="23" y2="23" />
                                          </>
                                        )}
                                      </svg>
                                    </button>
                                  </div>
                                </div>
                              );
                            })}
                            {totalPages > 1 && (
                              <div className="flex items-center justify-between px-3 py-2 border-t border-white/[0.03]">
                                <button
                                  onClick={() => setBandPage((prev) => ({ ...prev, [key]: Math.max(0, currentPage - 1) }))}
                                  disabled={currentPage === 0}
                                  className="text-[10px] text-zinc-500 hover:text-zinc-300 disabled:text-zinc-800 disabled:cursor-not-allowed transition-colors"
                                >
                                  ← Prev
                                </button>
                                <span className="text-[10px] text-zinc-600">
                                  {currentPage + 1} / {totalPages}
                                </span>
                                <button
                                  onClick={() => setBandPage((prev) => ({ ...prev, [key]: Math.min(totalPages - 1, currentPage + 1) }))}
                                  disabled={currentPage >= totalPages - 1}
                                  className="text-[10px] text-zinc-500 hover:text-zinc-300 disabled:text-zinc-800 disabled:cursor-not-allowed transition-colors"
                                >
                                  Next →
                                </button>
                              </div>
                            )}
                          </div>
                        );})()}
                        {isExpanded && bandPlans.length === 0 && (
                          <p className="px-3 py-2 pl-8 text-[10px] text-zinc-600">
                            No similar subdivisions in this band
                          </p>
                        )}
                      </div>
                    );
                  })}
                  </>
                  ) : null}
                </SidebarSection>
              )}

              {/* Zoning */}
              <SidebarSection
                title="Zoning"
                icon={
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                    <polygon points="12,2 22,8.5 22,15.5 12,22 2,15.5 2,8.5" />
                    <path d="M12 22V8.5M22 8.5L12 2 2 8.5" />
                  </svg>
                }
              >
                <SidebarRow
                  icon={<ZoneIcon />}
                  label="Zone"
                  value={status.zone_name ?? "—"}
                  valueColor={status.zone_name ? undefined : "text-zinc-500"}
                />
                <SidebarRow
                  icon={<PlanIcon />}
                  label="Lot / Plan"
                  value={`${status.cadastre_lot} / ${status.cadastre_plan}`}
                />
                <div className="px-3 py-1.5">
                  <a
                    href={`https://apps.information.qld.gov.au/data/cadastre/GenerateSmartMap?q=${encodeURIComponent(`${status.cadastre_lot}\\${status.cadastre_plan}`)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
                  >
                    <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                      <polyline points="15 3 21 3 21 9" />
                      <line x1="10" y1="14" x2="21" y2="3" />
                    </svg>
                    View Smart Map (QLD)
                  </a>
                </div>
              </SidebarSection>
            </div>
          </div>

          {/* CTA */}
          {typeInfo.allowSubdivision && (
            <div className="p-4 border-t border-white/[0.06]">
              <button className="w-full py-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white text-sm font-semibold transition-colors">
                Search Again
              </button>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

// ─── Shell for loading / error states ─────────────────────────────────────

function DarkShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen bg-[#111118] text-white flex flex-col">
      <nav className="flex items-center px-4 py-3 border-b border-white/[0.06]">
        <Link href="/" className="font-semibold text-white text-sm tracking-tight hover:text-zinc-300 transition-colors">
          PropertyProfiler
        </Link>
      </nav>
      <div className="flex-1">{children}</div>
    </div>
  );
}

// ─── Nav icon button ──────────────────────────────────────────────────────

function NavIcon({
  children,
  tooltip,
  active,
  badge,
  href,
  onClick,
}: {
  children: React.ReactNode;
  tooltip: string;
  active?: boolean;
  badge?: boolean;
  href?: string;
  onClick?: () => void;
}) {
  const cls = `relative p-2 rounded-lg transition-all ${
    active
      ? "bg-emerald-500/15 text-emerald-400"
      : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04]"
  }`;

  const inner = (
    <>
      {children}
      {badge && (
        <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-emerald-400" />
      )}
    </>
  );

  if (href) {
    return (
      <Link href={href} className={cls} title={tooltip}>
        {inner}
      </Link>
    );
  }

  return (
    <button className={cls} title={tooltip} onClick={onClick}>
      {inner}
    </button>
  );
}

// ─── Sidebar components ───────────────────────────────────────────────────

function SidebarSection({
  title,
  icon,
  info,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  info?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="relative group flex items-center gap-2 mb-2">
        <span className="text-zinc-600">{icon}</span>
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
          {title}
        </h3>
        {info && (
          <>
            <button className="w-3.5 h-3.5 rounded-full border border-zinc-700 text-zinc-600 hover:text-zinc-400 hover:border-zinc-500 transition-colors flex items-center justify-center text-[9px] leading-none flex-shrink-0 ml-0.5">
              i
            </button>
            <div className="absolute left-0 top-full mt-1 z-50 hidden group-hover:block w-64 bg-zinc-900 border border-white/10 rounded-lg shadow-xl p-3 text-[11px] text-zinc-300 leading-relaxed whitespace-pre-line">
              {info}
            </div>
          </>
        )}
      </div>
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] divide-y divide-white/[0.04]">
        {children}
      </div>
    </div>
  );
}

function SidebarRow({
  icon,
  label,
  value,
  highlight,
  valueColor,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  highlight?: boolean;
  valueColor?: string;
}) {
  return (
    <div className="flex items-center justify-between px-3 py-2.5 gap-3">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-zinc-600 flex-shrink-0">{icon}</span>
        <span className="text-xs text-zinc-400 truncate">{label}</span>
      </div>
      <span
        className={`text-xs font-semibold tabular-nums flex-shrink-0 ${
          valueColor ?? (highlight ? "text-white" : "text-zinc-300")
        }`}
      >
        {value}
      </span>
    </div>
  );
}

// ─── Icons ────────────────────────────────────────────────────────────────

function LotIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
    </svg>
  );
}

function PlanIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="4" y="4" width="16" height="16" rx="1" />
      <path d="M4 10h16M10 4v16" />
    </svg>
  );
}

function CouncilIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M12 2L2 7h20L12 2z" />
      <path d="M4 7v10h16V7" />
      <path d="M4 17h16v2H4z" />
      <path d="M8 7v10M12 7v10M16 7v10" />
    </svg>
  );
}

function FreeSpaceIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="3" y="3" width="18" height="18" rx="2" strokeDasharray="4 2" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function StructuresIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 21h18M5 21V11l7-5 7 5v10" />
      <rect x="9" y="15" width="6" height="6" />
    </svg>
  );
}

function PoolIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M2 12c2-2 4-2 6 0s4 2 6 0 4-2 6 0" />
      <path d="M2 17c2-2 4-2 6 0s4 2 6 0 4-2 6 0" />
      <path d="M6 8V4M18 8V4" />
    </svg>
  );
}

function BuildingCountIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="3" y="8" width="8" height="13" rx="1" />
      <rect x="13" y="3" width="8" height="18" rx="1" />
      <path d="M6 12h2M6 15h2M16 7h2M16 10h2M16 13h2" />
    </svg>
  );
}

function AreaIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 7v14h14" />
      <path d="M7 3v14h14" />
      <rect x="10" y="6" width="8" height="8" rx="1" />
    </svg>
  );
}

function ActivityIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <circle cx="12" cy="12" r="2" />
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  );
}

function ZoneIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M12 22c1-4 6-7 6-12a6 6 0 10-12 0c0 5 5 8 6 12z" />
      <circle cx="12" cy="10" r="2" />
    </svg>
  );
}

function Spinner({ className }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className ?? "w-5 h-5"}`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
