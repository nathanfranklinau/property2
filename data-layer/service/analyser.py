"""
Analysis pipeline orchestrator.

Coordinates image retrieval → building detection → satellite masking →
pool detection → mask2 generation → space calculation, updating
property_analysis in the DB as each step completes.

Image outputs (all stored in IMAGES_DIR/{parcel_id}/):
    satellite.png          — Google Maps satellite with red boundary
    styled_map.png         — Cloud-styled map (yellow buildings, pink roads on dark
                             purple); used for boundary detection and as the display image
    satellite_masked.jpg   — Satellite clipped to property boundary (black outside)
    mask2.png              — Colour-coded space visualisation (matches styled map palette)
    masked_raw_pool.jpg    — Satellite masked + YOLO pool bounding boxes
"""

import datetime
import json
import os
import logging
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from pyproj import Transformer

load_dotenv(Path(__file__).parent.parent / ".env")

log = logging.getLogger(__name__)

IMAGES_DIR = Path(os.getenv("IMAGES_DIR", "./images"))


# ─── DB helpers ──────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "subdivide"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def update_analysis(conn, parcel_id: str, **fields):
    """Update specific columns in property_analysis for a parcel."""
    if not fields:
        return
    set_parts = [f"{k} = %({k})s" for k in fields if k != "parcel_id"]
    set_parts.append("updated_at = NOW()")
    set_clause = ", ".join(set_parts)

    params = {k: v for k, v in fields.items()}
    params["parcel_id"] = parcel_id

    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE property_analysis SET {set_clause} WHERE parcel_id = %(parcel_id)s",
            params,
        )
    conn.commit()


# Pyproj transformer: GDA2020 (EPSG:7844) → GDA94 (EPSG:4283).
#
# Why GDA94 and not WGS84?
# PostGIS ST_Transform(geometry, 4326) is a no-op between 7844 and 4326 because
# pyproj/PROJ treats the two as identical (the Helmert parameters are near-zero).
# However, Google Maps' Australian map tiles and property boundary data are compiled
# from GDA94-era government datasets.  The datum shift between GDA2020 and GDA94 is
# ~1.5 m (south-west), which is visible at zoom 20.  Transforming to GDA94 aligns
# our cadastre boundary polyline with Google Maps' rendered property lines.
_GDA2020_TO_GDA94 = Transformer.from_crs("EPSG:7844", "EPSG:4283", always_xy=True)


