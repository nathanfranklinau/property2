"""Address parser benchmark.

Runs all available adapters against:
  1. The 41 labeled test cases from test_address_parsing.py (true ground truth)
  2. All distinct GC DA location_address values  (8107 rows)
  3. All Brisbane DA location_address values     (18 rows)

Scoring against labeled cases is "field-level exact match":
  - street_number, street_name, street_type, unit_type, unit_number
  - suburb and postcode where present in ground truth

Scoring against DB data ("full-dataset"):
  - "Parse rate" = fraction of real-street-address rows where street_number extracted
  - "Field extraction rate" per field
  - Comparison vs custom_regex parser

Usage (from data-layer/):
    venv/bin/python addr_eval/benchmark.py [--no-deepparse] [--no-addressnet]

Output: addr_eval/report.md
"""

import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict

# ── Path setup ──────────────────────────────────────────────────────────────

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "import"))

from adapters.base import ParsedResult, empty_result
from adapters.custom import parse_gc as custom_gc_parse, parse_bris as custom_bris_parse, NAME as CUSTOM_NAME
from adapters.au_addr import parse as au_parse, NAME as AU_NAME, AVAILABLE as AU_AVAILABLE
import adapters.deepparse_adapter as deepparse_mod
import adapters.addressnet_adapter as addressnet_mod


# ── Labeled ground truth (from test_address_parsing.py) ─────────────────────

