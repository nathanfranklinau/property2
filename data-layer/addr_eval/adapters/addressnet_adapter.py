"""Adapter for address-net (https://github.com/jasonrig/address-net).

pip install address-net address-net[tf]

Trained on GNAF (Geocoded National Address File) — Australian addresses only.
Requires TensorFlow. ARCHIVED Feb 2025.

Returns fields: building_name, flat_number, flat_number_suffix,
                number_first, number_last, street_name, street_type,
                locality_name, state, postcode

Note: no unit_type field — just flat_number. No street_type/street_name split
already done (street_type is its own field, unlike deepparse).
"""

import re
from .base import ParsedResult, empty_result

_predict_fn = None
_load_error: str | None = None
AVAILABLE = False
NAME = "address_net"


def _load() -> None:
    global _predict_fn, _load_error, AVAILABLE
    try:
        from addressnet.predict import predict_one
        # Warm up — trigger model load
        predict_one("1 Test St Sydney NSW 2000")
        _predict_fn = predict_one
        AVAILABLE = True
    except Exception as e:
        _load_error = str(e)
        AVAILABLE = False


def parse(addr: str | None) -> ParsedResult:
    out = empty_result(addr or "")
    if not addr:
        return out

    if _predict_fn is None and _load_error is None:
        _load()

    if not AVAILABLE or _predict_fn is None:
        return out

    try:
        d = _predict_fn(addr.upper())

        # street_number: number_first + optional "-" + number_last
        n_first = d.get("number_first")
        n_last = d.get("number_last")
        if n_first:
            out["street_number"] = f"{n_first}-{n_last}" if n_last else str(n_first)

        # street_name / type — already separate
        sname = d.get("street_name")
        stype = d.get("street_type")
        if sname:
            out["street_name"] = str(sname).title()
        if stype:
            out["street_type"] = str(stype).title()

        # unit — addressnet has flat_number but no unit_type
        flat = d.get("flat_number")
        if flat:
            out["unit_type"] = "UNIT"
            out["unit_number"] = str(flat)

        # suburb
        loc = d.get("locality_name")
        if loc:
            out["suburb"] = str(loc).title()

        # postcode
        pc = d.get("postcode")
        if pc:
            out["postcode"] = str(pc)

    except Exception:
        pass

    return out
