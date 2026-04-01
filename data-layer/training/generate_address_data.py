"""Generate address training data from GNAF.

Extracts structured addresses from PostgreSQL, generates realistic human-typed
permutations, and writes paired (input, label) rows to CSV or Parquet.

Usage:
    sh run.sh training/generate_address_data.py \
        --output training/data/address_training.csv \
        --states QLD \
        --limit 50000 \
        --seed 55 \
        --max-perms 55 \
        --noisy \
        --parquet

Run from data-layer/ directory.
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import sys
import time
from collections import defaultdict, deque
from typing import Iterator

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

# Add data-layer/ to path so training package imports work the same way as in tests
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from training.permutations import (
    AddressRecord,
    AbbrevLookups,
    generate_permutations,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

OUTPUT_COLUMNS = [
    "formatted_address",
    "unit_type",
    "unit_number",
    "level_type",
    "level_number",
    "lot_number",
    "street_number",
    "street_number_last",
    "street_name",
    "street_type",
    "street_suffix",
    "suburb",
    "state",
    "postcode",
    "building_name",
    "source",
    "permutation_type",
    "field_values_json",
]


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "subdivide"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def load_authority_tables(
    conn: psycopg2.extensions.connection,
) -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    """Load all 4 GNAF authority tables from DB.

    Returns:
        street_type_aut:  {FULL_NAME_UPPER: abbreviation_upper}  e.g. STREET → ST
        flat_type_aut:    {code_upper: full_name_upper}           e.g. APT → APARTMENT
        level_type_aut:   {code_upper: full_name_upper}           e.g. L → LEVEL
        street_suffix_aut: {code_upper: full_name_upper}          e.g. N → NORTH
    """
    cur = conn.cursor()

    cur.execute("SELECT code, name FROM gnaf_data_street_type_aut")
    # code = full name (e.g. AVENUE), name = abbreviation (e.g. AV)
    street_type_aut = {row[0].upper(): row[1].upper() for row in cur.fetchall()}

    cur.execute("SELECT code, name FROM gnaf_data_flat_type_aut")
    # code = abbreviation (e.g. APT), name = full name (e.g. APARTMENT)
    flat_type_aut = {row[0].upper(): row[1].upper() for row in cur.fetchall()}

    cur.execute("SELECT code, name FROM gnaf_data_level_type_aut")
    # code = abbreviation (e.g. L), name = full name (e.g. LEVEL)
    level_type_aut = {row[0].upper(): row[1].upper() for row in cur.fetchall()}

    cur.execute("SELECT code, name FROM gnaf_data_street_suffix_aut")
    # code = abbreviation (e.g. N), name = full name (e.g. NORTH)
    street_suffix_aut = {row[0].upper(): row[1].upper() for row in cur.fetchall()}

    cur.close()
    log.info(
        "Authority tables loaded: %d street types, %d flat types, "
        "%d level types, %d street suffixes",
        len(street_type_aut), len(flat_type_aut),
        len(level_type_aut), len(street_suffix_aut),
    )
    return street_type_aut, flat_type_aut, level_type_aut, street_suffix_aut


# ---------------------------------------------------------------------------
# GNAF extraction
# ---------------------------------------------------------------------------

_GNAF_SELECT = """
SELECT
    av.address_detail_pid,
    ad.building_name,
    av.flat_type                        AS flat_type_full,
    ad.flat_type_code,
    ad.flat_number_prefix,
    ad.flat_number,
    ad.flat_number_suffix,
    av.level_type                       AS level_type_full,
    ad.level_type_code,
    ad.level_number_prefix,
    ad.level_number,
    ad.level_number_suffix,
    ad.lot_number_prefix,
    ad.lot_number,
    ad.lot_number_suffix,
    ad.number_first_prefix,
    ad.number_first,
    ad.number_first_suffix,
    ad.number_last_prefix,
    ad.number_last,
    ad.number_last_suffix,
    av.street_name,
    av.street_type_code,
    av.street_suffix_code,
    av.street_suffix_type               AS street_suffix_full,
    av.locality_name,
    av.state_abbreviation,
    av.postcode
FROM address_view av
JOIN gnaf_data_address_detail ad ON av.address_detail_pid = ad.address_detail_pid
WHERE av.alias_principal = 'P'
  AND av.confidence >= 0
  AND av.street_name IS NOT NULL
