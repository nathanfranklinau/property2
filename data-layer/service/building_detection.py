"""
Building detection using OpenCV HSV colour analysis.

Detection runs on the STYLED MAP image (Cloud map_id=813ac30c17e4a918b39744c0)
which renders building footprints in yellow and roads in pink on a dark purple
background. This gives unambiguous colour separation for detection.

On the styled map:
    yellow (H≈20–38) → buildings ← target
    pink              → roads   (outside yellow detection range — excluded naturally)
    dark purple       → background (outside yellow range — excluded naturally)

Since buildings are already rendered yellow on the styled map, no outline drawing
is needed. The styled map is saved directly as the markup image.

Algorithm:
    1. Find property boundary — largest red contour in the styled map image.
       Red (H≈0) is clearly distinct from pink roads (H≈163) and yellow buildings
       (H≈30) so the polyline is reliably detected on the dark purple background.
    2. Create a filled mask of the property interior.
    3. Use boundary contour pixel area for the pixel→m² calibration ratio.
    4. Apply the mask to the styled map.
    5. Detect yellow shapes as buildings (HSV H:20–38, S>100, V>100).
    6. Filter by minimum area (100px²).

Helper functions:
    create_satellite_masked() — clip satellite image to property boundary.
    create_mask2_image()      — colour-coded space usage visualisation.
"""

import logging
import math
from pathlib import Path

log = logging.getLogger(__name__)

MIN_BUILDING_AREA_PX = 100


def contours_to_geo_coords(
    contours: list,
    center_lat: float,
    center_lon: float,
    zoom: int = 20,
    image_size: int = 640,
    scale: int = 2,
    areas_sqm: list[float] | None = None,
) -> list[dict]:
    """
    Convert OpenCV pixel contours to geographic coordinates (GDA94 lat/lon).

    Uses the Google Maps Static API Mercator projection to map pixel offsets
    from the image center back to lat/lon.

    Args:
        contours:    List of OpenCV contour arrays (pixel coordinates on the
                     scale*image_size × scale*image_size image).
        center_lat:  Latitude of the image center (GDA94).
        center_lon:  Longitude of the image center (GDA94).
        zoom:        Google Maps zoom level used for the static image.
        image_size:  Logical image size (before scale), e.g. 640.
        scale:       Google Maps scale factor (2 = 1280×1280 actual pixels).
        areas_sqm:   Optional list of building areas in m² (same order as contours).

    Returns:
        List of dicts: [{"area_sqm": float, "coords": [[lat, lon], ...]}, ...]
    """
    pixel_w = image_size * scale  # actual image width in pixels (1280)
    half_w = pixel_w / 2.0

    # Total world width in pixels at this zoom level
    world_size = 256 * (2 ** zoom)

    # Convert center lat/lon to world pixel coordinates (Mercator)
    center_wx = (center_lon + 180.0) / 360.0 * world_size
    sin_lat = math.sin(center_lat * math.pi / 180.0)
    center_wy = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * world_size

    results = []
    for i, contour in enumerate(contours):
        coords = []
        for point in contour:
            # OpenCV contour point shape: [[x, y]]
            px, py = float(point[0][0]), float(point[0][1])

            # Pixel offset from image center, then to world pixel
            wx = center_wx + (px - half_w) / scale
            wy = center_wy + (py - half_w) / scale

            # World pixel back to lat/lon
            lon = wx / world_size * 360.0 - 180.0
            n = math.pi - 2 * math.pi * wy / world_size
            lat = 180.0 / math.pi * math.atan(0.5 * (math.exp(n) - math.exp(-n)))

            coords.append([lat, lon])

        # Close the polygon if not already closed
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])

        area = areas_sqm[i] if areas_sqm and i < len(areas_sqm) else 0.0
        results.append({"area_sqm": area, "coords": coords})

    return results
# Yellow building detection ranges for the Cloud-styled map (map_id=813ac30c17e4a918b39744c0).
# Buildings render as bright yellow (≈#FFD700): H≈30 in OpenCV 0–180 scale.
BUILDING_YELLOW_LOWER = (20, 100, 100)
BUILDING_YELLOW_UPPER = (38, 255, 255)