def get_parcel_boundary_for_maps(
    conn, parcel_id: str
) -> tuple[list[tuple[float, float]], tuple[float, float]] | tuple[None, None]:
    """
    Return the property boundary and centroid, transformed for Google Maps.

    Reads geometry in SRID 7844 (GDA2020) from the parcels table, then applies
    a pyproj datum shift to GDA94 (EPSG:4283) so the boundary visually aligns
    with Google Maps' Australian basemap.

    Returns:
        (boundary_coords, centroid) where:
            boundary_coords: list of (lat, lon) tuples
            centroid:        (lat, lon) tuple — centroid of the transformed boundary
        or (None, None) if no geometry exists.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT ST_AsGeoJSON(geometry) FROM parcels WHERE id = %s",
            (parcel_id,),
        )
        row = cur.fetchone()

    if not row or not row[0]:
        return None, None

    gj = json.loads(row[0])
    ring = None
    if gj["type"] == "MultiPolygon":
        ring = gj["coordinates"][0][0]   # first polygon, outer ring
    elif gj["type"] == "Polygon":
        ring = gj["coordinates"][0]      # outer ring

    if not ring:
        return None, None

    # Transform each vertex from GDA2020 → GDA94 and swap to (lat, lon).
    # GeoJSON is [lon, lat]; Google Maps API wants (lat, lon).
    transformed: list[tuple[float, float]] = []
    sum_lat = 0.0
    sum_lon = 0.0
    n = 0
    for coord in ring:
        lon_94, lat_94 = _GDA2020_TO_GDA94.transform(coord[0], coord[1])
        transformed.append((lat_94, lon_94))
        sum_lat += lat_94
        sum_lon += lon_94
        n += 1

    centroid = (sum_lat / n, sum_lon / n) if n > 0 else (0.0, 0.0)
    return transformed, centroid


def get_registered_pool_count(conn, cadastre_lot: str, cadastre_plan: str) -> int:
    """
    Look up how many registered pools are associated with this parcel.
    Matches via suburb (approximate — registered pools don't have parcel IDs).
    Returns 0 if no match found.
    TODO: Replace with spatial join once parcel geometry is reliably populated.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT display_address FROM parcels WHERE cadastre_lot = %s AND cadastre_plan = %s",
            (cadastre_lot, cadastre_plan),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return 0

        address = row[0].upper()
        parts = address.split(",")
        suburb = parts[-1].strip() if parts else ""

        cur.execute(
            "SELECT COUNT(*) FROM qld_pools_registered WHERE UPPER(suburb) = %s",
            (suburb,),
        )
        count_row = cur.fetchone()
        return count_row[0] if count_row else 0


# ─── Pipeline ────────────────────────────────────────────────────────────────

def run_analysis(
    parcel_id: str,
    cadastre_lot: str,
    cadastre_plan: str,
    lat: float,
    lon: float,
    lot_area_sqm: float,
):
    """
    Full analysis pipeline. Updates property_analysis at each step.

    Steps:
        1. Fetch parcel boundary geometry from DB (→ GDA94-adjusted coords for image overlay)
        2. Download Google Maps imagery with red boundary polyline
        3. Detect buildings with OpenCV
        4. Create satellite_masked.jpg (boundary mask applied to satellite)
        5. Detect pools with YOLO (on masked satellite)
        6. Generate mask2.png (colour-coded space visualisation)
        7. Calculate available space
    """
    log.info(f"Starting analysis for parcel {parcel_id} ({cadastre_lot}/{cadastre_plan})")
    conn = get_connection()

    try:
        # ── Step 1: Fetch parcel boundary ─────────────────────────────────
        boundary_coords, boundary_centroid = get_parcel_boundary_for_maps(conn, parcel_id)
        if boundary_coords:
            log.info(f"  boundary: {len(boundary_coords)} vertices (GDA94-adjusted)")
        else:
            log.warning(
                "  No parcel geometry in DB — images will have no red boundary. "
                "Building detection will fail (no red contour to find)."
            )

        # Use the boundary centroid (GDA94-adjusted) as the image centre so
        # the boundary polyline and the map tiles are in the same datum.
        if boundary_centroid:
            image_lat, image_lon = boundary_centroid
        else:
            image_lat, image_lon = lat, lon

        # ── Step 2: Download imagery ──────────────────────────────────────
        update_analysis(conn, parcel_id, image_status="downloading")

        from .image_retrieval import download_property_images

        parcel_image_dir = IMAGES_DIR / parcel_id
        parcel_image_dir.mkdir(parents=True, exist_ok=True)

        images = download_property_images(
            lat=image_lat,
            lon=image_lon,
            output_dir=parcel_image_dir,
            boundary_coords=boundary_coords,
        )

        update_analysis(
            conn,
            parcel_id,
            image_status="complete",
            image_satellite_path=str(images["satellite"]),
            image_styled_map_path=str(images["styled_map"]),
        )

        # ── Step 2b: Street View hero shot ────────────────────────────────
        # Use the original GNAF address coordinates (lat, lon) — the address
        # point sits on the street frontage, giving the best hero shot angle.
        # Non-fatal: if Street View is unavailable the pipeline continues.
        try:
            from .image_retrieval import download_street_view_image

            sv_path = download_street_view_image(lat, lon, parcel_image_dir)
            if sv_path:
                update_analysis(conn, parcel_id, image_street_view_path=str(sv_path))
                log.info(f"  Street View saved: {sv_path.name}")
            else:
                log.info("  Street View: no coverage at this location")
        except Exception as sv_err:
            log.warning(f"  Street View fetch failed (non-fatal): {sv_err}")

        # ── Step 3: Detect buildings ──────────────────────────────────────
        update_analysis(conn, parcel_id, analysis_status="detecting")

        from .building_detection import detect_buildings, create_satellite_masked, create_mask2_image, contours_to_geo_coords

        detection = detect_buildings(
            styled_map_path=images["styled_map"],
            lot_area_sqm=lot_area_sqm,
        )

        main_house_sqm = detection.get("main_house_size_sqm", 0.0)
        building_count = detection.get("building_count", 0)
        # Union area from mask pixel count — all buildings, no double-counting
        total_buildings_sqm = detection.get("total_buildings_sqm", main_house_sqm)
        boundary_mask = detection.get("_boundary_mask")
        boundary_contour = detection.get("_boundary_contour")
        building_contours = detection.get("_building_contours", [])
        all_buildings_sqm = detection.get("all_buildings_sqm", [])

        # Convert building pixel contours to geographic coordinates (GDA94)
        building_footprints_geo = None
        if building_contours and boundary_centroid:
            building_footprints_geo = contours_to_geo_coords(
                contours=building_contours,
                center_lat=image_lat,
                center_lon=image_lon,
                areas_sqm=all_buildings_sqm,
            )
            log.info(f"  converted {len(building_footprints_geo)} building contours to geo coords")

        # Store boundary coords + centroid + building footprints for frontend map
        boundary_json = json.dumps([[lat, lon] for lat, lon in boundary_coords]) if boundary_coords else None
        footprints_json = json.dumps(building_footprints_geo) if building_footprints_geo else None

        update_analysis(
            conn,
            parcel_id,
            main_house_size_sqm=main_house_sqm,
            building_count=building_count,
            building_footprints_geo=footprints_json,
            boundary_coords_gda94=boundary_json,
            centroid_lat=image_lat if boundary_centroid else None,
            centroid_lon=image_lon if boundary_centroid else None,
        )

        # ── Step 4: Create satellite_masked.jpg ───────────────────────────
        satellite_masked_path = parcel_image_dir / "satellite_masked.jpg"
        if boundary_mask is not None:
            create_satellite_masked(
                satellite_path=images["satellite"],
                boundary_mask=boundary_mask,
                output_path=satellite_masked_path,
            )
            update_analysis(conn, parcel_id, image_satellite_masked_path=str(satellite_masked_path))
        else:
            satellite_masked_path = images["satellite"]  # fallback to raw satellite

        # ── Step 5: Detect pools (YOLO on masked satellite) ───────────────
        from .pool_detection import detect_pools

        annotated_pool_path = parcel_image_dir / "masked_raw_pool.jpg"
        pool_result = detect_pools(
            satellite_path=satellite_masked_path,
            lot_area_sqm=lot_area_sqm,
            output_annotated_path=annotated_pool_path,
        )

        pool_count_detected = pool_result.get("pool_count", 0)
        pool_area_sqm = pool_result.get("pool_area_sqm", 0.0)
        pool_bboxes = [d["bbox"] for d in pool_result.get("detections", [])]
        pool_count_registered = get_registered_pool_count(conn, cadastre_lot, cadastre_plan)

        update_analysis(
            conn,
            parcel_id,
            pool_count_detected=pool_count_detected,
            pool_count_registered=pool_count_registered,
            pool_area_sqm=pool_area_sqm,
        )

        # ── Step 6: Generate mask2.png ────────────────────────────────────
        mask2_path = parcel_image_dir / "mask2.png"
        if boundary_mask is not None and boundary_contour is not None:
            create_mask2_image(
                styled_map_path=images["styled_map"],
                boundary_contour=boundary_contour,
                boundary_mask=boundary_mask,
                building_contours=building_contours,
                pool_bboxes=pool_bboxes,
                output_path=mask2_path,
            )
            update_analysis(conn, parcel_id, image_mask2_path=str(mask2_path))

        # ── Step 7: Calculate available space ─────────────────────────────
        # Available = lot area - ALL building footprints (union) - pool area - setback buffer
        # Using total_buildings_sqm (from mask pixel count) avoids double-counting
        # when detected building contours overlap.
        SETBACK_BUFFER_SQM = 50
        available_space = max(
            0.0,
            lot_area_sqm - total_buildings_sqm - pool_area_sqm - SETBACK_BUFFER_SQM,
        )

        update_analysis(
            conn,
            parcel_id,
            available_space_sqm=round(available_space, 1),
            analysis_status="complete",
            analyzed_at=datetime.datetime.utcnow(),
        )

        log.info(
            f"Analysis complete for parcel {parcel_id}: "
            f"house={main_house_sqm}m², all_buildings={total_buildings_sqm}m², "
            f"pools={pool_count_detected}, available={available_space:.1f}m²"
        )

    except Exception as e:
        log.exception(f"Analysis failed for parcel {parcel_id}: {e}")
        try:
            update_analysis(conn, parcel_id, analysis_status="failed", error_message=str(e))
        except Exception:
            pass

    finally:
        conn.close()


# ─── Status query ────────────────────────────────────────────────────────────

def get_analysis_status(parcel_id: str) -> dict[str, Any] | None:
    """Fetch the current analysis status from the database."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    p.id AS parcel_id,
                    pa.image_status,
                    pa.analysis_status,
                    pa.main_house_size_sqm,
                    pa.building_count,
                    pa.available_space_sqm,
                    pa.pool_count_detected,
                    pa.pool_count_registered,
                    pa.pool_area_sqm,
                    pa.image_styled_map_path,
                    pa.image_satellite_masked_path,
                    pa.image_mask2_path,
                    pa.error_message
                FROM parcels p
                JOIN property_analysis pa ON pa.parcel_id = p.id
                WHERE p.id = %s
                """,
                (parcel_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()