"""

_GNAF_QUERY = _GNAF_SELECT + """
  AND (av.number_first IS NOT NULL OR ad.lot_number IS NOT NULL)
  {where_clause}
{limit_clause}
"""

# Stratified sampling: (name, extra_where, proportion).
# Each category is sampled separately to guarantee representation when --limit is used.
# Proportions sum to 1.0.
_STRATA: list[tuple[str, str, float]] = [
    # Bread-and-butter simple addresses
    ("simple",
     "AND av.number_first IS NOT NULL AND ad.lot_number IS NULL "
     "AND ad.flat_type_code IS NULL AND ad.level_type_code IS NULL "
     "AND ad.building_name IS NULL AND ad.number_last IS NULL "
     "AND av.street_suffix_code IS NULL",
     0.28),
    # Unit / flat (no level)
    ("unit_only",
     "AND ad.flat_type_code IS NOT NULL AND ad.level_type_code IS NULL",
     0.18),
    # Unit + level (complex strata)
    ("unit_level",
     "AND ad.flat_type_code IS NOT NULL AND ad.level_type_code IS NOT NULL",
     0.10),
    # Building name + unit
    ("building_unit",
     "AND ad.building_name IS NOT NULL AND ad.flat_type_code IS NOT NULL",
     0.08),
    # Building name without unit (commercial / named properties)
    ("building_only",
     "AND ad.building_name IS NOT NULL AND ad.flat_type_code IS NULL",
     0.06),
    # Street number range (12-14 Smith St)
    ("range",
     "AND av.number_first IS NOT NULL AND ad.number_last IS NOT NULL",
     0.08),
    # Street suffix (North, South, East, West…)
    ("suffix",
     "AND av.street_suffix_code IS NOT NULL",
     0.08),
    # Lot-only (no number_first)
    ("lot_only",
     "AND ad.lot_number IS NOT NULL AND av.number_first IS NULL",
     0.04),
    # Corner blocks (CD alias exists)
    ("corner",
     "AND av.address_detail_pid = ANY(%(corner_pids)s)",
     0.05),
    # Wild card — anything not covered above (catches rare combos)
    ("other",
     "AND av.number_first IS NOT NULL",
     0.05),
]

# Corner alias lookup: {principal_pid: (cross_number_first, cross_street_name, cross_street_type_code)}
CornerAlias = tuple[int | None, str, str | None]


def load_corner_aliases(conn: psycopg2.extensions.connection) -> dict[str, CornerAlias]:
    """Pre-load all CD (corner dual) aliases into memory.

    Only 12,485 rows — trivial to hold in RAM. Avoids a LATERAL join on the
    main streaming query which would do a seq scan of the alias table for every
    one of the 15M address rows.
    """
    cur = conn.cursor()
    # Avoid joining address_view (complex view) — go directly to the underlying tables.
    # gnaf_data_address_detail has street_locality_pid; gnaf_data_street_locality has street_name/type.
    cur.execute("""
        SELECT
            aa.principal_pid,
            x_ad.number_first          AS cross_number_first,
            x_sl.street_name           AS cross_street_name,
            x_sl.street_type_code      AS cross_street_type_code,
            p_sl.street_name           AS principal_street_name
        FROM gnaf_data_address_alias aa
        JOIN gnaf_data_address_detail x_ad ON x_ad.address_detail_pid = aa.alias_pid
        JOIN gnaf_data_street_locality x_sl ON x_sl.street_locality_pid = x_ad.street_locality_pid
        JOIN gnaf_data_address_detail p_ad ON p_ad.address_detail_pid = aa.principal_pid
        JOIN gnaf_data_street_locality p_sl ON p_sl.street_locality_pid = p_ad.street_locality_pid
        WHERE aa.alias_type_code = 'CD'
          AND x_sl.street_name != p_sl.street_name
    """)
    result: dict[str, CornerAlias] = {}
    for principal_pid, cross_num, cross_street, cross_type, _p_street in cur.fetchall():
        # Keep only the first alias per principal (corner blocks rarely have more than one)
        if principal_pid not in result:
            result[principal_pid] = (cross_num, cross_street, cross_type)
    cur.close()
    log.info("Loaded %d corner (CD) aliases.", len(result))
    return result


def _build_street_number(
    prefix: str | None,
    number: int | None,
    suffix: str | None,
) -> str | None:
    if number is None:
        return None
    parts = []
    if prefix:
        parts.append(prefix.strip())
    parts.append(str(number))
    if suffix:
        parts.append(suffix.strip())
    return "".join(parts)


def _build_flat_number(prefix: str | None, number: str | None, suffix: str | None) -> str | None:
    if not number:
        return None
    parts = []
    if prefix:
        parts.append(prefix.strip())
    parts.append(str(number).strip())
    if suffix:
        parts.append(suffix.strip())
    return "".join(parts)


def _normalise_row(
    row: psycopg2.extras.DictRow,
    street_type_aut: dict[str, str],
    corner_aliases: dict[str, CornerAlias],
) -> AddressRecord | None:
    """Convert a raw DB row into an AddressRecord. Returns None if the row should be skipped."""
    street_num = _build_street_number(
        row["number_first_prefix"], row["number_first"], row["number_first_suffix"]
    )
    if not street_num:
        lot_fallback = _build_flat_number(
            row["lot_number_prefix"], row["lot_number"], row["lot_number_suffix"]
        )
        if not lot_fallback:
            return None
        street_num = lot_fallback

    flat_type_full = row["flat_type_full"]
    flat_type_code = row["flat_type_code"]
    level_type_full = row["level_type_full"]
    level_type_code = row["level_type_code"]
    street_type_code = row["street_type_code"]
    street_type_full = street_type_code.title() if street_type_code else None
    street_type_abbrev = (
        street_type_aut.get(street_type_code.upper(), street_type_code).title()
        if street_type_code else None
    )
    # Don't emit the abbreviation if it equals the full name (e.g. WAY → WAY)
    if street_type_abbrev and street_type_code and street_type_abbrev.upper() == street_type_code.upper():
        street_type_abbrev = street_type_code

    corner = corner_aliases.get(row["address_detail_pid"])
    if corner:
        cross_num, cross_street_name, cross_street_type_code = corner
        cross_street_type_abbrev = (
            street_type_aut.get(cross_street_type_code.upper(), cross_street_type_code).title()
            if cross_street_type_code else None
        )
    else:
        cross_num = cross_street_name = cross_street_type_code = cross_street_type_abbrev = None

    return AddressRecord(
        building_name=row["building_name"],
        flat_type=flat_type_full.title() if flat_type_full else None,
        flat_type_code=flat_type_code,
        flat_type_gnaf_abbrev=flat_type_code,
        flat_number=_build_flat_number(
            row["flat_number_prefix"],
            str(row["flat_number"]) if row["flat_number"] is not None else None,
            row["flat_number_suffix"],
        ),
        level_type=level_type_full.title() if level_type_full else None,
        level_type_code=level_type_code,
        level_number=_build_flat_number(
            row["level_number_prefix"],
            str(row["level_number"]) if row["level_number"] is not None else None,
            row["level_number_suffix"],
        ),
        lot_number=_build_flat_number(
            row["lot_number_prefix"], row["lot_number"], row["lot_number_suffix"]
        ),
        street_number=street_num,
        street_number_last=_build_street_number(None, row["number_last"], row["number_last_suffix"]),
        street_name=row["street_name"].title(),
        street_type=street_type_full,
        street_type_code=street_type_code,
        street_type_abbrev=street_type_abbrev,
        street_suffix=row["street_suffix_full"].title() if row["street_suffix_full"] else None,
        street_suffix_code=row["street_suffix_code"],
        suburb=row["locality_name"].title(),
        state=row["state_abbreviation"].upper(),
        postcode=row["postcode"],
        source="gnaf",
        cross_street_number=str(cross_num) if cross_num is not None else None,
        cross_street_name=cross_street_name.title() if cross_street_name else None,
        cross_street_type=cross_street_type_code.title() if cross_street_type_code else None,
        cross_street_type_abbrev=cross_street_type_abbrev,
    )


def stream_gnaf(
    conn: psycopg2.extensions.connection,
    states: list[str],
    limit: int | None,
    street_type_aut: dict[str, str],
    flat_type_aut: dict[str, str],
    level_type_aut: dict[str, str],
    street_suffix_aut: dict[str, str],
    corner_aliases: dict[str, CornerAlias],
    seed: int = 42,
    batch_size: int = 5000,
    gnaf_pid: str | None = None,
) -> Iterator[AddressRecord]:
    """Stream GNAF ADDRESS_VIEW rows as AddressRecords.

    When --limit is set: stratified sampling — runs one query per address category
    (simple, unit, building, range, corner, etc.) to guarantee a representative mix,
    then shuffles all collected records before yielding. For limited runs the full
    result set fits comfortably in memory.

    When no limit: streams everything directly via a server-side cursor (no in-memory
    collection needed — the full dataset covers all types anyway).
    """
    if gnaf_pid:
        # Single-address debug mode — bypass stratification
        params: dict = {"gnaf_pid": gnaf_pid, "states": states}
        query = _GNAF_QUERY.format(
            where_clause="AND av.address_detail_pid = %(gnaf_pid)s",
            limit_clause="",
        )
        cur = conn.cursor("gnaf_stream", cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query, params)
        for row in cur:
            rec = _normalise_row(row, street_type_aut, corner_aliases)
            if rec:
                yield rec
        cur.close()
        return

    state_filter = "AND av.state_abbreviation = ANY(%(states)s)"
    base_params: dict = {"states": states}

    if limit is None:
        # Full run — stream all records directly, no stratification needed
        query = _GNAF_QUERY.format(where_clause=state_filter, limit_clause="")
        cur = conn.cursor("gnaf_stream", cursor_factory=psycopg2.extras.DictCursor)
        cur.itersize = batch_size
        cur.execute(query, base_params)
        for row in cur:
            rec = _normalise_row(row, street_type_aut, corner_aliases)
            if rec:
                yield rec
        cur.close()
        return

    # Stratified mode: sample proportionally from each category, then shuffle
    corner_pids = list(corner_aliases.keys())
    rng = random.Random(seed)
    all_records: list[AddressRecord] = []

    for stratum_name, extra_where, proportion in _STRATA:
        n = max(1, round(limit * proportion))
        # md5 pseudo-random ordering within each stratum — fast top-N sort, seed-stable
        order = f"ORDER BY md5(av.address_detail_pid || '{seed}')"
        query = (
            _GNAF_SELECT
            + f"  AND (av.number_first IS NOT NULL OR ad.lot_number IS NOT NULL)\n"
            + f"  {state_filter}\n"
            + f"  {extra_where}\n"
            + f"{order} LIMIT {n}"
        )
        params = {**base_params, "corner_pids": corner_pids}
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        stratum_records = [r for row in rows if (r := _normalise_row(row, street_type_aut, corner_aliases))]
        log.info("Stratum %-14s → %d records (target %d)", stratum_name, len(stratum_records), n)
        all_records.extend(stratum_records)

    rng.shuffle(all_records)
    yield from all_records


_TRAINING_TOTAL = 1_000_000

# Per-dimension coverage: ensures every authority table value appears in the dataset.
# (label, partition_col, extra_where, n_per_type)
_COVERAGE_DIMS: list[tuple[str, str, str, int]] = [
    ("flat_type",     "ad.flat_type_code",    "AND ad.flat_type_code IS NOT NULL AND av.number_first IS NOT NULL", 30),
    ("level_type",    "ad.level_type_code",   "AND ad.level_type_code IS NOT NULL AND av.number_first IS NOT NULL", 30),
    ("street_suffix", "av.street_suffix_code","AND av.street_suffix_code IS NOT NULL AND av.number_first IS NOT NULL", 40),
    ("street_type",   "av.street_type_code",  "AND av.number_first IS NOT NULL", 15),
]


def _fetch_coverage(
    conn: psycopg2.extensions.connection,
    partition_col: str,
    extra_where: str,
    n_per_type: int,
    seed: int,
    street_type_aut: dict[str, str],
    corner_aliases: dict[str, CornerAlias],
) -> list[AddressRecord]:
    """Fetch up to n_per_type examples of every distinct value of partition_col.

    Uses a single CTE + ROW_NUMBER() scan rather than one query per type value.
    """
    # Strip table alias (e.g. "ad.flat_type_code" → "flat_type_code") for use inside the CTE
    bare_col = partition_col.split(".")[-1]
    query = f"""
