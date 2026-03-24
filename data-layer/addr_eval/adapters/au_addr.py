"""Adapter for au-address-parser (https://pypi.org/project/au-address-parser/).

pip install au-address-parser

This library requires either:
  - A comma-separated address with state code (e.g. "24 DART ST, AUCHENFLOWER, QLD 4066"), OR
  - A 6-7 word inline address with state code

Gold Coast addresses like "7 Mornington Court" (no suburb/state) will fail.
Brisbane addresses like "24 DART ST AUCHENFLOWER QLD 4066" should parse.
"""

from .base import ParsedResult, empty_result

try:
    from au_address_parser import AbAddressUtility
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


NAME = "au_address_parser"
AVAILABLE = _AVAILABLE


def parse(addr: str | None) -> ParsedResult:
    out = empty_result(addr or "")
    if not addr or not _AVAILABLE:
        return out

    try:
        p = AbAddressUtility(addr)
        d = p.parsed_addr

        # street_number: combine number_first_prefix + number_first + number_first_suffix
        # + optional range (number_last) → "42-44"
        n_prefix = d.get("number_first_prefix") or ""
        n_first = d.get("number_first") or ""
        n_suffix = d.get("number_first_suffix") or ""
        n_last = d.get("number_last")
        if n_first:
            street_num = f"{n_prefix}{n_first}{n_suffix}"
            if n_last:
                l_prefix = d.get("number_last_prefix") or ""
                l_suffix = d.get("number_last_suffix") or ""
                street_num += f"-{l_prefix}{n_last}{l_suffix}"
            out["street_number"] = street_num

        # street_name / type — both returned separately by this library
        raw_name = d.get("street_name")
        raw_type = d.get("street_type")
        if raw_name:
            out["street_name"] = raw_name.title()
        if raw_type:
            out["street_type"] = raw_type.title()

        # unit
        flat = d.get("flat_number")
        if flat:
            out["unit_type"] = "UNIT"
            out["unit_number"] = str(flat)

        # locality / suburb
        locality = d.get("locality")
        if locality:
            out["suburb"] = locality.title()

        # postcode
        post = d.get("post")
        if post:
            out["postcode"] = str(post)

    except Exception:
        # Library raises Exception('Not Valid Address Format') on parse failure
        pass

    return out
