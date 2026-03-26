"""Supplementary informal abbreviation variants beyond GNAF authority tables.

GNAF authority tables already provide the official abbreviation for each component:
  - gnaf_data_street_type_aut: code=FULL_NAME (AVENUE), name=ABBREVIATION (AV)
  - gnaf_data_flat_type_aut: code=ABBREVIATION (APT), name=FULL_NAME (APARTMENT)
  - gnaf_data_level_type_aut: code=ABBREVIATION (L), name=FULL_NAME (LEVEL)
  - gnaf_data_street_suffix_aut: code=ABBREVIATION (N), name=FULL_NAME (NORTH)

This module adds *additional informal variants* that people commonly use but that
aren't in those authority tables.

Keys are uppercase full names (matching what comes out of the DB after normalisation).
Values are lists of informal variants in title case.
"""

# Additional informal street type abbreviations beyond the GNAF authority abbreviation.
# GNAF already gives the standard Aus Post abbrev (AV, ST, RD, etc.) — these are extras.
EXTRA_STREET_TYPE_VARIANTS: dict[str, list[str]] = {
    "AVENUE": ["Ave"],       # GNAF gives AV
    "STREET": ["Str"],       # GNAF gives ST
    "CRESCENT": ["Cres"],    # GNAF gives CR
    "BOULEVARD": ["Blvd"],   # GNAF gives BVD
    "TERRACE": ["Ter"],      # GNAF gives TCE
    "DRIVE": ["Dve"],        # GNAF gives DR
    "COURT": ["Crt"],        # GNAF gives CT
    "CIRCUIT": ["Cir"],      # GNAF gives CCT
    "GROVE": ["Gve"],        # GNAF gives GR
    "LANE": ["Ln"],          # GNAF gives LANE (same — no real abbrev in authority table)
    "PLACE": ["Pce"],        # GNAF gives PL
    "HIGHWAY": ["Hway"],     # GNAF gives HWY
    "CLOSE": ["Cls"],        # GNAF gives CL
    "PARADE": ["Prd"],       # GNAF gives PDE
    "ESPLANADE": ["Espl"],   # GNAF gives ESP
    "PATHWAY": ["Path"],     # GNAF gives PWAY
    "PARKWAY": ["Pkwy"],     # GNAF gives PWY
    "TRACK": ["Trk"],        # GNAF gives TRAK
    "TRAIL": ["Trl"],        # GNAF gives TRL
}

# Additional informal flat/unit type abbreviations.
# GNAF flat_type_aut has code=abbrev, name=full — so "UNIT" code is "UNIT" (unhelpful),
# "APARTMENT" code is "APT", "FLAT" code is "FLAT" (also unhelpful), etc.
# These fill in the real-world shorthand people actually use.
EXTRA_FLAT_TYPE_VARIANTS: dict[str, list[str]] = {
    "UNIT": ["U", "Ut"],             # Very common: U4, Ut 4
    "FLAT": ["F", "Flt"],            # F 9, Flt 9
    "APARTMENT": ["Apt", "Appt"],    # GNAF code is APT; Appt also common
    "SUITE": ["Ste"],                # GNAF code is SE
    "TOWNHOUSE": ["Ths", "Twnhse"],  # GNAF code is TNHS
    "VILLA": ["Vla"],                # GNAF code is VLLA
    "OFFICE": ["Ofc"],               # GNAF code is OFFC
    "PENTHOUSE": ["Pth"],            # GNAF code is PTHS
    "STUDIO": ["Std"],               # GNAF code is STU
    "DUPLEX": ["Dplx"],              # GNAF code is DUPL
    "WAREHOUSE": ["Whse"],           # GNAF code is WHSE (same — add variant)
    "FACTORY": ["Fctry"],            # GNAF code is FCTY
    "SHOP": ["Shp"],                 # GNAF code is SHOP
    "ROOM": ["Rm"],                  # GNAF code is RM (same)
    "BASEMENT": ["Bsmt"],            # GNAF code is BSMT (same)
}

# Additional informal level type abbreviations.
# GNAF level_type_aut has code=abbrev (L, FL, B…), name=full name (LEVEL, FLOOR, BASEMENT…).
# These add extra forms people write.
EXTRA_LEVEL_TYPE_VARIANTS: dict[str, list[str]] = {
    "LEVEL": ["Lvl", "Lv"],          # GNAF code is L
    "FLOOR": ["Flr"],                # GNAF code is FL; Fl is already the GNAF abbrev
    "BASEMENT": ["Bsmt"],            # GNAF code is B
    "GROUND": ["Gnd"],               # GNAF code is G
    "MEZZANINE": ["Mezz"],           # GNAF code is M
    "LOWER GROUND FLOOR": ["Lg", "Lower Gnd"],  # GNAF code is LG
    "UPPER GROUND FLOOR": ["Ug", "Upper Gnd"],  # GNAF code is UG
    "ROOFTOP": ["Roof"],             # GNAF code is RT
    "PARKING": ["Prk"],              # GNAF code is P
    "PODIUM": ["Pod"],               # GNAF code is PDM
}

# Additional informal street suffix abbreviations.
# GNAF street_suffix_aut has code=abbrev (N, S, E…), name=full name (NORTH, SOUTH…).
EXTRA_STREET_SUFFIX_VARIANTS: dict[str, list[str]] = {
    "NORTH": ["Nth"],      # GNAF code is N
    "SOUTH": ["Sth"],      # GNAF code is S
    "EAST": ["Est"],            # E is already minimal — no common extra
    "WEST": ["Wst"],            # W is already minimal
    "UPPER": ["Upr"],      # GNAF code is UP
    "LOWER": ["Lwr"],      # GNAF code is LR
    "CENTRAL": ["Ctrl"],   # GNAF code is CN
    "INNER": [],           # GNAF code is IN
    "OUTER": [],           # GNAF code is OT
    "NORTH EAST": [],      # NE is already minimal
    "NORTH WEST": [],
    "SOUTH EAST": [],
    "SOUTH WEST": [],
}

# Suburb prefix expansions — common abbreviations found in suburb names.
# Maps abbreviated prefix → full expansion (and vice versa for the reverse dict).
SUBURB_PREFIX_ABBREV_TO_FULL: dict[str, str] = {
    "Mt": "Mount",
    "St": "Saint",
    "Pt": "Point",
    "Nth": "North",
    "Sth": "South",
	"Wst": "West",
    "Est": "East",
    "New": "New",    # Not actually abbreviated — keep for completeness
    "Upr": "Upper",
    "Lwr": "Lower",
}

SUBURB_PREFIX_FULL_TO_ABBREV: dict[str, str] = {
    "Mount": "Mt",
    "Saint": "St",
    "Point": "Pt",
    "North": "Nth",
    "South": "Sth",
	"East": "Est",
    "West": "Wst",
    "Upper": "Upr",
    "Lower": "Lwr",
}

# Australian state full names.
STATE_FULL_NAMES: dict[str, str] = {
    "QLD": "Queensland",
    "NSW": "New South Wales",
    "VIC": "Victoria",
    "SA": "South Australia",
    "WA": "Western Australia",
    "TAS": "Tasmania",
    "NT": "Northern Territory",
    "ACT": "Australian Capital Territory",
}
