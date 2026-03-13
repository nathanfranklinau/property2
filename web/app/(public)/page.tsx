"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Script from "next/script";

type Suggestion = { text: string; source: "gnaf" | "google" };

export default function Home() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);
  const googleServiceRef = useRef<google.maps.places.AutocompleteService | null>(null);
  const sessionTokenRef = useRef<google.maps.places.AutocompleteSessionToken | null>(null);
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedAddress, setSelectedAddress] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Create a fresh session token (bundles keystrokes into one billable session)
  const newSessionToken = useCallback(() => {
    if (typeof google !== "undefined") {
      sessionTokenRef.current = new google.maps.places.AutocompleteSessionToken();
    }
  }, []);

  function onGoogleLoad() {
    googleServiceRef.current = new google.maps.places.AutocompleteService();
    newSessionToken();
  }

  useEffect(() => {
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleInputChange(value: string) {
    setQuery(value);
    setSelectedAddress(null);
    setError(null);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (value.length < 4) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      // 1. Try GNAF first (free)
      const res = await fetch(`/api/address/suggest?q=${encodeURIComponent(value)}`);
      if (res.ok) {
        const gnafResults: string[] = await res.json();
        if (gnafResults.length > 0) {
          const items = gnafResults.map((t) => ({ text: t, source: "gnaf" as const }));
          setSuggestions(items);
          setShowSuggestions(true);
          return;
        }
      }

      // 2. Fallback to Google Places AutocompleteService (no Place Details call)
      const service = googleServiceRef.current;
      if (!service) return;
      service.getPlacePredictions(
        {
          input: value,
          sessionToken: sessionTokenRef.current!,
          componentRestrictions: { country: "au" },
          types: ["address"],
        },
        (predictions, status) => {
          if (status === google.maps.places.PlacesServiceStatus.OK && predictions) {
            const items = predictions.map((p) => ({
              text: p.description,
              source: "google" as const,
            }));
            setSuggestions(items);
            setShowSuggestions(items.length > 0);
          } else {
            setSuggestions([]);
            setShowSuggestions(false);
          }
        }
      );
    }, 250);
  }

  function handleSelect(address: string) {
    setQuery(address);
    setSelectedAddress(address);
    setSuggestions([]);
    setShowSuggestions(false);
    // Reset session token so next search starts a new billing session
    newSessionToken();
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedAddress) return;

    setLoading(true);
    setError(null);

    try {
      const lookupRes = await fetch(
        `/api/properties/lookup?address=${encodeURIComponent(selectedAddress)}`
      );
      if (!lookupRes.ok) {
        const data = await lookupRes.json();
        throw new Error(
          data.error ??
            "We couldn't find a property at that address. Is it in Queensland?"
        );
      }
      const parcel = await lookupRes.json();

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
        onLoad={onGoogleLoad}
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
          <div className="relative" ref={wrapperRef}>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => handleInputChange(e.target.value)}
              onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
              placeholder="e.g. 12 Smith Street, Sunnybank QLD"
              className="w-full border border-white/10 bg-white/[0.05] rounded-lg px-4 py-3.5 text-base text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              disabled={loading}
              autoComplete="off"
            />
            {selectedAddress && (
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
            {showSuggestions && (
              <ul className="absolute z-50 left-0 right-0 top-full mt-1 bg-zinc-900 border border-white/10 rounded-lg overflow-hidden shadow-xl">
                {suggestions.map((s, i) => (
                  <li key={i}>
                    <button
                      type="button"
                      className="w-full text-left px-4 py-2.5 text-sm text-zinc-200 hover:bg-white/[0.08] transition-colors"
                      onMouseDown={() => handleSelect(s.text)}
                    >
                      {s.text}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {error && (
            <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2.5">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={!selectedAddress || loading}
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
