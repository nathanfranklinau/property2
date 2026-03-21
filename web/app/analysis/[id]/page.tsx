"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";

const PropertyMap = dynamic(() => import("@/components/PropertyMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-[#10101e] animate-pulse" />
  ),
});

import { simplifyFootprint, computeBufferCoords, type BuildingFootprint } from "@/components/PropertyMap";
import { classifyProperty, PROPERTY_TYPE_COLORS, type PropertyType, type PropertyTypeInfo } from "@/lib/property-type";
import { PlanTypeIcon } from "@/components/PlanTypeIcon";
import { getZoneDefinition } from "@/lib/zone-definitions";
import { getZoneRules } from "@/lib/zone-rules";
import { DAActivityPanel, buildDAMapMarkers } from "@/components/DAActivityPanel";

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

type CityPlanData = {
  zone: {
    lvl1_zone: string;
    zone: string;
    zone_precinct: string | null;
    building_height: string | null;
    bh_category: string | null;
  } | null;
  building_height: {
    height_in_metres: string;
    storey_number: string;
    height_label: string;
  } | null;
  bushfire_hazard: { level: string } | null;
  dwelling_house_overlay: boolean;
  minimum_lot_size: { mls: string } | null;
  airport_noise: { sensitive_use_type: string; buffer_source: string } | null;
  residential_density: { code: string } | null;
  buffer_area: boolean;
  flood: { level: string } | null;
  heritage: { place_name: string; lhr_id: string; qld_heritage_register: string | null; register_status: string | null } | null;
  heritage_proximity: { place_name: string } | null;
  environmental_significance: string[] | null;
  corner_lot: boolean;
};