# (input, expected_dict)  — only fields listed here are evaluated
_LABELED_GC: list[tuple[str | None, dict]] = [
    ("7 Mornington Court",           {"street_number": "7",       "street_name": "Mornington",            "street_type": "Court"}),
    ("635 Gold Coast Springbrook Road", {"street_number": "635",  "street_name": "Gold Coast Springbrook","street_type": "Road"}),
    ("9 Twenty Fourth Avenue",        {"street_number": "9",       "street_name": "Twenty Fourth",         "street_type": "Avenue"}),
    ("1179 Gold Coast Highway",       {"street_number": "1179",    "street_name": "Gold Coast",            "street_type": "Highway"}),
    ("88 Old Burleigh Road",          {"street_number": "88",      "street_name": "Old Burleigh",          "street_type": "Road"}),
    ("2 East Lane",                   {"street_number": "2",       "street_name": "East",                  "street_type": "Lane"}),
    ("11 Transport Street",           {"street_number": "11",      "street_name": "Transport",             "street_type": "Street"}),
    ("1293-1299 Gold Coast Highway",  {"street_number": "1293-1299","street_name": "Gold Coast",           "street_type": "Highway"}),
    ("UNIT 3, 14-16 Kohl Street",     {"unit_type": "UNIT", "unit_number": "3", "street_number": "14-16", "street_name": "Kohl",    "street_type": "Street"}),
    ("UNIT 2, 19 Venice Street",      {"unit_type": "UNIT", "unit_number": "2", "street_number": "19",    "street_name": "Venice",  "street_type": "Street"}),
    ("Unit 1104, 48 Ventura Road",    {"unit_type": "UNIT", "unit_number": "1104", "street_number": "48", "street_name": "Ventura", "street_type": "Road"}),
    ("Unit 702, 122 Surf Parade",     {"unit_type": "UNIT", "unit_number": "702", "street_number": "122", "street_name": "Surf",    "street_type": "Parade"}),
    ("Unit 1205, 2 Athena Boulevard", {"unit_type": "UNIT", "unit_number": "1205","street_number": "2",   "street_name": "Athena",  "street_type": "Boulevard"}),
    ("UNIT 5, 166 The Esplanade",     {"unit_type": "UNIT", "unit_number": "5",   "street_number": "166", "street_name": "The",     "street_type": "Esplanade"}),
    ("Unit 119, 370 Gainsborough Drive", {"unit_type": "UNIT","unit_number": "119","street_number": "370","street_name": "Gainsborough","street_type": "Drive"}),
    ("Lot 58 Gold Coast Highway",     {"street_number": "58",      "street_name": "Gold Coast",            "street_type": "Highway"}),
    ("Lot 2 Hope Island Road",        {"street_number": "2",       "street_name": "Hope Island",           "street_type": "Road"}),
    ("Lot 600 Ross Street",           {"street_number": "600",     "street_name": "Ross",                  "street_type": "Street"}),
    ("Lot 47 Shipper Drive",          {"street_number": "47",      "street_name": "Shipper",               "street_type": "Drive"}),
    ("Lot 800 SP348540",              {"street_number": None, "street_name": None, "street_type": None}),
    ("Lot 1 RP152544",                {"street_number": None, "street_name": None, "street_type": None}),
    ("Lot 303 SP289809",              {"street_number": None, "street_name": None, "street_type": None}),
    ("Lot 10 WD3134",                 {"street_number": None, "street_name": None, "street_type": None}),
    ("Lot 401 SP313661, Lot 47 Shipper Drive, COOMERA  QLD  4209",
     {"street_number": "47", "street_name": "Shipper", "street_type": "Drive", "suburb": "Coomera", "postcode": "4209"}),
    ("Lot 74 SP253434, 36 Buckingham Road, MAUDSLAND  QLD  4210",
     {"street_number": "36", "street_name": "Buckingham", "street_type": "Road", "suburb": "Maudsland", "postcode": "4210"}),
    ("Lot 24 B70832, 107 Golden Four Drive, BILINGA  QLD  4225",
     {"street_number": "107", "street_name": "Golden Four", "street_type": "Drive", "suburb": "Bilinga", "postcode": "4225"}),
    ("Lot 81 RP139722, 81 Clear Island Road, BROADBEACH WATERS  QLD  4218",
     {"street_number": "81", "street_name": "Clear Island", "street_type": "Road", "suburb": "Broadbeach Waters", "postcode": "4218"}),
    ("Lot 29 GTP3991, UNIT 29, 96 Galleon Way, CURRUMBIN WATERS  QLD  4223",
     {"unit_type": "UNIT","unit_number": "29","street_number": "96","street_name": "Galleon","street_type": "Way","suburb": "Currumbin Waters","postcode": "4223"}),
    ("635 Gold Coast Springbrook Road, MUDGEERABA QLD 4213",
     {"street_number": "635","street_name": "Gold Coast Springbrook","street_type": "Road","suburb": "Mudgeeraba","postcode": "4213"}),
    ("2 River Terrace, HOPE ISLAND QLD 4212",
     {"street_number": "2","street_name": "River","street_type": "Terrace","suburb": "Hope Island","postcode": "4212"}),
    ("UNIT 4, 19 Santa Barbara Road, HOPE ISLAND QLD 4212",
     {"unit_type": "UNIT","unit_number": "4","street_number": "19","street_name": "Santa Barbara","street_type": "Road","suburb": "Hope Island","postcode": "4212"}),
    (None,  {"street_number": None, "street_name": None, "street_type": None}),
    ("",    {"street_number": None, "street_name": None, "street_type": None}),
]

_LABELED_BRIS: list[tuple[str | None, dict]] = [
    ("4 TANDOOR ST MORNINGSIDE  QLD  4170",
     {"street_number": "4",   "street_name": "Tandoor",      "street_type": "Street", "suburb": "Morningside",      "postcode": "4170"}),
    ("8 HADDOCK ST WINDSOR  QLD  4030",
     {"street_number": "8",   "street_name": "Haddock",      "street_type": "Street", "suburb": "Windsor",          "postcode": "4030"}),
    ("89 DAYS RD GRANGE  QLD  4051",
     {"street_number": "89",  "street_name": "Days",         "street_type": "Road",   "suburb": "Grange",           "postcode": "4051"}),
    ("25 LANDSBORO AVE BOONDALL  QLD  4034",
     {"street_number": "25",  "street_name": "Landsboro",    "street_type": "Avenue", "suburb": "Boondall",         "postcode": "4034"}),
    ("68 NYLETA ST COOPERS PLAINS  QLD  4108",
     {"street_number": "68",  "street_name": "Nyleta",       "street_type": "Street", "suburb": "Coopers Plains",   "postcode": "4108"}),
    ("24 DART ST AUCHENFLOWER  QLD  4066",
     {"street_number": "24",  "street_name": "Dart",         "street_type": "Street", "suburb": "Auchenflower",     "postcode": "4066"}),
    ("136 LECKIE RD KEDRON  QLD  4031",
     {"street_number": "136", "street_name": "Leckie",       "street_type": "Road",   "suburb": "Kedron",           "postcode": "4031"}),
    ("1 AQUAMARINE ST HOLLAND PARK  QLD  4121",
     {"street_number": "1",   "street_name": "Aquamarine",   "street_type": "Street", "suburb": "Holland Park",     "postcode": "4121"}),
    ("184 COOPERS CAMP RD ASHGROVE  QLD  4060",
     {"street_number": "184", "street_name": "Coopers Camp", "street_type": "Road",   "suburb": "Ashgrove",         "postcode": "4060"}),
    ("115 NEWNHAM RD MOUNT GRAVATT EAST  QLD  4122",
     {"street_number": "115", "street_name": "Newnham",      "street_type": "Road",   "suburb": "Mount Gravatt East","postcode": "4122"}),
    ("2A PERRY ST HAMILTON  QLD  4007",
     {"street_number": "2A",  "street_name": "Perry",        "street_type": "Street", "suburb": "Hamilton",         "postcode": "4007"}),
    (None, {"street_number": None, "street_name": None, "street_type": None}),
    ("",   {"street_number": None, "street_name": None, "street_type": None}),
]


