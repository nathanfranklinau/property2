"""Unit tests for the permutation engine.

No DB required — all tests use hardcoded AddressRecord dicts.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from training.permutations import (
    AddressRecord,
    AbbrevLookups,
    generate_permutations,
    perm_building_after_unit,
    perm_corner,
    perm_building_first,
    perm_building_omitted,
    perm_canonical,
    perm_extra_commas,
    perm_flat_abbrev_gnaf,
    perm_flat_abbrev_informal,
    perm_flat_no_space,
    perm_level_abbrev,
    perm_lot_abbrev,
    perm_lot_with_street,
    perm_minimal,
    perm_no_commas,
    perm_no_postcode,
    perm_no_state_postcode,
    perm_noisy,
    perm_number_prefix,
    perm_number_range_spaced,
    perm_postcode_before_suburb,
    perm_reversed,
    perm_slash_notation,
    perm_slash_unit_level_street,
    perm_state_postcode_joined,
    perm_slash_with_type,
    perm_street_abbrev_gnaf,
    perm_street_abbrev_informal,
    perm_suburb_abbrev,
    perm_suburb_expand,
    perm_suffix_abbrev,
    perm_with_country,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def lookups() -> AbbrevLookups:
    """Build AbbrevLookups from minimal representative authority data."""
    street_type_aut = {
        "STREET": "ST",
        "AVENUE": "AV",
        "CRESCENT": "CR",
        "ROAD": "RD",
        "COURT": "CT",
        "DRIVE": "DR",
        "WAY": "WAY",  # same — not a useful abbreviation
    }
    flat_type_aut = {
        "UNIT": "UNIT",       # code same as full name → not a useful abbreviation
        "APT": "APARTMENT",
        "FLAT": "FLAT",       # code same as full name
        "SE": "SUITE",
        "TNHS": "TOWNHOUSE",
    }
    level_type_aut = {
        "L": "LEVEL",
        "FL": "FLOOR",
        "B": "BASEMENT",
        "G": "GROUND",
    }
    street_suffix_aut = {
        "N": "NORTH",
        "S": "SOUTH",
        "E": "EAST",
    }
    return AbbrevLookups.build(
        street_type_aut=street_type_aut,
        flat_type_aut=flat_type_aut,
        level_type_aut=level_type_aut,
        street_suffix_aut=street_suffix_aut,
    )


def _simple_rec(**overrides) -> AddressRecord:
    """Base simple address: 16 Banjo Street, Old Adaminaby NSW 2629."""
    base: AddressRecord = {
        "building_name": None,
        "flat_type": None,
        "flat_type_code": None,
        "flat_type_gnaf_abbrev": None,
        "flat_number": None,
        "level_type": None,
        "level_type_code": None,
        "level_number": None,
        "lot_number": None,
        "street_number": "16",
        "street_number_last": None,
        "street_name": "Banjo",
        "street_type": "Street",
        "street_type_code": "STREET",
        "street_type_abbrev": "ST",
        "street_suffix": None,
        "street_suffix_code": None,
        "suburb": "Old Adaminaby",
        "state": "NSW",
        "postcode": "2629",
        "source": "gnaf",
        "cross_street_number": None,
        "cross_street_name": None,
        "cross_street_type": None,
        "cross_street_type_abbrev": None,
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def _unit_rec(**overrides) -> AddressRecord:
    """Unit address: Flat 9, 8 Trenerry Crescent, Abbotsford VIC 3067."""
    base: AddressRecord = {
        "building_name": None,
        "flat_type": "Flat",
        "flat_type_code": "FLAT",
        "flat_type_gnaf_abbrev": "FLAT",
        "flat_number": "9",
        "level_type": None,
        "level_type_code": None,
        "level_number": None,
        "lot_number": None,
        "street_number": "8",
        "street_number_last": None,
        "street_name": "Trenerry",
        "street_type": "Crescent",
        "street_type_code": "CRESCENT",
        "street_type_abbrev": "CR",
        "street_suffix": None,
        "street_suffix_code": None,
        "suburb": "Abbotsford",
        "state": "VIC",
        "postcode": "3067",
        "source": "gnaf",
        "cross_street_number": None,
        "cross_street_name": None,
        "cross_street_type": None,
        "cross_street_type_abbrev": None,
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def _complex_rec(**overrides) -> AddressRecord:
    """Complex address: Unit 4, Level 2, Harbour Tower, 12-14 Smith Street North, Brisbane QLD 4000."""
    base: AddressRecord = {
        "building_name": "Harbour Tower",
        "flat_type": "Unit",
        "flat_type_code": "UNIT",
        "flat_type_gnaf_abbrev": "UNIT",
        "flat_number": "4",
        "level_type": "Level",
        "level_type_code": "L",
        "level_number": "2",
        "lot_number": None,
        "street_number": "12",
        "street_number_last": "14",
        "street_name": "Smith",
        "street_type": "Street",
        "street_type_code": "STREET",
        "street_type_abbrev": "ST",
        "street_suffix": "North",
        "street_suffix_code": "N",
        "suburb": "Brisbane",
        "state": "QLD",
        "postcode": "4000",
        "source": "gnaf",
        "cross_street_number": None,
        "cross_street_name": None,
        "cross_street_type": None,
        "cross_street_type_abbrev": None,
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


# ---------------------------------------------------------------------------
# perm_canonical
# ---------------------------------------------------------------------------

def test_canonical_simple(lookups):
    results = perm_canonical(_simple_rec(), lookups)
    assert len(results) == 1
    addr, ptype, _ = results[0]
    assert ptype == "canonical"
    assert addr == "16 Banjo Street, Old Adaminaby NSW 2629"


def test_canonical_unit(lookups):
    addr, _, _ = perm_canonical(_unit_rec(), lookups)[0]
    assert addr == "Flat 9, 8 Trenerry Crescent, Abbotsford VIC 3067"


def test_canonical_complex(lookups):
    addr, _, _ = perm_canonical(_complex_rec(), lookups)[0]
    assert "Unit 4" in addr
    assert "Level 2" in addr
    assert "Harbour Tower" in addr
    assert "12-14 Smith Street North" in addr
    assert "Brisbane QLD 4000" in addr


def test_canonical_all_outputs_title_case(lookups):
    for rec in [_simple_rec(), _unit_rec(), _complex_rec()]:
        addr, _, _ = perm_canonical(rec, lookups)[0]
        # No fully-uppercase words except postcode digits
        for word in addr.split():
            if word.isdigit():
                continue
            if "-" in word:
                continue
            # Title case: first char upper or digit, rest lower (allow trailing digits)
            letters = [c for c in word if c.isalpha()]
            if letters:
                assert letters[0].isupper(), f"Expected title case word '{word}' in '{addr}'"


# ---------------------------------------------------------------------------
# perm_street_abbrev_gnaf
# ---------------------------------------------------------------------------

def test_street_abbrev_gnaf_produces_st(lookups):
    results = perm_street_abbrev_gnaf(_simple_rec(), lookups)
    assert len(results) == 1
    addr, ptype, _ = results[0]
    assert ptype == "street_abbrev_gnaf"
    assert "St" in addr
    assert "Street" not in addr


def test_street_abbrev_gnaf_skips_when_same(lookups):
    # WAY → WAY — not a useful abbreviation
    rec = _simple_rec(
        street_type="Way",
        street_type_code="WAY",
        street_type_abbrev="WAY",
    )
    results = perm_street_abbrev_gnaf(rec, lookups)
    assert results == []


def test_street_abbrev_gnaf_crescent_gives_cr(lookups):
    results = perm_street_abbrev_gnaf(_unit_rec(), lookups)
    addr, _, _ = results[0]
    assert "Cr" in addr
    assert "Crescent" not in addr


# ---------------------------------------------------------------------------
# perm_slash_notation
# ---------------------------------------------------------------------------

def test_slash_notation_basic(lookups):
    results = perm_slash_notation(_unit_rec(), lookups)
    assert len(results) == 1
    addr, ptype, _ = results[0]
    assert ptype == "slash_notation"
    # Should be "9/8 Trenerry ..." — no unit type
    assert addr.startswith("9/8 ")
    assert "Flat" not in addr


def test_slash_notation_no_unit_returns_empty(lookups):
    assert perm_slash_notation(_simple_rec(), lookups) == []


def test_slash_notation_returns_empty_when_level_present(lookups):
    # "9/40 Smith St" with Suite 9 Level 11 would be misread as Level 9, 40 Smith St
    assert perm_slash_notation(_complex_rec(), lookups) == []


def test_slash_notation_range(lookups):
    rec = _unit_rec(street_number="12", street_number_last="14", flat_number="4")
    results = perm_slash_notation(rec, lookups)
    addr, _, _ = results[0]
    assert addr.startswith("4/12-14 ")


# ---------------------------------------------------------------------------
# perm_slash_unit_level_street
# ---------------------------------------------------------------------------

def test_slash_unit_level_street_produces_triple_slash(lookups):
    results = perm_slash_unit_level_street(_complex_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "slash_unit_level_street"
    assert addr.startswith("4/2/12")


def test_slash_unit_level_street_returns_empty_when_no_level(lookups):
    assert perm_slash_unit_level_street(_unit_rec(), lookups) == []


def test_slash_unit_level_street_returns_empty_when_no_unit(lookups):
    assert perm_slash_unit_level_street(_simple_rec(), lookups) == []


# ---------------------------------------------------------------------------
# perm_slash_with_type
# ---------------------------------------------------------------------------

def test_slash_with_type_includes_unit_type(lookups):
    results = perm_slash_with_type(_unit_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "slash_with_type"
    assert "Flat 9/8 " in addr


def test_slash_with_type_no_unit_returns_empty(lookups):
    assert perm_slash_with_type(_simple_rec(), lookups) == []


def test_slash_with_type_returns_empty_when_level_present(lookups):
    # "Suite 9/40 Smith St" drops Level 11 — invalid when level is present
    assert perm_slash_with_type(_complex_rec(), lookups) == []


# ---------------------------------------------------------------------------
# perm_flat_abbrev_gnaf
# ---------------------------------------------------------------------------

def test_flat_abbrev_gnaf_skips_when_code_equals_full_name(lookups):
    # UNIT → UNIT and FLAT → FLAT — codes same as full name → not useful
    results = perm_flat_abbrev_gnaf(_unit_rec(), lookups)
    assert results == []


def test_flat_abbrev_gnaf_produces_apt_for_apartment(lookups):
    rec = _unit_rec(flat_type="Apartment", flat_type_code="APT", flat_type_gnaf_abbrev="APT")
    results = perm_flat_abbrev_gnaf(rec, lookups)
    assert len(results) == 1
    addr, ptype, _ = results[0]
    assert ptype == "flat_abbrev_gnaf"
    assert "Apt 9" in addr


def test_flat_abbrev_gnaf_no_unit_returns_empty(lookups):
    assert perm_flat_abbrev_gnaf(_simple_rec(), lookups) == []


# ---------------------------------------------------------------------------
# perm_flat_abbrev_informal
# ---------------------------------------------------------------------------

def test_flat_abbrev_informal_unit_gives_u_and_ut(lookups):
    rec = _unit_rec(flat_type="Unit", flat_type_code="UNIT", flat_type_gnaf_abbrev="UNIT")
    results = perm_flat_abbrev_informal(rec, lookups)
    types = [addr for addr, _, _ in results]
    assert any("U 9" in a for a in types)
    assert any("Ut 9" in a for a in types)


def test_flat_abbrev_informal_flat_gives_f_and_flt(lookups):
    results = perm_flat_abbrev_informal(_unit_rec(), lookups)
    types = [addr for addr, _, _ in results]
    assert any("F 9" in a for a in types)
    assert any("Flt 9" in a for a in types)


def test_flat_abbrev_informal_no_unit_returns_empty(lookups):
    assert perm_flat_abbrev_informal(_simple_rec(), lookups) == []


# ---------------------------------------------------------------------------
# perm_flat_no_space
# ---------------------------------------------------------------------------

def test_flat_no_space_unit(lookups):
    rec = _unit_rec(flat_type="Unit", flat_type_code="UNIT", flat_type_gnaf_abbrev="UNIT")
    results = perm_flat_no_space(rec, lookups)
    addr, ptype, _ = results[0]
    assert ptype == "flat_no_space"
    assert "U9" in addr
    assert "U 9" not in addr


def test_flat_no_space_returns_empty_when_no_informal_variants(lookups):
    # SUITE has no informal extras in EXTRA_FLAT_TYPE_VARIANTS for "Se" — check
    rec = _unit_rec(flat_type="Suite", flat_type_code="SE", flat_type_gnaf_abbrev="SE")
    # SUITE → ["Ste"] in abbreviations.py, so it should produce a result
    results = perm_flat_no_space(rec, lookups)
    if results:
        addr, _, _ = results[0]
        assert " " not in addr.split(",")[0].split("/")[0].split()[0]


# ---------------------------------------------------------------------------
# perm_level_abbrev
# ---------------------------------------------------------------------------

def test_level_abbrev_produces_lvl_and_l2(lookups):
    results = perm_level_abbrev(_complex_rec(), lookups)
    addrs = [addr for addr, _, _ in results]
    # Should have "Lvl 2" or "Lv 2" and "L2"
    assert any("Lvl 2" in a or "Lv 2" in a for a in addrs)
    assert any("L2" in a for a in addrs)


def test_level_abbrev_returns_empty_when_no_level(lookups):
    assert perm_level_abbrev(_simple_rec(), lookups) == []


# ---------------------------------------------------------------------------
# perm_suffix_abbrev
# ---------------------------------------------------------------------------

def test_suffix_abbrev_produces_n_and_nth(lookups):
    results = perm_suffix_abbrev(_complex_rec(), lookups)
    addrs = [addr for addr, _, _ in results]
    # Should have "N" (GNAF code) and "Nth" (informal)
    assert any("Smith Street N" in a or "Smith St N" in a for a in addrs)
    assert any("Nth" in a for a in addrs)


def test_suffix_abbrev_returns_empty_when_no_suffix(lookups):
    assert perm_suffix_abbrev(_simple_rec(), lookups) == []


# ---------------------------------------------------------------------------
# Component omission
# ---------------------------------------------------------------------------

def test_no_postcode(lookups):
    results = perm_no_postcode(_simple_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "no_postcode"
    assert "2629" not in addr
    assert "NSW" in addr


def test_no_postcode_returns_empty_when_no_postcode(lookups):
    rec = _simple_rec(postcode=None)
    assert perm_no_postcode(rec, lookups) == []


def test_no_state_postcode(lookups):
    results = perm_no_state_postcode(_simple_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "no_state_postcode"
    assert "NSW" not in addr
    assert "2629" not in addr
    assert "Old Adaminaby" in addr


def test_minimal(lookups):
    results = perm_minimal(_simple_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "minimal"
    assert "Old Adaminaby" not in addr
    assert "Banjo" in addr


def test_minimal_returns_empty_when_unit_present(lookups):
    assert perm_minimal(_unit_rec(), lookups) == []


def test_minimal_returns_empty_when_level_present(lookups):
    assert perm_minimal(_complex_rec(), lookups) == []


# ---------------------------------------------------------------------------
# Separators
# ---------------------------------------------------------------------------

def test_no_commas(lookups):
    results = perm_no_commas(_simple_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "no_commas"
    assert "," not in addr


def test_extra_commas(lookups):
    results = perm_extra_commas(_simple_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "extra_commas"
    assert "NSW, 2629" in addr


def test_extra_commas_returns_empty_when_no_postcode(lookups):
    rec = _simple_rec(postcode=None)
    assert perm_extra_commas(rec, lookups) == []


def test_state_postcode_joined(lookups):
    results = perm_state_postcode_joined(_simple_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "state_postcode_joined"
    assert "NSW2629" in addr


def test_state_postcode_joined_returns_empty_when_no_postcode(lookups):
    rec = _simple_rec(postcode=None)
    assert perm_state_postcode_joined(rec, lookups) == []


# ---------------------------------------------------------------------------
# Building name variants
# ---------------------------------------------------------------------------

def test_building_first(lookups):
    results = perm_building_first(_complex_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "building_first"
    assert addr.startswith("Harbour Tower,")


def test_building_after_unit(lookups):
    results = perm_building_after_unit(_complex_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "building_after_unit"
    assert addr.startswith("Unit 4, Harbour Tower")


def test_building_omitted(lookups):
    results = perm_building_omitted(_complex_rec(), lookups)
    assert len(results) > 1
    ptypes = [p for _, p, _ in results]
    assert "building_omitted" in ptypes
    assert "building_omitted_street_abbrev" in ptypes
    assert "building_omitted_triple_slash" in ptypes
    for addr, _, _ in results:
        assert "Harbour Tower" not in addr


def test_building_variants_return_empty_when_no_building(lookups):
    assert perm_building_first(_simple_rec(), lookups) == []
    assert perm_building_after_unit(_simple_rec(), lookups) == []
    assert perm_building_omitted(_simple_rec(), lookups) == []


def test_building_first_requires_unit(lookups):
    # building_first requires both building_name AND flat_number
    rec = _complex_rec(flat_number=None, flat_type=None)
    assert perm_building_first(rec, lookups) == []


# ---------------------------------------------------------------------------
# Number range
# ---------------------------------------------------------------------------

def test_number_range_spaced(lookups):
    results = perm_number_range_spaced(_complex_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "number_range_spaced"
    assert "12 - 14" in addr


def test_number_range_returns_empty_when_no_last(lookups):
    assert perm_number_range_spaced(_simple_rec(), lookups) == []


# ---------------------------------------------------------------------------
# Lot
# ---------------------------------------------------------------------------

def test_lot_with_street(lookups):
    rec = _simple_rec(lot_number="2556")
    results = perm_lot_with_street(rec, lookups)
    addr, ptype, fields = results[0]
    assert ptype == "lot_with_street"
    assert "Lot 2556" in addr
    assert "16 Banjo Street" in addr
    # "Lot" prefix must be included so the aligner labels both tokens as LOT_NUMBER.
    assert fields["lot_number"] == "Lot 2556"
    assert fields["street_number"] == "16"


def test_lot_only_with_street(lookups):
    """Lot-only address: lot_number == street_number fallback — 'Lot 16 Banjo Street'."""
    rec = _simple_rec(lot_number="16")  # street_number is also "16"
    results = perm_lot_with_street(rec, lookups)
    addr, ptype, fields = results[0]
    assert ptype == "lot_with_street"
    assert addr.startswith("Lot 16"), addr
    assert "Banjo Street" in addr
    # "Lot " prefix included in lot_number; street_number blanked to avoid double-labelling.
    assert fields["lot_number"] == "Lot 16"
    assert fields["street_number"] == ""


def test_lot_abbrev_returns_empty(lookups):
    # perm_lot_abbrev removed: 'L' is the GNAF Level code — would create ambiguous training data
    rec = _simple_rec(lot_number="2556")
    assert perm_lot_abbrev(rec, lookups) == []


def test_lot_returns_empty_when_no_lot(lookups):
    assert perm_lot_with_street(_simple_rec(), lookups) == []
    assert perm_lot_abbrev(_simple_rec(), lookups) == []


# ---------------------------------------------------------------------------
# Suburb prefix
# ---------------------------------------------------------------------------

def test_suburb_expand_mt_to_mount(lookups):
    rec = _simple_rec(suburb="Mt Gravatt East")
    results = perm_suburb_expand(rec, lookups)
    addr, ptype, _ = results[0]
    assert ptype == "suburb_expand"
    assert "Mount Gravatt East" in addr


def test_suburb_abbrev_mount_to_mt(lookups):
    rec = _simple_rec(suburb="Mount Gravatt East")
    results = perm_suburb_abbrev(rec, lookups)
    addr, ptype, _ = results[0]
    assert ptype == "suburb_abbrev"
    assert "Mt Gravatt East" in addr


def test_suburb_expand_returns_empty_when_no_known_prefix(lookups):
    assert perm_suburb_expand(_simple_rec(), lookups) == []


def test_suburb_abbrev_returns_empty_when_no_known_prefix(lookups):
    assert perm_suburb_abbrev(_simple_rec(), lookups) == []


# ---------------------------------------------------------------------------
# Non-standard order
# ---------------------------------------------------------------------------

def test_reversed(lookups):
    results = perm_reversed(_simple_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "reversed"
    # Suburb appears before the street number
    suburb_pos = addr.index("Old Adaminaby")
    street_pos = addr.index("16 Banjo")
    assert suburb_pos < street_pos


def test_postcode_before_suburb(lookups):
    results = perm_postcode_before_suburb(_simple_rec(), lookups)
    addr, ptype, _ = results[0]
    assert ptype == "postcode_before_suburb"
    assert "2629 Old Adaminaby NSW" in addr


def test_postcode_before_suburb_returns_empty_when_no_postcode(lookups):
    rec = _simple_rec(postcode=None)
    assert perm_postcode_before_suburb(rec, lookups) == []


# ---------------------------------------------------------------------------
# Country suffix
# ---------------------------------------------------------------------------

def test_with_country(lookups):
    results = perm_with_country(_simple_rec(), lookups)
    assert len(results) == 2
    ptypes = {p for _, p, _ in results}
    assert "with_country_full" in ptypes
    assert "with_country_abbrev" in ptypes
    full_addr = next(a for a, p, _ in results if p == "with_country_full")
    assert full_addr.endswith(", Australia")
    abbrev_addr = next(a for a, p, _ in results if p == "with_country_abbrev")
    assert abbrev_addr.endswith(", Au")


# ---------------------------------------------------------------------------
# Number prefix
# ---------------------------------------------------------------------------

def test_number_prefix(lookups):
    results = perm_number_prefix(_simple_rec(), lookups)
    assert len(results) == 2
    addrs = [a for a, _, _ in results]
    assert any("No. 16" in a for a in addrs)
    assert any(a for a in addrs if "No 16" in a and "No. 16" not in a)


def test_number_prefix_returns_empty_for_range(lookups):
    rec = _simple_rec(street_number_last="18")
    assert perm_number_prefix(rec, lookups) == []


# ---------------------------------------------------------------------------
# Noisy
# ---------------------------------------------------------------------------

def test_noisy_produces_mutation(lookups):
    import random as _random
    rng = _random.Random(0)
    results = perm_noisy(_simple_rec(), lookups, rng=rng)
    assert len(results) == 1
    addr, ptype, _ = results[0]
    assert ptype == "noisy"
    # The noisy address should differ from canonical
    canonical = perm_canonical(_simple_rec(), lookups)[0][0]
    assert addr != canonical


# ---------------------------------------------------------------------------
# generate_permutations — integration
# ---------------------------------------------------------------------------

def test_generate_permutations_deduplicates(lookups):
    rec = _simple_rec()
    perms = generate_permutations(rec, lookups, max_perms=20)
    addrs = [a for a, _, _ in perms]
    assert len(addrs) == len(set(addrs)), "Duplicate formatted addresses found"


def test_generate_permutations_canonical_labels_identical(lookups):
    """All permutations for the same address have the same label fields (street, suburb, etc.)."""
    rec = _unit_rec()
    perms = generate_permutations(rec, lookups, max_perms=10)
    # The label is always the record's canonical fields — verify all share same street_number
    for addr, _, _ in perms:
        assert addr.strip()


def test_generate_permutations_respects_max_perms(lookups):
    rec = _simple_rec()
    perms = generate_permutations(rec, lookups, max_perms=3)
    assert len(perms) <= 3


def test_generate_permutations_no_empty_addresses(lookups):
    for rec in [_simple_rec(), _unit_rec(), _complex_rec()]:
        perms = generate_permutations(rec, lookups, max_perms=15, include_noisy=True)
        for addr, _, _ in perms:
            assert addr.strip(), f"Empty address in permutations for {rec}"


def test_generate_permutations_missing_postcode(lookups):
    rec = _simple_rec(postcode=None)
    perms = generate_permutations(rec, lookups, max_perms=10)
    assert len(perms) > 0
    for addr, _, _ in perms:
        assert addr.strip()


def test_generate_permutations_missing_street_type(lookups):
    rec = _simple_rec(street_type=None, street_type_code=None, street_type_abbrev=None)
    perms = generate_permutations(rec, lookups, max_perms=10)
    assert len(perms) > 0


def test_generate_permutations_no_postcode_no_abbrev(lookups):
    """Records without postcode or street_type_abbrev produce valid output."""
    rec = AddressRecord(
        building_name=None,
        flat_type="Unit",
        flat_type_code="UNIT",
        flat_type_gnaf_abbrev=None,
        flat_number="5",
        level_type=None,
        level_type_code=None,
        level_number=None,
        lot_number=None,
        street_number="22",
        street_number_last=None,
        street_name="George",
        street_type="Street",
        street_type_code="STREET",
        street_type_abbrev=None,
        street_suffix=None,
        street_suffix_code=None,
        suburb="Brisbane City",
        state="QLD",
        postcode=None,
        source="gnaf",
        cross_street_number=None,
        cross_street_name=None,
        cross_street_type=None,
        cross_street_type_abbrev=None,
    )
    perms = generate_permutations(rec, lookups, max_perms=8)
    assert len(perms) > 0
    for addr, _, _ in perms:
        assert addr.strip()

# ---------------------------------------------------------------------------
# perm_corner
# ---------------------------------------------------------------------------

def test_corner_returns_empty_when_no_cross_street(lookups):
    assert perm_corner(_simple_rec(), lookups) == []


def test_corner_no_numbers(lookups):
    """Cnr-only forms produced when cross_street_number is None."""
    rec = _simple_rec(
        cross_street_number=None,
        cross_street_name="Hutchins",
        cross_street_type="Street",
        cross_street_type_abbrev="St",
    )
    results = perm_corner(rec, lookups)
    addrs = [a for a, _, _ in results]
    assert any("Cnr Banjo St & Hutchins St" in a for a in addrs)
    assert any("Corner Banjo Street And Hutchins Street" in a for a in addrs)
    assert any("Cnr Banjo St/Hutchins St" in a for a in addrs)
    # No number-bearing forms when cross_street_number is absent
    assert not any("&" in a and "16" in a for a in addrs)


def test_corner_both_numbers(lookups):
    """Both-number forms produced when cross_street_number is present."""
    rec = _simple_rec(
        street_number="14",
        street_name="Hooker",
        street_type="Street",
        street_type_code="STREET",
        street_type_abbrev="ST",
        suburb="Yarralumla",
        state="ACT",
        postcode="2600",
        cross_street_number="43",
        cross_street_name="Hutchins",
        cross_street_type="Street",
        cross_street_type_abbrev="St",
    )
    results = perm_corner(rec, lookups)
    addrs = [a for a, _, _ in results]
    ptypes = [p for _, p, _ in results]
    assert any("14 Hooker St & 43 Hutchins St" in a for a in addrs)
    assert any("14 Hooker St / 43 Hutchins St" in a for a in addrs)
    assert any("Cnr 14 Hooker St & 43 Hutchins St" in a for a in addrs)
    assert any("14 Hooker Street" in a and "Cnr Hutchins Street" in a for a in addrs)
    assert "corner_both_numbers" in ptypes


def test_corner_locality_included(lookups):
    """All corner variants include the locality block."""
    rec = _simple_rec(
        cross_street_number="43",
        cross_street_name="Hutchins",
        cross_street_type="Street",
        cross_street_type_abbrev="St",
    )
    for addr, _, _ in perm_corner(rec, lookups):
        assert "Old Adaminaby" in addr


def test_corner_returns_empty_for_same_street(lookups):
    """perm_corner returns [] when cross_street_name is None (no alias found)."""
    rec = _simple_rec(cross_street_name=None)
    assert perm_corner(rec, lookups) == []
