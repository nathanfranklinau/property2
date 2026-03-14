"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { APIProvider, Map, useMap } from "@vis.gl/react-google-maps";

// ─── Types ──────────────────────────────────────────────────────────────────

export type BuildingFootprint = {
  area_sqm: number;
  coords: [number, number][]; // [lat, lon]
  hasBuffer?: boolean;
};

export type Encumbrance = {
  lotplan: string | null;
  parcel_typ: string;
  tenure: string | null;
  label: string;
  area_sqm: number;
  coords: [number, number][][]; // array of rings, each [[lat, lon], ...]
};

/** Colour palette for each encumbrance type shown on the map. */
export const ENCUMBRANCE_COLOURS: Record<string, { fill: string; stroke: string }> = {
  Easement:          { fill: "#F59E0B", stroke: "#D97706" },
  Road:              { fill: "#EF4444", stroke: "#DC2626" },
  Watercourse:       { fill: "#3B82F6", stroke: "#2563EB" },
  "Transport Route": { fill: "#EC4899", stroke: "#DB2777" },
  Covenant:          { fill: "#8B5CF6", stroke: "#7C3AED" },
  "Profit à Prendre":{ fill: "#10B981", stroke: "#059669" },
};

const DEFAULT_ENCUMBRANCE_COLOUR = { fill: "#94A3B8", stroke: "#64748B" };

function encumbranceColour(label: string) {
  return ENCUMBRANCE_COLOURS[label] ?? DEFAULT_ENCUMBRANCE_COLOUR;
}

type DrawMode = "edit" | "draw-polygon" | "draw-rectangle";

type PropertyMapProps = {
  apiKey: string;
  boundaryCoords: [number, number][]; // [lat, lon] in GDA94
  centroid: { lat: number; lng: number };
  footprints: BuildingFootprint[];
  onFootprintsChange: (footprints: BuildingFootprint[]) => void;
  encumbrances?: Encumbrance[];
  visibleEncumbranceTypes?: Set<string>;
  /** When true, hides toolbar and disables all drawing/editing interaction. */
  readOnly?: boolean;
  /** Complex boundary for BUP/GTP — rendered as dashed outline behind the lot boundary. */
  complexBoundary?: [number, number][][]; // array of rings [[lat, lon], ...]
  /** Nearby subdivision boundaries to display on map. */
  nearbySubdivisions?: {
    plan: string;
    rings: [number, number][][];
    addresses: string[];
    lot_count: number;
    total_area_sqm: number;
    distance_m: number;
    centroid: { lat: number; lng: number };
  }[];
  /** When set, the map pans/zooms to this location (for locating a nearby subdivision). */
  focusedNearbyPlan?: { lat: number; lng: number } | null;
  /** Called when user clicks a nearby subdivision polygon. */
  onNearbyPlanClick?: (plan: {
    plan: string;
    addresses: string[];
    lot_count: number;
    total_area_sqm: number;
    distance_m: number;
    centroid: { lat: number; lng: number };
  }) => void;
};

type LatLng = google.maps.LatLngLiteral;

const MAX_BUILDINGS = 3;
const MAX_HISTORY = 50;
// ~1 metre nudge step in degrees
const NUDGE_STEP = 0.00001;
// Rotation step in degrees per button click
const ROTATE_STEP = 15;
// Clearance zone radius in metres (shown as red ring around buildings)
const BUFFER_RADIUS_M = 1;

// ─── Geometry helpers ───────────────────────────────────────────────────────