# ── Scoring helpers ───────────────────────────────────────────────────────────

EVAL_FIELDS = ["street_number", "street_name", "street_type", "unit_type",
               "unit_number", "suburb", "postcode"]


def _normalise(v: str | None) -> str | None:
    """Case-insensitive, strip comparison."""
    return v.strip().lower() if v else None


def score_against_truth(result: ParsedResult, truth: dict) -> dict[str, bool]:
    """Return per-field bool: True = correct, False = wrong, None = not in truth."""
    scores: dict[str, bool | None] = {}
    for field in EVAL_FIELDS:
        if field not in truth:
            continue
        expected = _normalise(truth[field])
        got = _normalise(result.get(field))
        scores[field] = (expected == got)
    return scores


def score_against_db(result: ParsedResult, db_row: dict) -> dict[str, bool]:
    """Compare result vs DB-stored parsed values."""
    scores: dict[str, bool | None] = {}
    for field in EVAL_FIELDS:
        db_val = db_row.get(field)
        res_val = result.get(field)
        if db_val is None and res_val is None:
            scores[field] = True
        elif db_val is None or res_val is None:
            scores[field] = False
        else:
            scores[field] = _normalise(db_val) == _normalise(res_val)
    return scores


# ── CSV loading ───────────────────────────────────────────────────────────────

def load_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Adapter registry ──────────────────────────────────────────────────────────

def build_adapters(args: argparse.Namespace) -> list[dict]:
    """Return list of adapter dicts: {name, gc_fn, bris_fn, available}."""
    adapters = []

    # Custom regex — always available, two separate parse functions
    adapters.append({
        "name": CUSTOM_NAME,
        "gc_fn":   custom_gc_parse,
        "bris_fn": custom_bris_parse,
        "available": True,
    })

    # au-address-parser — parses standard AU addresses; fails on bare lot refs
    adapters.append({
        "name": AU_NAME,
        "gc_fn":   au_parse,
        "bris_fn": au_parse,
        "available": AU_AVAILABLE,
    })

    # deepparse — neural model, requires PyTorch >= 2.4
    if not args.no_deepparse:
        print("Loading deepparse model (may download ~50 MB on first run)...")
        t0 = time.time()
        deepparse_mod._load_parser()
        elapsed = time.time() - t0
        print(f"  deepparse {'loaded' if deepparse_mod.AVAILABLE else 'UNAVAILABLE: ' + str(deepparse_mod._load_error)} ({elapsed:.1f}s)")
        adapters.append({
            "name": deepparse_mod.NAME,
            "gc_fn":   deepparse_mod.parse,
            "bris_fn": deepparse_mod.parse,
            "available": deepparse_mod.AVAILABLE,
        })

    # address-net — GNAF-trained, needs TensorFlow
    if not args.no_addressnet:
        print("Loading address-net model...")
        t0 = time.time()
        addressnet_mod._load()
        elapsed = time.time() - t0
        print(f"  address-net {'loaded' if addressnet_mod.AVAILABLE else 'UNAVAILABLE: ' + str(addressnet_mod._load_error)} ({elapsed:.1f}s)")
        adapters.append({
            "name": addressnet_mod.NAME,
            "gc_fn":   addressnet_mod.parse,
            "bris_fn": addressnet_mod.parse,
            "available": addressnet_mod.AVAILABLE,
        })

    return adapters


