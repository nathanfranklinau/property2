"""Permutation engine: AddressRecord → list of (formatted_address, permutation_type, field_values).

All output strings are title-cased. Case is not a training concern — the model's
preprocessing handles normalisation.

Each permutation function takes (record, lookups) and returns a list of
(formatted_address, permutation_type, field_values) triples. Returns [] when not applicable.

field_values maps each FIELD_ORDER key to the token string that actually appears in
formatted_address for that field. Empty string means the field is absent from the string.
The prepare_iob alignment code uses these values — not the canonical parquet columns —
so abbreviated and fused formats align correctly.
"""

import random
import re
from dataclasses import dataclass, field
from typing import TypedDict

from .abbreviations import (
    EXTRA_FLAT_TYPE_VARIANTS,
    EXTRA_LEVEL_TYPE_VARIANTS,
    EXTRA_STREET_SUFFIX_VARIANTS,
    EXTRA_STREET_TYPE_VARIANTS,
    SUBURB_PREFIX_ABBREV_TO_FULL,
    SUBURB_PREFIX_FULL_TO_ABBREV,
    STATE_FULL_NAMES,
)


class AddressRecord(TypedDict):
    """Normalised address record from GNAF or cadastre, ready for permutation."""

    building_name: str | None
    flat_type: str | None          # Title-cased full name: "Unit", "Apartment"
    flat_type_code: str | None     # GNAF code: "UNIT", "APT", "FLAT"
    flat_type_gnaf_abbrev: str | None  # GNAF authority abbreviation (may == full name)
    flat_number: str | None        # "4", "4A"
    level_type: str | None         # Title-cased full name: "Level", "Floor"
    level_type_code: str | None    # GNAF code: "L", "FL", "B"
    level_number: str | None       # "2", "G"
    lot_number: str | None         # "2556"
    street_number: str             # "12", "12A"
    street_number_last: str | None  # "14" for range 12–14
    street_name: str               # "Smith" (title case)
    street_type: str | None        # Title-cased full name: "Street", "Avenue"
    street_type_code: str | None   # Uppercase full name (GNAF code): "STREET", "AVENUE"
    street_type_abbrev: str | None  # GNAF authority abbreviation: "ST", "AV"
    street_suffix: str | None      # Title-cased full name: "North", "South"
    street_suffix_code: str | None  # GNAF code (= abbreviation): "N", "S"
    suburb: str                    # Title-cased: "Brisbane"
    state: str                     # "QLD"
    postcode: str | None
    source: str                    # "gnaf"
    # Corner block (CD alias): alternate address on a different street
    cross_street_number: str | None   # e.g. "43"
    cross_street_name: str | None     # e.g. "Hutchins" (title case)
    cross_street_type: str | None     # e.g. "Street" (title case)
    cross_street_type_abbrev: str | None  # e.g. "St"


@dataclass
class AbbrevLookups:
    """Pre-loaded abbreviation tables for permutation generation.

    Loaded once from DB + merged with informal variants from abbreviations.py.
    All keys are uppercase. Values are lists of title-cased variant strings.
    """

    # {UPPERCASE_FULL_NAME: [gnaf_abbrev_title, informal1, informal2, ...]}
    street_type_variants: dict[str, list[str]] = field(default_factory=dict)
    # {UPPERCASE_FULL_NAME: [gnaf_code_title, informal1, ...]}
    flat_type_variants: dict[str, list[str]] = field(default_factory=dict)
    # {UPPERCASE_FULL_NAME: [gnaf_code_title, informal1, ...]}
    level_type_variants: dict[str, list[str]] = field(default_factory=dict)
    # {UPPERCASE_FULL_NAME: [gnaf_code_title, informal1, ...]}
    street_suffix_variants: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        street_type_aut: dict[str, str],    # {FULL_NAME: abbreviation}  e.g. STREET→ST
        flat_type_aut: dict[str, str],      # {code: full_name}           e.g. APT→APARTMENT
        level_type_aut: dict[str, str],     # {code: full_name}           e.g. L→LEVEL
        street_suffix_aut: dict[str, str],  # {code: full_name}           e.g. N→NORTH
    ) -> "AbbrevLookups":
        """Merge GNAF authority tables with informal variants from abbreviations.py."""
        lookups = cls()

        # Street types: code=FULL_NAME, name=ABBREVIATION (inverted vs others)
        for full_name, abbrev in street_type_aut.items():
            variants: list[str] = []
            abbrev_title = abbrev.title()
            # Only include if it's a real abbreviation (different from full name)
            if abbrev.upper() != full_name.upper():
                variants.append(abbrev_title)
            extras = EXTRA_STREET_TYPE_VARIANTS.get(full_name.upper(), [])
            variants.extend(extras)
            lookups.street_type_variants[full_name.upper()] = variants

        # Flat types: code=abbreviation, name=full name
        # Build a full_name → [gnaf_code, informal…] mapping
        for code, full_name in flat_type_aut.items():
            full_upper = full_name.upper()
            variants = []
            code_title = code.title()
            # Only useful as abbreviation if different from full name
            if code.upper() != full_upper:
                variants.append(code_title)
            extras = EXTRA_FLAT_TYPE_VARIANTS.get(full_upper, [])
            variants.extend(extras)
            lookups.flat_type_variants[full_upper] = variants

        # Level types: code=abbreviation, name=full name
        for code, full_name in level_type_aut.items():
            full_upper = full_name.upper()
            variants = []
            code_title = code.title()
            if code.upper() != full_upper:
                variants.append(code_title)
            extras = EXTRA_LEVEL_TYPE_VARIANTS.get(full_upper, [])
            variants.extend(extras)
            lookups.level_type_variants[full_upper] = variants

        # Street suffixes: code=abbreviation, name=full name
        for code, full_name in street_suffix_aut.items():
            full_upper = full_name.upper()
            variants = []
            code_title = code.title()
            if code.upper() != full_upper:
                variants.append(code_title)
            extras = EXTRA_STREET_SUFFIX_VARIANTS.get(full_upper, [])
            variants.extend(extras)
            lookups.street_suffix_variants[full_upper] = variants

        return lookups


