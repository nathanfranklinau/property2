"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";

const PropertyMap = dynamic(() => import("@/components/PropertyMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full aspect-[4/3] rounded-xl bg-zinc-100 animate-pulse" />
  ),
});

import { simplifyFootprint, type BuildingFootprint } from "@/components/PropertyMap";

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
};

// Derive a simplified pipeline stage from the raw status fields
type Stage = "queuing" | "imagery" | "analysing" | "complete" | "failed";

function getStage(status: AnalysisStatus): Stage {
  if (
    status.analysis_status === "failed" ||
    status.image_status === "failed"
  ) {
    return "failed";
  }
  if (status.analysis_status === "complete") return "complete";
  if (
    status.image_status === "complete" ||
    status.analysis_status === "running"
  ) {
    return "analysing";
  }
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

function sqm(value: number | null): string {
  if (value == null) return "—";
  return `${Math.round(value).toLocaleString()} m²`;
}

export default function AnalysisPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const parcelId = params.id;

  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [footprints, setFootprints] = useState<BuildingFootprint[]>([]);
  const [footprintsInitialized, setFootprintsInitialized] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

      // Initialize footprints from API data once (on first complete)
      if (!footprintsInitialized && data.building_footprints_geo) {
        setFootprints(data.building_footprints_geo.map(simplifyFootprint));
        setFootprintsInitialized(true);
      }

      const stage = getStage(data);
      if (stage === "complete" || stage === "failed") {
        if (intervalRef.current) clearInterval(intervalRef.current);
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

  if (fetchError) {
    return (
      <Shell>
        <div className="text-center py-20">
          <p className="text-zinc-500 mb-6">{fetchError}</p>
          <Link
            href="/"
            className="text-zinc-900 font-medium underline underline-offset-4"
          >
            Start a new search
          </Link>
        </div>
      </Shell>
    );
  }

  if (!status) {
    return (
      <Shell>
        <div className="flex justify-center py-20">
          <Spinner className="w-6 h-6 text-zinc-400" />
        </div>
      </Shell>
    );
  }

  const stage = getStage(status);

  return (
    <Shell>
      {/* Address header */}
      <div className="mb-8">
        <p className="text-sm text-zinc-400 mb-1">
          <Link href="/" className="hover:text-zinc-600 transition-colors">
            &larr; New search
          </Link>
        </p>
        <h1 className="text-xl font-semibold text-zinc-900">
          {status.display_address ?? `Lot ${status.cadastre_lot} on ${status.cadastre_plan}`}
        </h1>
        <p className="text-sm text-zinc-500 mt-0.5">
          Lot {status.cadastre_lot} on {status.cadastre_plan}
          {status.lot_area_sqm
            ? ` · ${Math.round(status.lot_area_sqm).toLocaleString()} m²`
            : ""}
        </p>
      </div>

      {/* Progress steps */}
      {stage !== "complete" && stage !== "failed" && (
        <div className="mb-10">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-4">
            Analysing your property
          </h2>
          <ol className="space-y-3">
            {STEPS.map((step) => {
              const done = stepDone(step.id, stage);
              const active = stepActive(step.id, stage);
              return (
                <li key={step.id} className="flex items-center gap-3">
                  <span
                    className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center ${
                      done
                        ? "bg-green-500"
                        : active
                        ? "border-2 border-zinc-900"
                        : "border-2 border-zinc-200"
                    }`}
                  >
                    {done && (
                      <svg
                        className="w-3 h-3 text-white"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={3}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    )}
                    {active && (
                      <span className="w-1.5 h-1.5 rounded-full bg-zinc-900 animate-pulse" />
                    )}
                  </span>
                  <span
                    className={`text-sm ${
                      done
                        ? "text-zinc-400 line-through"
                        : active
                        ? "text-zinc-900 font-medium"
                        : "text-zinc-400"
                    }`}
                  >
                    {step.label}
                  </span>
                  {active && (
                    <Spinner className="w-4 h-4 text-zinc-400 ml-auto" />
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {/* Error state */}
      {stage === "failed" && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-4 mb-8">
          <p className="text-sm font-medium text-red-700">Analysis failed</p>
          {status.error_message && (
            <p className="text-sm text-red-600 mt-1">{status.error_message}</p>
          )}
          <button
            onClick={() => router.push("/")}
            className="mt-3 text-sm text-red-700 underline underline-offset-4"
          >
            Try a different address
          </button>
        </div>
      )}

      {/* Results */}
      {stage === "complete" && (
        <div className="space-y-6">
          <div className="flex items-center gap-2 text-green-600 mb-2">
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span className="text-sm font-semibold">Analysis complete</span>
          </div>

          {/* Live satellite map hero */}
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
              />
            )}

          {/* Lot */}
          <ResultSection title="Lot">
            <DataRow label="Total area" value={sqm(status.lot_area_sqm)} />
            <DataRow
              label="Lot / Plan"
              value={`${status.cadastre_lot} / ${status.cadastre_plan}`}
            />
          </ResultSection>

          {/* Buildings */}
          <ResultSection title="Buildings">
            <DataRow
              label="Buildings marked"
              value={String(footprints.length)}
            />
            <DataRow
              label="Main building (approx.)"
              value={sqm(
                footprints.length > 0
                  ? Math.max(...footprints.map((f) => f.area_sqm))
                  : status.main_house_size_sqm
              )}
              note="Largest building footprint"
            />
            <DataRow
              label="Available space"
              value={sqm(
                status.lot_area_sqm != null
                  ? status.lot_area_sqm -
                      footprints.reduce((sum, f) => sum + f.area_sqm, 0) -
                      (status.pool_area_sqm ?? 0) -
                      50
                  : status.available_space_sqm
              )}
              highlight
              note="Unbuilt area within the lot"
            />
          </ResultSection>

          {/* Pools */}
          <ResultSection title="Swimming Pools">
            <DataRow
              label="Detected in imagery"
              value={
                status.pool_count_detected != null
                  ? String(status.pool_count_detected)
                  : "—"
              }
            />
            <DataRow
              label="Registered with council"
              value={
                status.pool_count_registered != null
                  ? String(status.pool_count_registered)
                  : "—"
              }
            />
            {status.pool_area_sqm != null && status.pool_area_sqm > 0 && (
              <DataRow label="Pool area (approx.)" value={sqm(status.pool_area_sqm)} />
            )}
          </ResultSection>

          {/* CTA placeholder for Phase 2 */}
          <div className="rounded-lg border border-zinc-200 bg-zinc-50 px-5 py-5 mt-2">
            <p className="text-sm font-semibold text-zinc-700 mb-1">
              Next: Assess subdivision potential
            </p>
            <p className="text-sm text-zinc-500">
              A detailed assessment — zoning rules, minimum lot sizes, council
              requirements, and a step-by-step approval roadmap — is coming in
              Phase 2.
            </p>
          </div>

          {/* Pipeline imagery */}
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-3 mt-2">
              Property Imagery
            </h2>
            <div className="grid grid-cols-2 gap-3">
              <DebugImage
                parcelId={status.parcel_id}
                filename="styled_map.png"
                label="Property map"
                desc="Yellow = buildings · Pink = roads"
              />
              <DebugImage
                parcelId={status.parcel_id}
                filename="mask2.png"
                label="Space usage"
                desc="Purple = usable · Yellow = buildings · Green = pools · Pink = roads"
              />
              <DebugImage
                parcelId={status.parcel_id}
                filename="satellite_masked.jpg"
                label="Satellite"
                desc="Property boundary clipped from satellite imagery"
              />
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <header className="border-b border-zinc-100 px-6 py-4">
        <Link
          href="/"
          className="font-semibold text-zinc-900 text-base tracking-tight hover:text-zinc-600 transition-colors"
        >
          SubdivideGuide
        </Link>
      </header>
      <main className="flex-1 w-full max-w-3xl mx-auto px-6 py-10">
        {children}
      </main>
    </div>
  );
}

function ResultSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-3">
        {title}
      </h2>
      <div className="rounded-lg border border-zinc-200 divide-y divide-zinc-100">
        {children}
      </div>
    </div>
  );
}

function DataRow({
  label,
  value,
  note,
  highlight,
}: {
  label: string;
  value: string;
  note?: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-start justify-between px-4 py-3 gap-4">
      <div>
        <p className="text-sm text-zinc-600">{label}</p>
        {note && <p className="text-xs text-zinc-400 mt-0.5">{note}</p>}
      </div>
      <p
        className={`text-sm font-semibold tabular-nums flex-shrink-0 ${
          highlight ? "text-zinc-900" : "text-zinc-700"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function DebugImage({
  parcelId,
  filename,
  label,
  desc,
}: {
  parcelId: string;
  filename: string;
  label: string;
  desc: string;
}) {
  return (
    <div className="rounded-lg overflow-hidden border border-zinc-200 bg-zinc-50">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/images/${parcelId}/${filename}`}
        alt={label}
        className="w-full aspect-square object-cover bg-zinc-100"
      />
      <div className="px-3 py-2 border-t border-zinc-100">
        <p className="text-xs font-semibold text-zinc-700">{label}</p>
        <p className="text-xs text-zinc-400 mt-0.5 leading-snug">{desc}</p>
        <p className="text-xs text-zinc-300 mt-1 font-mono">{filename}</p>
      </div>
    </div>
  );
}

function Spinner({ className }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className ?? "w-5 h-5"}`} fill="none" viewBox="0 0 24 24">
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