# ── Main evaluation ───────────────────────────────────────────────────────────

def run_labeled(adapters: list[dict], labeled: list[tuple], parse_key: str) -> dict:
    """Run all adapters against labeled cases. Returns {adapter_name: {field: [correct, total]}}"""
    results: dict[str, dict] = {}
    for adapter in adapters:
        fn = adapter[parse_key]
        field_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        wrong_examples: list[dict] = []
        for addr, truth in labeled:
            result = fn(addr)
            scores = score_against_truth(result, truth)
            for field, correct in scores.items():
                field_counts[field][1] += 1
                if correct:
                    field_counts[field][0] += 1
                elif len(wrong_examples) < 10:
                    wrong_examples.append({
                        "addr": addr,
                        "field": field,
                        "expected": truth.get(field),
                        "got": result.get(field),
                    })
        results[adapter["name"]] = {
            "field_counts": dict(field_counts),
            "wrong_examples": wrong_examples,
            "available": adapter["available"],
        }
    return results


def run_full_dataset(adapters: list[dict], rows: list[dict], parse_key: str) -> dict:
    """Run all adapters against full CSV data. Returns per-adapter stats."""
    results: dict[str, dict] = {}

    for adapter in adapters:
        if not adapter["available"]:
            results[adapter["name"]] = {"available": False, "n": 0}
            continue

        fn = adapter[parse_key]
        n_total = len(rows)
        field_extracted: dict[str, int] = defaultdict(int)
        n_street_parsed = 0    # has street_number AND street_name
        n_bare_lot_correct = 0 # bare lot refs (db street_name NULL) where parser returns null street_number
        n_bare_lot = 0
        n_street_addr = 0      # rows where db has street_name (real address)
        n_street_addr_parsed = 0  # real addresses where parser gets street_number

        # Compare vs custom_regex for agreement
        custom_key = CUSTOM_NAME
        field_agree: dict[str, int] = defaultdict(int)
        field_agree_total: dict[str, int] = defaultdict(int)

        print(f"  Running {adapter['name']} on {n_total} rows... ", end="", flush=True)
        t0 = time.time()

        for row in rows:
            addr = row.get("location_address")
            db_street_name = row.get("street_name") or None

            result = fn(addr)

            # Field extraction counts
            for field in EVAL_FIELDS:
                if result.get(field):
                    field_extracted[field] += 1

            # Parse rate
            if result.get("street_number") and result.get("street_name"):
                n_street_parsed += 1

            # Bare lot refs vs real addresses
            if db_street_name:
                n_street_addr += 1
                if result.get("street_number"):
                    n_street_addr_parsed += 1
            else:
                n_bare_lot += 1
                # Correct if parser also returns no street_number (or no street_name)
                if not result.get("street_number") or not result.get("street_name"):
                    n_bare_lot_correct += 1

        elapsed = time.time() - t0
        print(f"{elapsed:.1f}s")

        results[adapter["name"]] = {
            "available": True,
            "n": n_total,
            "n_street_parsed": n_street_parsed,
            "n_street_addr": n_street_addr,
            "n_street_addr_parsed": n_street_addr_parsed,
            "n_bare_lot": n_bare_lot,
            "n_bare_lot_correct": n_bare_lot_correct,
            "field_extracted": dict(field_extracted),
            "elapsed_s": round(elapsed, 1),
        }

    return results


# ── Report generation ─────────────────────────────────────────────────────────

def pct(num: int, den: int) -> str:
    if den == 0:
        return "n/a"
    return f"{100 * num / den:.1f}%"