type NearbyPlan = {
  plan: string;
  addresses: string[];
  lot_count: number;
  total_area_sqm: number;
  distance_m: number;
  centroid: { lat: number; lng: number };
  boundary_coords: [number, number][][];
  zone_name: string | null;
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

const UNIT_TYPE_LABELS: Record<string, string> = {
  U: "Unit",
  UNIT: "Unit",
  T: "Townhouse",
  V: "Villa",
  APT: "Apartment",
  FLAT: "Flat",
  SE: "Suite",
  SHOP: "Shop",
  OFFICE: "Office",
  STUDIO: "Studio",
  LOT: "Lot",
};

// ─── City Plan helpers ───────────────────────────────────────────────────

function zoneColor(lvl1: string): string {
  const z = lvl1.toLowerCase();
  if (z.includes("low density res"))    return "bg-emerald-500/15 text-emerald-400";
  if (z.includes("medium density res")) return "bg-blue-500/15 text-blue-400";
  if (z.includes("high density res"))   return "bg-indigo-500/15 text-indigo-400";
  if (z.includes("rural res"))          return "bg-lime-500/15 text-lime-400";
  if (z.includes("rural"))              return "bg-amber-500/15 text-amber-400";
  if (z.includes("conservation"))       return "bg-green-500/15 text-green-400";
  if (z.includes("centre"))             return "bg-purple-500/15 text-purple-400";
  if (z.includes("mixed use"))          return "bg-cyan-500/15 text-cyan-400";
  if (z.includes("waterfront"))         return "bg-sky-500/15 text-sky-400";
  if (z.includes("extractive"))         return "bg-stone-500/15 text-stone-400";
  if (z.includes("high impact"))        return "bg-red-500/15 text-red-400";
  if (z.includes("medium impact"))      return "bg-orange-500/15 text-orange-400";
  if (z.includes("low impact"))         return "bg-yellow-500/15 text-yellow-400";
  if (z.includes("open space"))         return "bg-teal-500/15 text-teal-400";
  if (z.includes("sport"))             return "bg-teal-500/15 text-teal-400";
  if (z.includes("community"))          return "bg-pink-500/15 text-pink-400";
  if (z.includes("township"))           return "bg-yellow-500/15 text-yellow-400";
  if (z.includes("innovation"))         return "bg-violet-500/15 text-violet-400";
  if (z.includes("emerging"))           return "bg-sky-500/15 text-sky-400";
  if (z.includes("tourism"))            return "bg-rose-500/15 text-rose-400";
  if (z.includes("special"))            return "bg-fuchsia-500/15 text-fuchsia-400";
  if (z.includes("limited"))            return "bg-zinc-500/15 text-zinc-400";
  if (z.includes("unzoned"))            return "bg-zinc-500/15 text-zinc-500";
  return "bg-white/[0.08] text-zinc-300";
}

/** Returns an inline SVG icon specific to the Gold Coast zone type */
function zoneIcon(lvl1: string): React.ReactNode {
  const z = lvl1.toLowerCase();
  const cls = "w-3.5 h-3.5 flex-shrink-0";

  // Low density residential — single house with pitched roof
  if (z.includes("low density res")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M4 12l8-7 8 7" /><path d="M6 10.5v9h12v-9" /><path d="M10 19.5v-5h4v5" />
    </svg>
  );
  // Medium density residential — duplex / side-by-side houses
  if (z.includes("medium density res")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 13l5-5 4 4 4-4 5 5" /><path d="M5 12v8h6v-8" /><path d="M13 12v8h6v-8" />
      <path d="M7 16h2M15 16h2" />
    </svg>
  );
  // High density residential — tall apartment tower
  if (z.includes("high density res")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="6" y="3" width="12" height="18" rx="1" /><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2" />
      <path d="M10 21v-3h4v3" />
    </svg>
  );
  // Rural residential — house with fence and tree
  if (z.includes("rural res")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 14l5-5 5 5" /><path d="M5 13v7h8v-7" /><path d="M8 20v-3h2v3" />
      <circle cx="19" cy="9" r="3" /><path d="M19 12v8" /><path d="M15 20h8" />
    </svg>
  );
  // Rural — wheat/crop field
  if (z.includes("rural")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M12 21V8" /><path d="M8 10c2-2 4 0 4 0s2-2 4 0" />
      <path d="M7 7c2.5-3 5 0 5 0s2.5-3 5 0" /><path d="M9 4c1.5-2 3 0 3 0s1.5-2 3 0" />
      <path d="M3 21h18" />
    </svg>
  );
  // Conservation — leaf inside shield
  if (z.includes("conservation")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M12 3C8 7 5 10 5 14c0 4 3.5 7 7 7s7-3 7-7c0-4-3-7-7-11z" />
      <path d="M12 21c0-5 4-8 4-8" /><path d="M12 17c-2-2-3-5-1-8" />
    </svg>
  );
  // Open space — tree in park
  if (z.includes("open space")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <circle cx="12" cy="8" r="5" /><path d="M12 13v8" /><path d="M7 21h10" />
      <path d="M9 11l3 2 3-2" />
    </svg>
  );
  // Centre — city skyline
  if (z.includes("centre") && !z.includes("neighbour")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="3" y="10" width="5" height="11" rx="0.5" /><rect x="10" y="4" width="5" height="17" rx="0.5" />
      <rect x="17" y="7" width="5" height="14" rx="0.5" /><path d="M4.5 14h2M11.5 8h2M18.5 11h2M11.5 12h2" />
    </svg>
  );
  // Neighbourhood centre — shopfront with awning
  if (z.includes("neighbour")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 10l2-6h14l2 6" /><path d="M3 10c0 2 1.5 2 3 2s3 0 3-2" /><path d="M9 10c0 2 1.5 2 3 2s3 0 3-2" />
      <path d="M15 10c0 2 1.5 2 3 2s3 0 3-2" /><path d="M4 12v9h16v-9" /><path d="M9 21v-5h6v5" />
    </svg>
  );
  // Mixed use — building: shop ground floor + residential above
  if (z.includes("mixed use")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="4" y="3" width="16" height="18" rx="1" /><path d="M4 14h16" />
      <path d="M8 7h3M13 7h3M8 10h3M13 10h3" /><path d="M8 17h2v4h-2zM14 17h2v4h-2z" />
    </svg>
  );
  // Community facilities — people group
  if (z.includes("community")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <circle cx="8" cy="7" r="2.5" /><circle cx="16" cy="7" r="2.5" />
      <path d="M3 21c0-3.5 2.5-6 5-6s5 2.5 5 6" /><path d="M13 21c0-3.5 2-6 3-6" />
      <path d="M11 21c0-3.5 2.5-6 5-6s5 2.5 5 6" />
    </svg>
  );
  // Township — cluster of small buildings
  if (z.includes("township")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M2 15l4-4 4 4" /><path d="M4 14v7h4v-7" />
      <path d="M10 12l4-5 4 5" /><path d="M12 11v10h4v-10" />
      <path d="M18 15l3-3 1 1" /><path d="M19 14v7h3v-7" />
    </svg>
  );
  // Innovation — lightbulb with gear
  if (z.includes("innovation")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M9 18h6M10 21h4" /><path d="M12 2a7 7 0 00-4 12.7V17h8v-2.3A7 7 0 0012 2z" />
      <path d="M12 6v4l2 2" />
    </svg>
  );
  // Sport and recreation — running figure
  if (z.includes("sport")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <circle cx="14" cy="4" r="2" /><path d="M8 21l2-7 4 2v-5l3-3" />
      <path d="M10 14l-4-2" /><path d="M16 11l2 3h3" />
    </svg>
  );
  // Emerging community — seedling sprouting
  if (z.includes("emerging")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M12 21v-9" /><path d="M12 12c-3 0-6-3-6-6 3 0 6 3 6 6z" />
      <path d="M12 12c3 0 6-4 6-7-3 0-6 4-6 7z" /><path d="M7 21h10" />
    </svg>
  );
  // Special purpose — star badge
  if (z.includes("special")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" />
    </svg>
  );
  // Major tourism — palm tree
  if (z.includes("tourism")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M13 21V10" /><path d="M13 10c-4-1-7 2-10 1 3-3 5-6 10-5" />
      <path d="M13 10c4-1 7 2 10 1-3-3-5-6-10-5" /><path d="M13 7c1-4 4-5 6-5-1 3-3 5-6 5z" />
      <path d="M8 21h10" />
    </svg>
  );
  // Waterfront and marine industry — anchor
  if (z.includes("waterfront")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <circle cx="12" cy="5" r="2" /><path d="M12 7v13" /><path d="M8 11h8" />
      <path d="M5 18c0-4 3.5-7 7-7s7 3 7 7" /><path d="M5 18h14" />
    </svg>
  );
  // Extractive industry — pickaxe
  if (z.includes("extractive")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M14 4l6 6-2 2-6-6" /><path d="M6 18L14 10" /><path d="M4 20l2-2" />
      <path d="M18 4c0 0 2 0 2 2" /><path d="M3 21h8" /><path d="M11 21v-4" />
    </svg>
  );
  // High impact industry — factory with smoke stacks
  if (z.includes("high impact")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M4 21V11l5 3V9l5 3V8l6 4v9" /><path d="M4 21h16" />
      <path d="M17 8V4" /><path d="M17 4c0-1 1-2 2-1" /><path d="M14 8V5" /><path d="M14 5c0-1 1-2 2-1" />
    </svg>
  );
  // Medium impact industry — factory with chimney
  if (z.includes("medium impact")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M4 21V11l5 3V9l5 3v9" /><path d="M14 21h6V12l-6 3" /><path d="M4 21h16" />
      <path d="M18 12V7" /><path d="M18 7c0-1 1-1.5 1.5-0.5" />
    </svg>
  );
  // Low impact industry — warehouse
  if (z.includes("low impact")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 12l9-6 9 6" /><path d="M5 11v10h14V11" />
      <path d="M9 21v-5h6v5" /><path d="M9 13h6" />
    </svg>
  );
  // Limited development — lock/restricted
  if (z.includes("limited")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="5" y="11" width="14" height="10" rx="1.5" /><path d="M8 11V7a4 4 0 018 0v4" />
      <circle cx="12" cy="16" r="1.5" /><path d="M12 17.5V19" />
    </svg>
  );
  // Unzoned — question mark
  if (z.includes("unzoned")) return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <circle cx="12" cy="12" r="9" /><path d="M9 9c0-1.7 1.3-3 3-3s3 1.3 3 3-1.5 2-3 3v1" />
      <circle cx="12" cy="18" r="0.5" fill="currentColor" />
    </svg>
  );
  // Fallback — generic map pin
  return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M12 22c1-4 6-7 6-12a6 6 0 10-12 0c0 5 5 8 6 12z" />
      <circle cx="12" cy="10" r="2" />
    </svg>
  );
}

function heightColor(h: string): string {
  if (h === "HX") return "text-violet-400";
  const m = parseFloat(h);
  if (isNaN(m)) return "text-zinc-300";
  if (m <= 9)  return "text-emerald-400";
  if (m <= 15) return "text-teal-400";
  if (m <= 25) return "text-blue-400";
  if (m <= 40) return "text-indigo-400";
  return "text-purple-400";
}

