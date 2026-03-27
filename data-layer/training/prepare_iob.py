"""
prepare_iob.py — Convert address_training.parquet to a HuggingFace dataset with IOB2 labels.

For each row, aligns each field value to its character span in the formatted_address,
tokenizes with the DistilBERT tokenizer, and assigns token-level IOB2 labels.
Continuation subwords get label -100 (ignored during training loss computation).

Output: HuggingFace DatasetDict saved to training/data/iob_dataset/
  - train split: 95%
  - validation split: 5%
  - label_config.json: label names and id↔label mappings

Usage (run from data-layer/):
    python -m training.prepare_iob
    python -m training.prepare_iob --sample 50000   # quick test run
    python -m training.prepare_iob --input training/data/address_training.parquet \
                                   --output training/data/iob_dataset
"""

import argparse
import json
import logging
import re
import shutil
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datasets import DatasetDict, load_dataset
from transformers import AutoTokenizer

log = logging.getLogger(__name__)

# ── Label scheme ──────────────────────────────────────────────────────────────
# Fields listed in natural address order; used for greedy left-to-right alignment.

FIELD_ORDER = [
    "building_name",
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
]

LABEL_NAMES = (
    ["O"]
    + [f"B-{f.upper()}" for f in FIELD_ORDER]
    + [f"I-{f.upper()}" for f in FIELD_ORDER]
)
LABEL_TO_ID: dict[str, int] = {name: i for i, name in enumerate(LABEL_NAMES)}

# ── Excluded permutation types ────────────────────────────────────────────────
# These replace full field values with abbreviations, making direct substring
# matching against the parquet field value unreliable.

EXCLUDED_PERMUTATIONS: set[str] = {
    "street_abbrev_gnaf",
    "street_abbrev_informal",
    "flat_abbrev_informal",
    "flat_abbrev_gnaf",
    "level_abbrev_informal",
    "level_code_joined",
    "slash_notation",
    "state_postcode_joined",
    "number_prefix_no",
    "number_prefix_no_dot",
    "state_full_name",
}

TOKENIZER_NAME = "distilbert-base-uncased"
MAX_LENGTH = 128


# ── Alignment ─────────────────────────────────────────────────────────────────


def _find_field_spans(
    address: str,
    fields: dict[str, str],
) -> list[tuple[int, int, str]] | None:
    """
    Locate each non-empty field value within `address` (case-insensitive, word-bounded).

    Iterates fields in FIELD_ORDER and greedily assigns each to its first
    available (non-overlapping) match. Returns None if any matched field
    cannot be placed without overlap.

    Fields absent from the formatted_address (omitted by the permutation) are
    silently skipped — they just won't contribute labels.
    """
    text_lower = address.lower()
    spans: list[tuple[int, int, str]] = []
    # Track occupied character positions to prevent double-assignment.
    occupied: set[int] = set()

    for field_name in FIELD_ORDER:
        value = fields.get(field_name, "")
        if not value:
            continue

        value_lower = value.lower()
        # \b-equivalent for alphanumeric boundaries; handles "35" inside "4350".
        pattern = r"(?<![a-z0-9])" + re.escape(value_lower) + r"(?![a-z0-9])"
        matches = list(re.finditer(pattern, text_lower))

        if not matches:
            continue  # Field omitted in this permutation — not an error.

        # Pick the first match whose span doesn't overlap any already-assigned span.
        chosen = None
        for m in matches:
            span_chars = set(range(m.start(), m.end()))
            if not span_chars & occupied:
                chosen = m
                break

        if chosen is None:
            # All candidate positions are occupied — alignment is ambiguous; skip row.
            return None

        spans.append((chosen.start(), chosen.end(), field_name))
        occupied.update(range(chosen.start(), chosen.end()))

    spans.sort(key=lambda x: x[0])
    return spans