def write_report(
    adapters: list[dict],
    labeled_gc: dict,
    labeled_bris: dict,
    full_gc: dict,
    full_bris: dict,
    out_path: str,
) -> None:
    lines = []

    def h1(s: str) -> None: lines.append(f"\n# {s}\n")
    def h2(s: str) -> None: lines.append(f"\n## {s}\n")
    def h3(s: str) -> None: lines.append(f"\n### {s}\n")
    def row(*cols: str) -> None: lines.append("| " + " | ".join(str(c) for c in cols) + " |")
    def sep(*n: int) -> None: lines.append("| " + " | ".join("-" * max(k, 3) for k in n) + " |")

    h1("Address Parser Benchmark Report")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # ── Adapter availability ──
    h2("Parser Availability")
    row("Parser", "Status", "Notes")
    sep(20, 15, 40)
    notes = {
        CUSTOM_NAME:        "Custom regex — GC (ePathway) + Brisbane (Development.i) formats",
        AU_NAME:            "au-address-parser — standard AU format; requires state code in address",
        deepparse_mod.NAME: "deepparse bpemb — neural model; PyTorch 2.2+ works despite transformers warning",
        addressnet_mod.NAME:"address-net — GNAF-trained neural model, requires TensorFlow (archived Feb 2025)",
    }
    for adapter in adapters:
        status = "✅ Available" if adapter["available"] else "❌ Unavailable"
        note = notes.get(adapter["name"], "")
        row(adapter["name"], status, note)

    # ── Labeled test accuracy ──
    h2("Accuracy on Labeled Test Cases (Ground Truth)")
    lines.append(f"_These {len(_LABELED_GC)} GC + {len(_LABELED_BRIS)} Brisbane cases were manually verified._\n")

    for section, labeled_results, n_cases, label in [
        ("Gold Coast ePathway format", labeled_gc, len(_LABELED_GC), "GC"),
        ("Brisbane Development.i format", labeled_bris, len(_LABELED_BRIS), "Brisbane"),
    ]:
        h3(section)
        lines.append(f"_n = {n_cases} cases_\n")
        row("Parser", "Overall", "street_number", "street_name", "street_type", "unit_type", "unit_number", "suburb", "postcode")
        sep(20, 9, 13, 11, 11, 9, 11, 8, 9)
        for adapter in adapters:
            name = adapter["name"]
            if name not in labeled_results:
                continue
            stats = labeled_results[name]
            if not stats["available"]:
                row(name, "❌ N/A", *["—"] * 7)
                continue
            fc = stats["field_counts"]
            # Overall: % of all field-checks correct
            total_correct = sum(v[0] for v in fc.values())
            total_all = sum(v[1] for v in fc.values())
            overall = pct(total_correct, total_all)
            cells = [name, overall]
            for field in ["street_number", "street_name", "street_type", "unit_type", "unit_number", "suburb", "postcode"]:
                if field in fc:
                    cells.append(pct(fc[field][0], fc[field][1]))
                else:
                    cells.append("—")
            row(*cells)

    # ── Wrong examples ──
    h2("Labeled Test: Parse Errors (first 5 per parser)")
    for section, labeled_results, label in [
        ("Gold Coast", labeled_gc, "GC"),
        ("Brisbane", labeled_bris, "Bris"),
    ]:
        h3(section)
        for adapter in adapters:
            name = adapter["name"]
            if name not in labeled_results:
                continue
            stats = labeled_results[name]
            if not stats.get("available"):
                lines.append(f"**{name}**: ❌ unavailable — skipped\n")
                continue
            examples = stats.get("wrong_examples", [])
            if not examples:
                lines.append(f"**{name}**: all labeled cases correct ✅\n")
                continue
            lines.append(f"**{name}**:\n")
            for ex in examples[:5]:
                lines.append(f"  - `{ex['addr']}` → field `{ex['field']}`: expected `{ex['expected']!r}`, got `{ex['got']!r}`")
            lines.append("")

    # ── Full dataset stats ──
    h2("Full Dataset Statistics")

    for section, full_results, n_rows, label in [
        ("Gold Coast DA (8,107 distinct addresses)", full_gc, None, "GC"),
        ("Brisbane DA (18 addresses)", full_bris, None, "Brisbane"),
    ]:
        h3(section)
        row("Parser", "Available", "Total Rows", "Real Street Addrs", "Parse Rate (real)", "Bare Lot Correct", "Elapsed")
        sep(20, 9, 10, 17, 17, 16, 9)
        for adapter in adapters:
            name = adapter["name"]
            if name not in full_results:
                continue
            s = full_results[name]
            if not s.get("available"):
                row(name, "❌", "—", "—", "—", "—", "—")
                continue
            real = s["n_street_addr"]
            real_parsed = s["n_street_addr_parsed"]
            bare = s["n_bare_lot"]
            bare_correct = s["n_bare_lot_correct"]
            row(
                name,
                "✅",
                s["n"],
                real,
                pct(real_parsed, real),
                pct(bare_correct, bare),
                f"{s['elapsed_s']}s",
            )

    # ── Field extraction rates ──
    h2("Field Extraction Rates (Full Dataset)")
    lines.append("_% of addresses where each field was populated in parser output_\n")

    for section, full_results, label in [
        ("Gold Coast", full_gc, "GC"),
        ("Brisbane", full_bris, "Bris"),
    ]:
        h3(section)
        row("Parser", "street_number", "street_name", "street_type", "unit_type", "unit_number", "suburb", "postcode")
        sep(20, 13, 11, 11, 9, 11, 8, 9)
        for adapter in adapters:
            name = adapter["name"]
            if name not in full_results:
                continue
            s = full_results[name]
            if not s.get("available"):
                row(name, *["❌"] * 7)
                continue
            fe = s.get("field_extracted", {})
            n = s["n"]
            cells = [name]
            for field in ["street_number", "street_name", "street_type", "unit_type", "unit_number", "suburb", "postcode"]:
                cells.append(pct(fe.get(field, 0), n))
            row(*cells)

    # ── Summary & Recommendation ──
    h2("Summary & Recommendation")
    lines.append("""
| Parser | Strengths | Weaknesses |
|--------|-----------|-----------|
| **custom_regex** | Handles all GC-specific formats (bare lot refs, Lot+plan+address, ePathway variants); fast | Brittle to new formats; manual maintenance |
| **au_address_parser** | Clean AU standard addresses; no deps | Requires state code; fails on GC bare-format addresses |
| **deepparse_bpemb** | Neural approach; handles varied formats; suburb/postcode extraction | Street type folded into StreetName (needs post-processing split); heavy model download |
| **address_net** | Separate street_type field; trained on GNAF AU data | Archived (2025); TensorFlow dependency; old architecture |

**Recommendation:** For the GC DA use case, the custom_regex parser is best suited — it handles the GC-specific lot/plan formats, ePathway summary format, and the unit-prefix patterns that external libraries don't see. For a complementary "clean address" fallback (standard suburb+state+postcode format), au_address_parser adds value.
""")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nReport written → {out_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Address parser benchmark")
    parser.add_argument("--no-deepparse",   action="store_true", help="Skip deepparse")
    parser.add_argument("--no-addressnet",  action="store_true", help="Skip address-net")
    args = parser.parse_args()

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    out_path = os.path.join(os.path.dirname(__file__), "report.md")

    gc_rows   = load_csv(os.path.join(data_dir, "gc_addresses.csv"))
    bris_rows = load_csv(os.path.join(data_dir, "bris_addresses.csv"))
    print(f"Loaded {len(gc_rows)} GC rows, {len(bris_rows)} Brisbane rows")

    print("\nInitialising adapters...")
    adapters = build_adapters(args)

    # ── Labeled accuracy ──
    print("\nScoring labeled GC test cases...")
    labeled_gc_results = run_labeled(adapters, _LABELED_GC, "gc_fn")

    print("Scoring labeled Brisbane test cases...")
    labeled_bris_results = run_labeled(adapters, _LABELED_BRIS, "bris_fn")

    # ── Full dataset ──
    print("\nRunning full GC dataset...")
    full_gc_results = run_full_dataset(adapters, gc_rows, "gc_fn")

    print("Running full Brisbane dataset...")
    full_bris_results = run_full_dataset(adapters, bris_rows, "bris_fn")

    # ── Report ──
    write_report(adapters, labeled_gc_results, labeled_bris_results,
                 full_gc_results, full_bris_results, out_path)


if __name__ == "__main__":
    main()
