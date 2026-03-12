"use client";

import { useState, useRef, useCallback, useEffect } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

type DebugData = Record<string, unknown>;

type GeomEntry = {
  lot: string;
  plan: string;
  geometry: { type: string; coordinates: number[][][] | number[][][][] } | null;
  centroid_lat: number;
  centroid_lon: number;
  distance?: number;
};

// ─── Colors for different layers ─────────────────────────────────────────────

const COLORS = {
  geocode: "#FF0000",           // red — Google geocode point
  geocodeBounds: "#FF000044",   // red translucent — geocode bounding box
  gnafPoint: "#00FF00",         // green — GNAF address point
  spatialContains: "#0066FF",   // blue — ST_Contains parcels
  spatialDWithin: "#FF9900",    // orange — ST_DWithin fallback parcels
  refinement: "#FF00FF",       // magenta — address refinement parcel
  centroid: "#FFFF00",          // yellow — parcel centroids
  cadastreAddr: "#00FFFF",      // cyan — QLD cadastre address point
  gnafGeocodes: "#FF88FF",      // pink — GNAF geocode points (all types)
  cadastreAddrDirect: "#00FF88", // lime — direct cadastre address match
  allPieces: "#FF6600",          // orange-red — all geometry pieces for matched lot/plan
};

// ─── Page component ──────────────────────────────────────────────────────────