def _build_char_label_map(
    address: str,
    spans: list[tuple[int, int, str]],
) -> dict[int, str]:
    """
    Build a char-position → IOB2 label string mapping from field spans.

    Within each span, the first word's characters get B-FIELD and subsequent
    words' characters get I-FIELD. Non-alphanumeric characters (spaces, commas)
    between words are not added to the map and default to "O" during tokenization.
    """
    char_label: dict[int, str] = {}

    for start, end, field_name in spans:
        tag_b = f"B-{field_name.upper()}"
        tag_i = f"I-{field_name.upper()}"

        in_word = False
        first_word = True
        current_tag = tag_b

        for i in range(start, end):
            c = address[i]
            is_word_char = c.isalnum() or c in "'-"
            if is_word_char:
                if not in_word:
                    current_tag = tag_b if first_word else tag_i
                    first_word = False
                    in_word = True
                char_label[i] = current_tag
            else:
                in_word = False

    return char_label


def _tokenize_and_align(
    address: str,
    char_label: dict[int, str],
    tokenizer,
) -> dict | None:
    """
    Tokenize `address` and assign IOB2 label ids to each token.

    Convention:
    - Special tokens ([CLS], [SEP]): -100
    - Continuation subwords (no whitespace gap from previous token): -100
    - All other tokens: label id from char_label (defaulting to O=0)
    """
    encoding = tokenizer(
        address,
        truncation=True,
        max_length=MAX_LENGTH,
        return_offsets_mapping=True,
        padding=False,
    )

    offset_mapping: list[tuple[int, int]] = encoding["offset_mapping"]
    labels: list[int] = []
    prev_end: int | None = None

    for t_start, t_end in offset_mapping:
        if t_start == t_end:  # Special token.
            labels.append(-100)
            prev_end = None
            continue

        # Continuation subword: offset immediately follows previous token with no gap.
        if prev_end is not None and prev_end == t_start:
            labels.append(-100)
        else:
            label_str = char_label.get(t_start, "O")
            labels.append(LABEL_TO_ID[label_str])

        prev_end = t_end

    # Discard if no real labels survived (e.g. all special tokens after truncation).
    if not any(l != -100 for l in labels):
        return None

    return {
        "input_ids": encoding["input_ids"],
        "attention_mask": encoding["attention_mask"],
        "labels": labels,
    }


# ── Batch processing ──────────────────────────────────────────────────────────


def _process_batch(batch: pd.DataFrame, tokenizer) -> list[dict]:
    results: list[dict] = []
    for _, row in batch.iterrows():
        address: str = row["formatted_address"]
        fields = {f: str(row[f]) for f in FIELD_ORDER if row.get(f)}

        spans = _find_field_spans(address, fields)
        if spans is None:
            continue

        char_label = _build_char_label_map(address, spans)
        example = _tokenize_and_align(address, char_label, tokenizer)
        if example is None:
            continue

        results.append(example)

    return results


# ── Shard writer ──────────────────────────────────────────────────────────────

_SHARD_SCHEMA = pa.schema([
    pa.field("input_ids", pa.list_(pa.int32())),
    pa.field("attention_mask", pa.list_(pa.int8())),
    pa.field("labels", pa.list_(pa.int32())),
])

SHARD_SIZE = 500_000  # examples per parquet shard


