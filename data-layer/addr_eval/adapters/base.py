"""Common interface for all address parser adapters."""

from typing import TypedDict


class ParsedResult(TypedDict):
    street_number: str | None
    street_name: str | None
    street_type: str | None
    unit_type: str | None
    unit_number: str | None
    suburb: str | None
    postcode: str | None
    # Original input for tracing
    raw: str


def empty_result(raw: str = "") -> ParsedResult:
    return {
        "street_number": None,
        "street_name": None,
        "street_type": None,
        "unit_type": None,
        "unit_number": None,
        "suburb": None,
        "postcode": None,
        "raw": raw,
    }
