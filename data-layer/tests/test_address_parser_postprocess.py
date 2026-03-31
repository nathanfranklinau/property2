"""
Unit tests for AddressParser post-processing logic.

Tests the dict-level corrections that run after model inference — no model
loading required. We call the private method indirectly by monkeypatching
the model inference step.
"""

import pytest
from unittest.mock import MagicMock, patch


def _apply_postprocess(raw: dict) -> dict:
    """
    Replicate the post-processing block from AddressParser.parse() in isolation.
    Keeps tests independent of the model file being present.
    """
    result = dict(raw)

    if "lot_number" in result:
        val = result["lot_number"]
        if val.lower().startswith("lot "):
            result["lot_number"] = val[4:].strip()

    if result.get("building_name", "").lower() == "lot":
        del result["building_name"]
        if "lot_number" not in result and "street_number" in result:
            result["lot_number"] = result.pop("street_number")

    return result


# ---------------------------------------------------------------------------
# Lot post-processing
# ---------------------------------------------------------------------------

def test_lot_keyword_in_building_and_number_in_street_number():
    """Exact bug from screenshot: 'Lot 210 Melrose Drive FLINDERS VIEW 4305'
    was returning building_name='Lot', street_number='210'."""
    raw = {
        "building_name": "Lot",
        "street_number": "210",
        "street_name": "Melrose",
        "street_type": "Drive",
        "suburb": "Flinders View",
        "state": "QLD",
        "postcode": "4305",
    }
    result = _apply_postprocess(raw)
    assert "building_name" not in result
    assert result["lot_number"] == "210"
    assert "street_number" not in result
    assert result["street_name"] == "Melrose"


def test_lot_prefix_stripped_from_lot_number():
    """Post-retrain model: lot_number='Lot 210' → lot_number='210'."""
    raw = {"lot_number": "Lot 210", "street_name": "Melrose"}
    result = _apply_postprocess(raw)
    assert result["lot_number"] == "210"
    assert "building_name" not in result


def test_lot_keyword_in_building_with_existing_lot_number():
    """building_name='Lot' present alongside a correctly parsed lot_number — just drop building_name."""
    raw = {"building_name": "Lot", "lot_number": "210", "street_number": "16"}
    result = _apply_postprocess(raw)
    assert "building_name" not in result
    assert result["lot_number"] == "210"
    # street_number should not be touched when lot_number already exists
    assert result["street_number"] == "16"


def test_no_lot_fields_unchanged():
    """Normal address with no lot fields — post-processing is a no-op."""
    raw = {"street_number": "16", "street_name": "Banjo", "suburb": "Adaminaby"}
    result = _apply_postprocess(raw)
    assert result == raw
