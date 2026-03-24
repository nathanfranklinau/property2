"""Tests for address parsing functions in da_common.

All test cases are sourced from real rows in the database
(goldcoast_da_properties and brisbane_da_properties), using the
parsed column values already stored there as ground-truth expectations.
"""

import pytest
from da_common import parse_location_address, parse_brisbane_address

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EMPTY = {
    "unit_type": None,
    "unit_number": None,
    "unit_suffix": None,
    "street_number": None,
    "street_name": None,
    "street_type": None,
}


def _expected(**kwargs):
    """Build a full expected dict, defaulting all fields to None."""
    return {**_EMPTY, **kwargs}


# ---------------------------------------------------------------------------
# parse_location_address — Gold Coast ePathway format
# ---------------------------------------------------------------------------

# Ground truth: (input, expected_fields)
# Derived from live rows in goldcoast_da_properties where cadastre_lotplan IS NOT NULL.

_GC_CASES = [
    # --- Standard: number + multi-word name + type ---
    (
        "7 Mornington Court",
        _expected(street_number="7", street_name="Mornington", street_type="Court"),
    ),
    (
        "635 Gold Coast Springbrook Road",
        _expected(street_number="635", street_name="Gold Coast Springbrook", street_type="Road"),
    ),
    (
        "9 Twenty Fourth Avenue",
        _expected(street_number="9", street_name="Twenty Fourth", street_type="Avenue"),
    ),
    (
        "1179 Gold Coast Highway",
        _expected(street_number="1179", street_name="Gold Coast", street_type="Highway"),
    ),
    (
        "88 Old Burleigh Road",
        _expected(street_number="88", street_name="Old Burleigh", street_type="Road"),
    ),
    (
        "2 East Lane",
        _expected(street_number="2", street_name="East", street_type="Lane"),
    ),
    (
        "11 Transport Street",
        _expected(street_number="11", street_name="Transport", street_type="Street"),
    ),
    # --- Hyphenated range ---
    (
        "1293-1299 Gold Coast Highway",
        _expected(street_number="1293-1299", street_name="Gold Coast", street_type="Highway"),
    ),
    (
        "UNIT 3, 14-16 Kohl Street",
        _expected(
            unit_type="UNIT", unit_number="3",
            street_number="14-16", street_name="Kohl", street_type="Street",
        ),
    ),
    # --- Unit prefix (UNIT N, NUMBER NAME TYPE) ---
    (
        "UNIT 2, 19 Venice Street",
        _expected(
            unit_type="UNIT", unit_number="2",
            street_number="19", street_name="Venice", street_type="Street",
        ),
    ),
    (
        "Unit 1104, 48 Ventura Road",
        _expected(
            unit_type="UNIT", unit_number="1104",
            street_number="48", street_name="Ventura", street_type="Road",
        ),
    ),
    (
        "Unit 702, 122 Surf Parade",
        _expected(
            unit_type="UNIT", unit_number="702",
            street_number="122", street_name="Surf", street_type="Parade",
        ),
    ),
    (
        "Unit 1205, 2 Athena Boulevard",
        _expected(
            unit_type="UNIT", unit_number="1205",
            street_number="2", street_name="Athena", street_type="Boulevard",
        ),
    ),
    (
        "UNIT 5, 166 The Esplanade",
        _expected(
            unit_type="UNIT", unit_number="5",
            street_number="166", street_name="The", street_type="Esplanade",
        ),
    ),
    (
        "Unit 119, 370 Gainsborough Drive",
        _expected(
            unit_type="UNIT", unit_number="119",
            street_number="370", street_name="Gainsborough", street_type="Drive",
        ),
    ),
    # --- Lot prefix: lot number becomes the street number ---
    (
        "Lot 58 Gold Coast Highway",
        _expected(street_number="58", street_name="Gold Coast", street_type="Highway"),
    ),
    (
        "Lot 2 Hope Island Road",
        _expected(street_number="2", street_name="Hope Island", street_type="Road"),
    ),
    (
        "Lot 600 Ross Street",
        _expected(street_number="600", street_name="Ross", street_type="Street"),
    ),
    (
        "Lot 47 Shipper Drive",
        _expected(street_number="47", street_name="Shipper", street_type="Drive"),
    ),
    # --- Bare lot reference (plan code follows) → nothing parseable ---
    ("Lot 800 SP348540", _expected()),
    ("Lot 1 RP152544", _expected()),
    ("Lot 303 SP289809", _expected()),
    ("Lot 10 WD3134", _expected()),
    # --- Null / empty ---
    (None, _expected()),
    ("", _expected()),
]


@pytest.mark.parametrize("addr,expected", _GC_CASES)
def test_parse_location_address(addr, expected):
    result = parse_location_address(addr)
    assert result == expected, f"Input: {addr!r}"


# ---------------------------------------------------------------------------
# parse_brisbane_address — Brisbane Development.i abbreviated format
# ---------------------------------------------------------------------------

# Ground truth: rows from brisbane_da_properties where cadastre_lotplan IS NOT NULL.
# Brisbane addresses include suburb + state + postcode; parser strips those.

_BRIS_CASES = [
    # --- Standard abbreviated street types ---
    (
        "4 TANDOOR ST MORNINGSIDE  QLD  4170",
        _expected(street_number="4", street_name="Tandoor", street_type="Street"),
    ),
    (
        "8 HADDOCK ST WINDSOR  QLD  4030",
        _expected(street_number="8", street_name="Haddock", street_type="Street"),
    ),
    (
        "89 DAYS RD GRANGE  QLD  4051",
        _expected(street_number="89", street_name="Days", street_type="Road"),
    ),
    (
        "25 LANDSBORO AVE BOONDALL  QLD  4034",
        _expected(street_number="25", street_name="Landsboro", street_type="Avenue"),
    ),
    (
        "68 NYLETA ST COOPERS PLAINS  QLD  4108",
        _expected(street_number="68", street_name="Nyleta", street_type="Street"),
    ),
    (
        "24 DART ST AUCHENFLOWER  QLD  4066",
        _expected(street_number="24", street_name="Dart", street_type="Street"),
    ),
    (
        "136 LECKIE RD KEDRON  QLD  4031",
        _expected(street_number="136", street_name="Leckie", street_type="Road"),
    ),
    (
        "1 AQUAMARINE ST HOLLAND PARK  QLD  4121",
        _expected(street_number="1", street_name="Aquamarine", street_type="Street"),
    ),
    # --- Multi-word street name ---
    (
        "184 COOPERS CAMP RD ASHGROVE  QLD  4060",
        _expected(street_number="184", street_name="Coopers Camp", street_type="Road"),
    ),
    (
        "115 NEWNHAM RD MOUNT GRAVATT EAST  QLD  4122",
        _expected(street_number="115", street_name="Newnham", street_type="Road"),
    ),
    # --- Street number with letter suffix ---
    (
        "2A PERRY ST HAMILTON  QLD  4007",
        _expected(street_number="2A", street_name="Perry", street_type="Street"),
    ),
    # --- Null / empty ---
    (None, _expected()),
    ("", _expected()),
]


@pytest.mark.parametrize("addr,expected", _BRIS_CASES)
def test_parse_brisbane_address(addr, expected):
    result = parse_brisbane_address(addr)
    assert result == expected, f"Input: {addr!r}"
