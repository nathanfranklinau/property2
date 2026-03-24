"""Adapter for deepparse (https://deepparse.org/).

pip install deepparse  (requires PyTorch >= 2.4)

deepparse uses a neural sequence-to-sequence model. It does NOT output a
separate street_type — the street type is folded into StreetName
(e.g. "DART ST" → StreetName="DART ST").

We attempt to split StreetName into name + type using the same STREET_TYPES
set used by our custom parser, so results are comparable.

Model 'bpemb' downloads ~50 MB on first use.
"""

import re
from .base import ParsedResult, empty_result

_STREET_TYPES = {
    "ALLEY", "APPROACH", "ARCADE", "AVENUE", "BOULEVARD", "BRACE",
    "BYPASS", "CAUSEWAY", "CIRCUIT", "CIRCUS", "CLOSE", "CONCOURSE",
    "CORNER", "COURT", "COVE", "CRESCENT", "CREST", "DRIVE",
    "ESPLANADE", "FAIRWAY", "FREEWAY", "FRONTAGE", "GLADE", "GLEN",
    "GROVE", "GULLY", "HEIGHTS", "HIGHWAY", "ISLAND", "JUNCTION",
    "LANE", "LINK", "LOOP", "MEWS", "MOTORWAY", "NOOK", "OUTLOOK",
    "PARADE", "PARKWAY", "PASS", "PATHWAY", "PLACE", "PLAZA",
    "PROMENADE", "RAMBLE", "RETREAT", "RIDGE", "RISE", "ROAD",
    "ROUTE", "ROW", "RUN", "SQUARE", "STREET", "STRIP", "TERRACE",
    "TRACK", "TRAIL", "VALE", "VIEW", "VISTA", "WALK", "WAY", "WHARF",
    # Abbreviated forms also seen in deepparse output
    "ST", "RD", "AVE", "AV", "CT", "DR", "PL", "CL", "CR", "CRS",
    "GR", "TCE", "HWY", "BLVD", "PKWY", "CCT", "ESP", "SQ", "WY",
    "PDE", "PROM",
}

_ABBREV_MAP = {
    "ST": "Street", "RD": "Road", "AVE": "Avenue", "AV": "Avenue",
    "CT": "Court", "DR": "Drive", "PL": "Place", "CL": "Close",
    "CR": "Crescent", "CRS": "Crescent", "GR": "Grove", "TCE": "Terrace",
    "HWY": "Highway", "BLVD": "Boulevard", "PKWY": "Parkway",
    "CCT": "Circuit", "ESP": "Esplanade", "SQ": "Square",
    "WY": "Way", "PDE": "Parade", "PROM": "Promenade",
}

_parser = None
_load_error: str | None = None
AVAILABLE = False
NAME = "deepparse_bpemb"


def _load_parser() -> None:
    global _parser, _load_error, AVAILABLE
    try:
        import warnings
        import logging
        # transformers checks for torch >= 2.4 and emits a noisy warning,
        # but deepparse's BPEmb model works fine with torch 2.2+.
        warnings.filterwarnings("ignore")
        logging.disable(logging.WARNING)
        from deepparse.parser import AddressParser
        _parser = AddressParser(model_type="bpemb", device="cpu")
        AVAILABLE = True
        logging.disable(logging.NOTSET)
    except Exception as e:
        _load_error = str(e)
        AVAILABLE = False


def _split_street_name_type(raw: str | None) -> tuple[str | None, str | None]:
    """Split 'DART ST' → ('Dart', 'Street'), 'GOLD COAST HWY' → ('Gold Coast', 'Highway')."""
    if not raw:
        return None, None
    words = raw.upper().split()
    # Find last word that is a known street type
    for i in range(len(words) - 1, -1, -1):
        if words[i] in _STREET_TYPES:
            type_raw = words[i]
            type_out = _ABBREV_MAP.get(type_raw, type_raw.title())
            name_words = words[:i]
            name_out = " ".join(w.title() for w in name_words) if name_words else None
            return name_out, type_out
    # No type found — return everything as name
    return raw.title(), None


def parse(addr: str | None) -> ParsedResult:
    global _parser
    out = empty_result(addr or "")
    if not addr:
        return out

    if _parser is None and _load_error is None:
        _load_parser()

    if not AVAILABLE or _parser is None:
        return out

    try:
        result = _parser(addr)
        d = result.to_dict() if hasattr(result, "to_dict") else {}

        # StreetNumber
        sn = d.get("StreetNumber")
        if sn:
            out["street_number"] = str(sn).strip()

        # StreetName — deepparse folds type into name; split it out
        raw_name = d.get("StreetName")
        name, stype = _split_street_name_type(raw_name)
        out["street_name"] = name
        out["street_type"] = stype

        # Unit
        unit = d.get("Unit")
        if unit:
            unit_str = str(unit).strip()
            # Unit might be "UNIT 4" or just "4"
            m = re.match(r"^(?:(UNIT|FLAT|APT|SHOP|SUITE)\s+)?(\S+)$", unit_str, re.IGNORECASE)
            if m:
                out["unit_type"] = (m.group(1) or "UNIT").upper()
                out["unit_number"] = m.group(2)
            else:
                out["unit_type"] = "UNIT"
                out["unit_number"] = unit_str

        # Municipality → suburb
        mun = d.get("Municipality")
        if mun:
            out["suburb"] = str(mun).strip().title()

        # PostalCode
        pc = d.get("PostalCode")
        if pc:
            out["postcode"] = str(pc).strip()

    except Exception:
        pass

    return out