def detect_buildings(
    styled_map_path: Path,
    lot_area_sqm: float,
) -> dict:
    """
    Detect buildings using the Cloud-styled map.

    Args:
        styled_map_path:  Styled map PNG (yellow buildings, pink roads on dark
                          purple). Red boundary polyline used for property
                          boundary detection; yellow regions used for buildings.
        lot_area_sqm:     Known parcel area in m² (for pixel→m² conversion).

    Returns:
        {
            "main_house_size_sqm": float,
            "building_count":      int,
            "all_buildings_sqm":   list[float],
            # Internal — used by create_satellite_masked and create_mask2_image:
            "_boundary_mask":     ndarray | None,
            "_boundary_contour":  ndarray | None,
            "_building_contours": list,
        }
    """
    _empty = {
        "main_house_size_sqm": 0.0,
        "building_count": 0,
        "all_buildings_sqm": [],
        "total_buildings_sqm": 0.0,
        "_boundary_mask": None,
        "_boundary_contour": None,
        "_building_contours": [],
    }

    try:
        import cv2
        import numpy as np
    except ImportError:
        log.warning("OpenCV not installed — building detection skipped")
        return _empty

    styled_map = cv2.imread(str(styled_map_path))
    if styled_map is None:
        log.error(f"Could not read styled map: {styled_map_path}")
        return _empty

    img_h, img_w = styled_map.shape[:2]

    # ── Find property boundary from the styled map (largest red contour) ──
    # Red (H≈0) is clearly distinct from pink roads (H≈163) and yellow
    # buildings (H≈30), so the boundary polyline is reliably detected.
    hsv_road = cv2.cvtColor(styled_map, cv2.COLOR_BGR2HSV)
    red1 = cv2.inRange(hsv_road, (0, 120, 70), (10, 255, 255))
    red2 = cv2.inRange(hsv_road, (170, 120, 70), (180, 255, 255))
    red_mask = cv2.bitwise_or(red1, red2)

    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        log.warning("No red boundary contour found — was boundary_coords_wgs84 passed to image retrieval?")
        return _empty

    boundary_contour = max(contours, key=cv2.contourArea)
    boundary_mask = np.zeros((img_h, img_w), dtype=np.uint8)
    cv2.fillPoly(boundary_mask, [boundary_contour], 255)

    # ── Pixel → m² using boundary contour area ────────────────────────────
    boundary_area_px = cv2.contourArea(boundary_contour)
    if boundary_area_px < 1:
        log.error("Zero-area property boundary contour")
        return {**_empty, "_boundary_mask": boundary_mask, "_boundary_contour": boundary_contour}

    sqm_per_pixel = lot_area_sqm / boundary_area_px
    log.info(f"  boundary={boundary_area_px:.0f}px, ratio={sqm_per_pixel:.5f}m²/px")

    # ── Resize styled map if needed (should match roadmap) ─────────────────
    if styled_map.shape[:2] != (img_h, img_w):
        styled_map = cv2.resize(styled_map, (img_w, img_h))

    # ── Erode boundary mask before searching ──────────────────────────────
    # Shrink the search area by ~8px inward to exclude:
    #   • Anti-aliased edges of the red boundary polyline
    #   • Thin cadastral lot-boundary lines drawn at the parcel edge by Google Maps
    # These artefacts sit within a few pixels of the contour edge and would
    # otherwise be detected as building outlines.
    erode_kernel = np.ones((8, 8), np.uint8)
    inner_mask = cv2.erode(boundary_mask, erode_kernel, iterations=1)

    # ── Apply property boundary to styled map ─────────────────────────────
    property_roi = cv2.bitwise_and(styled_map, styled_map, mask=inner_mask)
    hsv_roi = cv2.cvtColor(property_roi, cv2.COLOR_BGR2HSV)

    # ── Detect yellow buildings ───────────────────────────────────────────
    # Buildings render as bright yellow (≈#FFD700) on the Cloud-styled map.
    # Pink roads, dark purple background, and red boundary all fall well outside
    # this yellow HSV range, so no additional exclusion masks are needed.
    building_mask = cv2.inRange(hsv_roi, BUILDING_YELLOW_LOWER, BUILDING_YELLOW_UPPER)
    building_mask = cv2.bitwise_and(building_mask, inner_mask)

    # Morphological cleanup
    kernel = np.ones((3, 3), np.uint8)
    building_mask = cv2.morphologyEx(building_mask, cv2.MORPH_OPEN, kernel, iterations=2)
    building_mask = cv2.morphologyEx(building_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # ── Compute total building coverage from the mask (true union) ────────
    # Using pixel count from the binary mask ensures overlapping detections
    # are NOT double-counted — each pixel is counted exactly once regardless
    # of how many contours cover it.
    total_buildings_sqm = round(int(np.count_nonzero(building_mask)) * sqm_per_pixel, 1)

    # ── Extract and filter contours ───────────────────────────────────────
    bld_contours, _ = cv2.findContours(
        building_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    buildings: list[tuple[float, any]] = []  # (area_sqm, contour) pairs

    for cnt in bld_contours:
        area_px = cv2.contourArea(cnt)
        if area_px < MIN_BUILDING_AREA_PX:
            continue
        area_sqm = round(area_px * sqm_per_pixel, 1)
        buildings.append((area_sqm, cnt))

    # Sort by area descending so index 0 = main house
    buildings.sort(key=lambda b: b[0], reverse=True)
    building_areas_sqm = [b[0] for b in buildings]
    valid_contours = [b[1] for b in buildings]
    main_house_sqm = building_areas_sqm[0] if building_areas_sqm else 0.0

    log.info(
        f"Building detection: {len(building_areas_sqm)} building(s), "
        f"main house ~{main_house_sqm:.1f}m²"
    )

    return {
        "main_house_size_sqm": main_house_sqm,
        "building_count": len(building_areas_sqm),
        "all_buildings_sqm": building_areas_sqm,
        # Union area from mask pixel count — immune to contour overlap issues
        "total_buildings_sqm": total_buildings_sqm,
        "_boundary_mask": boundary_mask,
        "_boundary_contour": boundary_contour,
        "_building_contours": valid_contours,
    }


def create_satellite_masked(
    satellite_path: Path,
    boundary_mask,
    output_path: Path,
) -> None:
    """
    Save the satellite image masked to the property boundary (black outside).

    Used as input for YOLO pool detection to prevent detections from
    neighbouring properties.
    """
    try:
        import cv2
    except ImportError:
        log.warning("OpenCV not installed — satellite masking skipped")
        return

    satellite = cv2.imread(str(satellite_path))
    if satellite is None:
        log.error(f"Could not read satellite: {satellite_path}")
        return

    if boundary_mask.shape[:2] != satellite.shape[:2]:
        boundary_mask = cv2.resize(boundary_mask, (satellite.shape[1], satellite.shape[0]))

    masked = satellite.copy()
    masked[boundary_mask == 0] = 0

    cv2.imwrite(str(output_path), masked, [cv2.IMWRITE_JPEG_QUALITY, 99])
    log.info(f"  satellite_masked saved: {output_path.name}")


def create_mask2_image(
    styled_map_path: Path,
    boundary_contour,
    boundary_mask,
    building_contours: list,
    pool_bboxes: list,
    output_path: Path,
) -> None:
    """
    Colour-coded space usage visualisation — colours match the styled map aesthetic.

    BGR colours:
        Purple (95,   5,  55) = usable space  (matches styled map background)
        Yellow ( 0, 255, 255) = buildings      (matches styled map buildings)
        Green  ( 0, 200,   0) = pools
        Pink   (180, 105, 255) = roads (unusable, matches styled map roads)
        White  (255, 255, 255) = property boundary (3px, visible on dark bg)
        Black                  = outside property
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        log.warning("OpenCV not installed — mask2 generation skipped")
        return

    h, w = boundary_mask.shape[:2]

    # ── Unusable space (roads) from styled map ────────────────────────────
    unusable_mask = np.zeros((h, w), dtype=np.uint8)
    styled_map_img = cv2.imread(str(styled_map_path))
    if styled_map_img is not None:
        if styled_map_img.shape[:2] != (h, w):
            styled_map_img = cv2.resize(styled_map_img, (w, h))
        hsv_m = cv2.cvtColor(styled_map_img, cv2.COLOR_BGR2HSV)
        # Roads are hot pink on the styled map
        pink = cv2.inRange(hsv_m, (150, 60, 80), (180, 255, 255))
        unusable_mask = cv2.bitwise_and(pink, boundary_mask)

    # ── Building mask (filled) ────────────────────────────────────────────
    building_mask = np.zeros((h, w), dtype=np.uint8)
    if building_contours:
        cv2.fillPoly(building_mask, building_contours, 255)

    # ── Pool mask (bounding rectangles) ──────────────────────────────────
    pool_mask = np.zeros((h, w), dtype=np.uint8)
    for bbox in pool_bboxes:
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        cv2.rectangle(pool_mask, (x1, y1), (x2, y2), 255, thickness=-1)
    pool_mask = cv2.bitwise_and(pool_mask, boundary_mask)

    # ── Usable = interior minus everything else ───────────────────────────
    usable_mask = boundary_mask.copy()
    usable_mask[unusable_mask > 0] = 0
    usable_mask[building_mask > 0] = 0
    usable_mask[pool_mask > 0] = 0

    # ── Compose ───────────────────────────────────────────────────────────
    result = np.zeros((h, w, 3), dtype=np.uint8)
    result[usable_mask > 0] = (95, 5, 55)        # dark purple — usable space
    result[unusable_mask > 0] = (180, 105, 255)  # hot pink — roads
    result[building_mask > 0] = (0, 255, 255)    # yellow — buildings
    result[pool_mask > 0] = (0, 200, 0)          # green — pools
    cv2.drawContours(result, [boundary_contour], -1, (255, 255, 255), 3)  # white boundary

    cv2.imwrite(str(output_path), result)
    log.info(f"  mask2 saved: {output_path.name}")