function densityColor(code: string): string {
  if (code.startsWith("LDR")) return "text-emerald-400";
  const n = parseInt(code.replace("RD", "").replace("A", ""));
  if (isNaN(n)) return "text-zinc-300";
  if (n <= 2) return "text-emerald-400";
  if (n <= 4) return "text-teal-400";
  if (n <= 6) return "text-blue-400";
  return "text-indigo-400";
}

function bushfireIconColor(level: string): string {
  if (level.includes("Very High")) return "text-red-500";
  if (level.includes("High"))      return "text-orange-500";
  if (level.includes("Medium"))    return "text-amber-500";
  return "text-yellow-500";
}

function bushfireTextColor(level: string): string {
  if (level.includes("Very High")) return "text-red-400";
  if (level.includes("High"))      return "text-orange-400";
  if (level.includes("Medium"))    return "text-amber-400";
  return "text-yellow-400";
}

function bushfireBadge(level: string): string {
  if (level.includes("Very High")) return "bg-red-500/20 text-red-400";
  if (level.includes("High"))      return "bg-orange-500/20 text-orange-400";
  if (level.includes("Medium"))    return "bg-amber-500/20 text-amber-400";
  return "bg-yellow-500/20 text-yellow-400";
}

function bushfireSeverity(level: string): string {
  if (level.includes("Very High")) return "Very High";
  if (level.includes("High"))      return "High";
  if (level.includes("Medium"))    return "Medium";
  return "Buffer";
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
    counts: { km0_2: number; km2_5: number; km5_10: number; km10_20: number };
    plans: NearbyPlan[];
  } | null>(null);
  const [nearbyLoading, setNearbyLoading] = useState(false);
  const [expandedBands, setExpandedBands] = useState<Set<string>>(new Set());
  const [visibleNearbyPlans, setVisibleNearbyPlans] = useState<Set<string>>(new Set());
  const [focusedNearbyPlan, setFocusedNearbyPlan] = useState<{ lat: number; lng: number } | null>(null);
  const [expandedPlanAddresses, setExpandedPlanAddresses] = useState<Set<string>>(new Set());
  const [nearbySearch, setNearbySearch] = useState("");
  const [bandPage, setBandPage] = useState<Record<string, number>>({});
  const [addressesOpen, setAddressesOpen] = useState(false);
  const [unitAddresses, setUnitAddresses] = useState<string[] | null>(null);
  const [unitAddressesLoading, setUnitAddressesLoading] = useState(false);
  const [cityPlan, setCityPlan] = useState<CityPlanData | null>(null);
  const [das, setDas] = useState<import("@/app/api/analysis/das/route").DevelopmentApplication[] | null>(null);
  const [dasLoading, setDasLoading] = useState(false);
  const [nearbyDAs, setNearbyDAs] = useState<import("@/app/api/analysis/nearby-das/route").NearbyDA[] | null>(null);
  const [nearbyDAsLoading, setNearbyDAsLoading] = useState(false);
  const [nearbyDARadius, setNearbyDARadius] = useState(1000);
  const [nearbyDATotal, setNearbyDATotal] = useState(0);
  const [nearbyDASummary, setNearbyDASummary] = useState<{ by_type: Record<string, number>; by_category: Record<string, number>; by_status: Record<string, number> } | null>(null);
  const [showDAsOnMap, setShowDAsOnMap] = useState(false);

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
    return Math.max(0, status.lot_area_sqm - totalStructuresArea);
  }, [status?.lot_area_sqm, status?.available_space_sqm, totalStructuresArea]);

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
          // Fetch City Plan data (Gold Coast only — API returns null for other LGAs)
          fetch(`/api/analysis/cityplan?parcel_id=${encodeURIComponent(parcelId)}`)
            .then((r) => r.ok ? r.json() : null)
            .then((d) => { if (d) setCityPlan(d); })
            .catch(() => {});

          setDasLoading(true);
          fetch(`/api/analysis/das?parcel_id=${encodeURIComponent(parcelId)}`)
            .then((r) => r.ok ? r.json() : null)
            .then((d) => { setDas(d ? d.applications : []); })
            .catch(() => { setDas([]); })
            .finally(() => setDasLoading(false));

          setNearbyLoading(true);
          fetch(`/api/analysis/nearby-subdivisions?parcel_id=${encodeURIComponent(parcelId)}`)
            .then((r) => {
              if (!r.ok) {
                console.warn(`Nearby subdivisions API returned ${r.status}`);
                return { counts: { km0_2: 0, km2_5: 0, km5_10: 0, km10_20: 0 }, plans: [] };
              }
              return r.json();
            })
            .then((d) => {
              // Ensure the response has the expected structure
              if (d && typeof d === 'object') {
                setNearbyData({
                  counts: d.counts || { km0_2: 0, km2_5: 0, km5_10: 0, km10_20: 0 },
                  plans: d.plans || []
                });
              }
            })
            .catch((err) => {
              console.error("Nearby subdivisions error:", err);
              setNearbyData({
                counts: { km0_2: 0, km2_5: 0, km5_10: 0, km10_20: 0 },
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

  // ─── Fetch nearby DAs whenever parcelId or radius changes ───────────────
  useEffect(() => {
    if (!parcelId || das === null) return; // only fetch after property DAs are loaded (confirms Gold Coast)
    setNearbyDAsLoading(true);
    fetch(`/api/analysis/nearby-das?parcel_id=${encodeURIComponent(parcelId)}&radius_m=${nearbyDARadius}`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => {
        if (d) {
          setNearbyDAs(d.applications);
          setNearbyDATotal(d.total);
          setNearbyDASummary(d.summary);
        } else {
          setNearbyDAs(null);
        }
      })
      .catch(() => { setNearbyDAs(null); })
      .finally(() => setNearbyDAsLoading(false));
  }, [parcelId, das, nearbyDARadius]);

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
            <p className="text-sm text-zinc-400 mb-8">
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
                        <span className={`text-sm ${done ? "text-zinc-500 line-through" : active ? "text-white font-medium" : "text-zinc-500"}`}>
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
    <div className="h-screen bg-[#131320] text-white flex flex-col overflow-hidden">
      {/* Top navigation bar */}
      <nav className="flex items-center gap-1 px-3 py-2 border-b border-white/[0.08] bg-[#131320]">
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
                  daMarkers={showDAsOnMap && nearbyDAs ? buildDAMapMarkers(nearbyDAs) : undefined}
                />
              )}
          </div>

          {/* Tab bar */}
          <div className="flex items-center gap-0.5 px-2 py-1.5 border-t border-white/[0.08] bg-[#131320] overflow-x-auto">
            {visibleTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  activeTab === tab.id
                    ? "bg-white/[0.10] text-white"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.05]"
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
            <button className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.05] whitespace-nowrap transition-all">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
              See More
            </button>
          </div>
        </div>

        {/* Right: Sidebar */}
        <aside className="w-[380px] flex-shrink-0 border-l border-white/[0.08] bg-[#1a1a2e] flex flex-col">
          <div className="flex-1 overflow-y-auto pp-sidebar-scroll">
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
                  <p className="text-xs text-zinc-400 mt-0.5">{typeInfo.label}</p>
                  {status.building_name && (
                    <p className="text-xs text-zinc-400">{status.building_name}</p>
                  )}
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
                <div className="rounded-lg bg-blue-500/10 border border-blue-500/20 overflow-hidden">
                  <button
                    onClick={() => {
                      if (!addressesOpen && unitAddresses === null) {
                        setUnitAddressesLoading(true);
                        fetch(`/api/properties/addresses?lot=${encodeURIComponent(status.cadastre_lot)}&plan=${encodeURIComponent(status.cadastre_plan)}`)
                          .then((r) => r.json())
                          .then((d) => setUnitAddresses(d.addresses ?? []))
                          .catch(() => setUnitAddresses([]))
                          .finally(() => setUnitAddressesLoading(false));
                      }
                      setAddressesOpen((o) => !o);
                    }}
                    className="w-full flex items-center justify-between px-3 py-2.5 text-left"
                  >
                    <div>
                      <p className="text-xs font-semibold text-blue-400">
                        {status.address_count ?? 0} {(status.address_count ?? 0) === 1 ? "address" : "addresses"} on this lot
                      </p>
                      {status.flat_types && status.flat_types.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {status.flat_types.map((t) => (
                            <span key={t} className="text-[10px] bg-blue-500/15 border border-blue-500/25 px-2 py-0.5 rounded-full text-blue-300/90 font-medium">
                              {UNIT_TYPE_LABELS[t] ?? t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <svg
                      className={`w-3.5 h-3.5 text-blue-400/50 flex-shrink-0 ml-2 transition-transform ${addressesOpen ? "rotate-180" : ""}`}
                      viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {addressesOpen && (
                    <div className="border-t border-blue-500/10 px-3 pb-3">
                      {unitAddressesLoading ? (
                        <p className="text-[11px] text-blue-400/50 pt-2">Loading…</p>
                      ) : unitAddresses && unitAddresses.length > 0 ? (
                        <ul className="space-y-1.5 pt-2">
                          {unitAddresses.map((addr, i) => (
                            <li key={i} className="text-[11px] text-blue-300/70 flex items-center gap-1.5">
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-400/30 flex-shrink-0" />
                              {addr}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-[11px] text-blue-400/40 pt-2">No addresses found.</p>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Big numbers — lot size, free space, covered */}
              {status.lot_area_sqm != null && (
                <div className="flex items-end gap-4">
                  <div>
                    <p className="text-[11px] text-zinc-400 mb-0.5 uppercase tracking-wider font-medium">Lot Size</p>
                    <p className="text-4xl font-bold tracking-tight tabular-nums leading-none">
                      {Math.round(status.lot_area_sqm).toLocaleString()}
                      <span className="text-lg font-medium text-zinc-300 ml-0.5">m²</span>
                    </p>
                  </div>
                  {freeSpace != null && !isNaN(totalStructuresArea) && (
                    <>
                      <div className="w-px h-8 bg-white/[0.12] mb-1 flex-shrink-0" />
                      <div>
                        <p className="text-[11px] text-zinc-400 mb-0.5 uppercase tracking-wider font-medium">Free</p>
                        <p className="text-2xl font-semibold tracking-tight tabular-nums leading-none text-zinc-200">
                          {Math.round(freeSpace).toLocaleString()}
                          <span className="text-sm font-medium text-zinc-400 ml-0.5">m²</span>
                        </p>
                      </div>
                      <div className="w-px h-8 bg-white/[0.12] mb-1 flex-shrink-0" />
                      <div>
                        <p className="text-[11px] text-zinc-400 mb-0.5 uppercase tracking-wider font-medium">Covered</p>
                        <p className="text-2xl font-semibold tracking-tight tabular-nums leading-none text-zinc-200">
                          {Math.round(Math.min(totalStructuresArea, status.lot_area_sqm)).toLocaleString()}
                          <span className="text-sm font-medium text-zinc-400 ml-0.5">m²</span>
                          <span className="text-xs font-medium text-zinc-500 ml-1.5">
                            {Math.round((Math.min(totalStructuresArea, status.lot_area_sqm) / status.lot_area_sqm) * 100)}%
                          </span>
                        </p>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Dismissible notice */}
              {showNotice && (
                <div className="flex items-start gap-2 rounded-lg bg-amber-500/[0.08] border border-amber-500/20 px-3 py-2.5">
                  <p className="text-[11px] text-amber-300/80 leading-relaxed flex-1">
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

              {/* Your Property */}
              <SidebarSection
                title="Your Property"
                icon={
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <path d="M3 9h18M9 3v18" />
                  </svg>
                }
              >
                <SidebarRow
                  icon={<PlanIcon />}
                  label="Lot / Plan"
                  value={`${status.cadastre_lot} / ${status.cadastre_plan}`}
                />
                <SidebarRow
                  icon={<LotIcon />}
                  label="Lot Size"
                  value={sqm(status.lot_area_sqm)}
                />
                <SidebarRow
                  icon={<CouncilIcon />}
                  label="Council"
                  value={status.lga_name ?? "—"}
                  valueColor={status.lga_name ? undefined : "text-zinc-500"}
                />
                {/* Zone — show from City Plan if available, otherwise from state-level data */}
                {cityPlan?.zone ? (
                  <div className="px-3 py-2.5 flex items-start gap-2">
                    <span className="text-zinc-500 mt-0.5 shrink-0"><CityPlanZoneIcon /></span>
                    <span className="text-xs text-zinc-300 shrink-0">Zone</span>
                    <div className="flex-1 flex flex-col items-end">
                      <ZoneTooltip
                        zoneName={cityPlan.zone.lvl1_zone}
                        lgaName={status?.lga_name ?? null}
                      />
                      {cityPlan.zone.zone_precinct && (
                        <p className="text-[10px] text-zinc-500 mt-0.5">
                          {cityPlan.zone.zone_precinct}
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <SidebarRow
                    icon={<ZoneIcon />}
                    label="Zone"
                    value={status.zone_name ?? "—"}
                    valueColor={status.zone_name ? undefined : "text-zinc-500"}
                  />
                )}
                {propertyType === "special_tenure" && (
                  <SidebarRow
                    icon={<ZoneIcon />}
                    label="Tenure"
                    value={typeInfo.label}
                  />
                )}
                {/* Development Applications (Gold Coast only) */}
                {das !== null && (
                  <PropertyDAList das={das} loading={dasLoading} />
                )}
              </SidebarSection>

              {/* City Plan (Gold Coast only) */}
              {cityPlan && (
                <>
                  {/* Development Potential — merged controls + insights */}
                  {(() => {
                    const hasControls = cityPlan.building_height || cityPlan.minimum_lot_size || cityPlan.residential_density
                      || (!cityPlan.building_height && cityPlan.zone?.building_height && cityPlan.zone.building_height !== "No deisgnated heights");
                    const lotArea = status?.lot_area_sqm;
                    const mls = cityPlan.minimum_lot_size ? parseFloat(cityPlan.minimum_lot_size.mls) : null;
                    const subdivisibleLots = (lotArea && mls && mls > 0) ? Math.floor(lotArea / mls) : null;
                    const zoneRules = getZoneRules(cityPlan.zone?.lvl1_zone ?? null);
                    const maxCover = zoneRules?.maxSiteCover ?? null;
                    const siteCoverHeadroom = (lotArea && maxCover && totalStructuresArea != null)
                      ? Math.max(0, (maxCover * lotArea) - totalStructuresArea)
                      : null;
                    const hasInsights = subdivisibleLots !== null || siteCoverHeadroom !== null || cityPlan.corner_lot;
                    if (!hasControls && !hasInsights) return null;

                    return (
                      <SidebarSection
                        title="Development Potential"
                        icon={<RulerIcon />}
                        info="What can be built on this property — height limits, lot sizes, density, and derived indicators from the Gold Coast City Plan. These are estimates — always verify with a town planner."
                      >
                        {cityPlan.building_height && (
                          <div className="px-3 py-2.5">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="text-zinc-500"><HeightIcon /></span>
                                <span className="text-xs text-zinc-300">Max Building Height</span>
                              </div>
                              <span className={`text-xs font-bold tabular-nums ${heightColor(cityPlan.building_height.height_in_metres)}`}>
                                {cityPlan.building_height.height_label || cityPlan.building_height.height_in_metres}
                              </span>
                            </div>
                            {cityPlan.building_height.storey_number && cityPlan.building_height.storey_number !== "N/A" && (
                              <p className="text-[10px] text-zinc-500 mt-1 pl-6">
                                {cityPlan.building_height.storey_number} {Number(cityPlan.building_height.storey_number) === 1 ? "storey" : "storeys"} max
                              </p>
                            )}
                          </div>
                        )}
                        {!cityPlan.building_height && cityPlan.zone?.building_height && cityPlan.zone.building_height !== "No deisgnated heights" && (
                          <SidebarRow
                            icon={<HeightIcon />}
                            label="Base Height (Zone)"
                            value={cityPlan.zone.building_height}
                          />
                        )}
                        {cityPlan.minimum_lot_size && (
                          <SidebarRow
                            icon={<MinLotIcon />}
                            label="Min Lot Size"
                            value={cityPlan.minimum_lot_size.mls}
                            highlight
                          />
                        )}
                        {cityPlan.residential_density && (
                          <SidebarRow
                            icon={<DensityIcon />}
                            label="Residential Density"
                            value={cityPlan.residential_density.code}
                            valueColor={densityColor(cityPlan.residential_density.code)}
                          />
                        )}
                        {subdivisibleLots !== null && subdivisibleLots >= 2 && (
                          <SidebarRow
                            icon={<SubdivisionPotentialIcon />}
                            label="Potential Lots"
                            value={`${subdivisibleLots}`}
                            valueColor={subdivisibleLots >= 3 ? "text-emerald-400" : "text-zinc-300"}
                          />
                        )}
                        {subdivisibleLots !== null && subdivisibleLots < 2 && (
                          <SidebarRow
                            icon={<SubdivisionPotentialIcon />}
                            label="Potential Lots"
                            value="Below min"
                            valueColor="text-zinc-500"
                          />
                        )}
                        {siteCoverHeadroom !== null && (
                          <SidebarRow
                            icon={<SiteCoverIcon />}
                            label="Site Cover Remaining"
                            value={sqm(siteCoverHeadroom)}
                            valueColor={siteCoverHeadroom > 50 ? "text-emerald-400" : "text-amber-400"}
                            tooltip={`Your zone allows a maximum of ${Math.round((maxCover ?? 0) * 100)}% of the lot to be covered by structures (${sqm(lotArea ? (maxCover ?? 0) * lotArea : null)} allowed).\n\nSource: Gold Coast City Plan, Section 6.2.1`}
                          />
                        )}
                        {cityPlan.corner_lot && (
                          <SidebarRow
                            icon={<CornerLotIcon />}
                            label="Corner Lot"
                            value="Yes"
                            valueColor="text-indigo-400"
                          />
                        )}
                      </SidebarSection>
                    );
                  })()}
                </>
              )}

              {cityPlan && (
                <>
                  {(cityPlan.bushfire_hazard || cityPlan.airport_noise || cityPlan.buffer_area || cityPlan.dwelling_house_overlay || cityPlan.flood || cityPlan.heritage || cityPlan.heritage_proximity || cityPlan.environmental_significance) && (
                    <SidebarSection
                      title="Constraints"
                      icon={<ConstraintIcon />}
                      info="Planning overlays from the Gold Coast City Plan that impose additional requirements on development. These may affect building materials, setbacks, or permissible uses."
                    >
                      {cityPlan.flood && (
                        <div className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className="text-blue-500"><FloodIcon /></span>
                            <div className="flex-1 min-w-0">
                              <span className="text-xs text-zinc-300">Flood Overlay</span>
                              <p className="text-xs font-semibold text-blue-400">Flood assessment required</p>
                              {cityPlan.flood.level && (
                                <p className="text-[10px] text-blue-400/70 mt-0.5">{cityPlan.flood.level}</p>
                              )}
                            </div>
                            <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">
                              Constraint
                            </span>
                          </div>
                        </div>
                      )}
                      {cityPlan.heritage && (
                        <div className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className="text-amber-600"><HeritageIcon /></span>
                            <div className="flex-1 min-w-0">
                              <span className="text-xs text-zinc-300">Heritage Place</span>
                              <p className="text-xs font-semibold text-amber-400">{cityPlan.heritage.place_name}</p>
                              {cityPlan.heritage.qld_heritage_register === "Yes" && (
                                <p className="text-[10px] text-amber-400/70 mt-0.5">QLD Heritage Register listed</p>
                              )}
                            </div>
                            <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400">
                              Heritage
                            </span>
                          </div>
                        </div>
                      )}
                      {!cityPlan.heritage && cityPlan.heritage_proximity && (
                        <div className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className="text-amber-600/70"><HeritageIcon /></span>
                            <div className="flex-1 min-w-0">
                              <span className="text-xs text-zinc-300">Near Heritage Place</span>
                              <p className="text-[10px] text-amber-400/70 mt-0.5">Adjacent to: {cityPlan.heritage_proximity.place_name}</p>
                            </div>
                          </div>
                        </div>
                      )}
                      {cityPlan.environmental_significance && (
                        <div className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className="text-emerald-500"><EnvironmentalIcon /></span>
                            <div className="flex-1 min-w-0">
                              <span className="text-xs text-zinc-300">Environmental Significance</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {cityPlan.environmental_significance.map((cat) => (
                                  <span key={cat} className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400">
                                    {cat}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                      {cityPlan.bushfire_hazard && (
                        <div className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className={bushfireIconColor(cityPlan.bushfire_hazard.level)}><FlameIcon /></span>
                            <div className="flex-1 min-w-0">
                              <span className="text-xs text-zinc-300">Bushfire Hazard</span>
                              <p className={`text-xs font-semibold ${bushfireTextColor(cityPlan.bushfire_hazard.level)}`}>
                                {cityPlan.bushfire_hazard.level.replace(" Potential Bushfire Intensity", "")}
                              </p>
                            </div>
                            <span className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${bushfireBadge(cityPlan.bushfire_hazard.level)}`}>
                              {bushfireSeverity(cityPlan.bushfire_hazard.level)}
                            </span>
                          </div>
                        </div>
                      )}
                      {cityPlan.airport_noise && (
                        <div className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className="text-amber-500"><PlaneIcon /></span>
                            <div className="flex-1 min-w-0">
                              <span className="text-xs text-zinc-300">Airport Noise</span>
                              <p className="text-[10px] text-amber-400/80 mt-0.5">{cityPlan.airport_noise.buffer_source} — ANEF 25+</p>
                            </div>
                          </div>
                        </div>
                      )}
                      {cityPlan.buffer_area && (
                        <div className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className="text-orange-500"><ShieldIcon /></span>
                            <div className="flex-1 min-w-0">
                              <span className="text-xs text-zinc-300">Buffer Area</span>
                              <p className="text-[10px] text-orange-400/80 mt-0.5">Sensitive land use restrictions may apply</p>
                            </div>
                          </div>
                        </div>
                      )}
                      {cityPlan.dwelling_house_overlay && (
                        <div className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className="text-sky-500"><DwellingOverlayIcon /></span>
                            <div className="flex-1 min-w-0">
                              <span className="text-xs text-zinc-300">Dwelling House Overlay</span>
                              <p className="text-[10px] text-sky-400/80 mt-0.5">Single dwelling only — unit &amp; dual-occ development requires a DA</p>
                            </div>
                          </div>
                        </div>
                      )}
                    </SidebarSection>
                  )}
                </>
              )}

              {/* Development Activity (Gold Coast only) */}
              <DAActivityPanel
                parcelDAs={das}
                nearbyDAs={nearbyDAs}
                nearbyTotal={nearbyDATotal}
                nearbySummary={nearbyDASummary}
                nearbyRadius={nearbyDARadius}
                onNearbyRadiusChange={setNearbyDARadius}
                showOnMap={showDAsOnMap}
                onShowOnMapChange={setShowDAsOnMap}
                loading={dasLoading}
                nearbyLoading={nearbyDAsLoading}
              />

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
                  <div className="px-3 py-2 border-b border-white/[0.07]">
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
                        className="w-full bg-white/[0.04] border border-white/[0.08] rounded text-[11px] text-zinc-300 placeholder-zinc-500 pl-6 pr-6 py-1.5 focus:outline-none focus:border-indigo-500/50 focus:bg-white/[0.06] transition-colors"
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
                      { label: "Within 2 km", key: "km0_2" as const, maxDist: 2000, minDist: 0 },
                      { label: "2 km – 5 km", key: "km2_5" as const, maxDist: 5000, minDist: 2000 },
                      { label: "5 km – 10 km", key: "km5_10" as const, maxDist: 10000, minDist: 5000 },
                      { label: "10 km – 20 km", key: "km10_20" as const, maxDist: 20000, minDist: 10000 },
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
                              <span className="text-zinc-500 flex-shrink-0"><ActivityIcon /></span>
                              <span className="text-xs text-zinc-300">{label}</span>
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
                                    <p className={`text-[10px] mt-0.5 ${isVisible ? "text-indigo-400/60" : "text-zinc-500"}`}>
                                      {plan.plan} · {plan.lot_count} lots · {plan.total_area_sqm.toLocaleString()} m² · {(plan.distance_m / 1000).toFixed(1)} km
                                    </p>
                                    {plan.zone_name && (
                                      <div className="mt-1">
                                        <ZoneTooltip zoneName={plan.zone_name} lgaName={status?.lga_name ?? null} />
                                      </div>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-0.5 flex-shrink-0 mt-0.5">
                                    <button
                                      onClick={() => {
                                        if (!isVisible) {
                                          setVisibleNearbyPlans((prev) => new Set(prev).add(plan.plan));
                                        }
                                        setFocusedNearbyPlan(plan.centroid);
                                      }}
                                      className={`p-1 rounded transition-colors ${isVisible ? "text-indigo-400/70 hover:text-indigo-300" : "text-zinc-500 hover:text-zinc-300"}`}
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
                                          : "text-zinc-500 hover:text-zinc-300"
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
                  {visibleNearbyPlans.size > 0 && (() => {
                    const PLAN_META = [
                      { prefix: "SP",  color: "#10B981", label: "Survey Plan",        desc: "Land formally split into separate freehold titles — each owner holds their own piece of ground." },
                      { prefix: "BUP", color: "#6366F1", label: "Building Unit Plan", desc: "Older-style unit scheme (pre-1994) where owners hold a unit in a building with shared common areas." },
                      { prefix: "GTP", color: "#F59E0B", label: "Group Title Plan",   desc: "Townhouses or villas where each home has its own title but owners share common driveways or gardens." },
                    ] as const;
                    const visibleTypes = new Set(
                      [...visibleNearbyPlans].map((p) => p.match(/^(SP|BUP|GTP)/)?.[1]).filter(Boolean)
                    );
                    const active = PLAN_META.filter((m) => visibleTypes.has(m.prefix));
                    if (active.length === 0) return null;
                    return (
                      <div className="px-3 py-2.5 border-t border-white/[0.04] flex items-center gap-3 flex-wrap">
                        <span className="text-[9px] uppercase tracking-widest text-zinc-700 flex-shrink-0">Key</span>
                        {active.map(({ prefix, color, label, desc }) => (
                          <div key={prefix} className="relative group flex items-center gap-1.5 cursor-default">
                            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
                            <span className="text-[10px] font-medium text-zinc-500">{prefix}</span>
                            <div className="absolute bottom-full left-0 mb-2 z-50 hidden group-hover:block w-56 bg-zinc-900 border border-white/10 rounded-lg shadow-xl p-2.5 pointer-events-none">
                              <p className="text-[10px] font-semibold text-zinc-300 mb-1">{prefix} — {label}</p>
                              <p className="text-[10px] text-zinc-500 leading-relaxed">{desc}</p>
                            </div>
                          </div>
                        ))}
                        <a
                          href="/blog/reading-a-cadastral-survey-plan"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-auto text-[9px] text-zinc-700 hover:text-indigo-400 transition-colors flex-shrink-0"
                        >
                          Learn more →
                        </a>
                      </div>
                    );
                  })()}
                  </>
                  ) : null}
                </SidebarSection>
              )}

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
    <div className="h-screen bg-[#131320] text-white flex flex-col">
      <nav className="flex items-center px-4 py-3 border-b border-white/[0.08]">
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
      : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.05]"
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

// ─── Property DA list (inside Your Property section) ─────────────────────

function PropertyDAList({
  das,
  loading,
}: {
  das: import("@/app/api/analysis/das/route").DevelopmentApplication[];
  loading: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  if (loading) {
    return (
      <div className="flex items-center justify-between px-3 py-2.5 gap-3">
        <div className="flex items-center gap-2">
          <span className="text-zinc-500"><DAIcon /></span>
          <span className="text-xs text-zinc-300">Applications</span>
        </div>
        <span className="text-xs text-zinc-500 animate-pulse">loading…</span>
      </div>
    );
  }

  const count = das.length;
  const activeDAs = das.filter(d => {
    const s = (d.status ?? "").toLowerCase();
    return s.includes("current") || s.includes("pending") || s.includes("assessment") || s.includes("lodged");
  });

  function daShortType(appType: string | null): string {
    const t = (appType ?? "").toUpperCase().trim();
    if (t.includes("MATERIAL CHANGE") || t === "MCU") return "MCU";
    if (t.includes("RECONFIGUR") || t === "ROL") return "ROL";
    if (t.includes("OPERATIONAL") || t === "OPW") return "OPW";
    if (t.includes("BUILDING WORK") || t === "BWA" || t === "BA") return "BA";
    if (t.includes("COMBINED")) return "Combined";
    return appType ?? "DA";
  }

  function daStatusStyle(status: string | null): string {
    const s = (status ?? "").toLowerCase();
    if (s.includes("approved") || s.includes("decision made")) return "bg-emerald-500/15 text-emerald-400";
    if (s.includes("refused")) return "bg-red-500/15 text-red-400";
    if (s.includes("withdrawn") || s.includes("lapsed")) return "bg-zinc-600/30 text-zinc-400";
    if (s.includes("current") || s.includes("pending") || s.includes("assessment") || s.includes("lodged")) return "bg-amber-500/15 text-amber-400";
    return "bg-zinc-600/20 text-zinc-400";
  }

  function formatDate(d: string | null): string {
    if (!d) return "";
    const dt = new Date(d);
    if (isNaN(dt.getTime())) return "";
    return dt.toLocaleDateString("en-AU", { month: "short", year: "numeric" });
  }

  return (
    <>
      <div
        className="flex items-center justify-between px-3 py-2.5 gap-3 cursor-pointer hover:bg-white/[0.02] transition-colors"
        onClick={() => count > 0 && setExpanded(e => !e)}
      >
        <div className="flex items-center gap-2">
          <span className="text-zinc-500"><DAIcon /></span>
          <span className="text-xs text-zinc-300">Applications</span>
        </div>
        <div className="flex items-center gap-1.5">
          {activeDAs.length > 0 && (
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse flex-shrink-0" />
          )}
          <span className={`text-xs font-semibold tabular-nums ${count > 0 ? "text-zinc-300" : "text-zinc-500"}`}>
            {count === 0 ? "None" : count}
          </span>
          {count > 0 && (
            <svg className={`w-3 h-3 text-zinc-600 transition-transform ${expanded ? "rotate-180" : ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <polyline points="6 9 12 15 18 9" />
            </svg>
          )}
        </div>
      </div>
      {expanded && count > 0 && (
        <div className="divide-y divide-white/[0.04]">
          {das.map((da) => (
            <div key={da.application_number} className="px-3 py-2.5">
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="text-[10px] font-mono text-zinc-500 flex-shrink-0">{daShortType(da.application_type)}</span>
                  <span className="text-[10px] text-zinc-500 flex-shrink-0">{da.application_number}</span>
                </div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded flex-shrink-0 ${daStatusStyle(da.status)}`}>
                  {da.status ?? "Unknown"}
                </span>
              </div>
              {da.description && (
                <p className="text-[10px] text-zinc-400 leading-relaxed line-clamp-2">{da.description}</p>
              )}
              <div className="flex items-center gap-3 mt-1">
                {da.lodgement_date && (
                  <span className="text-[10px] text-zinc-600">Lodged {formatDate(da.lodgement_date)}</span>
                )}
                {da.decision_date && (
                  <span className="text-[10px] text-zinc-600">Decided {formatDate(da.decision_date)}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function DAIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M9 12h6M9 16h6M9 8h6M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
    </svg>
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
        <span className="text-zinc-300">{icon}</span>
        <h3 className="text-xs font-semibold tracking-wide text-zinc-200">
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
      <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] divide-y divide-white/[0.055]">
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
  tooltip,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  highlight?: boolean;
  valueColor?: string;
  tooltip?: string;
}) {
  return (
    <div className="flex items-center justify-between px-3 py-2.5 gap-3">
      <div className="relative group flex items-center gap-2 min-w-0">
        <span className="text-zinc-500 flex-shrink-0">{icon}</span>
        <span className="text-xs text-zinc-300 truncate">{label}</span>
        {tooltip && (
          <>
            <button className="w-3.5 h-3.5 rounded-full border border-zinc-700 text-zinc-600 hover:text-zinc-400 hover:border-zinc-500 transition-colors flex items-center justify-center text-[9px] leading-none flex-shrink-0">
              i
            </button>
            <div className="absolute left-0 top-full mt-1 z-50 hidden group-hover:block w-56 bg-zinc-900 border border-white/10 rounded-lg shadow-xl p-3 text-[11px] text-zinc-300 leading-relaxed whitespace-pre-line">
              {tooltip}
            </div>
          </>
        )}
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

// ─── City Plan Icons ─────────────────────────────────────────────────────

function RulerIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M21 6L3 6M21 6v12a2 2 0 01-2 2H5a2 2 0 01-2-2V6" />
      <path d="M7 6v4M11 6v3M15 6v4M19 6v3" />
    </svg>
  );
}

/**
 * Zone badge with hover tooltip showing the authoritative purpose statement.
 * Definitions are sourced from each council's published planning scheme via
 * getZoneDefinition() in web/lib/zone-definitions.ts — see that file for
 * exact source citations per LGA.
 */
function ZoneTooltip({ zoneName, lgaName }: { zoneName: string; lgaName: string | null }) {
  const def = getZoneDefinition(lgaName, zoneName);
  const sourceLabel = "Planning Scheme";
  const badgeRef = useRef<HTMLSpanElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  if (!def) {
    return (
      <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg cursor-default ${zoneColor(zoneName)}`}>
        {zoneIcon(zoneName)}
        {zoneName}
      </span>
    );
  }

  return (
    <div className="inline-block">
      <span
        ref={badgeRef}
        className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg cursor-default ${zoneColor(zoneName)}`}
        onMouseEnter={() => {
          const r = badgeRef.current?.getBoundingClientRect();
          if (r) setPos({ top: r.bottom + 6, left: r.left });
        }}
        onMouseLeave={() => setPos(null)}
      >
        {zoneIcon(zoneName)}
        {zoneName}
        <svg className="w-3 h-3 opacity-50 flex-shrink-0 ml-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4M12 8h.01" strokeLinecap="round" />
        </svg>
      </span>
      {pos && (
        <div
          className="fixed w-72 bg-zinc-950 border border-white/10 rounded-xl p-3 text-[11px] text-zinc-300 leading-relaxed shadow-2xl z-[9999] pointer-events-none"
          style={{ top: pos.top, left: pos.left }}
        >
          {sourceLabel && (
            <p className="text-[9px] font-semibold uppercase tracking-wider text-zinc-500 mb-2 flex items-center gap-1.5">
              <svg className="w-2.5 h-2.5 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" />
              </svg>
              {sourceLabel}
            </p>
          )}
          {def}
        </div>
      )}
    </div>
  );
}

function CityPlanZoneIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 6l9-4 9 4" />
      <path d="M3 6v12l9 4 9-4V6" />
      <path d="M3 18l9-4 9 4" />
      <path d="M12 2v20" />
    </svg>
  );
}

function HeightIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M12 3v18" />
      <path d="M8 7l4-4 4 4" />
      <path d="M8 17l4 4 4-4" />
      <path d="M4 12h16" />
    </svg>
  );
}

function MinLotIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="4" y="4" width="16" height="16" rx="1" strokeDasharray="3 2" />
      <path d="M4 12h16" />
      <path d="M12 4v16" />
    </svg>
  );
}

function DensityIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="3" y="13" width="5" height="8" rx="1" />
      <rect x="10" y="8" width="5" height="13" rx="1" />
      <rect x="17" y="3" width="5" height="18" rx="1" />
    </svg>
  );
}

function ConstraintIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M12 2L2 22h20L12 2z" />
      <path d="M12 9v5" />
      <circle cx="12" cy="17" r="0.5" fill="currentColor" />
    </svg>
  );
}

function FlameIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M12 22c4-3 7-6 7-10a7 7 0 00-7-9c-1 3-3 5-5 6a7 7 0 00-2 5c0 4 3 6 7 8z" />
      <path d="M12 22c-2-1.5-3-3-3-5a3 3 0 013-3 3 3 0 013 3c0 2-1 3.5-3 5z" />
    </svg>
  );
}

function PlaneIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 10-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M12 2l8 4v5c0 5.25-3.5 9.75-8 11-4.5-1.25-8-5.75-8-11V6l8-4z" />
      <path d="M12 8v4M12 16h.01" />
    </svg>
  );
}

function SubdivisionPotentialIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="3" y="3" width="8" height="8" rx="1" />
      <rect x="13" y="3" width="8" height="8" rx="1" />
      <rect x="3" y="13" width="8" height="8" rx="1" />
      <rect x="13" y="13" width="8" height="8" rx="1" />
    </svg>
  );
}

function SiteCoverIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <rect x="6" y="6" width="8" height="8" rx="1" fill="currentColor" opacity={0.3} />
    </svg>
  );
}

function CornerLotIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 3h18v18" />
      <path d="M3 3v18h18" />
      <path d="M7 7h10v10H7z" strokeDasharray="3 2" />
    </svg>
  );
}


function FloodIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 17c1.5-2 3-3 4.5-1s3 1 4.5-1 3-3 4.5-1 3 1 4.5-1" />
      <path d="M3 21c1.5-2 3-3 4.5-1s3 1 4.5-1 3-3 4.5-1 3 1 4.5-1" />
      <path d="M12 3v10M8 7l4-4 4 4" />
    </svg>
  );
}

function HeritageIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 21h18" />
      <path d="M5 21V7l7-4 7 4v14" />
      <path d="M9 21v-4h6v4" />
      <path d="M9 10h1M14 10h1" />
    </svg>
  );
}

function EnvironmentalIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M12 22c-4 0-8-2-8-8 0-4 4-11 8-11s8 7 8 11c0 6-4 8-8 8z" />
      <path d="M12 22V8" />
      <path d="M8 14c2-1 4 0 4 0" />
      <path d="M16 12c-2-1-4 0-4 0" />
    </svg>
  );
}

function DwellingOverlayIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 12l9-8 9 8" />
      <path d="M5 10v10h14V10" />
      <path d="M9 21v-6h6v6" />
      <path d="M16 5l3 2.5" strokeDasharray="2 2" />
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
