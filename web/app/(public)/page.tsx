"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Script from "next/script";

// Minimal typings for the Google Maps Places API we use
declare global {
  interface Window {
    google: {
      maps: {
        places: {
          Autocomplete: new (
            input: HTMLInputElement,
            opts: {
              types: string[];
              componentRestrictions: { country: string };
              fields: string[];
            }
          ) => {
            addListener: (event: string, handler: () => void) => void;
            getPlace: () => {
              formatted_address?: string;
              geometry?: {
                location: { lat: () => number; lng: () => number };
              };
            };
          };
        };
      };
    };
  }
}

type SelectedPlace = {
  displayAddress: string;
  rawInput: string;
  lat: number;
  lon: number;
};

export default function Home() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedPlace, setSelectedPlace] = useState<SelectedPlace | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function initAutocomplete() {
    if (!inputRef.current || !window.google) return;
    const autocomplete = new window.google.maps.places.Autocomplete(
      inputRef.current,
      {
        types: ["address"],
        componentRestrictions: { country: "au" },
        fields: ["formatted_address", "geometry"],
      }
    );
    autocomplete.addListener("place_changed", () => {
      const place = autocomplete.getPlace();
      if (!place.geometry?.location) return;
      setSelectedPlace({
        displayAddress: place.formatted_address ?? "",
        rawInput: inputRef.current?.value ?? place.formatted_address ?? "",
        lat: place.geometry.location.lat(),
        lon: place.geometry.location.lng(),
      });
      setError(null);
    });
  }

  // In case the script loads before React hydration completes
  useEffect(() => {
    if (window.google) initAutocomplete();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedPlace) return;

    setLoading(true);
    setError(null);

    try {
      // 1. Resolve lat/lon → cadastre parcel
      const lookupRes = await fetch(
        `/api/properties/lookup?lat=${selectedPlace.lat}&lon=${selectedPlace.lon}&address=${encodeURIComponent(selectedPlace.rawInput)}`
      );
      if (!lookupRes.ok) {
        const data = await lookupRes.json();
        throw new Error(
          data.error ??
            "We couldn't find a property at that address. Is it in Queensland?"
        );
      }
      const parcel = await lookupRes.json();

      // 2. Trigger analysis (returns immediately; Python service runs async)
      const analysisRes = await fetch("/api/analysis/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parcel),
      });
      if (!analysisRes.ok) {
        const data = await analysisRes.json();
        throw new Error(data.error ?? "Failed to start analysis");
      }
      const analysis = await analysisRes.json();

      router.push(`/analysis/${analysis.parcel_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  }

  return (
    <>
      <Script
        src={`https://maps.googleapis.com/maps/api/js?key=${process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY}&libraries=places`}
        strategy="afterInteractive"
        onLoad={initAutocomplete}
      />

      <div className="flex-1 flex flex-col items-center justify-center px-6 py-20">
        <div className="w-full max-w-lg">
          <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-4">
            Queensland
          </p>
          <h1 className="text-4xl font-bold text-white tracking-tight leading-tight mb-4">
            Understand your
            <br />
            property
          </h1>
          <p className="text-zinc-400 text-base leading-relaxed mb-10">
            Enter your address to analyse your property &mdash; lot boundaries,
            existing structures, available space, zoning, and subdivision
            potential.
          </p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="relative">
              <input
                ref={inputRef}
                type="text"
                placeholder="e.g. 12 Smith Street, Sunnybank QLD"
                className="w-full border border-white/10 bg-white/[0.05] rounded-lg px-4 py-3.5 text-base text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                disabled={loading}
                autoComplete="off"
              />
              {selectedPlace && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2 text-emerald-400">
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
                </div>
              )}
            </div>

            {error && (
              <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2.5">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={!selectedPlace || loading}
              className="w-full bg-emerald-500 text-white py-3.5 rounded-lg font-medium text-base hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <Spinner />
                  Starting analysis&hellip;
                </span>
              ) : (
                "Analyse my property"
              )}
            </button>
          </form>
        </div>
      </div>
    </>
  );
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
    >
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