# ---------------------------------------------------------------------------
# Address formatter helpers
# ---------------------------------------------------------------------------

def _tc(s: str | None) -> str:
    """Return s title-cased, or empty string if None."""
    if not s:
        return ""
    return s.title()


def _street_block(
    rec: AddressRecord,
    street_type_override: str | None = None,
    suffix_override: str | None = None,
    spaced_range: bool = False,
) -> str:
    """Build 'NN[-MM] Name Type [Suffix]' block."""
    num = rec["street_number"]
    last = rec["street_number_last"]
    if last:
        sep = " - " if spaced_range else "-"
        num_part = f"{num}{sep}{last}"
    else:
        num_part = num

    name = _tc(rec["street_name"])
    st = street_type_override if street_type_override is not None else _tc(rec["street_type"])
    sfx = suffix_override if suffix_override is not None else _tc(rec["street_suffix"])

    parts = [num_part, name]
    if st:
        parts.append(st)
    if sfx:
        parts.append(sfx)
    return " ".join(parts)


def _locality_block(
    rec: AddressRecord,
    omit_postcode: bool = False,
    omit_state: bool = False,
) -> str:
    """Build 'Suburb State Postcode' block."""
    suburb = _tc(rec["suburb"])
    state = rec["state"].upper() if not omit_state else ""
    postcode = rec["postcode"] if not omit_postcode else ""

    parts = [p for p in [suburb, state, postcode] if p]
    return " ".join(parts)


def _unit_prefix(rec: AddressRecord, flat_type_override: str | None = None) -> str:
    """Build 'UnitType Number' prefix (e.g. 'Unit 4')."""
    flat_num = rec["flat_number"] or ""
    flat_type = flat_type_override if flat_type_override is not None else _tc(rec["flat_type"])
    if not flat_type:
        return flat_num
    return f"{flat_type} {flat_num}".strip()


def _level_prefix(rec: AddressRecord, level_override: str | None = None) -> str:
    """Build 'LevelType Number' prefix (e.g. 'Level 2')."""
    lvl_num = rec["level_number"] or ""
    lvl_type = level_override if level_override is not None else _tc(rec["level_type"])
    if not lvl_type:
        return lvl_num
    return f"{lvl_type} {lvl_num}".strip()


def _assemble(parts: list[str], separator: str = ", ") -> str:
    """Join non-empty parts with separator."""
    return separator.join(p for p in parts if p)


def _canonical_fields(rec: AddressRecord) -> dict[str, str]:
    """Return field values as they appear in the canonical formatted address.

    Keys match FIELD_ORDER in prepare_iob.py. Empty string means the field
    is absent from this record (alignment code skips empty values).
    """
    return {
        "building_name": _tc(rec.get("building_name")) or "",
        "unit_type":     _tc(rec.get("flat_type")) or "",
        "unit_number":   rec.get("flat_number") or "",
        "level_type":    _tc(rec.get("level_type")) or "",
        "level_number":  rec.get("level_number") or "",
        "lot_number":    rec.get("lot_number") or "",
        "street_number": rec["street_number"],
        "street_number_last": rec.get("street_number_last") or "",
        "street_name":   _tc(rec["street_name"]),
        "street_type":   _tc(rec.get("street_type")) or "",
        "street_suffix": _tc(rec.get("street_suffix")) or "",
        "suburb":        _tc(rec["suburb"]),
        "state":         rec["state"].upper(),
        "postcode":      rec.get("postcode") or "",
    }


# ---------------------------------------------------------------------------
# Core canonical assembler
# ---------------------------------------------------------------------------

def _canonical(
    rec: AddressRecord,
    unit_str: str | None = None,    # pre-built unit prefix; None = use default; "" = omit
    level_str: str | None = None,
    building_str: str | None = None,
    street_str: str | None = None,
    locality_str: str | None = None,
    separator: str = ", ",
) -> str:
    """Assemble address components into a full string."""
    unit = unit_str if unit_str is not None else (
        _unit_prefix(rec) if rec.get("flat_number") else ""
    )
    level = level_str if level_str is not None else (
        _level_prefix(rec) if rec.get("level_number") else ""
    )
    building = building_str if building_str is not None else _tc(rec.get("building_name"))
    street = street_str if street_str is not None else _street_block(rec)
    locality = locality_str if locality_str is not None else _locality_block(rec)

    return _assemble([unit, level, building, street, locality], separator)


# ---------------------------------------------------------------------------
# Permutation functions
# Each returns list[tuple[str, str]]: [(formatted_address, permutation_type), ...]
# ---------------------------------------------------------------------------