def _flush_shard(shard_dir: Path, shard_idx: int, examples: list[dict]) -> None:
    table = pa.table(
        {
            "input_ids": [e["input_ids"] for e in examples],
            "attention_mask": [e["attention_mask"] for e in examples],
            "labels": [e["labels"] for e in examples],
        },
        schema=_SHARD_SCHEMA,
    )
    path = shard_dir / f"shard_{shard_idx:04d}.parquet"
    pq.write_table(table, path)
    mb = path.stat().st_size / 1_000_000
    log.info(f"  → Shard {shard_idx} written: {len(examples):,} examples ({mb:.0f} MB)")


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare IOB2 training data for DistilBERT address parser"
    )
    parser.add_argument(
        "--input",
        default="training/data/address_training.parquet",
        help="Path to address_training.parquet",
    )
    parser.add_argument(
        "--output",
        default="training/data/iob_dataset",
        help="Directory to save the HuggingFace DatasetDict",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Limit total rows (useful for testing)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10_000,
        help="Rows processed per batch (controls memory usage)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    log.info(f"Loading parquet: {args.input}")
    df = pd.read_parquet(args.input)
    log.info(f"Total rows: {len(df):,}")

    before = len(df)
    df = df[~df["permutation_type"].isin(EXCLUDED_PERMUTATIONS)]
    log.info(
        f"After permutation filter: {len(df):,} rows "
        f"(excluded {before - len(df):,} abbreviated-format rows)"
    )

    if args.sample:
        df = df.sample(n=min(args.sample, len(df)), random_state=42)
        log.info(f"Sampled {len(df):,} rows for testing")

    # Parquet may encode missing values as NaN; normalise to empty string.
    df = df.fillna("")

    log.info(f"Loading tokenizer: {TOKENIZER_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write examples to parquet shards as we go — avoids accumulating 9M+
    # Python dicts in memory before the HuggingFace Dataset conversion.
    shard_dir = output_dir / "shards"
    shard_dir.mkdir(exist_ok=True)

    log.info("Aligning fields and tokenizing...")
    n_batches = (len(df) + args.batch_size - 1) // args.batch_size
    shard_buf: list[dict] = []
    shard_idx = 0
    total_examples = 0

    for i in range(n_batches):
        batch = df.iloc[i * args.batch_size : (i + 1) * args.batch_size]
        examples = _process_batch(batch, tokenizer)
        shard_buf.extend(examples)
        total_examples += len(examples)

        if len(shard_buf) >= SHARD_SIZE:
            _flush_shard(shard_dir, shard_idx, shard_buf)
            shard_idx += 1
            shard_buf = []

        if (i + 1) % 10 == 0 or (i + 1) == n_batches:
            log.info(
                f"  Batch {i + 1}/{n_batches} "
                f"({100 * (i + 1) / n_batches:.0f}%) — "
                f"{total_examples:,} valid examples"
            )

    # Flush remaining examples.
    if shard_buf:
        _flush_shard(shard_dir, shard_idx, shard_buf)

    skip_rate = 100 * (1 - total_examples / len(df))
    log.info(
        f"Prepared {total_examples:,} examples "
        f"({skip_rate:.1f}% rows skipped due to alignment failures)"
    )

    # Load all shards into a HuggingFace Dataset (memory-mapped Arrow, no RAM spike).
    log.info("Loading shards into HuggingFace Dataset...")
    shard_files = sorted(str(p) for p in shard_dir.glob("shard_*.parquet"))
    dataset = load_dataset("parquet", data_files=shard_files, split="train")

    log.info("Splitting 95% train / 5% validation...")
    splits = dataset.train_test_split(test_size=0.05, seed=42)
    dataset_dict = DatasetDict({"train": splits["train"], "validation": splits["test"]})

    dataset_dict.save_to_disk(str(output_dir))
    log.info(f"Dataset saved to {output_dir}")
    log.info(f"  train:      {len(dataset_dict['train']):,} examples")
    log.info(f"  validation: {len(dataset_dict['validation']):,} examples")

    # Remove shards now that the DatasetDict is saved.
    shutil.rmtree(shard_dir)
    log.info("Shards cleaned up.")

    label_config = {
        "label_names": LABEL_NAMES,
        "label_to_id": LABEL_TO_ID,
        "id_to_label": {str(v): k for k, v in LABEL_TO_ID.items()},
        "num_labels": len(LABEL_NAMES),
    }
    config_path = output_dir / "label_config.json"
    config_path.write_text(json.dumps(label_config, indent=2))
    log.info(f"Label config saved to {config_path}")
    log.info("Done.")


if __name__ == "__main__":
    main()
