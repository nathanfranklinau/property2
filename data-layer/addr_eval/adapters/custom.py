"""Adapter wrapping the existing da_common regex parsers.

Two parsers are exposed:
  - custom_gc  — parse_location_address  (Gold Coast / ePathway format)
  - custom_bris — parse_brisbane_address (Brisbane Development.i format)
"""

import sys
import os

# da_common lives in data-layer/import/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "import"))

from da_common import parse_location_address, parse_brisbane_address
from .base import ParsedResult, empty_result


def _to_result(parsed: dict, raw: str) -> ParsedResult:
    return {
        "street_number": parsed.get("street_number"),
        "street_name": parsed.get("street_name"),
        "street_type": parsed.get("street_type"),
        "unit_type": parsed.get("unit_type"),
        "unit_number": parsed.get("unit_number"),
        "suburb": parsed.get("suburb"),
        "postcode": parsed.get("postcode"),
        "raw": raw,
    }


def parse_gc(addr: str | None) -> ParsedResult:
    """Gold Coast ePathway format parser."""
    if not addr:
        return empty_result(addr or "")
    return _to_result(parse_location_address(addr), addr)


def parse_bris(addr: str | None) -> ParsedResult:
    """Brisbane Development.i abbreviated format parser."""
    if not addr:
        return empty_result(addr or "")
    return _to_result(parse_brisbane_address(addr), addr)


NAME = "custom_regex"