function pointInPolygon(point: LatLng, polygon: LatLng[]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].lat,
      yi = polygon[i].lng;
    const xj = polygon[j].lat,
      yj = polygon[j].lng;
    const intersect =
      yi > point.lng !== yj > point.lng &&
      point.lat < ((xj - xi) * (point.lng - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function nearestPointOnSegment(p: LatLng, a: LatLng, b: LatLng): LatLng {
  const dx = b.lat - a.lat;
  const dy = b.lng - a.lng;
  const lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return a;
  let t = ((p.lat - a.lat) * dx + (p.lng - a.lng) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));
  return { lat: a.lat + t * dx, lng: a.lng + t * dy };
}

function clampToProperty(point: LatLng, boundary: LatLng[]): LatLng {
  if (pointInPolygon(point, boundary)) return point;
  let nearest = boundary[0];
  let minDist = Infinity;
  for (let i = 0; i < boundary.length; i++) {
    const j = (i + 1) % boundary.length;
    const candidate = nearestPointOnSegment(point, boundary[i], boundary[j]);
    const dist =
      (candidate.lat - point.lat) ** 2 + (candidate.lng - point.lng) ** 2;
    if (dist < minDist) {
      minDist = dist;
      nearest = candidate;
    }
  }
  return nearest;
}

/** Clamp an entire polygon so all vertices stay inside the boundary. Translates the shape if needed. */
function clampPolygonToProperty(coords: LatLng[], boundary: LatLng[]): LatLng[] {
  const outside = coords.filter((c) => !pointInPolygon(c, boundary));
  if (outside.length === 0) return coords;

  let maxPushLat = 0;
  let maxPushLng = 0;
  let maxPushDist = 0;

  for (const v of outside) {
    const clamped = clampToProperty(v, boundary);
    const pushLat = clamped.lat - v.lat;
    const pushLng = clamped.lng - v.lng;
    const dist = pushLat * pushLat + pushLng * pushLng;
    if (dist > maxPushDist) {
      maxPushDist = dist;
      maxPushLat = pushLat;
      maxPushLng = pushLng;
    }
  }

  return coords.map((c) => ({
    lat: c.lat + maxPushLat,
    lng: c.lng + maxPushLng,
  }));
}

// ─── Sutherland-Hodgman polygon clipping ────────────────────────────────────

function _polygonSignedArea(coords: LatLng[]): number {
  let area = 0;
  for (let i = 0; i < coords.length; i++) {
    const j = (i + 1) % coords.length;
    area += coords[i].lat * coords[j].lng - coords[j].lat * coords[i].lng;
  }
  return area / 2;
}

function _segmentIntersect(p1: LatLng, p2: LatLng, p3: LatLng, p4: LatLng): LatLng {
  const d1 = { lat: p2.lat - p1.lat, lng: p2.lng - p1.lng };
  const d2 = { lat: p4.lat - p3.lat, lng: p4.lng - p3.lng };
  const denom = d1.lat * d2.lng - d1.lng * d2.lat;
  if (Math.abs(denom) < 1e-12) return p1;
  const t = ((p3.lat - p1.lat) * d2.lng - (p3.lng - p1.lng) * d2.lat) / denom;
  return { lat: p1.lat + t * d1.lat, lng: p1.lng + t * d1.lng };
}

function _isInsideEdge(point: LatLng, a: LatLng, b: LatLng): boolean {
  return (b.lat - a.lat) * (point.lng - a.lng) - (b.lng - a.lng) * (point.lat - a.lat) >= 0;
}

/**
 * Clip `subject` to the interior of `boundary` using Sutherland-Hodgman.
 * Returns the clipped polygon, or null if the result has < 3 vertices.
 */
function clipPolygonToBoundary(subject: LatLng[], boundary: LatLng[]): LatLng[] | null {
  // Ensure boundary is CCW (positive signed area in lat/lng coords)
  const clip = _polygonSignedArea(boundary) >= 0 ? boundary : [...boundary].reverse();
  let output = [...subject];

  for (let i = 0; i < clip.length; i++) {
    if (output.length === 0) return null;
    const input = [...output];
    output = [];
    const a = clip[i];
    const b = clip[(i + 1) % clip.length];

    for (let j = 0; j < input.length; j++) {
      const curr = input[j];
      const prev = input[(j + input.length - 1) % input.length];
      const currIn = _isInsideEdge(curr, a, b);
      const prevIn = _isInsideEdge(prev, a, b);

      if (currIn) {
        if (!prevIn) output.push(_segmentIntersect(prev, curr, a, b));
        output.push(curr);
      } else if (prevIn) {
        output.push(_segmentIntersect(prev, curr, a, b));
      }
    }
  }

  return output.length >= 3 ? output : null;
}

function polygonCentroid(coords: LatLng[]): LatLng {
  let lat = 0,
    lng = 0;
  for (const c of coords) {
    lat += c.lat;
    lng += c.lng;
  }
  const n = coords.length;
  return { lat: lat / n, lng: lng / n };
}

function rotatePolygon(coords: LatLng[], angleDeg: number, center: LatLng): LatLng[] {
  const rad = (angleDeg * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  return coords.map((c) => {
    const dx = c.lat - center.lat;
    const dy = c.lng - center.lng;
    return {
      lat: center.lat + dx * cos - dy * sin,
      lng: center.lng + dx * sin + dy * cos,
    };
  });
}

function approxAreaSqm(coords: LatLng[]): number {
  if (coords.length < 3) return 0;
  const centroid = polygonCentroid(coords);
  const mPerLat = 111320;
  const mPerLng = 111320 * Math.cos((centroid.lat * Math.PI) / 180);
  let area = 0;
  for (let i = 0; i < coords.length; i++) {
    const j = (i + 1) % coords.length;
    const x1 = (coords[i].lng - centroid.lng) * mPerLng;
    const y1 = (coords[i].lat - centroid.lat) * mPerLat;
    const x2 = (coords[j].lng - centroid.lng) * mPerLng;
    const y2 = (coords[j].lat - centroid.lat) * mPerLat;
    area += x1 * y2 - x2 * y1;
  }
  return Math.abs(area) / 2;
}

function toLatLngs(coords: [number, number][]): LatLng[] {
  return coords.map(([lat, lng]) => ({ lat, lng }));
}

function toTuples(coords: LatLng[]): [number, number][] {
  return coords.map((c) => [c.lat, c.lng]);
}

/**
 * Expand a polygon outward by `radiusM` metres using a miter-join offset.
 * Works in local Cartesian space (metres) at the polygon's centroid latitude.
 */
function offsetPolygon(coords: LatLng[], radiusM: number): LatLng[] {
  if (coords.length < 3) return coords;
  const centroid = polygonCentroid(coords);
  const mPerLat = 111320;
  const mPerLng = 111320 * Math.cos((centroid.lat * Math.PI) / 180);

  // Convert to local metres
  const pts = coords.map((c) => ({
    x: (c.lng - centroid.lng) * mPerLng,
    y: (c.lat - centroid.lat) * mPerLat,
  }));

  // Ensure CCW winding in local (x=lng, y=lat) space.
  // _polygonSignedArea uses (lat,lng) as (x,y), so positive there means CW in local space — reverse it.
  const localPts = _polygonSignedArea(coords) >= 0 ? [...pts].reverse() : pts;
  const n = localPts.length;
  const result: { x: number; y: number }[] = [];

  for (let i = 0; i < n; i++) {
    const prev = localPts[(i - 1 + n) % n];
    const curr = localPts[i];
    const next = localPts[(i + 1) % n];

    const e1 = { x: curr.x - prev.x, y: curr.y - prev.y };
    const e2 = { x: next.x - curr.x, y: next.y - curr.y };
    const len1 = Math.sqrt(e1.x * e1.x + e1.y * e1.y);
    const len2 = Math.sqrt(e2.x * e2.x + e2.y * e2.y);
    if (len1 === 0 || len2 === 0) {
      result.push(curr);
      continue;
    }

    // Outward normals (right-hand perp for CCW polygon)
    const n1 = { x: e1.y / len1, y: -e1.x / len1 };
    const n2 = { x: e2.y / len2, y: -e2.x / len2 };

    // Bisector of the two outward normals
    const bx = n1.x + n2.x;
    const by = n1.y + n2.y;
    const blen = Math.sqrt(bx * bx + by * by);
    if (blen < 1e-9) {
      result.push({ x: curr.x + n1.x * radiusM, y: curr.y + n1.y * radiusM });
      continue;
    }

    // Miter length = radius / dot(bisector_norm, n1); cap at 2× radius for sharp corners
    const dot = (bx / blen) * n1.x + (by / blen) * n1.y;
    const miterLen = Math.min(radiusM / Math.max(dot, 0.1), radiusM * 2);

    if (dot < 0.5) {
      // Sharp corner (> ~120°) — insert arc points instead of a miter spike
      const startAngle = Math.atan2(n1.y, n1.x);
      const endAngle = Math.atan2(n2.y, n2.x);
      let sweep = endAngle - startAngle;
      if (sweep < 0) sweep += 2 * Math.PI;
      if (sweep > Math.PI) sweep -= 2 * Math.PI;
      const steps = Math.max(2, Math.ceil(Math.abs(sweep) / (Math.PI / 8)));
      for (let s = 0; s <= steps; s++) {
        const a = startAngle + (sweep * s) / steps;
        result.push({ x: curr.x + Math.cos(a) * radiusM, y: curr.y + Math.sin(a) * radiusM });
      }
    } else {
      result.push({ x: curr.x + (bx / blen) * miterLen, y: curr.y + (by / blen) * miterLen });
    }
  }

  return result.map((p) => ({
    lat: centroid.lat + p.y / mPerLat,
    lng: centroid.lng + p.x / mPerLng,
  }));
}

/**
 * Returns the outer ring of the clearance zone around `fp`, clipped to `boundary`.
 * Returns null if the result is degenerate.
 */
export function computeBufferCoords(
  fp: BuildingFootprint,
  boundary: [number, number][]
): [number, number][] | null {
  const boundaryLatLng = boundary.map(([lat, lng]) => ({ lat, lng }));
  const expanded = offsetPolygon(toLatLngs(fp.coords), BUFFER_RADIUS_M);
  const clipped = clipPolygonToBoundary(expanded, boundaryLatLng);
  if (!clipped) return null;
  return toTuples(clipped);
}

/** Length of the edge from a to b in metres. */
function edgeLengthM(a: LatLng, b: LatLng): number {
  const mPerLat = 111320;
  const mPerLng = 111320 * Math.cos(((a.lat + b.lat) / 2 * Math.PI) / 180);
  const dy = (b.lat - a.lat) * mPerLat;
  const dx = (b.lng - a.lng) * mPerLng;
  return Math.sqrt(dx * dx + dy * dy);
}

/** Build a Google Maps icon for an encumbrance label (e.g. "Easement"). */
function makeLabelIcon(text: string, colour: string): google.maps.Icon {
  const pillW = Math.ceil(text.length * 6.5 + 16);
  const pillH = 18;
  const S = pillW + 4;
  const cx = S / 2;
  const cy = pillH / 2 + 2;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${pillH + 4}"><rect x="2" y="2" width="${pillW}" height="${pillH}" rx="${pillH / 2}" fill="${colour}" fill-opacity="0.85"/><text x="${cx}" y="${cy + 4.5}" font-family="-apple-system,BlinkMacSystemFont,Helvetica,sans-serif" font-size="10" font-weight="700" letter-spacing="0.02em" fill="white" text-anchor="middle">${text}</text></svg>`;
  return {
    url: `data:image/svg+xml,${encodeURIComponent(svg)}`,
    scaledSize: new google.maps.Size(S, pillH + 4),
    anchor: new google.maps.Point(cx, cy),
  };
}

/** Build a Google Maps icon showing the block area (total_area_sqm) of a nearby subdivision. */
function makeAreaLabelIcon(areaSqm: number): google.maps.Icon {
  const text = areaSqm >= 10000
    ? `${(areaSqm / 10000).toFixed(2)} ha`
    : `${Math.round(areaSqm).toLocaleString()} m²`;
  const pillW = Math.ceil(text.length * 6.5 + 16);
  const pillH = 18;
  const S = pillW + 4;
  const cx = S / 2;
  const cy = pillH / 2 + 2;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${pillH + 4}"><rect x="2" y="2" width="${pillW}" height="${pillH}" rx="${pillH / 2}" fill="#4F46E5" fill-opacity="0.9"/><text x="${cx}" y="${cy + 4.5}" font-family="-apple-system,BlinkMacSystemFont,Helvetica,sans-serif" font-size="10" font-weight="700" letter-spacing="0.02em" fill="white" text-anchor="middle">${text}</text></svg>`;
  return {
    url: `data:image/svg+xml,${encodeURIComponent(svg)}`,
    scaledSize: new google.maps.Size(S, pillH + 4),
    anchor: new google.maps.Point(cx, cy),
  };
}

/** Build a Google Maps icon for a measurement label rotated to align with an edge. */
function makeMeasurementIcon(distM: number, angleDeg: number): google.maps.Icon {
  const text = distM >= 10 ? `${Math.round(distM)}m` : `${distM.toFixed(1)}m`;
  const pillW = Math.ceil(text.length * 6.2 + 14);
  const pillH = 16;
  const S = 72; // SVG canvas size — large enough for any rotation
  const cx = S / 2;
  const cy = S / 2;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><g transform="rotate(${angleDeg.toFixed(1)},${cx},${cy})"><rect x="${cx - pillW / 2}" y="${cy - pillH / 2}" width="${pillW}" height="${pillH}" rx="${pillH / 2}" fill="#111827" fill-opacity="0.72"/><text x="${cx}" y="${cy + 4.5}" font-family="-apple-system,BlinkMacSystemFont,Helvetica,sans-serif" font-size="10" font-weight="600" letter-spacing="0.01em" fill="white" text-anchor="middle">${text}</text></g></svg>`;
  return {
    url: `data:image/svg+xml,${encodeURIComponent(svg)}`,
    scaledSize: new google.maps.Size(S, S),
    anchor: new google.maps.Point(cx, cy),
  };
}

/** Perpendicular distance from point to line segment (a→b). */
function perpendicularDist(p: LatLng, a: LatLng, b: LatLng): number {
  const dx = b.lat - a.lat;
  const dy = b.lng - a.lng;
  const lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return Math.sqrt((p.lat - a.lat) ** 2 + (p.lng - a.lng) ** 2);
  const area2 = Math.abs(dx * (a.lng - p.lng) - (a.lat - p.lat) * dy);
  return area2 / Math.sqrt(lenSq);
}

/** Douglas-Peucker polygon simplification. Epsilon is in degrees (~0.000009° ≈ 1m). */
function simplifyPath(coords: LatLng[], epsilon: number): LatLng[] {
  if (coords.length <= 3) return coords;

  let maxDist = 0;
  let maxIdx = 0;
  const last = coords.length - 1;

  for (let i = 1; i < last; i++) {
    const d = perpendicularDist(coords[i], coords[0], coords[last]);
    if (d > maxDist) {
      maxDist = d;
      maxIdx = i;
    }
  }

  if (maxDist > epsilon) {
    const left = simplifyPath(coords.slice(0, maxIdx + 1), epsilon);
    const right = simplifyPath(coords.slice(maxIdx), epsilon);
    return [...left.slice(0, -1), ...right];
  }
  return [coords[0], coords[last]];
}

/** Simplify a building footprint to at most ~8-12 vertices. */
export function simplifyFootprint(fp: BuildingFootprint): BuildingFootprint {
  let coords = toLatLngs(fp.coords);
  // Remove duplicate closing vertex if present
  if (
    coords.length > 1 &&
    coords[0].lat === coords[coords.length - 1].lat &&
    coords[0].lng === coords[coords.length - 1].lng
  ) {
    coords = coords.slice(0, -1);
  }
  if (coords.length <= 6) return { area_sqm: fp.area_sqm, coords: toTuples(coords) };

  const epsilon = 0.0000045;
  let simplified = simplifyPath(coords, epsilon);

  let tries = 0;
  let eps = epsilon;
  while (simplified.length > 12 && tries < 5) {
    eps *= 2;
    simplified = simplifyPath(coords, eps);
    tries++;
  }

  if (simplified.length < 3) return { area_sqm: fp.area_sqm, coords: toTuples(coords) };
  return { area_sqm: approxAreaSqm(simplified), coords: toTuples(simplified) };
}

// ─── Undo/Redo hook ─────────────────────────────────────────────────────────

function useHistory(
  footprints: BuildingFootprint[],
  onFootprintsChange: (f: BuildingFootprint[]) => void
) {
  const historyRef = useRef<BuildingFootprint[][]>([]);
  const redoRef = useRef<BuildingFootprint[][]>([]);
  const isUndoRedoRef = useRef(false);
  const lastSnapshotRef = useRef<string>("");

  const pushChange = useCallback(
    (next: BuildingFootprint[]) => {
      if (isUndoRedoRef.current) {
        isUndoRedoRef.current = false;
        onFootprintsChange(next);
        return;
      }
      const snap = JSON.stringify(next);
      if (snap !== lastSnapshotRef.current) {
        historyRef.current.push(footprints);
        if (historyRef.current.length > MAX_HISTORY) historyRef.current.shift();
        redoRef.current = [];
        lastSnapshotRef.current = snap;
      }
      onFootprintsChange(next);
    },
    [footprints, onFootprintsChange]
  );

  useEffect(() => {
    if (!lastSnapshotRef.current) {
      lastSnapshotRef.current = JSON.stringify(footprints);
    }
  }, [footprints]);

  const undo = useCallback(() => {
    if (historyRef.current.length === 0) return;
    const prev = historyRef.current.pop()!;
    redoRef.current.push(footprints);
    isUndoRedoRef.current = true;
    lastSnapshotRef.current = JSON.stringify(prev);
    onFootprintsChange(prev);
  }, [footprints, onFootprintsChange]);

  const redo = useCallback(() => {
    if (redoRef.current.length === 0) return;
    const next = redoRef.current.pop()!;
    historyRef.current.push(footprints);
    isUndoRedoRef.current = true;
    lastSnapshotRef.current = JSON.stringify(next);
    onFootprintsChange(next);
  }, [footprints, onFootprintsChange]);

  const canUndo = historyRef.current.length > 0;
  const canRedo = redoRef.current.length > 0;

  return { pushChange, undo, redo, canUndo, canRedo };
}

// ─── Toolbar ────────────────────────────────────────────────────────────────

function MapToolbar({
  mode,
  setMode,
  canDraw,
  selectedIndex,
  onDelete,
  onNudge,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  selectedHasBuffer,
  onToggleBuffer,
  showMeasurements,
  onToggleMeasurements,
  hasNearbySubdivisions,
  showSubdivisionLabels,
  onToggleSubdivisionLabels,
}: {
  mode: DrawMode;
  setMode: (m: DrawMode) => void;
  canDraw: boolean;
  selectedIndex: number | null;
  onDelete: () => void;
  onNudge: (dir: "up" | "down" | "left" | "right") => void;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  selectedHasBuffer: boolean;
  onToggleBuffer: () => void;
  showMeasurements: boolean;
  onToggleMeasurements: () => void;
  hasNearbySubdivisions: boolean;
  showSubdivisionLabels: boolean;
  onToggleSubdivisionLabels: () => void;
}) {
  return (
    <div className="absolute top-3 left-3 z-10 flex items-center gap-1 bg-white/95 backdrop-blur rounded-lg shadow-lg px-1.5 py-1 border border-zinc-200">
      <ToolBtn
        active={mode === "edit"}
        onClick={() => setMode("edit")}
        title="Select & edit"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
          <path d="M3.196 12.87l-.825.483a.75.75 0 000 1.294l7.004 4.086a.75.75 0 00.756 0l7.004-4.086a.75.75 0 000-1.294l-.825-.484-5.328 3.108a2.25 2.25 0 01-2.268 0L3.196 12.87z" />
          <path d="M3.196 8.87l-.825.483a.75.75 0 000 1.294l7.004 4.086a.75.75 0 00.756 0l7.004-4.086a.75.75 0 000-1.294l-.825-.484-5.328 3.108a2.25 2.25 0 01-2.268 0L3.196 8.87z" />
          <path d="M10.38 1.103a.75.75 0 00-.756 0l-7.004 4.086a.75.75 0 000 1.294l7.004 4.086a.75.75 0 00.756 0l7.004-4.086a.75.75 0 000-1.294l-7.004-4.086z" />
        </svg>
      </ToolBtn>

      <Sep />

      <ToolBtn
        active={mode === "draw-polygon"}
        onClick={() => setMode("draw-polygon")}
        disabled={!canDraw}
        title="Draw polygon"
      >
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
          <path d="M4 15l3-10 6 3 4 4-5 5z" strokeLinejoin="round" />
          <circle cx="4" cy="15" r="1.5" fill="currentColor" />
          <circle cx="7" cy="5" r="1.5" fill="currentColor" />
          <circle cx="13" cy="8" r="1.5" fill="currentColor" />
          <circle cx="17" cy="12" r="1.5" fill="currentColor" />
          <circle cx="12" cy="17" r="1.5" fill="currentColor" />
        </svg>
      </ToolBtn>

      <ToolBtn
        active={mode === "draw-rectangle"}
        onClick={() => setMode("draw-rectangle")}
        disabled={!canDraw}
        title="Draw rectangle"
      >
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
          <rect x="3" y="5" width="14" height="10" rx="1" />
        </svg>
      </ToolBtn>

      {selectedIndex !== null && (
        <>
          <Sep />

          {/* Nudge arrows */}
          <ToolBtn onClick={() => onNudge("up")} title="Move up">
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M10 17a.75.75 0 01-.75-.75V5.612L5.29 9.77a.75.75 0 01-1.08-1.04l5.25-5.5a.75.75 0 011.08 0l5.25 5.5a.75.75 0 11-1.08 1.04l-3.96-4.158V16.25A.75.75 0 0110 17z" clipRule="evenodd" />
            </svg>
          </ToolBtn>
          <ToolBtn onClick={() => onNudge("down")} title="Move down">
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z" clipRule="evenodd" />
            </svg>
          </ToolBtn>
          <ToolBtn onClick={() => onNudge("left")} title="Move left">
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z" clipRule="evenodd" />
            </svg>
          </ToolBtn>
          <ToolBtn onClick={() => onNudge("right")} title="Move right">
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" />
            </svg>
          </ToolBtn>

          <Sep />

          <ToolBtn onClick={onDelete} title="Delete selected">
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-red-500">
              <path
                fillRule="evenodd"
                d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                clipRule="evenodd"
              />
            </svg>
          </ToolBtn>

          <Sep />

          <ToolBtn
            active={selectedHasBuffer}
            onClick={onToggleBuffer}
            title={selectedHasBuffer ? `Remove ${BUFFER_RADIUS_M}m clearance` : `Add ${BUFFER_RADIUS_M}m clearance`}
          >
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
              <rect x="3" y="3" width="14" height="14" rx="1" />
              <rect x="6.5" y="6.5" width="7" height="7" rx="0.5" />
            </svg>
          </ToolBtn>
        </>
      )}

      <Sep />

      <ToolBtn onClick={onUndo} disabled={!canUndo} title="Undo (Ctrl+Z)">
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
          <path
            fillRule="evenodd"
            d="M7.793 2.232a.75.75 0 01-.025 1.06L3.622 7.25h10.003a5.375 5.375 0 010 10.75H10.75a.75.75 0 010-1.5h2.875a3.875 3.875 0 000-7.75H3.622l4.146 3.957a.75.75 0 01-1.036 1.085l-5.5-5.25a.75.75 0 010-1.085l5.5-5.25a.75.75 0 011.06.025z"
            clipRule="evenodd"
          />
        </svg>
      </ToolBtn>
      <ToolBtn onClick={onRedo} disabled={!canRedo} title="Redo (Ctrl+Y)">
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
          <path
            fillRule="evenodd"
            d="M12.207 2.232a.75.75 0 00.025 1.06l4.146 3.958H6.375a5.375 5.375 0 000 10.75H9.25a.75.75 0 000-1.5H6.375a3.875 3.875 0 010-7.75h10.003l-4.146 3.957a.75.75 0 001.036 1.085l5.5-5.25a.75.75 0 000-1.085l-5.5-5.25a.75.75 0 00-1.06.025z"
            clipRule="evenodd"
          />
        </svg>
      </ToolBtn>

      <Sep />

      <ToolBtn active={showMeasurements} onClick={onToggleMeasurements} title={showMeasurements ? "Hide measurements" : "Show measurements"}>
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="7" width="16" height="6" rx="1" />
          <line x1="5" y1="7" x2="5" y2="10" />
          <line x1="8" y1="7" x2="8" y2="9" />
          <line x1="11" y1="7" x2="11" y2="9" />
          <line x1="14" y1="7" x2="14" y2="10" />
        </svg>
      </ToolBtn>

      {hasNearbySubdivisions && (
        <>
          <Sep />
          <ToolBtn active={showSubdivisionLabels} onClick={onToggleSubdivisionLabels} title={showSubdivisionLabels ? "Hide block sizes" : "Show block sizes"}>
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="3" width="11" height="11" rx="1" />
              <line x1="15" y1="7" x2="18" y2="7" />
              <line x1="15" y1="10" x2="17" y2="10" />
              <line x1="5" y1="17" x2="15" y2="17" />
              <line x1="5" y1="17" x2="5" y2="15" />
              <line x1="15" y1="17" x2="15" y2="15" />
            </svg>
          </ToolBtn>
        </>
      )}
    </div>
  );
}

function Sep() {
  return <div className="w-px h-5 bg-zinc-200" />;
}

function ToolBtn({
  active,
  disabled,
  onClick,
  title,
  children,
}: {
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`p-1.5 rounded transition-colors ${
        active
          ? "bg-zinc-900 text-white"
          : disabled
          ? "text-zinc-300 cursor-not-allowed"
          : "text-zinc-600 hover:bg-zinc-100"
      }`}
    >
      {children}
    </button>
  );
}

// ─── Map interior: polygons + drawing ───────────────────────────────────────

function MapInterior({
  boundaryCoords,
  footprints,
  onFootprintsChange,
  encumbrances = [],
  visibleEncumbranceTypes,
  readOnly = false,
  complexBoundary,
  nearbySubdivisions,
  focusedNearbyPlan,
  onNearbyPlanClick,
}: {
  boundaryCoords: [number, number][];
  footprints: BuildingFootprint[];
  onFootprintsChange: (f: BuildingFootprint[]) => void;
  encumbrances?: Encumbrance[];
  visibleEncumbranceTypes?: Set<string>;
  readOnly?: boolean;
  complexBoundary?: [number, number][][];
  nearbySubdivisions?: {
    plan: string;
    rings: [number, number][][];
    addresses: string[];
    lot_count: number;
    total_area_sqm: number;
    distance_m: number;
    centroid: { lat: number; lng: number };
  }[];
  focusedNearbyPlan?: { lat: number; lng: number } | null;
  onNearbyPlanClick?: (plan: {
    plan: string;
    addresses: string[];
    lot_count: number;
    total_area_sqm: number;
    distance_m: number;
    centroid: { lat: number; lng: number };
  }) => void;
}) {
  const map = useMap();

  useEffect(() => {
    if (!map || boundaryCoords.length === 0) return;
    const bounds = new google.maps.LatLngBounds();
    for (const [lat, lng] of boundaryCoords) bounds.extend({ lat, lng });
    map.fitBounds(bounds, 40);
  }, [map, boundaryCoords]);

  const [mode, setMode] = useState<DrawMode>("edit");
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [drawingVertices, setDrawingVertices] = useState<LatLng[]>([]);
  const [rectFirstCorner, setRectFirstCorner] = useState<LatLng | null>(null);
  const [showMeasurements, setShowMeasurements] = useState(false);
  const [showSubdivisionLabels, setShowSubdivisionLabels] = useState(false);
  const [nearbyInfoWindow, setNearbyInfoWindow] = useState<{
    plan: string;
    addresses: string[];
    lot_count: number;
    total_area_sqm: number;
    distance_m: number;
    position: LatLng;
  } | null>(null);
  const nearbyInfoWindowRef = useRef<google.maps.InfoWindow | null>(null);

  const { pushChange, undo, redo, canUndo, canRedo } = useHistory(
    footprints,
    onFootprintsChange
  );

  // Refs for Google Maps objects
  const maskPolyRef = useRef<google.maps.Polygon | null>(null);
  const boundaryPolyRef = useRef<google.maps.Polygon | null>(null);
  const buildingPolysRef = useRef<google.maps.Polygon[]>([]);
  const bufferPolysRef = useRef<google.maps.Polygon[]>([]);
  const measureMarkersRef = useRef<google.maps.Marker[]>([]);
  const drawingPolylineRef = useRef<google.maps.Polyline | null>(null);
  const vertexMarkersRef = useRef<google.maps.Marker[]>([]);
  const mapClickListenerRef = useRef<google.maps.MapsEventListener | null>(null);
  const mapDblClickListenerRef = useRef<google.maps.MapsEventListener | null>(null);
  const encumbrancePolysRef = useRef<google.maps.Polygon[]>([]);
  const encumbranceLabelMarkersRef = useRef<google.maps.Marker[]>([]);
  const subdivisionLabelMarkersRef = useRef<google.maps.Marker[]>([]);

  const boundaryPath = useMemo(
    () => boundaryCoords.map(([lat, lng]) => ({ lat, lng })),
    [boundaryCoords]
  );

  const canDraw = footprints.length < MAX_BUILDINGS;

  // Rotation drag state
  const rotateStateRef = useRef<{
    isRotating: boolean;
    startAngle: number;
    baseCoords: LatLng[];
    centroid: LatLng;
    polyIndex: number;
  } | null>(null);
  const rotatingPolyRef = useRef<google.maps.Polygon | null>(null);
  const rotationHandleRef = useRef<google.maps.Marker | null>(null);
  const handleRelativeRef = useRef<LatLng>({ lat: 0, lng: 0 });
  // Stable refs so the rotation effect can depend only on [map]
  const footprintsRef = useRef(footprints);
  const pushChangeRef = useRef(pushChange);
  const boundaryPathRef = useRef(boundaryPath);
  useEffect(() => { footprintsRef.current = footprints; }, [footprints]);
  useEffect(() => { pushChangeRef.current = pushChange; }, [pushChange]);
  useEffect(() => { boundaryPathRef.current = boundaryPath; }, [boundaryPath]);

  // Rotate selected polygon by a step
  const handleRotate = useCallback(
    (dir: "cw" | "ccw") => {
      if (selectedIndex === null) return;
      const fp = footprints[selectedIndex];
      if (!fp) return;

      const coords = toLatLngs(fp.coords);
      const center = polygonCentroid(coords);
      const angle = dir === "cw" ? ROTATE_STEP : -ROTATE_STEP;
      const rotated = rotatePolygon(coords, angle, center);
      const confined =
        clipPolygonToBoundary(rotated, boundaryPath) ??
        clampPolygonToProperty(rotated, boundaryPath);

      const next = [...footprints];
      next[selectedIndex] = {
        area_sqm: approxAreaSqm(confined),
        coords: toTuples(confined),
        hasBuffer: fp.hasBuffer,
      };
      pushChange(next);
    },
    [selectedIndex, footprints, boundaryPath, pushChange]
  );

  // Nudge selected polygon in a direction
  const handleNudge = useCallback(
    (dir: "up" | "down" | "left" | "right") => {
      if (selectedIndex === null) return;
      const fp = footprints[selectedIndex];
      if (!fp) return;

      const dLat = dir === "up" ? NUDGE_STEP : dir === "down" ? -NUDGE_STEP : 0;
      const dLng = dir === "right" ? NUDGE_STEP : dir === "left" ? -NUDGE_STEP : 0;

      const moved = toLatLngs(fp.coords).map((c) => ({
        lat: c.lat + dLat,
        lng: c.lng + dLng,
      }));
      const clamped = clampPolygonToProperty(moved, boundaryPath);

      const next = [...footprints];
      next[selectedIndex] = {
        area_sqm: approxAreaSqm(clamped),
        coords: toTuples(clamped),
        hasBuffer: fp.hasBuffer,
      };
      pushChange(next);
    },
    [selectedIndex, footprints, boundaryPath, pushChange]
  );

  // Toggle clearance zone on selected polygon
  const handleToggleBuffer = useCallback(() => {
    if (selectedIndex === null) return;
    const next = [...footprints];
    next[selectedIndex] = { ...next[selectedIndex], hasBuffer: !next[selectedIndex].hasBuffer };
    pushChange(next);
  }, [selectedIndex, footprints, pushChange]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        undo();
      }
      if (
        ((e.metaKey || e.ctrlKey) && e.key === "y") ||
        ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "z")
      ) {
        e.preventDefault();
        redo();
      }
      if (e.key === "Escape") {
        if (mode === "draw-polygon" || mode === "draw-rectangle") {
          setMode("edit");
          setDrawingVertices([]);
          setRectFirstCorner(null);
        } else {
          setSelectedIndex(null);
        }
      }
      if ((e.key === "Delete" || e.key === "Backspace") && selectedIndex !== null) {
        const next = footprints.filter((_, i) => i !== selectedIndex);
        pushChange(next);
        setSelectedIndex(null);
      }
      // Arrow keys nudge, [ ] rotate selected polygon
      if (selectedIndex !== null && mode === "edit") {
        if (e.key === "ArrowUp") { e.preventDefault(); handleNudge("up"); }
        if (e.key === "ArrowDown") { e.preventDefault(); handleNudge("down"); }
        if (e.key === "ArrowLeft") { e.preventDefault(); handleNudge("left"); }
        if (e.key === "ArrowRight") { e.preventDefault(); handleNudge("right"); }
        if (e.key === "[") { e.preventDefault(); handleRotate("ccw"); }
        if (e.key === "]") { e.preventDefault(); handleRotate("cw"); }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [undo, redo, mode, selectedIndex, footprints, pushChange, handleNudge, handleRotate]);

  const handleSetMode = useCallback((newMode: DrawMode) => {
    setMode(newMode);
    setSelectedIndex(null);
    setDrawingVertices([]);
    setRectFirstCorner(null);
  }, []);

  const handleDelete = useCallback(() => {
    if (selectedIndex === null) return;
    const next = footprints.filter((_, i) => i !== selectedIndex);
    pushChange(next);
    setSelectedIndex(null);
  }, [selectedIndex, footprints, pushChange]);

  const finalizePolygon = useCallback(
    (vertices: LatLng[]) => {
      if (vertices.length < 3 || !canDraw) return;
      const clamped = vertices.map((v) => clampToProperty(v, boundaryPath));
      const newFp: BuildingFootprint = {
        area_sqm: approxAreaSqm(clamped),
        coords: toTuples(clamped),
        hasBuffer: true,
      };
      pushChange([...footprints, newFp]);
      setDrawingVertices([]);
      setRectFirstCorner(null);
      setMode("edit");
      setSelectedIndex(footprints.length);
    },
    [canDraw, boundaryPath, footprints, pushChange]
  );

  // ── Render mask + boundary (static) ──────────────────────────────────────
  useEffect(() => {
    if (!map) return;
    const outer = [
      { lat: -10, lng: 110 },
      { lat: -10, lng: 160 },
      { lat: -45, lng: 160 },
      { lat: -45, lng: 110 },
    ];
    const hole = [...boundaryPath].reverse();
    maskPolyRef.current = new google.maps.Polygon({
      paths: [outer, hole],
      fillColor: "#000000",
      fillOpacity: 0.6,
      strokeWeight: 0,
      clickable: false,
      zIndex: 1,
      map,
    });
    boundaryPolyRef.current = new google.maps.Polygon({
      paths: boundaryPath,
      fillColor: "transparent",
      fillOpacity: 0,
      strokeColor: "#ffffff",
      strokeWeight: 2,
      strokeOpacity: 0.8,
      clickable: false,
      zIndex: 2,
      map,
    });
    return () => {
      maskPolyRef.current?.setMap(null);
      boundaryPolyRef.current?.setMap(null);
    };
  }, [map, boundaryPath]);

  // ── Render complex boundary (BUP/GTP) ─────────────────────────────────
  const complexBoundaryRef = useRef<google.maps.Polygon[]>([]);
  useEffect(() => {
    complexBoundaryRef.current.forEach((p) => p.setMap(null));
    complexBoundaryRef.current = [];
    if (!map || !complexBoundary || complexBoundary.length === 0) return;

    for (const ring of complexBoundary) {
      const path = ring.map(([lat, lng]) => ({ lat, lng }));
      const poly = new google.maps.Polygon({
        paths: path,
        fillColor: "transparent",
        fillOpacity: 0,
        strokeColor: "#ffffff",
        strokeWeight: 1.5,
        strokeOpacity: 0.4,
        clickable: false,
        zIndex: 0,
      });
      poly.setMap(map);
      // Dashed stroke via icons on a polyline overlay
      complexBoundaryRef.current.push(poly);
    }

    return () => {
      complexBoundaryRef.current.forEach((p) => p.setMap(null));
      complexBoundaryRef.current = [];
    };
  }, [map, complexBoundary]);

  // ── Pan to focused nearby subdivision ────────────────────────────────
  useEffect(() => {
    if (!map || !focusedNearbyPlan) return;
    map.panTo(focusedNearbyPlan);
    const currentZoom = map.getZoom();
    if (currentZoom != null && currentZoom > 17) map.setZoom(17);
  }, [map, focusedNearbyPlan]);

  // ── Render nearby subdivision boundaries ──────────────────────────────
  const nearbySubdivisionRef = useRef<google.maps.Polygon[]>([]);
  useEffect(() => {
    nearbySubdivisionRef.current.forEach((p) => p.setMap(null));
    nearbySubdivisionRef.current = [];
    if (!map || !nearbySubdivisions || nearbySubdivisions.length === 0) return;

    for (const sub of nearbySubdivisions) {
      for (const ring of sub.rings) {
        const path = ring.map(([lat, lng]) => ({ lat, lng }));
        const poly = new google.maps.Polygon({
          paths: path,
          fillColor: "#6366F1",
          fillOpacity: 0.35,
          strokeColor: "#818CF8",
          strokeWeight: 1.5,
          strokeOpacity: 1,
          clickable: true,
          zIndex: 0,
        });
        poly.setMap(map);

        poly.addListener("click", (e: google.maps.PolyMouseEvent) => {
          const position = e.latLng?.toJSON() ?? sub.centroid;
          setNearbyInfoWindow({
            plan: sub.plan,
            addresses: sub.addresses,
            lot_count: sub.lot_count,
            total_area_sqm: sub.total_area_sqm,
            distance_m: sub.distance_m,
            position,
          });
          onNearbyPlanClick?.({
            plan: sub.plan,
            addresses: sub.addresses,
            lot_count: sub.lot_count,
            total_area_sqm: sub.total_area_sqm,
            distance_m: sub.distance_m,
            centroid: sub.centroid,
          });
        });

        poly.addListener("mouseover", () => {
          poly.setOptions({ fillOpacity: 0.55, strokeWeight: 2.5 });
        });
        poly.addListener("mouseout", () => {
          poly.setOptions({ fillOpacity: 0.35, strokeWeight: 1.5 });
        });

        nearbySubdivisionRef.current.push(poly);
      }
    }

    return () => {
      nearbySubdivisionRef.current.forEach((p) => p.setMap(null));
      nearbySubdivisionRef.current = [];
    };
  }, [map, nearbySubdivisions, onNearbyPlanClick]);

  // ── Nearby subdivision area labels ────────────────────────────────────
  useEffect(() => {
    for (const m of subdivisionLabelMarkersRef.current) m.setMap(null);
    subdivisionLabelMarkersRef.current = [];
    if (!map || !showSubdivisionLabels || !nearbySubdivisions || nearbySubdivisions.length === 0) return;

    for (const sub of nearbySubdivisions) {
      const marker = new google.maps.Marker({
        position: sub.centroid,
        icon: makeAreaLabelIcon(sub.total_area_sqm),
        clickable: false,
        zIndex: 5,
        map,
      });
      subdivisionLabelMarkersRef.current.push(marker);
    }

    return () => {
      for (const m of subdivisionLabelMarkersRef.current) m.setMap(null);
      subdivisionLabelMarkersRef.current = [];
    };
  }, [map, nearbySubdivisions, showSubdivisionLabels]);

  // ── Nearby subdivision InfoWindow ──────────────────────────────────────
  useEffect(() => {
    if (!map) return;

    if (nearbyInfoWindowRef.current) {
      nearbyInfoWindowRef.current.close();
      nearbyInfoWindowRef.current = null;
    }

    if (!nearbyInfoWindow) return;

    const distKm = (nearbyInfoWindow.distance_m / 1000).toFixed(1);
    const area = nearbyInfoWindow.total_area_sqm.toLocaleString();
    const addressList = nearbyInfoWindow.addresses
      .map((a) => `<li style="margin:1px 0">${a}</li>`)
      .join("");

    const content = `
      <div style="font-family:system-ui,sans-serif;font-size:13px;max-width:280px;line-height:1.4">
        <div style="font-weight:600;font-size:14px;margin-bottom:6px;color:#1e1b4b">${nearbyInfoWindow.plan}</div>
        <ul style="margin:0 0 8px 0;padding-left:16px;color:#374151">${addressList}</ul>
        <div style="display:flex;gap:12px;color:#6b7280;font-size:12px">
          <span>${nearbyInfoWindow.lot_count} lots</span>
          <span>${area} m²</span>
          <span>${distKm} km away</span>
        </div>
      </div>`;

    const iw = new google.maps.InfoWindow({ content, position: nearbyInfoWindow.position });
    iw.open(map);
    nearbyInfoWindowRef.current = iw;

    const closeListener = iw.addListener("closeclick", () => setNearbyInfoWindow(null));
    return () => {
      google.maps.event.removeListener(closeListener);
      iw.close();
    };
  }, [map, nearbyInfoWindow]);

  // Helper: check if a point falls inside any nearby subdivision polygon
  const isInsideNearbySubdivision = useCallback(
    (point: LatLng): boolean => {
      if (!nearbySubdivisions || nearbySubdivisions.length === 0) return false;
      for (const sub of nearbySubdivisions) {
        for (const ring of sub.rings) {
          const poly = ring.map(([lat, lng]) => ({ lat, lng }));
          if (pointInPolygon(point, poly)) return true;
        }
      }
      return false;
    },
    [nearbySubdivisions]
  );

  // ── Render building polygons ─────────────────────────────────────────────
  useEffect(() => {
    if (!map) return;

    for (const p of buildingPolysRef.current) {
      google.maps.event.clearInstanceListeners(p);
      p.setMap(null);
    }
    buildingPolysRef.current = [];

    footprints.forEach((fp, idx) => {
      const path = toLatLngs(fp.coords);
      const isSelected = idx === selectedIndex && mode === "edit";

      const poly = new google.maps.Polygon({
        paths: path,
        fillColor: "#FFDD00",
        fillOpacity: isSelected ? 0.65 : 0.5,
        strokeColor: isSelected ? "#ffffff" : "#FFDD00",
        strokeWeight: isSelected ? 2.5 : 1,
        strokeOpacity: 0.9,
        editable: isSelected,
        draggable: false,
        clickable: mode === "edit",
        zIndex: 10 + idx,
        map,
      });

      if (mode === "edit") {
        poly.addListener("click", () => setSelectedIndex(idx));
      }

      if (isSelected) {
        const coords = toLatLngs(fp.coords);
        const center = polygonCentroid(coords);

        // Place rotation handle at top-right of the polygon's bounding box
        const maxLat = Math.max(...coords.map((c) => c.lat));
        const maxLng = Math.max(...coords.map((c) => c.lng));
        const HANDLE_OFFSET = 0.00004;
        const handlePos = { lat: maxLat + HANDLE_OFFSET, lng: maxLng + HANDLE_OFFSET };
        handleRelativeRef.current = {
          lat: handlePos.lat - center.lat,
          lng: handlePos.lng - center.lng,
        };

        const rotateIconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="white" stroke="#ddd" stroke-width="1.5"/><path d="M5.5 12A6.5 6.5 0 0 1 18.5 12" fill="none" stroke="#555" stroke-width="2" stroke-linecap="round"/><polyline points="16.5,10 18.5,12 20.5,10" fill="none" stroke="#555" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 12A6.5 6.5 0 0 1 5.5 12" fill="none" stroke="#555" stroke-width="2" stroke-linecap="round"/><polyline points="3.5,14 5.5,12 7.5,14" fill="none" stroke="#555" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

        const handle = new google.maps.Marker({
          position: handlePos,
          icon: {
            url: `data:image/svg+xml,${encodeURIComponent(rotateIconSvg)}`,
            scaledSize: new google.maps.Size(26, 26),
            anchor: new google.maps.Point(13, 13),
          },
          cursor: "grab",
          zIndex: 30,
          map,
        });
        rotationHandleRef.current = handle;

        handle.addListener("mousedown", (e: google.maps.MapMouseEvent) => {
          if (!e.latLng) return;
          const point = { lat: e.latLng.lat(), lng: e.latLng.lng() };
          rotateStateRef.current = {
            isRotating: true,
            startAngle: Math.atan2(point.lng - center.lng, point.lat - center.lat),
            baseCoords: [...coords],
            centroid: { ...center },
            polyIndex: idx,
          };
          rotatingPolyRef.current = poly;
          map.setOptions({ gestureHandling: "none" });
        });

        // Sync after vertex edit
        const syncPath = () => {
          const updatedPath = poly
            .getPath()
            .getArray()
            .map((ll) =>
              clampToProperty({ lat: ll.lat(), lng: ll.lng() }, boundaryPath)
            );
          poly.setPath(updatedPath);
          const next = [...footprints];
          next[idx] = {
            area_sqm: approxAreaSqm(updatedPath),
            coords: toTuples(updatedPath),
            hasBuffer: footprints[idx].hasBuffer,
          };
          pushChange(next);
        };

        poly.getPath().addListener("set_at", syncPath);
        poly.getPath().addListener("insert_at", syncPath);
      }

      buildingPolysRef.current.push(poly);
    });

    return () => {
      for (const p of buildingPolysRef.current) {
        google.maps.event.clearInstanceListeners(p);
        p.setMap(null);
      }
      buildingPolysRef.current = [];
      if (rotationHandleRef.current) {
        google.maps.event.clearInstanceListeners(rotationHandleRef.current);
        rotationHandleRef.current.setMap(null);
        rotationHandleRef.current = null;
      }
    };
  }, [map, footprints, selectedIndex, mode, boundaryPath, pushChange]);

  // ── Render clearance polygons (red ring around buildings with hasBuffer) ──
  useEffect(() => {
    if (!map) return;

    for (const p of bufferPolysRef.current) p.setMap(null);
    bufferPolysRef.current = [];

    footprints.forEach((fp, fpIdx) => {
      if (!fp.hasBuffer) return;
      const bufCoords = computeBufferCoords(fp, boundaryCoords);
      if (!bufCoords) return;
      // Outer ring = buffer boundary, inner hole = own building footprint
      // Other buildings don't need holes — they render at higher zIndex and paint over the buffer
      const outerPath = bufCoords.map(([lat, lng]) => ({ lat, lng }));
      const holePath = [...fp.coords].map(([lat, lng]) => ({ lat, lng })).reverse();
      const poly = new google.maps.Polygon({
        paths: [outerPath, holePath],
        fillColor: "#EF4444",
        fillOpacity: 0.35,
        strokeColor: "#DC2626",
        strokeWeight: 1,
        strokeOpacity: 0.6,
        clickable: false,
        zIndex: 5,
        map,
      });
      bufferPolysRef.current.push(poly);
    });

    return () => {
      for (const p of bufferPolysRef.current) p.setMap(null);
      bufferPolysRef.current = [];
    };
  }, [map, footprints, boundaryCoords, boundaryPath]);

  // ── Encumbrance overlays (easements, roads, watercourses, covenants…) ───────
  useEffect(() => {
    if (!map) return;

    for (const p of encumbrancePolysRef.current) p.setMap(null);
    for (const m of encumbranceLabelMarkersRef.current) m.setMap(null);
    encumbrancePolysRef.current = [];
    encumbranceLabelMarkersRef.current = [];

    const visible = encumbrances.filter(
      (e) => !visibleEncumbranceTypes || visibleEncumbranceTypes.has(e.label)
    );

    for (const enc of visible) {
      const { fill, stroke } = encumbranceColour(enc.label);

      for (const ring of enc.coords) {
        if (ring.length < 3) continue;
        const path = ring.map(([lat, lng]) => ({ lat, lng }));

        const poly = new google.maps.Polygon({
          paths: path,
          fillColor: fill,
          fillOpacity: 0.35,
          strokeColor: stroke,
          strokeWeight: 2,
          strokeOpacity: 0.8,
          clickable: false,
          zIndex: 3,
          map,
        });
        encumbrancePolysRef.current.push(poly);

        // Label at centroid of ring
        const centroid = polygonCentroid(path);
        const labelSvg = makeLabelIcon(enc.label, fill);
        const marker = new google.maps.Marker({
          position: centroid,
          icon: labelSvg,
          clickable: false,
          zIndex: 4,
          map,
        });
        encumbranceLabelMarkersRef.current.push(marker);
      }
    }

    return () => {
      for (const p of encumbrancePolysRef.current) p.setMap(null);
      for (const m of encumbranceLabelMarkersRef.current) m.setMap(null);
      encumbrancePolysRef.current = [];
      encumbranceLabelMarkersRef.current = [];
    };
  }, [map, encumbrances, visibleEncumbranceTypes]);

  // ── Edge measurement labels ───────────────────────────────────────────────
  useEffect(() => {
    if (!map) return;

    for (const m of measureMarkersRef.current) m.setMap(null);
    measureMarkersRef.current = [];

    if (!showMeasurements) return;

    const addEdgeLabels = (path: LatLng[], zIndex: number) => {
      const n = path.length;
      for (let i = 0; i < n; i++) {
        const a = path[i];
        const b = path[(i + 1) % n];
        const distM = edgeLengthM(a, b);
        if (distM < 1.5) continue; // skip edges too short to label

        const mid: LatLng = { lat: (a.lat + b.lat) / 2, lng: (a.lng + b.lng) / 2 };

        const mPerLat = 111320;
        const mPerLng = 111320 * Math.cos((mid.lat * Math.PI) / 180);
        let angle = (Math.atan2(-(b.lat - a.lat) * mPerLat, (b.lng - a.lng) * mPerLng) * 180) / Math.PI;
        if (angle > 90) angle -= 180;
        if (angle < -90) angle += 180;

        const marker = new google.maps.Marker({
          position: mid,
          icon: makeMeasurementIcon(distM, angle),
          clickable: false,
          zIndex,
          map,
        });
        measureMarkersRef.current.push(marker);
      }
    };

    // Boundary edges
    addEdgeLabels(boundaryPath, 24);

    // Building footprint edges + buffer edges
    footprints.forEach((fp) => {
      addEdgeLabels(toLatLngs(fp.coords), 25);
      if (fp.hasBuffer) {
        const bufCoords = computeBufferCoords(fp, boundaryCoords);
        if (bufCoords) addEdgeLabels(toLatLngs(bufCoords), 23);
      }
    });

    return () => {
      for (const m of measureMarkersRef.current) m.setMap(null);
      measureMarkersRef.current = [];
    };
  }, [map, footprints, boundaryPath, boundaryCoords, showMeasurements]);

  // ── Rotation drag: live rotate on mousemove, commit on mouseup ──────────
  useEffect(() => {
    if (!map) return;

    const mapMoveListener = map.addListener(
      "mousemove",
      (e: google.maps.MapMouseEvent) => {
        const state = rotateStateRef.current;
        if (!state || !e.latLng) return;

        const point = { lat: e.latLng.lat(), lng: e.latLng.lng() };
        const currentAngle = Math.atan2(
          point.lng - state.centroid.lng,
          point.lat - state.centroid.lat
        );
        const deltaRad = currentAngle - state.startAngle;

        if (state.isRotating && rotatingPolyRef.current) {
          const deltaDeg = (deltaRad * 180) / Math.PI;
          const rotated = rotatePolygon(state.baseCoords, deltaDeg, state.centroid);
          rotatingPolyRef.current.setPath(rotated);

          // Orbit the handle around the centroid to match the rotation
          if (rotationHandleRef.current) {
            const hr = handleRelativeRef.current;
            const cos = Math.cos(deltaRad);
            const sin = Math.sin(deltaRad);
            rotationHandleRef.current.setPosition({
              lat: state.centroid.lat + hr.lat * cos - hr.lng * sin,
              lng: state.centroid.lng + hr.lat * sin + hr.lng * cos,
            });
          }
        }
      }
    );

    const handleMouseUp = () => {
      const state = rotateStateRef.current;
      if (!state) return;

      if (state.isRotating && rotatingPolyRef.current) {
        const finalPath = rotatingPolyRef.current
          .getPath()
          .getArray()
          .map((ll) => ({ lat: ll.lat(), lng: ll.lng() }));
        const boundary = boundaryPathRef.current;
        const confined =
          clipPolygonToBoundary(finalPath, boundary) ??
          clampPolygonToProperty(finalPath, boundary);
        const next = [...footprintsRef.current];
        next[state.polyIndex] = {
          area_sqm: approxAreaSqm(confined),
          coords: toTuples(confined),
          hasBuffer: footprintsRef.current[state.polyIndex].hasBuffer,
        };
        pushChangeRef.current(next);
      }

      map.setOptions({ gestureHandling: "greedy" });
      rotateStateRef.current = null;
      rotatingPolyRef.current = null;
    };

    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      google.maps.event.removeListener(mapMoveListener);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [map]);

  // ── Drawing: polyline preview + vertex markers ───────────────────────────
  useEffect(() => {
    if (!map) return;

    drawingPolylineRef.current?.setMap(null);
    for (const m of vertexMarkersRef.current) m.setMap(null);
    vertexMarkersRef.current = [];

    if (mode !== "draw-polygon" || drawingVertices.length === 0) return;

    drawingPolylineRef.current = new google.maps.Polyline({
      path: drawingVertices,
      strokeColor: "#FFDD00",
      strokeWeight: 2,
      strokeOpacity: 0.8,
      clickable: false,
      zIndex: 20,
      map,
    });

    drawingVertices.forEach((v, i) => {
      const isFirst = i === 0;
      const canClose = isFirst && drawingVertices.length >= 3;

      const marker = new google.maps.Marker({
        position: v,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: isFirst ? 7 : 5,
          fillColor: isFirst ? "#ffffff" : "#FFDD00",
          fillOpacity: 1,
          strokeColor: isFirst ? "#FFDD00" : "#ffffff",
          strokeWeight: 2,
        },
        clickable: canClose,
        zIndex: 25,
        map,
      });

      if (canClose) {
        marker.addListener("click", () => finalizePolygon(drawingVertices));
      }

      vertexMarkersRef.current.push(marker);
    });

    return () => {
      drawingPolylineRef.current?.setMap(null);
      for (const m of vertexMarkersRef.current) m.setMap(null);
      vertexMarkersRef.current = [];
    };
  }, [map, mode, drawingVertices, finalizePolygon]);

  // ── Drawing: rectangle first corner marker ───────────────────────────────
  useEffect(() => {
    if (!map) return;
    if (mode !== "draw-rectangle") return;
    if (!rectFirstCorner) return;

    const marker = new google.maps.Marker({
      position: rectFirstCorner,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 6,
        fillColor: "#FFDD00",
        fillOpacity: 1,
        strokeColor: "#ffffff",
        strokeWeight: 2,
      },
      zIndex: 25,
      map,
    });

    return () => {
      marker.setMap(null);
    };
  }, [map, mode, rectFirstCorner]);

  // ── Map click handler (mode-dependent) ───────────────────────────────────
  useEffect(() => {
    if (!map) return;

    mapClickListenerRef.current?.remove();
    mapDblClickListenerRef.current?.remove();

    if (mode === "edit") {
      mapClickListenerRef.current = map.addListener("click", () =>
        setSelectedIndex(null)
      );
      return () => {
        mapClickListenerRef.current?.remove();
      };
    }

    if (mode === "draw-polygon") {
      mapClickListenerRef.current = map.addListener(
        "click",
        (e: google.maps.MapMouseEvent) => {
          if (!e.latLng) return;
          const raw = { lat: e.latLng.lat(), lng: e.latLng.lng() };
          if (isInsideNearbySubdivision(raw)) return;
          const point = clampToProperty(raw, boundaryPath);
          setDrawingVertices((prev) => [...prev, point]);
        }
      );
      mapDblClickListenerRef.current = map.addListener(
        "dblclick",
        (e: google.maps.MapMouseEvent) => {
          e.stop?.();
          setDrawingVertices((prev) => {
            if (prev.length >= 3) {
              setTimeout(() => finalizePolygon(prev), 0);
            }
            return prev;
          });
        }
      );
      return () => {
        mapClickListenerRef.current?.remove();
        mapDblClickListenerRef.current?.remove();
      };
    }

    if (mode === "draw-rectangle") {
      mapClickListenerRef.current = map.addListener(
        "click",
        (e: google.maps.MapMouseEvent) => {
          if (!e.latLng) return;
          const raw = { lat: e.latLng.lat(), lng: e.latLng.lng() };
          if (isInsideNearbySubdivision(raw)) return;
          const point = clampToProperty(raw, boundaryPath);
          setRectFirstCorner((prev) => {
            if (!prev) return point;
            const corners: LatLng[] = [
              { lat: prev.lat, lng: prev.lng },
              { lat: prev.lat, lng: point.lng },
              { lat: point.lat, lng: point.lng },
              { lat: point.lat, lng: prev.lng },
            ];
            setTimeout(() => finalizePolygon(corners), 0);
            return null;
          });
        }
      );
      return () => {
        mapClickListenerRef.current?.remove();
      };
    }
  }, [map, mode, boundaryPath, finalizePolygon, isInsideNearbySubdivision]);

  // Change cursor based on mode
  useEffect(() => {
    if (!map) return;
    if (mode === "draw-polygon" || mode === "draw-rectangle") {
      map.setOptions({ draggableCursor: "crosshair" });
    } else {
      map.setOptions({ draggableCursor: undefined });
    }
  }, [map, mode]);

  if (readOnly) return null;

  return (
    <MapToolbar
      mode={mode}
      setMode={handleSetMode}
      canDraw={canDraw}
      selectedIndex={selectedIndex}
      onDelete={handleDelete}
      onNudge={handleNudge}
      canUndo={canUndo}
      canRedo={canRedo}
      onUndo={undo}
      onRedo={redo}
      selectedHasBuffer={selectedIndex !== null ? (footprints[selectedIndex]?.hasBuffer ?? false) : false}
      onToggleBuffer={handleToggleBuffer}
      showMeasurements={showMeasurements}
      onToggleMeasurements={() => setShowMeasurements((v) => !v)}
      hasNearbySubdivisions={(nearbySubdivisions?.length ?? 0) > 0}
      showSubdivisionLabels={showSubdivisionLabels}
      onToggleSubdivisionLabels={() => setShowSubdivisionLabels((v) => !v)}
    />
  );
}

// ─── Main component ─────────────────────────────────────────────────────────

export default function PropertyMap({
  apiKey,
  boundaryCoords,
  centroid,
  footprints,
  onFootprintsChange,
  readOnly,
  complexBoundary,
  nearbySubdivisions,
  focusedNearbyPlan,
  onNearbyPlanClick,
}: PropertyMapProps) {
  return (
    <APIProvider apiKey={apiKey}>
      <div className="relative w-full aspect-[4/3] rounded-xl overflow-hidden border border-zinc-200">
        <Map
          defaultCenter={centroid}
          defaultZoom={19}
          mapTypeId="hybrid"
          disableDefaultUI={true}
          zoomControl={true}
          minZoom={10}
          maxZoom={22}
          gestureHandling="greedy"
          tilt={0}
        >
          <MapInterior
            boundaryCoords={boundaryCoords}
            footprints={footprints}
            onFootprintsChange={onFootprintsChange}
            readOnly={readOnly}
            complexBoundary={complexBoundary}
            nearbySubdivisions={nearbySubdivisions}
            focusedNearbyPlan={focusedNearbyPlan}
            onNearbyPlanClick={onNearbyPlanClick}
          />
        </Map>
      </div>
    </APIProvider>
  );
}