WITH base AS (
    {_GNAF_SELECT}
    {extra_where}
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY {bare_col}
        ORDER BY md5(address_detail_pid || %(seed_str)s)
    ) AS rn
    FROM base
)
SELECT * FROM ranked WHERE rn <= %(n)s
"""
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(query, {"seed_str": str(seed), "n": n_per_type})
    rows = cur.fetchall()
    cur.close()
    return [r for row in rows if (r := _normalise_row(row, street_type_aut, corner_aliases))]


def stream_gnaf_training(
    conn: psycopg2.extensions.connection,
    states: list[str],
    street_type_aut: dict[str, str],
    flat_type_aut: dict[str, str],
    level_type_aut: dict[str, str],
    street_suffix_aut: dict[str, str],
    corner_aliases: dict[str, CornerAlias],
    seed: int = 42,
) -> Iterator[AddressRecord]:
    """Comprehensive training data stream: 300K source addresses with guaranteed coverage.

    Phase 1 — Coverage: one CTE query per dimension (flat type, level type, street
    suffix, street type) fetches N examples of every authority table value in a single
    pass. Covers all 54 flat types, 16 level types, 19 suffixes, 276 street types.

    Phase 2 — Bulk: remaining budget split evenly across all 8 states, run through
    _STRATA proportions so each state has the full mix of simple/unit/complex/etc.

    Results shuffled before yielding so the output file isn't ordered by type.
    """
    rng = random.Random(seed)
    all_records: list[AddressRecord] = []
    corner_pids = list(corner_aliases.keys())

    # --- Phase 1: type coverage ---
    for label, partition_col, extra_where, n_per_type in _COVERAGE_DIMS:
        records = _fetch_coverage(
            conn, partition_col, extra_where, n_per_type, seed,
            street_type_aut, corner_aliases,
        )
        log.info("Coverage %-12s → %d records", label, len(records))
        all_records.extend(records)

    coverage_count = len(all_records)
    log.info("Coverage phase complete: %d records across all type dimensions", coverage_count)

    # --- Phase 2: per-state bulk stratified sampling ---
    bulk_budget = max(0, _TRAINING_TOTAL - coverage_count)
    per_state = bulk_budget // len(states)
    state_filter = "AND av.state_abbreviation = ANY(%(states)s)"

    for state in states:
        state_params: dict = {"states": [state], "corner_pids": corner_pids}
        state_count = 0
        for stratum_name, extra_where, proportion in _STRATA:
            n = max(1, round(per_state * proportion))
            query = (
                _GNAF_SELECT
                + f"  AND (av.number_first IS NOT NULL OR ad.lot_number IS NOT NULL)\n"
                + f"  {state_filter}\n"
                + f"  {extra_where}\n"
                + f"ORDER BY md5(av.address_detail_pid || '{seed}') LIMIT {n}"
            )
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute(query, state_params)
            rows = cur.fetchall()
            cur.close()
            records = [r for row in rows if (r := _normalise_row(row, street_type_aut, corner_aliases))]
            all_records.extend(records)
            state_count += len(records)

        log.info("State %-4s → %d records", state, state_count)

    log.info(
        "Training collection complete: %d source records (%d coverage + %d bulk)",
        len(all_records), coverage_count, len(all_records) - coverage_count,
    )
    rng.shuffle(all_records)
    yield from all_records


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def _row_to_output(rec: AddressRecord, formatted: str, ptype: str, field_values: dict[str, str]) -> list:
    return [
        formatted,
        rec.get("flat_type") or "",
        rec.get("flat_number") or "",
        rec.get("level_type") or "",
        rec.get("level_number") or "",
        rec.get("lot_number") or "",
        rec["street_number"],
        rec.get("street_number_last") or "",
        rec["street_name"],
        rec.get("street_type") or "",
        rec.get("street_suffix") or "",
        rec["suburb"],
        rec["state"],
        rec.get("postcode") or "",
        rec.get("building_name") or "",
        rec["source"],
        ptype,
        json.dumps(field_values, separators=(",", ":")),
    ]


class CsvWriter:
    def __init__(self, path: str) -> None:
        if dirpart := os.path.dirname(path):
            os.makedirs(dirpart, exist_ok=True)
        self._file = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(OUTPUT_COLUMNS)
        self.rows_written = 0

    def write(self, rows: list[list]) -> None:
        self._writer.writerows(rows)
        self.rows_written += len(rows)

    def close(self) -> None:
        self._file.close()


class ParquetWriter:
    def __init__(self, path: str, batch_size: int = 100_000) -> None:
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            raise ImportError(
                "pyarrow is required for --parquet output. "
                "Install with: pip install pyarrow"
            )
        import pyarrow as pa
        import pyarrow.parquet as pq

        if dirpart := os.path.dirname(path):
            os.makedirs(dirpart, exist_ok=True)
        self._pa = pa
        self._batch_size = batch_size
        self._buffer: list[list] = []
        self._schema = pa.schema([(col, pa.string()) for col in OUTPUT_COLUMNS])
        # Open the writer immediately so the file exists from the start
        self._writer = pq.ParquetWriter(path, self._schema)
        self.rows_written = 0

    def write(self, rows: list[list]) -> None:
        self._buffer.extend(rows)
        if len(self._buffer) >= self._batch_size:
            self._flush()

    def _flush(self) -> None:
        if not self._buffer:
            return
        arrays = [
            self._pa.array([row[i] for row in self._buffer], type=self._pa.string())
            for i in range(len(OUTPUT_COLUMNS))
        ]
        table = self._pa.table(
            {col: arr for col, arr in zip(OUTPUT_COLUMNS, arrays)},
            schema=self._schema,
        )
        self._writer.write_table(table)
        self.rows_written += len(self._buffer)
        self._buffer.clear()

    def close(self) -> None:
        self._flush()
        self._writer.close()


# ---------------------------------------------------------------------------
# Test mode — evaluate trained model against generated permutations
# ---------------------------------------------------------------------------

_ANSI_STRIP = re.compile(r"\033\[[0-9;]*m")

# ANSI colour / cursor helpers
_A_BOLD     = "\033[1m"
_A_DIM      = "\033[2m"
_A_GREEN    = "\033[32m"
_A_RED      = "\033[31m"
_A_YELLOW   = "\033[33m"
_A_CYAN     = "\033[36m"
_A_RESET    = "\033[0m"
_A_HIDE_CUR = "\033[?25l"
_A_SHOW_CUR = "\033[?25h"

# Fields compared between model output and permutation field_values.
# lot_keyword excluded — it is a display-only training label, not a model output field.
TEST_COMPARE_FIELDS: list[str] = [
    "building_name",
    "unit_type", "unit_number",
    "level_type", "level_number",
    "lot_number",
    "street_number", "street_number_last",
    "street_name", "street_type", "street_suffix",
    "suburb", "state", "postcode",
]

TEST_CSV_COLUMNS: list[str] = (
    ["formatted_address", "permutation_type", "overall_pass", "failed_fields"]
    + [f"expected_{f}" for f in TEST_COMPARE_FIELDS]
    + [f"got_{f}" for f in TEST_COMPARE_FIELDS]
)

_DASH_W  = 78           # total dashboard width including borders
_DASH_IW = _DASH_W - 2  # inner width between ║ characters


def _vlen(s: str) -> int:
    """Visible string length — strips ANSI escape codes before measuring."""
    return len(_ANSI_STRIP.sub("", s))


def _rpad(s: str, width: int) -> str:
    """Right-pad s so its visible length equals width."""
    return s + " " * max(0, width - _vlen(s))


def _bar(frac: float, w: int = 16) -> str:
    n = round(max(0.0, min(1.0, frac)) * w)
    return "█" * n + "░" * (w - n)


def _pct(n: int, d: int) -> str:
    return f"{100 * n / d:5.1f}%" if d else "     —"


def compare_address(
    expected: dict[str, str],
    got: dict[str, str | None],
) -> tuple[bool, list[str], dict[str, bool]]:
    """Compare model output against the expected field_values from a permutation.

    An empty string in expected means the field should be absent from the output.

    Returns:
        (overall_pass, list_of_failed_field_names, per_field_pass_dict)
    """
    field_results: dict[str, bool] = {}
    for field in TEST_COMPARE_FIELDS:
        exp    = (expected.get(field) or "").strip().lower()
        actual = (got.get(field) or "").strip().lower()
        field_results[field] = exp == actual
    failed = [f for f, ok in field_results.items() if not ok]
    return not failed, failed, field_results


class LiveDashboard:
    """ANSI-rewriting terminal dashboard for real-time test progress.

    Overwrites its own output on every refresh — no external libraries needed.
    Refresh rate is governed by _UPDATE_EVERY so terminal I/O never bottlenecks
    the parser loop.
    """

    _MAX_FAILURES = 6   # recent-failures ring buffer depth
    _UPDATE_EVERY = 3   # re-render every N permutations

    def __init__(self, total_perms_hint: int | None = None) -> None:
        self.total_perms  = 0
        self.pass_count   = 0
        self.fail_count   = 0
        self.source_count = 0
        # Per-field stats (only for perms where the field is expected non-empty)
        self.field_total: dict[str, int] = defaultdict(int)
        self.field_pass:  dict[str, int] = defaultdict(int)
        # False positives: model predicted a value but expected was empty
        self.field_fp: dict[str, int] = defaultdict(int)
        self.recent_failures: deque[tuple] = deque(maxlen=self._MAX_FAILURES)
        self._start    = time.monotonic()
        self._rendered = 0   # number of lines written in last render pass
        self._hint     = total_perms_hint
        sys.stdout.write(_A_HIDE_CUR)
        sys.stdout.flush()

    def record(
        self,
        formatted: str,
        ptype: str,
        passed: bool,
        failed_fields: list[str],
        field_results: dict[str, bool],
        expected: dict[str, str],
        got: dict[str, str | None],
    ) -> None:
        self.total_perms += 1
        if passed:
            self.pass_count += 1
        else:
            self.fail_count += 1
            self.recent_failures.append(
                (formatted, ptype, failed_fields, dict(expected), dict(got))
            )

        for f in TEST_COMPARE_FIELDS:
            exp_v = (expected.get(f) or "").strip()
            got_v = (got.get(f) or "").strip()
            if exp_v:
                self.field_total[f] += 1
                if field_results[f]:
                    self.field_pass[f] += 1
            elif got_v:
                # Model hallucinated a value that wasn't in the address
                self.field_fp[f] += 1

        if self.total_perms % self._UPDATE_EVERY == 0:
            self._render()

    def new_source(self) -> None:
        self.source_count += 1

    # ── rendering ──────────────────────────────────────────────────────────

    def _row(self, content: str) -> str:
        return "║" + _rpad(content, _DASH_IW) + "║"

    def _hr(self) -> str:
        return "╠" + "═" * _DASH_IW + "╣"

    def _render(self) -> None:  # noqa: C901
        elapsed   = time.monotonic() - self._start
        speed     = self.total_perms / elapsed if elapsed > 0 else 0.0
        pass_rate = self.pass_count / self.total_perms if self.total_perms else 0.0

        rows: list[str] = []

        # ── header ────────────────────────────────────────────────────────
        ts = time.strftime("%H:%M:%S")
        rows.append("╔" + "═" * _DASH_IW + "╗")
        rows.append(self._row(
            f"  {_A_BOLD}{_A_CYAN}ADDRESS PARSER TEST{_A_RESET}  —  {ts}"
        ))
        rows.append(self._hr())

        # ── progress / speed ──────────────────────────────────────────────
        eta = ""
        if self._hint and speed > 0:
            rem = max(0, (self._hint - self.total_perms) / speed)
            eta = f"  ·  ETA {rem:.0f}s"
        rows.append(self._row(
            f"  Perms  {self.total_perms:,} tested"
            f"  ({self.source_count} src)  ·  {speed:,.0f}/s{eta}"
        ))

        # ── pass/fail bar ─────────────────────────────────────────────────
        pr_c = (
            _A_GREEN  if pass_rate >= 0.99 else
            _A_YELLOW if pass_rate >= 0.95 else
            _A_RED
        )
        rows.append(self._row(
            f"  Result  {pr_c}[{_bar(pass_rate)}]{_A_RESET}  {pass_rate * 100:5.1f}%"
            f"  {_A_GREEN}✓ {self.pass_count:,}{_A_RESET}"
            f"  {_A_RED}✗ {self.fail_count:,}{_A_RESET}"
        ))
        rows.append(self._hr())

        # ── field accuracy ────────────────────────────────────────────────
        rows.append(self._row(f"  {_A_BOLD}FIELD ACCURACY{_A_RESET}"))
        active = [
            f for f in TEST_COMPARE_FIELDS
            if self.field_total.get(f, 0) or self.field_fp.get(f, 0)
        ]
        if not active:
            rows.append(self._row(f"  {_A_DIM}(waiting for data…){_A_RESET}"))
        else:
            for f in active:
                total = self.field_total.get(f, 0)
                ok    = self.field_pass.get(f, 0)
                fp    = self.field_fp.get(f, 0)
                fp_s  = f"  {_A_RED}fp:{fp}{_A_RESET}" if fp else ""
                if total:
                    frac = ok / total
                    bc   = (
                        _A_GREEN  if frac >= 0.99 else
                        _A_YELLOW if frac >= 0.95 else
                        _A_RED
                    )
                    rows.append(self._row(
                        f"  {f:<18}  {bc}[{_bar(frac)}]{_A_RESET}"
                        f"  {_pct(ok, total)}  {ok:>5}/{total:<5}{fp_s}"
                    ))
                else:
                    rows.append(self._row(
                        f"  {f:<18}  {'─' * 16}  (fp only){fp_s}"
                    ))
        rows.append(self._hr())

        # ── recent failures ───────────────────────────────────────────────
        rows.append(self._row(f"  {_A_BOLD}RECENT FAILURES{_A_RESET}"))
        if not self.recent_failures:
            rows.append(self._row(f"  {_A_DIM}(none yet){_A_RESET}"))
        else:
            for (fmt, ptype, failed, exp_d, got_d) in self.recent_failures:
                diffs: list[str] = []
                for ff in failed[:2]:
                    e = (exp_d.get(ff) or "")
                    g = (got_d.get(ff) or "")
                    if e and not g:
                        diffs.append(f"{ff}→∅")
                    elif g and not e:
                        diffs.append(f"∅→{ff}='{g}'")
                    else:
                        diffs.append(f"{ff}:'{e}'≠'{g}'")
                if len(failed) > 2:
                    diffs.append(f"+{len(failed) - 2} more")
                addr_s = (fmt[:27] + "…") if len(fmt) > 28 else fmt
                rows.append(self._row(
                    f"  {_A_RED}✗{_A_RESET} [{ptype[:10]:<10}]"
                    f" {addr_s!r:<31}  {'  '.join(diffs)}"
                ))

        rows.append("╚" + "═" * _DASH_IW + "╝")

        # ── overwrite previous render ─────────────────────────────────────
        if self._rendered:
            sys.stdout.write(f"\033[{self._rendered}A")
        for r in rows:
            sys.stdout.write(f"\033[2K\r{r}\n")
        sys.stdout.flush()
        self._rendered = len(rows)

    def finalize(self) -> None:
        """Force a final render, restore cursor, emit summary log line."""
        self._render()
        elapsed = time.monotonic() - self._start
        sys.stdout.write(_A_SHOW_CUR + "\n")
        sys.stdout.flush()
        log.info(
            "Test complete: %d perms  %d sources  pass %.2f%%  %.1fs",
            self.total_perms,
            self.source_count,
            100 * self.pass_count / self.total_perms if self.total_perms else 0.0,
            elapsed,
        )


def run_test_mode(
    stream: Iterator[AddressRecord],
    lookups: AbbrevLookups,
    address_parser: object,
    args: argparse.Namespace,
) -> None:
    """Evaluate the trained model against generated address permutations.

    For each source address: generate all permutations, run each through the
    parser, compare output to the expected field_values dict. Writes a CSV
    with one row per permutation and renders a live ANSI dashboard while running.
    """
    output_path = args.output
    if dirpart := os.path.dirname(output_path):
        os.makedirs(dirpart, exist_ok=True)

    total_hint = args.limit * args.max_perms if args.limit else None
    rng = random.Random(args.seed)
    dash = LiveDashboard(total_perms_hint=total_hint)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(TEST_CSV_COLUMNS)

        for rec in stream:
            dash.new_source()
            perms = generate_permutations(
                rec,
                lookups,
                max_perms=args.max_perms,
                include_noisy=args.noisy,
                rng=rng,
            )
            for formatted, ptype, field_values in perms:
                got = address_parser.parse(formatted)  # type: ignore[attr-defined]
                # Normalise fused expected values (e.g. unit_number="Unit59" → unit_type="Unit",
                # unit_number="59") so both sides of compare_address use the same representation.
                expected = split_fused_tokens(dict(field_values))  # type: ignore[attr-defined]
                passed, failed_fields, field_results = compare_address(expected, got)
                dash.record(formatted, ptype, passed, failed_fields, field_results, expected, got)
                writer.writerow([
                    formatted,
                    ptype,
                    "1" if passed else "0",
                    ",".join(failed_fields),
                    *[(expected.get(f) or "") for f in TEST_COMPARE_FIELDS],
                    *[(got.get(f) or "")      for f in TEST_COMPARE_FIELDS],
                ])

    dash.finalize()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Australian address training data from GNAF."
    )
    parser.add_argument("--output", required=True, help="Output file path (.csv or .parquet)")
    parser.add_argument(
        "--states", nargs="+", default=None,
        help="Filter by state(s) (e.g. QLD NSW VIC). Default: all."
    )
    parser.add_argument(
        "--training", action="store_true",
        help=(
            f"Generate full training dataset ({_TRAINING_TOTAL:,} source addresses). "
            "Covers every flat type, level type, street suffix, and street type; "
            "balanced across all states. Mutually exclusive with --limit and --gnaf-pid."
        ),
    )
    parser.add_argument("--limit", type=int, default=None, help="Max source addresses to process")
    parser.add_argument("--gnaf-pid", default=None, help="Generate for a single GNAF address_detail_pid only")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--max-perms", type=int, default=40, help="Max permutations per address")
    parser.add_argument("--noisy", action="store_true", help="Include noisy/dirty permutations")
    parser.add_argument("--parquet", action="store_true", help="Output Parquet instead of CSV")
    parser.add_argument("--batch-size", type=int, default=5000, help="DB cursor batch size")
    parser.add_argument(
        "--test", action="store_true",
        help=(
            "Evaluate the trained model: generate permutations, parse each through the "
            "address parser, and write a test-report CSV to --output. "
            "Use ADDRESS_MODEL_DIR env var to override model path (default: training/model). "
            "Compatible with --limit, --states, --seed, --max-perms, --noisy, --gnaf-pid. "
            "Mutually exclusive with --training and --parquet."
        ),
    )
    args = parser.parse_args()

    if args.test and args.training:
        parser.error("--test cannot be combined with --training")

    rng = random.Random(args.seed)

    log.info("Connecting to database…")
    conn = get_connection()

    log.info("Loading GNAF authority tables…")
    street_type_aut, flat_type_aut, level_type_aut, street_suffix_aut = load_authority_tables(conn)

    lookups = AbbrevLookups.build(
        street_type_aut=street_type_aut,
        flat_type_aut=flat_type_aut,
        level_type_aut=level_type_aut,
        street_suffix_aut=street_suffix_aut,
    )
    log.info("AbbrevLookups built.")

    log.info("Loading corner (CD) aliases…")
    corner_aliases = load_corner_aliases(conn)

    states = [s.upper() for s in args.states] if args.states else [
        "QLD", "NSW", "VIC", "SA", "WA", "TAS", "NT", "ACT"
    ]

    if args.test:
        model_dir = os.getenv("ADDRESS_MODEL_DIR", "training/model")
        try:
            # Lazy import — torch/transformers not always installed in this venv
            from service.address_parser import AddressParser, split_fused_tokens
        except ImportError as exc:
            conn.close()
            sys.exit(f"--test requires torch and transformers to be installed: {exc}")
        log.info("Loading address parser from %s…", model_dir)
        try:
            address_parser = AddressParser(model_dir)
        except Exception as exc:
            conn.close()
            sys.exit(f"Failed to load model from {model_dir!r}: {exc}")
        log.info("Model ready.")
        stream = stream_gnaf(
            conn, states, args.limit,
            street_type_aut, flat_type_aut, level_type_aut, street_suffix_aut,
            corner_aliases=corner_aliases,
            seed=args.seed,
            batch_size=args.batch_size,
            gnaf_pid=args.gnaf_pid,
        )
        try:
            run_test_mode(stream, lookups, address_parser, args)
        finally:
            conn.close()
        return

    output_path = args.output
    writer: CsvWriter | ParquetWriter
    if args.parquet:
        writer = ParquetWriter(output_path)
    else:
        writer = CsvWriter(output_path)

    source_count = 0
    log_interval = 10_000
    # Global dedup: multiple GNAF records can share the same street address
    # (e.g. different lots on the same road) and produce identical formatted strings.
    seen_formatted: set[str] = set()

    def process_stream(stream: Iterator[AddressRecord]) -> None:
        nonlocal source_count
        for rec in stream:
            perms = generate_permutations(
                rec,
                lookups,
                max_perms=args.max_perms,
                include_noisy=args.noisy,
                rng=rng,
            )
            rows = [
                _row_to_output(rec, fmt, ptype, fvals)
                for fmt, ptype, fvals in perms
                if fmt not in seen_formatted
            ]
            seen_formatted.update(r[0] for r in rows)
            writer.write(rows)
            source_count += 1
            if source_count % log_interval == 0:
                log.info(
                    "Processed %d source addresses → %d output rows",
                    source_count, writer.rows_written,
                )

    try:
        if args.training:
            if args.limit or args.gnaf_pid:
                parser.error("--training cannot be combined with --limit or --gnaf-pid")
            log.info(
                "Training mode: %d source addresses, all states, full type coverage.",
                _TRAINING_TOTAL,
            )
            process_stream(stream_gnaf_training(
                conn, states,
                street_type_aut, flat_type_aut, level_type_aut, street_suffix_aut,
                corner_aliases=corner_aliases,
                seed=args.seed,
            ))
        else:
            log.info("Streaming GNAF (states=%s, limit=%s, pid=%s)…", states, args.limit, args.gnaf_pid)
            process_stream(stream_gnaf(
                conn, states, args.limit,
                street_type_aut, flat_type_aut, level_type_aut, street_suffix_aut,
                corner_aliases=corner_aliases,
                seed=args.seed,
                batch_size=args.batch_size,
                gnaf_pid=args.gnaf_pid,
            ))
    finally:
        writer.close()
        conn.close()

    log.info(
        "Done. %d source addresses → %d output rows → %s",
        source_count, writer.rows_written, output_path,
    )


if __name__ == "__main__":
    main()
