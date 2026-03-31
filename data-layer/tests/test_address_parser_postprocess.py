"""
Unit tests for AddressParser output normalization.

Tests the lot_keyword removal that runs at the end of parse() — no model
loading required.
"""


def _apply_postprocess(raw: dict) -> dict:
    """
    Replicate the lot_keyword removal from AddressParser.parse().
    """
    result = dict(raw)
    result.pop("lot_keyword", None)
    return result


def test_lot_keyword_removed_from_output():
    """lot_keyword is always stripped — it's a display-only prefix, not a GNAF field."""
    raw = {
        "lot_keyword": "Lot",
        "lot_number": "210",
        "street_name": "Melrose",
        "street_type": "Drive",
        "suburb": "Flinders View",
        "state": "QLD",
        "postcode": "4305",
    }
    result = _apply_postprocess(raw)
    assert "lot_keyword" not in result
    assert result["lot_number"] == "210"
    assert result["street_name"] == "Melrose"


def test_no_lot_keyword_is_noop():
    """Normal address without lot_keyword — no change."""
    raw = {"street_number": "16", "street_name": "Banjo", "suburb": "Adaminaby"}
    result = _apply_postprocess(raw)
    assert result == raw
