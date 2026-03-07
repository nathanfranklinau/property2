"""
Download property images from Google Maps Static API.

Downloads two image types for a given lat/lon:
    satellite  — used for pool detection and display
    styled_map — Cloud-styled roadmap (map_id=813ac30c17e4a918b39744c0) with yellow
                 building footprints and pink roads on a dark purple background.
                 Used for both boundary detection and as the display markup image.

The property boundary is drawn as a red polyline on both images so that
OpenCV can find it as the largest red contour during building detection.

Google Maps Static API docs:
    https://developers.google.com/maps/documentation/maps-static/overview
"""

import os
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

log = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Image parameters — proven settings from realestateopportunities
ZOOM = 20
SIZE = "640x640"
SCALE = 2   # returns 1280x1280 pixel image

# Cloud-styled map: yellow buildings, pink roads — used directly as the markup image
STYLED_MAP_ID = "813ac30c17e4a918b39744c0"


def _maps_url(
    map_type: str,
    lat: float,
    lon: float,
    styles: list[dict] | None = None,
    boundary_coords: list[tuple[float, float]] | None = None,
    map_id: str | None = None,
) -> str:
    """
    Build a Google Maps Static API URL.

    Args:
        map_type:         'roadmap' or 'satellite'
        lat, lon:         Centre point of the image
        styles:           Optional list of map style dicts (ignored when map_id is set)
        boundary_coords:  Optional list of (lat, lon) tuples for a red boundary polyline
        map_id:           Optional Cloud-based map style ID
    """
    params = [
        f"center={lat},{lon}",
        f"zoom={ZOOM}",
        f"size={SIZE}",
        f"scale={SCALE}",
        f"maptype={map_type}",
        f"key={GOOGLE_MAPS_API_KEY}",
    ]

    if map_id:
        params.append(f"map_id={map_id}")
    else:
        # Hide POI markers — they clutter building detection
        params.append("style=feature:poi|visibility:off")

    if styles and not map_id:
        for style in styles:
            feature = style.get("feature", "all")
            element = style.get("element", "all")
            rules = "|".join(f"{k}:{v}" for k, v in style.get("rules", {}).items())
            params.append(f"style=feature:{feature}|element:{element}|{rules}")

    if boundary_coords:
        # Red polyline around the property boundary.
        # OpenCV uses this to find the property contour (largest red contour).
        parts = ["color:0xff0000ff", "weight:3"]
        for lat_c, lon_c in boundary_coords:
            parts.append(f"{lat_c:.6f},{lon_c:.6f}")
        params.append("path=" + "|".join(parts))

    return "https://maps.googleapis.com/maps/api/staticmap?" + "&".join(params)


def _download(url: str, output_path: Path) -> None:
    """Download a URL to a file."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    log.debug(f"Downloaded {output_path.name} ({len(response.content):,} bytes)")




def download_street_view_image(
    lat: float,
    lon: float,
    output_dir: Path,
) -> Path | None:
    """
    Download a Google Street View hero shot of the property frontage.

    Checks the free metadata endpoint first to confirm coverage exists before
    spending a paid image request. Returns None if no Street View imagery is
    available at this location.

    Args:
        lat, lon:    Property address coordinates (GNAF geocode — the address
                     point, typically on the street frontage).
        output_dir:  Directory to save street_view.jpg into.
    """
    if not GOOGLE_MAPS_API_KEY:
        log.warning("GOOGLE_MAPS_API_KEY not set — skipping Street View")
        return None

    # Free metadata check — no quota consumed, confirms coverage exists
    meta_url = (
        "https://maps.googleapis.com/maps/api/streetview/metadata"
        f"?location={lat},{lon}"
        f"&key={GOOGLE_MAPS_API_KEY}"
    )
    meta_resp = requests.get(meta_url, timeout=15)
    meta_resp.raise_for_status()
    meta = meta_resp.json()

    if meta.get("status") != "OK":
        log.info(f"  No Street View coverage at ({lat:.6f}, {lon:.6f}): {meta.get('status')}")
        return None

    # Fetch the actual image (charged request)
    # Omit heading — Google auto-calculates direction toward the coordinates
    # from the nearest street panorama, naturally producing a front-of-house shot.
    image_url = (
        "https://maps.googleapis.com/maps/api/streetview"
        f"?location={lat},{lon}"
        "&size=640x640"
        "&fov=80"
        "&pitch=5"
        "&source=outdoor"
        "&return_error_code=true"
        f"&key={GOOGLE_MAPS_API_KEY}"
    )

    output_path = output_dir / "street_view.jpg"
    _download(image_url, output_path)
    log.info("  street_view downloaded")
    return output_path


def download_property_images(
    lat: float,
    lon: float,
    output_dir: Path,
    boundary_coords: list[tuple[float, float]] | None = None,
) -> dict[str, Path]:
    """
    Download satellite and styled map images for a property.

    Args:
        lat, lon:         Centre point of the property centroid (GDA94-adjusted)
        output_dir:       Directory to save images into
        boundary_coords:  Property boundary as list of (lat, lon) tuples (GDA94-adjusted).
                          When provided, a red polyline is drawn on all images so
                          OpenCV can identify the property boundary.

    Returns:
        Dict with keys 'satellite', 'styled_map' mapping to file Paths.
    """
    if not GOOGLE_MAPS_API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable is not set")

    output_dir.mkdir(parents=True, exist_ok=True)

    images = {
        "satellite": output_dir / "satellite.png",
        "styled_map": output_dir / "styled_map.png",
    }

    bc = boundary_coords
    if bc:
        log.info(f"Downloading imagery for ({lat:.6f}, {lon:.6f}) with {len(bc)}-point boundary...")
    else:
        log.info(f"Downloading imagery for ({lat:.6f}, {lon:.6f}) (no boundary)...")

    _download(_maps_url("satellite", lat, lon, boundary_coords=bc), images["satellite"])
    log.info("  satellite downloaded")

    _download(_maps_url("roadmap", lat, lon, boundary_coords=bc, map_id=STYLED_MAP_ID), images["styled_map"])
    log.info("  styled_map downloaded")

    return images