def perm_canonical(rec: AddressRecord, lookups: AbbrevLookups) -> list[tuple[str, str, dict[str, str]]]:
    """Full formal address — all present components."""
    return [(_canonical(rec), "canonical", _canonical_fields(rec))]


def perm_street_abbrev_gnaf(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """GNAF official street type abbreviation (ST, RD, AV…)."""
    abbrev = rec.get("street_type_abbrev")
    if not abbrev or not rec.get("street_type"):
        return []
    abbrev_title = abbrev.title()
    # Skip if abbreviation equals the full name (e.g. WAY → WAY — not useful)
    if abbrev.upper() == (rec.get("street_type_code") or "").upper():
        return []
    street = _street_block(rec, street_type_override=abbrev_title)
    addr = _assemble([
        _unit_prefix(rec) if rec.get("flat_number") else "",
        _level_prefix(rec) if rec.get("level_number") else "",
        _tc(rec.get("building_name")),
        street,
        _locality_block(rec),
    ])
    return [(addr, "street_abbrev_gnaf", {**_canonical_fields(rec), "street_type": abbrev_title})]


def perm_street_abbrev_informal(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Informal street type abbreviation variants (Ave, Cres, Blvd…)."""
    code = rec.get("street_type_code")
    if not code:
        return []
    extras = EXTRA_STREET_TYPE_VARIANTS.get(code.upper(), [])
    results = []
    for variant in extras:
        street = _street_block(rec, street_type_override=variant)
        addr = _assemble([
            _unit_prefix(rec) if rec.get("flat_number") else "",
            _level_prefix(rec) if rec.get("level_number") else "",
            _tc(rec.get("building_name")),
            street,
            _locality_block(rec),
        ])
        results.append((addr, "street_abbrev_informal", {**_canonical_fields(rec), "street_type": variant}))
    return results


def perm_slash_notation(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Slash notation for unit addresses: '4/12 Smith St, Brisbane Qld 4000'.

    Skipped when a level number is present — '9/40 Smith St' with Suite 9, Level 11
    would be misread as Level 9, 40 Smith St. perm_slash_unit_level_street covers
    that case with '9/11/40 Smith St'.
    """
    if not rec.get("flat_number") or rec.get("level_number"):
        return []
    flat_num = rec["flat_number"]
    abbrev = rec.get("street_type_abbrev")
    st = abbrev.title() if abbrev and abbrev.upper() != (rec.get("street_type_code") or "").upper() else _tc(rec.get("street_type"))
    street = _street_block(rec, street_type_override=st)
    # No space between flat num and slash, no unit type
    addr = _assemble([
        f"{flat_num}/{rec['street_number']}" if not rec.get("street_number_last") else
        f"{flat_num}/{rec['street_number']}-{rec['street_number_last']}",
        _tc(rec["street_name"]) + (f" {st}" if st else "") + (f" {_tc(rec.get('street_suffix'))}" if rec.get("street_suffix") else ""),
        _locality_block(rec),
    ])
    # Simpler build:
    num_part = rec["street_number"]
    if rec.get("street_number_last"):
        num_part = f"{rec['street_number']}-{rec['street_number_last']}"
    street_name = _tc(rec["street_name"])
    street_parts = [f"{flat_num}/{num_part}", street_name]
    if st:
        street_parts.append(st)
    if rec.get("street_suffix"):
        street_parts.append(_tc(rec["street_suffix"]))
    street_str = " ".join(street_parts)
    full = _assemble([street_str, _locality_block(rec)])
    # unit_type is absent (slash replaces it); street_type may be abbreviated
    fvals = {**_canonical_fields(rec), "unit_type": "", "street_type": st or ""}
    return [(full, "slash_notation", fvals)]


def perm_slash_unit_level_street(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Unit/level/street slash: '9/11/40 Marcus Clarke St, City Act 2601'.

    Only applicable when both flat_number and level_number are present.
    """
    if not rec.get("flat_number") or not rec.get("level_number"):
        return []
    flat_num = rec["flat_number"]
    lvl_num = rec["level_number"]
    abbrev = rec.get("street_type_abbrev")
    st = abbrev.title() if abbrev and abbrev.upper() != (rec.get("street_type_code") or "").upper() else _tc(rec.get("street_type"))
    num_part = rec["street_number"]
    if rec.get("street_number_last"):
        num_part = f"{rec['street_number']}-{rec['street_number_last']}"
    street_parts = [f"{flat_num}/{lvl_num}/{num_part}", _tc(rec["street_name"])]
    if st:
        street_parts.append(st)
    if rec.get("street_suffix"):
        street_parts.append(_tc(rec["street_suffix"]))
    street_str = " ".join(street_parts)
    full = _assemble([street_str, _locality_block(rec)])
    # unit_type and level_type absent; street_type may be abbreviated
    fvals = {**_canonical_fields(rec), "unit_type": "", "level_type": "", "street_type": st or ""}
    return [(full, "slash_unit_level_street", fvals)]


def perm_slash_with_type(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Hybrid slash: 'Unit 4/12 Smith Street North, Brisbane Qld 4000'.

    Skipped when a level number is present — 'Suite 9/40 Smith St' would silently
    drop Level 11, producing an incorrect label. perm_slash_unit_level_street
    covers the unit+level case with '9/11/40 Smith St'.
    """
    if not rec.get("flat_number") or not rec.get("flat_type") or rec.get("level_number"):
        return []
    flat_num = rec["flat_number"]
    flat_type = _tc(rec["flat_type"])
    num_part = rec["street_number"]
    if rec.get("street_number_last"):
        num_part = f"{rec['street_number']}-{rec['street_number_last']}"
    street_name = _tc(rec["street_name"])
    st = _tc(rec.get("street_type"))
    sfx = _tc(rec.get("street_suffix"))
    street_parts = [f"{flat_type} {flat_num}/{num_part}", street_name]
    if st:
        street_parts.append(st)
    if sfx:
        street_parts.append(sfx)
    street_str = " ".join(street_parts)
    full = _assemble([street_str, _locality_block(rec)])
    return [(full, "slash_with_type", _canonical_fields(rec))]


def perm_flat_abbrev_gnaf(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """GNAF flat type abbreviation (U, F, Offc…) where it differs from full name."""
    if not rec.get("flat_number") or not rec.get("flat_type"):
        return []
    full_upper = (rec["flat_type"] or "").upper()
    gnaf_code = rec.get("flat_type_gnaf_abbrev") or rec.get("flat_type_code")
    if not gnaf_code:
        return []
    gnaf_code_upper = gnaf_code.upper()
    if gnaf_code_upper == full_upper:
        return []  # code IS the full name — not a useful abbreviation
    abbrev_title = gnaf_code.title()
    unit = f"{abbrev_title} {rec['flat_number']}"
    addr = _canonical(rec, unit_str=unit)
    return [(addr, "flat_abbrev_gnaf", {**_canonical_fields(rec), "unit_type": abbrev_title})]


def perm_flat_abbrev_informal(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Informal flat type abbreviations (Ut, Flt, Apt…)."""
    if not rec.get("flat_number") or not rec.get("flat_type"):
        return []
    full_upper = (rec["flat_type"] or "").upper()
    extras = EXTRA_FLAT_TYPE_VARIANTS.get(full_upper, [])
    results = []
    for variant in extras:
        unit = f"{variant} {rec['flat_number']}"
        addr = _canonical(rec, unit_str=unit)
        results.append((addr, "flat_abbrev_informal", {**_canonical_fields(rec), "unit_type": variant}))
    return results


def perm_flat_no_space(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """No-space unit notation: 'U4', 'F9'."""
    if not rec.get("flat_number") or not rec.get("flat_type"):
        return []
    full_upper = (rec["flat_type"] or "").upper()
    extras = EXTRA_FLAT_TYPE_VARIANTS.get(full_upper, [])
    if not extras:
        return []
    # Use first (shortest) variant — typically single letter
    short = extras[0]
    fused = f"{short}{rec['flat_number']}"  # no space — e.g. "U4"
    addr = _canonical(rec, unit_str=fused)
    # The fused token "U4" can't be split by the aligner; treat the whole thing
    # as unit_number so the model learns to label "U4" as B-UNIT_NUMBER.
    fvals = {**_canonical_fields(rec), "unit_type": "", "unit_number": fused}
    return [(addr, "flat_no_space", fvals)]


def perm_level_abbrev(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Level abbreviations: 'Lvl 2', 'Fl 2', 'L2' (code+number joined)."""
    if not rec.get("level_number") or not rec.get("level_type"):
        return []
    full_upper = (rec["level_type"] or "").upper()
    code = rec.get("level_type_code")
    extras = EXTRA_LEVEL_TYPE_VARIANTS.get(full_upper, [])
    results = []
    # Informal variants with space: "Lvl 2" — level_type token changes
    for variant in extras:
        level = f"{variant} {rec['level_number']}"
        addr = _canonical(rec, level_str=level)
        results.append((addr, "level_abbrev", {**_canonical_fields(rec), "level_type": variant}))
    # Code+number joined (e.g. L2, FL3) — only if code is short (≤2 chars)
    # The fused token can't be split; label the whole thing as level_number.
    if code and len(code) <= 2 and code.upper() != full_upper:
        fused = f"{code.title()}{rec['level_number']}"
        addr = _canonical(rec, level_str=fused)
        fvals = {**_canonical_fields(rec), "level_type": "", "level_number": fused}
        results.append((addr, "level_code_joined", fvals))
    return results


def perm_suffix_abbrev(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Street suffix abbreviations: 'Nth', 'Sth', 'N', 'S'."""
    if not rec.get("street_suffix"):
        return []
    full_upper = (rec["street_suffix"] or "").upper()
    code = rec.get("street_suffix_code")  # e.g. "N"
    extras = EXTRA_STREET_SUFFIX_VARIANTS.get(full_upper, [])
    results = []
    # GNAF code (single/double letter abbreviation)
    if code and code.upper() != full_upper:
        code_title = code.title()
        street = _street_block(rec, suffix_override=code_title)
        addr = _assemble([
            _unit_prefix(rec) if rec.get("flat_number") else "",
            _level_prefix(rec) if rec.get("level_number") else "",
            _tc(rec.get("building_name")),
            street,
            _locality_block(rec),
        ])
        results.append((addr, "suffix_abbrev_gnaf", {**_canonical_fields(rec), "street_suffix": code_title}))
    # Informal variants (Nth, Sth…)
    for variant in extras:
        street = _street_block(rec, suffix_override=variant)
        addr = _assemble([
            _unit_prefix(rec) if rec.get("flat_number") else "",
            _level_prefix(rec) if rec.get("level_number") else "",
            _tc(rec.get("building_name")),
            street,
            _locality_block(rec),
        ])
        results.append((addr, "suffix_abbrev_informal", {**_canonical_fields(rec), "street_suffix": variant}))
    return results


def perm_no_postcode(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Omit postcode: '12 Smith Street, Brisbane Qld'."""
    if not rec.get("postcode"):
        return []
    locality = _locality_block(rec, omit_postcode=True)
    addr = _canonical(rec, locality_str=locality)
    return [(addr, "no_postcode", {**_canonical_fields(rec), "postcode": ""})]


def perm_no_state_postcode(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Omit state and postcode: '12 Smith Street, Brisbane'."""
    locality = _tc(rec["suburb"])
    addr = _canonical(rec, locality_str=locality)
    return [(addr, "no_state_postcode", {**_canonical_fields(rec), "state": "", "postcode": ""})]


def perm_minimal(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Minimal: street number + name + type only.

    Skipped when unit or level is present — '40 Marcus Clarke St' is the building
    address, not Suite 9 Level 11. Stripping unit/level changes the target address.
    """
    if rec.get("flat_number") or rec.get("level_number"):
        return []
    abbrev = rec.get("street_type_abbrev")
    st = abbrev.title() if abbrev and abbrev.upper() != (rec.get("street_type_code") or "").upper() else _tc(rec.get("street_type"))
    street = _street_block(rec, street_type_override=st, suffix_override="")
    fvals = {**_canonical_fields(rec), "street_type": st or "", "street_suffix": "",
             "building_name": "", "suburb": "", "state": "", "postcode": ""}
    return [(street, "minimal", fvals)]


def perm_no_commas(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """No commas — all components separated by spaces."""
    addr = _canonical(rec, separator=" ")
    return [(addr, "no_commas", _canonical_fields(rec))]


def perm_state_postcode_joined(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """State and postcode joined without space: 'Brisbane QLD4000', 'Old Adaminaby NSW2629'."""
    if not rec.get("postcode") or not rec.get("state"):
        return []
    suburb = _tc(rec["suburb"])
    fused = f"{rec['state'].upper()}{rec['postcode']}"  # e.g. "QLD4000"
    locality = f"{suburb} {fused}"
    addr = _canonical(rec, locality_str=locality)
    # Label the fused "QLD4000" token as B-STATE; postcode is absent as a separate token.
    return [(addr, "state_postcode_joined", {**_canonical_fields(rec), "state": fused, "postcode": ""})]


def perm_extra_commas(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Extra comma between state and postcode."""
    if not rec.get("postcode") or not rec.get("state"):
        return []
    suburb = _tc(rec["suburb"])
    state = rec["state"].upper()
    postcode = rec["postcode"]
    locality = f"{suburb}, {state}, {postcode}"
    addr = _canonical(rec, locality_str=locality)
    return [(addr, "extra_commas", _canonical_fields(rec))]


def perm_building_first(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Building name before unit: 'Harbour Tower, Unit 4, 12 Smith St, Brisbane'."""
    if not rec.get("building_name") or not rec.get("flat_number"):
        return []
    unit = _unit_prefix(rec)
    building = _tc(rec["building_name"])
    street = _street_block(rec)
    locality = _locality_block(rec)
    addr = _assemble([building, unit, street, locality])
    return [(addr, "building_first", _canonical_fields(rec))]


def perm_building_after_unit(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Building after unit: 'Unit 4, Harbour Tower, 12 Smith St, Brisbane'."""
    if not rec.get("building_name") or not rec.get("flat_number"):
        return []
    unit = _unit_prefix(rec)
    building = _tc(rec["building_name"])
    street = _street_block(rec)
    locality = _locality_block(rec)
    addr = _assemble([unit, building, street, locality])
    return [(addr, "building_after_unit", _canonical_fields(rec))]


def perm_building_omitted(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Building name omitted — several core variants without the building.

    A human writing the address without the building name can still use any of
    the common formats: full, street abbreviation, no postcode, no state/postcode,
    slash notation (unit-only addresses), triple-slash (unit+level), state joined.
    """
    if not rec.get("building_name"):
        return []

    results: list[tuple[str, str, dict[str, str]]] = []
    base = {**_canonical_fields(rec), "building_name": ""}

    def _no_bldg(locality_str: str | None = None, street_str: str | None = None) -> str:
        return _canonical(rec, building_str="", locality_str=locality_str, street_str=street_str)

    # Full address without building
    results.append((_no_bldg(), "building_omitted", base))

    # Street type abbreviation without building
    abbrev = rec.get("street_type_abbrev")
    if abbrev and abbrev.upper() != (rec.get("street_type_code") or "").upper():
        st = abbrev.title()
        results.append((_no_bldg(street_str=_street_block(rec, street_type_override=st)),
                         "building_omitted_street_abbrev", {**base, "street_type": st}))

    # No postcode without building
    if rec.get("postcode"):
        results.append((_no_bldg(locality_str=_locality_block(rec, omit_postcode=True)),
                         "building_omitted_no_postcode", {**base, "postcode": ""}))

    # No state/postcode without building
    results.append((_no_bldg(locality_str=_tc(rec["suburb"])),
                     "building_omitted_no_state_postcode", {**base, "state": "", "postcode": ""}))

    # State+postcode joined without building
    if rec.get("postcode"):
        fused = f"{rec['state'].upper()}{rec['postcode']}"
        joined_locality = f"{_tc(rec['suburb'])} {fused}"
        results.append((_no_bldg(locality_str=joined_locality),
                         "building_omitted_state_joined", {**base, "state": fused, "postcode": ""}))

    # No commas without building (space-separated) — full unit type plus each abbreviation
    results.append((_canonical(rec, building_str="", separator=" "), "building_omitted_no_commas", base))
    if rec.get("flat_number") and rec.get("flat_type"):
        full_upper = (rec["flat_type"] or "").upper()
        for variant in EXTRA_FLAT_TYPE_VARIANTS.get(full_upper, []):
            unit_str = f"{variant} {rec['flat_number']}"
            addr = _canonical(rec, building_str="", unit_str=unit_str, separator=" ")
            results.append((addr, "building_omitted_no_commas", {**base, "unit_type": variant}))

    # Slash notation without building (unit, no level)
    if rec.get("flat_number") and not rec.get("level_number"):
        flat_num = rec["flat_number"]
        num_part = rec["street_number"]
        if rec.get("street_number_last"):
            num_part = f"{rec['street_number']}-{rec['street_number_last']}"
        st = abbrev.title() if abbrev and abbrev.upper() != (rec.get("street_type_code") or "").upper() else _tc(rec.get("street_type"))
        street_parts = [f"{flat_num}/{num_part}", _tc(rec["street_name"])]
        if st:
            street_parts.append(st)
        if rec.get("street_suffix"):
            street_parts.append(_tc(rec["street_suffix"]))
        slash_str = " ".join(street_parts)
        results.append((_assemble([slash_str, _locality_block(rec)]),
                         "building_omitted_slash", {**base, "unit_type": "", "street_type": st or ""}))

    # Triple-slash without building (unit + level)
    if rec.get("flat_number") and rec.get("level_number"):
        flat_num = rec["flat_number"]
        lvl_num = rec["level_number"]
        num_part = rec["street_number"]
        if rec.get("street_number_last"):
            num_part = f"{rec['street_number']}-{rec['street_number_last']}"
        st = abbrev.title() if abbrev and abbrev.upper() != (rec.get("street_type_code") or "").upper() else _tc(rec.get("street_type"))
        street_parts = [f"{flat_num}/{lvl_num}/{num_part}", _tc(rec["street_name"])]
        if st:
            street_parts.append(st)
        if rec.get("street_suffix"):
            street_parts.append(_tc(rec["street_suffix"]))
        triple_str = " ".join(street_parts)
        results.append((_assemble([triple_str, _locality_block(rec)]),
                         "building_omitted_triple_slash",
                         {**base, "unit_type": "", "level_type": "", "street_type": st or ""}))

    return results


def perm_number_range_spaced(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Spaced range: '12 - 14 Smith Street'."""
    if not rec.get("street_number_last"):
        return []
    street = _street_block(rec, spaced_range=True)
    addr = _assemble([
        _unit_prefix(rec) if rec.get("flat_number") else "",
        _level_prefix(rec) if rec.get("level_number") else "",
        _tc(rec.get("building_name")),
        street,
        _locality_block(rec),
    ])
    return [(addr, "number_range_spaced", _canonical_fields(rec))]


def perm_lot_with_street(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Lot+street: 'Lot 2556, 12 Daisy Hill Road, Buckajo QLD 2550'.

    For lot-only addresses (lot_number == street_number, no separate street number),
    produces 'Lot 9 Burton Close, Malanda QLD 4885' — lot prefix replaces the number.
    For addresses with both lot and street number, produces 'Lot 24, 107 Golden Four Drive'.
    """
    if not rec.get("lot_number"):
        return []
    # Strata title: lot_number == flat_number means the lot IS the unit (e.g. APT 3414 = Lot 3414).
    # "Lot 3414, 222 Margaret Street" is not a real address form for a strata unit.
    if rec.get("flat_number") and rec["lot_number"] == rec["flat_number"]:
        return []
    lot = f"Lot {rec['lot_number']}"
    # Lot-only address: lot number was used as street_number fallback — don't repeat it
    if rec["street_number"] == rec["lot_number"]:
        street_parts = [_tc(rec["street_name"])]
        if rec.get("street_type"):
            street_parts.append(_tc(rec["street_type"]))
        if rec.get("street_suffix"):
            street_parts.append(_tc(rec["street_suffix"]))
        street_str = " ".join(street_parts)
        addr = _assemble([lot, street_str, _locality_block(rec)])
        # Include "Lot " prefix in lot_number so the aligner labels both tokens as
        # LOT_NUMBER (B- + I-) rather than leaving "Lot" unlabelled (O), which caused
        # the model to misclassify the keyword as BUILDING_NAME.
        # street_number is blanked so "210" isn't double-labelled.
        fields = {**_canonical_fields(rec), "street_number": "", "lot_number": lot}
        return [(addr, "lot_with_street", fields)]
    else:
        addr = _assemble([lot, _street_block(rec), _locality_block(rec)])
        # Include "Lot " prefix so the aligner labels it as part of LOT_NUMBER.
        fields = {**_canonical_fields(rec), "lot_number": lot}
    return [(addr, "lot_with_street", fields)]


def perm_lot_abbrev(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Removed: 'L' is the GNAF code for Level, not Lot — would produce ambiguous training data."""
    return []


def perm_suburb_expand(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Expand suburb prefix abbreviation: 'Mt Gravatt' → 'Mount Gravatt'."""
    suburb = _tc(rec["suburb"])
    words = suburb.split()
    if not words:
        return []
    first = words[0]
    expanded = SUBURB_PREFIX_ABBREV_TO_FULL.get(first)
    if not expanded or expanded == first:
        return []
    new_suburb = " ".join([expanded] + words[1:])
    locality = _locality_block(rec).replace(suburb, new_suburb)
    addr = _canonical(rec, locality_str=locality)
    return [(addr, "suburb_expand", {**_canonical_fields(rec), "suburb": new_suburb})]


def perm_suburb_abbrev(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Abbreviate suburb prefix: 'Mount Gravatt' → 'Mt Gravatt'."""
    suburb = _tc(rec["suburb"])
    words = suburb.split()
    if not words:
        return []
    first = words[0]
    abbrev = SUBURB_PREFIX_FULL_TO_ABBREV.get(first)
    if not abbrev or abbrev == first:
        return []
    new_suburb = " ".join([abbrev] + words[1:])
    locality = _locality_block(rec).replace(suburb, new_suburb)
    addr = _canonical(rec, locality_str=locality)
    return [(addr, "suburb_abbrev", {**_canonical_fields(rec), "suburb": new_suburb})]


def perm_reversed(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Suburb-first: 'Brisbane Qld 4000, 12 Smith Street North'."""
    locality = _locality_block(rec)
    street = _street_block(rec)
    unit = _unit_prefix(rec) if rec.get("flat_number") else ""
    level = _level_prefix(rec) if rec.get("level_number") else ""
    addr = _assemble([locality, unit, level, street])
    return [(addr, "reversed", _canonical_fields(rec))]


def perm_postcode_before_suburb(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Postcode before suburb: '12 Smith St, 4000 Brisbane Qld'."""
    if not rec.get("postcode"):
        return []
    suburb = _tc(rec["suburb"])
    state = rec["state"].upper()
    locality = f"{rec['postcode']} {suburb} {state}"
    addr = _canonical(rec, locality_str=locality)
    return [(addr, "postcode_before_suburb", _canonical_fields(rec))]


def perm_with_country(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Append country: ', Australia' or ', Au'."""
    base = _canonical(rec)
    fvals = _canonical_fields(rec)
    return [
        (f"{base}, Australia", "with_country_full", fvals),
        (f"{base}, Au", "with_country_abbrev", fvals),
    ]


def perm_number_prefix(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Number prefix: 'No. 12 Smith Street' or 'No 12 Smith Street'."""
    num = rec["street_number"]
    name = _tc(rec["street_name"])
    st = _tc(rec.get("street_type"))
    sfx = _tc(rec.get("street_suffix"))
    last = rec.get("street_number_last")
    if last:
        # Range doesn't commonly get No. prefix — skip
        return []
    # Lot-only address: street_number is the lot number — "No. 9" is not meaningful
    if rec.get("lot_number") and rec["street_number"] == rec["lot_number"]:
        return []
    unit = _unit_prefix(rec) if rec.get("flat_number") else ""
    level = _level_prefix(rec) if rec.get("level_number") else ""
    locality = _locality_block(rec)
    fvals = _canonical_fields(rec)
    results = []
    for prefix, ptype in [("No. ", "number_prefix_period"), ("No ", "number_prefix_nospace")]:
        street_parts = [f"{prefix}{num}", name]
        if st:
            street_parts.append(st)
        if sfx:
            street_parts.append(sfx)
        street = " ".join(street_parts)
        addr = _assemble([unit, level, street, locality])
        results.append((addr, ptype, fvals))
    return results


def perm_corner(
    rec: AddressRecord, lookups: AbbrevLookups
) -> list[tuple[str, str, dict[str, str]]]:
    """Corner address permutations using the CD alias cross-street from GNAF.

    Generates multiple formats — with and without street numbers, using &, /, And.
    Principal address labels are preserved; cross-street only appears in the string.
    Returns [] when no cross-street data is available.
    """
    if not rec.get("cross_street_name"):
        return []

    p_num = rec["street_number"]
    p_name = _tc(rec["street_name"])
    p_type = _tc(rec.get("street_type"))
    p_abbrev = rec.get("street_type_abbrev")
    p_abbrev_tc = p_abbrev.title() if p_abbrev and p_abbrev.upper() != (rec.get("street_type_code") or "").upper() else p_type

    x_num = rec.get("cross_street_number") or ""
    x_name = _tc(rec["cross_street_name"])
    x_type = _tc(rec.get("cross_street_type"))
    x_abbrev = _tc(rec.get("cross_street_type_abbrev")) or x_type

    locality = _locality_block(rec)

    # Build street strings in full and abbreviated forms
    p_full = " ".join(p for p in [p_name, p_type] if p)
    p_short = " ".join(p for p in [p_name, p_abbrev_tc] if p)
    x_full = " ".join(p for p in [x_name, x_type] if p)
    x_short = " ".join(p for p in [x_name, x_abbrev] if p)

    # Corner formats use the abbreviated street type; principal labels are canonical.
    fvals = {**_canonical_fields(rec), "street_type": p_abbrev_tc or p_type or ""}
    results: list[tuple[str, str, dict[str, str]]] = []

    # --- No numbers (classic Cnr format) ---
    # "Cnr Hooker St & Hutchins St, Yarralumla ACT 2600"
    results.append((_assemble([f"Cnr {p_short} & {x_short}", locality]), "corner", fvals))
    # "Corner Hooker Street And Hutchins Street, Yarralumla ACT 2600"
    results.append((_assemble([f"Corner {p_full} And {x_full}", locality]), "corner",
                     {**_canonical_fields(rec), "street_type": p_type or ""}))
    # "Cnr Hooker St/Hutchins St, Yarralumla ACT 2600"
    results.append((_assemble([f"Cnr {p_short}/{x_short}", locality]), "corner", fvals))

    # --- Both numbers ---
    if x_num:
        # "14 Hooker St & 43 Hutchins St, Yarralumla ACT 2600"
        results.append((_assemble([f"{p_num} {p_short} & {x_num} {x_short}", locality]), "corner_both_numbers", fvals))
        # "14 Hooker St / 43 Hutchins St, Yarralumla ACT 2600"
        results.append((_assemble([f"{p_num} {p_short} / {x_num} {x_short}", locality]), "corner_both_numbers", fvals))
        # "Cnr 14 Hooker St & 43 Hutchins St, Yarralumla ACT 2600"
        results.append((_assemble([f"Cnr {p_num} {p_short} & {x_num} {x_short}", locality]), "corner_both_numbers", fvals))
        # "14 Hooker Street, Cnr Hutchins Street, Yarralumla ACT 2600"
        results.append((_assemble([f"{p_num} {p_full}", f"Cnr {x_full}", locality]), "corner_both_numbers",
                         {**_canonical_fields(rec), "street_type": p_type or ""}))

    return results


def perm_noisy(
    rec: AddressRecord, lookups: AbbrevLookups, rng: random.Random | None = None
) -> list[tuple[str, str, dict[str, str]]]:
    """Noisy/dirty variant: random mutations (double space, missing space, etc.)."""
    if rng is None:
        rng = random.Random()
    base = _canonical(rec)
    mutations = [
        lambda s: re.sub(r" ", "  ", s, count=1),            # double space (first)
        lambda s: re.sub(r", ", ",", s, count=1),             # missing space after comma
        lambda s: re.sub(r"(\w)(,)", r"\1 ,", s, count=1),   # space before comma
        lambda s: s.strip() + "  ",                           # trailing spaces
        lambda s: "  " + s.strip(),                           # leading spaces
        lambda s: re.sub(r"(\d)/(\d)", r"\1/ \2", s),         # space after slash
        lambda s: re.sub(r"([A-Z][a-z]+) (\d)", r"\1\2", s, count=1),  # missing space before number
    ]
    chosen = rng.sample(mutations, k=min(2, len(mutations)))
    noisy = base
    for fn in chosen:
        noisy = fn(noisy)
    return [(noisy, "noisy", _canonical_fields(rec))]


# ---------------------------------------------------------------------------
# All permutation functions (ordered: always-generated first, then optional)
# ---------------------------------------------------------------------------

_ALWAYS: list = [
    perm_canonical,
    perm_street_abbrev_gnaf,
    perm_slash_notation,
]

_OPTIONAL: list = [
    perm_street_abbrev_informal,
    perm_flat_abbrev_gnaf,
    perm_flat_abbrev_informal,
    perm_flat_no_space,
    perm_slash_unit_level_street,
    perm_slash_with_type,
    perm_level_abbrev,
    perm_suffix_abbrev,
    perm_no_postcode,
    perm_no_state_postcode,
    perm_minimal,
    perm_no_commas,
    perm_extra_commas,
    perm_state_postcode_joined,
    perm_building_first,
    perm_building_after_unit,
    perm_building_omitted,
    perm_number_range_spaced,
    perm_lot_with_street,
    perm_lot_abbrev,
    perm_suburb_expand,
    perm_suburb_abbrev,
    perm_reversed,
    perm_postcode_before_suburb,
    perm_with_country,
    perm_number_prefix,
    perm_corner,
]


def generate_permutations(
    rec: AddressRecord,
    lookups: AbbrevLookups,
    max_perms: int = 8,
    include_noisy: bool = False,
    rng: random.Random | None = None,
) -> list[tuple[str, str, dict[str, str]]]:
    """Generate up to max_perms permutations for a single AddressRecord.

    Always includes: canonical, street_abbrev_gnaf (if applicable), slash_notation (if unit).
    Randomly samples from the optional pool to reach max_perms.
    Deduplicates by formatted string before returning.

    Returns triples of (formatted_address, permutation_type, field_values) where
    field_values maps each FIELD_ORDER key to the token string that actually appears
    in formatted_address for that field (empty string = field absent from string).
    """
    if rng is None:
        rng = random.Random()

    results: list[tuple[str, str, dict[str, str]]] = []

    # Always-generated permutations
    for fn in _ALWAYS:
        results.extend(fn(rec, lookups))

    # Build pool of all applicable optional permutations
    optional_pool: list[tuple[str, str, dict[str, str]]] = []
    for fn in _OPTIONAL:
        optional_pool.extend(fn(rec, lookups))

    if include_noisy:
        optional_pool.extend(perm_noisy(rec, lookups, rng))

    # Shuffle and fill up to max_perms
    rng.shuffle(optional_pool)
    remaining = max_perms - len(results)
    results.extend(optional_pool[:remaining])

    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[tuple[str, str, dict[str, str]]] = []
    for addr, ptype, fvals in results:
        if addr not in seen and addr.strip():
            seen.add(addr)
            unique.append((addr, ptype, fvals))

    return unique