export default function DebugLookupPage() {
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<DebugData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<google.maps.Map | null>(null);
  const overlaysRef = useRef<(google.maps.Marker | google.maps.Polygon | google.maps.Rectangle)[]>([]);
  const markerColorRef = useRef<Map<google.maps.Marker, string>>(new Map());
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load Google Maps script
  useEffect(() => {
    const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    if (!apiKey) return;
    if (document.querySelector('script[src*="maps.googleapis.com"]')) return;

    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`;
    script.async = true;
    script.onload = () => initMap();
    document.head.appendChild(script);
  }, []);

  function initMap() {
    if (!mapRef.current) return;
    mapInstanceRef.current = new google.maps.Map(mapRef.current, {
      center: { lat: -27.47, lng: 153.02 },
      zoom: 14,
      mapTypeId: "hybrid",
    });

    // Setup autocomplete
    if (inputRef.current) {
      autocompleteRef.current = new google.maps.places.Autocomplete(inputRef.current, {
        componentRestrictions: { country: "au" },
        fields: ["formatted_address"],
      });
      autocompleteRef.current.addListener("place_changed", () => {
        const place = autocompleteRef.current?.getPlace();
        if (place?.formatted_address) {
          setAddress(place.formatted_address);
        }
      });
    }
  }

  // Clear all map overlays
  const clearOverlays = useCallback(() => {
    overlaysRef.current.forEach((o) => o.setMap(null));
    overlaysRef.current = [];
    markerColorRef.current.clear();
  }, []);

  // Add a marker
  function addMarker(lat: number, lng: number, title: string, color: string, label?: string) {
    const map = mapInstanceRef.current;
    if (!map) return;
    const marker = new google.maps.Marker({
      position: { lat, lng },
      map,
      title,
      label: label ? { text: label, color: "#fff", fontSize: "11px", fontWeight: "bold" } : undefined,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 12,
        fillColor: color,
        fillOpacity: 1,
        strokeColor: "#fff",
        strokeWeight: 3,
      },
      zIndex: 999,
    });
    markerColorRef.current.set(marker, color);
    marker.addListener("click", () => {
      overlaysRef.current.forEach((o) => {
        if (o instanceof google.maps.Marker) o.setZIndex(999);
      });
      marker.setZIndex(10000);
    });
    overlaysRef.current.push(marker);
  }

  function bringColorToFront(color: string) {
    overlaysRef.current.forEach((o) => {
      if (o instanceof google.maps.Marker) o.setZIndex(999);
    });
    overlaysRef.current.forEach((o) => {
      if (o instanceof google.maps.Marker && markerColorRef.current.get(o) === color) {
        o.setZIndex(10000);
      }
    });
  }

  // Add a polygon from GeoJSON
  function addPolygon(geojson: GeomEntry["geometry"], color: string, title: string) {
    const map = mapInstanceRef.current;
    if (!map || !geojson) return;

    const rings =
      geojson.type === "MultiPolygon"
        ? (geojson.coordinates as number[][][][]).flatMap((p) => p)
        : (geojson.coordinates as number[][][]);

    rings.forEach((ring) => {
      const paths = ring.map(([lng, lat]) => ({ lat, lng }));
      const poly = new google.maps.Polygon({
        paths,
        map,
        strokeColor: color,
        strokeWeight: 4,
        strokeOpacity: 1,
        fillColor: color,
        fillOpacity: 0.15,
      });

      const infoWindow = new google.maps.InfoWindow({ content: `<b>${title}</b>` });
      poly.addListener("click", (e: google.maps.MapMouseEvent) => {
        infoWindow.setPosition(e.latLng!);
        infoWindow.open(map);
      });

      overlaysRef.current.push(poly);
    });
  }

  // Add a thin outline polygon (no fill) for individual pieces
  function addThinOutline(geojson: GeomEntry["geometry"], color: string, title: string) {
    const map = mapInstanceRef.current;
    if (!map || !geojson) return;

    const rings =
      geojson.type === "MultiPolygon"
        ? (geojson.coordinates as number[][][][]).flatMap((p) => p)
        : (geojson.coordinates as number[][][]);

    rings.forEach((ring) => {
      const paths = ring.map(([lng, lat]) => ({ lat, lng }));
      const poly = new google.maps.Polygon({
        paths,
        map,
        strokeColor: color,
        strokeWeight: 1,
        strokeOpacity: 0.7,
        fillOpacity: 0,
      });
      const infoWindow = new google.maps.InfoWindow({ content: `<b>${title}</b>` });
      poly.addListener("click", (e: google.maps.MapMouseEvent) => {
        infoWindow.setPosition(e.latLng!);
        infoWindow.open(map);
      });
      overlaysRef.current.push(poly);
    });
  }

  // Add a thick border outline (no fill) for the final matched parcel
  function addThickBorder(geojson: GeomEntry["geometry"], title: string) {
    const map = mapInstanceRef.current;
    if (!map || !geojson) return;

    const rings =
      geojson.type === "MultiPolygon"
        ? (geojson.coordinates as number[][][][]).flatMap((p) => p)
        : (geojson.coordinates as number[][][]);

    rings.forEach((ring) => {
      const paths = ring.map(([lng, lat]) => ({ lat, lng }));
      const poly = new google.maps.Polygon({
        paths,
        map,
        strokeColor: "#FFD700",
        strokeWeight: 6,
        strokeOpacity: 1,
        fillOpacity: 0,
        zIndex: 2000,
      });
      const infoWindow = new google.maps.InfoWindow({ content: `<b>${title}</b>` });
      poly.addListener("click", (e: google.maps.MapMouseEvent) => {
        infoWindow.setPosition(e.latLng!);
        infoWindow.open(map);
      });
      overlaysRef.current.push(poly);
    });
  }

  // Add a bounding box rectangle
  function addBounds(low: { latitude: number; longitude: number }, high: { latitude: number; longitude: number }, color: string, title: string) {
    const map = mapInstanceRef.current;
    if (!map) return;
    const rect = new google.maps.Rectangle({
      bounds: {
        south: low.latitude,
        west: low.longitude,
        north: high.latitude,
        east: high.longitude,
      },
      map,
      strokeColor: color,
      strokeWeight: 2,
      strokeOpacity: 0.8,
      fillColor: color,
      fillOpacity: 0.1,
    });

    const infoWindow = new google.maps.InfoWindow({ content: `<b>${title}</b>` });
    rect.addListener("click", (e: google.maps.MapMouseEvent) => {
      infoWindow.setPosition(e.latLng!);
      infoWindow.open(map);
    });

    overlaysRef.current.push(rect);
  }

  // Plot all data on map
  const plotData = useCallback((d: DebugData) => {
    clearOverlays();
    const map = mapInstanceRef.current;
    if (!map) return;

    const bounds = new google.maps.LatLngBounds();
    const parsed = d.parsed as Record<string, unknown> | undefined;

    // 1. Google geocode point
    if (parsed?.lat && parsed?.lng) {
      const lat = parsed.lat as number;
      const lng = parsed.lng as number;
      addMarker(lat, lng, "Google Geocode", COLORS.geocode, "G");
      bounds.extend({ lat, lng });

      // Geocode bounding box
      if (parsed.boundsLow && parsed.boundsHigh) {
        addBounds(
          parsed.boundsLow as { latitude: number; longitude: number },
          parsed.boundsHigh as { latitude: number; longitude: number },
          COLORS.geocodeBounds,
          "Google Geocode Bounds"
        );
      }
    }

    // 2. GNAF point
    const gnafPoint = d.gnafPoint as { lat: number; lng: number } | undefined;
    if (gnafPoint) {
      addMarker(gnafPoint.lat, gnafPoint.lng, "GNAF Address Point", COLORS.gnafPoint, "N");
      bounds.extend({ lat: gnafPoint.lat, lng: gnafPoint.lng });
    }

    // 2b. GNAF geocode points (all types) — pink
    const gnafGeocodes = d.gnafGeocodes as Array<{ latitude: string; longitude: string; geocode_type_code: string }> | undefined;
    if (gnafGeocodes) {
      gnafGeocodes.forEach((g) => {
        const lat = parseFloat(g.latitude);
        const lng = parseFloat(g.longitude);
        if (!isNaN(lat) && !isNaN(lng)) {
          addMarker(lat, lng, `GNAF ${g.geocode_type_code}`, COLORS.gnafGeocodes, g.geocode_type_code.slice(0, 2));
          bounds.extend({ lat, lng });
        }
      });
    }

    // 2c. Direct cadastre address match geometries — lime
    const cadastreDirectGeoms = d.cadastreAddressDirectGeometries as GeomEntry[] | undefined;
    if (cadastreDirectGeoms) {
      cadastreDirectGeoms.forEach((g, i) => {
        addPolygon(g.geometry, COLORS.cadastreAddrDirect, `CadAddr Direct #${i + 1}: Lot ${g.lot}/${g.plan}`);
      });
    }

    // 3. ST_Contains parcels (blue)
    const containsGeoms = d.cadastreSpatialContainsGeometries as GeomEntry[] | undefined;
    if (containsGeoms) {
      containsGeoms.forEach((g, i) => {
        addPolygon(g.geometry, COLORS.spatialContains, `ST_Contains #${i + 1}: Lot ${g.lot}/${g.plan}`);
        if (g.centroid_lat && g.centroid_lon) {
          addMarker(
            parseFloat(g.centroid_lat as unknown as string),
            parseFloat(g.centroid_lon as unknown as string),
            `Centroid: ${g.lot}/${g.plan}`,
            COLORS.centroid,
            `C${i + 1}`
          );
        }
        // Extend bounds from geometry
        if (g.geometry) {
          const coords =
            g.geometry.type === "MultiPolygon"
              ? (g.geometry.coordinates as number[][][][]).flat(2)
              : (g.geometry.coordinates as number[][][]).flat();
          coords.forEach(([lng, lat]) => bounds.extend({ lat, lng }));
        }
      });
    }

    // 4. ST_DWithin fallback parcels (orange) — only if no contains results
    const dwithinGeoms = d.cadastreDWithinGeometries as GeomEntry[] | undefined;
    if (dwithinGeoms && (!containsGeoms || containsGeoms.length === 0)) {
      dwithinGeoms.forEach((g, i) => {
        addPolygon(g.geometry, COLORS.spatialDWithin, `DWithin #${i + 1}: Lot ${g.lot}/${g.plan} (d=${g.distance})`);
        if (g.geometry) {
          const coords =
            g.geometry.type === "MultiPolygon"
              ? (g.geometry.coordinates as number[][][][]).flat(2)
              : (g.geometry.coordinates as number[][][]).flat();
          coords.forEach(([lng, lat]) => bounds.extend({ lat, lng }));
        }
      });
    }

    // 5. Address refinement parcel (magenta) + cadastre address points (cyan)
    const refinementGeoms = d.addressRefinementGeometries as Array<{
      lot: string;
      plan: string;
      parcelGeometry: GeomEntry["geometry"];
      addrPoint: { lat: number; lng: number } | null;
      centroid_lat: number;
      centroid_lon: number;
    }> | undefined;
    if (refinementGeoms && refinementGeoms.length > 0) {
      refinementGeoms.forEach((g, i) => {
        addPolygon(g.parcelGeometry, COLORS.refinement, `Refinement #${i + 1}: Lot ${g.lot}/${g.plan}`);
        if (g.addrPoint) {
          addMarker(g.addrPoint.lat, g.addrPoint.lng, `Cadastre Addr: ${g.lot}/${g.plan}`, COLORS.cadastreAddr, "A");
          bounds.extend(g.addrPoint);
        }
      });
    }

    // 6. All geometry pieces for matched lot/plan — thin outlines + union border
    const allPiecesGeoms = d.allPiecesForMatchedLotGeometries as (GeomEntry & { id: number })[] | undefined;
    const unionGeom = d.allPiecesUnionGeometry as GeomEntry["geometry"] | null | undefined;
    if (allPiecesGeoms && allPiecesGeoms.length > 1) {
      // Draw each piece as a thin line
      allPiecesGeoms.forEach((g, i) => {
        addThinOutline(g.geometry, COLORS.allPieces, `Piece #${i + 1} (id=${g.id}): Lot ${g.lot}/${g.plan}`);
      });
      // Draw the union as a thick outer border
      if (unionGeom) {
        addThickBorder(unionGeom, `Union: Lot ${allPiecesGeoms[0].lot}/${allPiecesGeoms[0].plan} (${allPiecesGeoms.length} pieces)`);
      }
    } else {
      // Single piece — just draw the thick matched border as before
      const matchedGeom: GeomEntry["geometry"] | null =
        refinementGeoms?.[0]?.parcelGeometry ??
        (containsGeoms?.find((g) => g.geometry)?.geometry ?? null);
      if (matchedGeom) {
        const matchedRow = refinementGeoms?.[0] ?? containsGeoms?.[0];
        addThickBorder(matchedGeom, `Matched: Lot ${matchedRow?.lot}/${matchedRow?.plan}`);
      }
    }

    // Fit map to bounds
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, 60);
    }
  }, [clearOverlays]);

  // Fetch debug data
  const doLookup = useCallback(async () => {
    if (!address.trim()) return;
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const res = await fetch(`/api/debug/lookup?address=${encodeURIComponent(address)}`);
      const json = await res.json();
      setData(json);
      plotData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [address, plotData]);

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "monospace", fontSize: 13 }}>
      {/* Left panel — controls + debug JSON */}
      <div style={{ width: 480, overflow: "auto", padding: 12, background: "#1a1a2e", color: "#eee" }}>
        <h2 style={{ margin: "0 0 12px", fontSize: 16 }}>Debug Lookup</h2>

        <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
          <input
            ref={inputRef}
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doLookup()}
            placeholder="Type address..."
            style={{
              flex: 1, padding: "6px 8px", borderRadius: 4, border: "1px solid #444",
              background: "#0f0f23", color: "#eee", fontSize: 13,
            }}
          />
          <button
            onClick={doLookup}
            disabled={loading}
            style={{
              padding: "6px 14px", borderRadius: 4, border: "none",
              background: loading ? "#555" : "#0066FF", color: "#fff",
              cursor: loading ? "wait" : "pointer", fontSize: 13,
            }}
          >
            {loading ? "..." : "Lookup"}
          </button>
          {data && (
            <>
              <button
                onClick={() => {
                  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `debug-${(data.input as string || "lookup").replace(/[^a-zA-Z0-9]/g, "_")}.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                style={{
                  padding: "6px 10px", borderRadius: 4, border: "1px solid #444",
                  background: "#0f0f23", color: "#8bf", cursor: "pointer", fontSize: 13,
                }}
              >
                Export JSON
              </button>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(JSON.stringify(data, null, 2));
                }}
                style={{
                  padding: "6px 10px", borderRadius: 4, border: "1px solid #444",
                  background: "#0f0f23", color: "#8bf", cursor: "pointer", fontSize: 13,
                }}
              >
                Copy
              </button>
            </>
          )}
        </div>

        {/* Legend */}
        <div style={{ marginBottom: 12, lineHeight: 1.8 }}>
          <b>Legend:</b><br />
          {Object.entries({
            "G = Google Geocode": COLORS.geocode,
            "Geocode Bounds (rect)": COLORS.geocodeBounds,
            "N = GNAF Point": COLORS.gnafPoint,
            "ST_Contains parcels": COLORS.spatialContains,
            "ST_DWithin fallback": COLORS.spatialDWithin,
            "Address Refinement": COLORS.refinement,
            "A = Cadastre Addr Pt": COLORS.cadastreAddr,
            "C = Parcel Centroid": COLORS.centroid,
            "GNAF Geocodes (all)": COLORS.gnafGeocodes,
            "CadAddr Direct": COLORS.cadastreAddrDirect,
            "All Lot Pieces": COLORS.allPieces,
            "Matched Parcel": "#FFD700",
          }).map(([label, color]) => (
            <span key={label} style={{ display: "inline-block", marginRight: 12, cursor: "pointer" }}
              onClick={() => bringColorToFront(color)}>
              <span style={{
                display: "inline-block", width: 10, height: 10, borderRadius: "50%",
                background: color, marginRight: 4, verticalAlign: "middle",
              }} />
              {label}
            </span>
          ))}
        </div>

        {error && <div style={{ color: "#f66", marginBottom: 8 }}>Error: {error}</div>}

        {data && (
          <div>
            {/* Summary */}
            <Section title="Parsed Address" data={data.parsed} />
            <Section title="GNAF Matches" data={data.gnaf} />
            <Section title="GNAF Point" data={data.gnafPoint} />
            <Section title="GNAF Geocodes (all types)" data={data.gnafGeocodes} />
            <Section title="ST_Contains Parcels" data={data.cadastreSpatialContains} />
            <Section title="ST_DWithin Parcels" data={data.cadastreDWithin} />
            <Section title="Refinement Input" data={data.refinementInput} />
            <Section title="Address Refinement" data={data.addressRefinement} />
            <Section title="Cadastre Address (direct lookup)" data={data.cadastreAddressDirect} />
            <Section title="All Addresses on Plan" data={data.allAddressesOnPlan} collapsed />
            <Section title="LGA" data={data.lga} />
            <Section title="Zoning" data={data.zoning} />
            <Section title="Raw Validation Response" data={data.addressValidation} collapsed />
          </div>
        )}
      </div>

      {/* Right panel — map */}
      <div ref={mapRef} style={{ flex: 1 }} />
    </div>
  );
}

// ─── Collapsible JSON section ────────────────────────────────────────────────

function Section({ title, data, collapsed = false }: { title: string; data: unknown; collapsed?: boolean }) {
  const [open, setOpen] = useState(!collapsed);
  if (data === undefined || data === null) return null;

  return (
    <div style={{ marginBottom: 8 }}>
      <div
        onClick={() => setOpen(!open)}
        style={{ cursor: "pointer", fontWeight: "bold", color: "#8bf", userSelect: "none" }}
      >
        {open ? "▾" : "▸"} {title}
        {Array.isArray(data) && <span style={{ color: "#888" }}> ({data.length})</span>}
      </div>
      {open && (
        <pre style={{
          background: "#0f0f23", padding: 8, borderRadius: 4,
          overflow: "auto", maxHeight: 300, fontSize: 11, lineHeight: 1.4,
          whiteSpace: "pre-wrap", wordBreak: "break-all",
        }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}
