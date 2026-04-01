"""
address_parser.py — CPU inference wrapper for the trained DistilBERT address parser.

Loads the model once at startup. parse() takes a raw address string and returns
a dict of structured fields. No GPU required at inference time.

Usage:
    parser = AddressParser("training/model")
    result = parser.parse("Unit 4, 35 Smallman Street, Bulimba QLD 4171")
    # → {"unit_type": "Unit", "unit_number": "4", "street_number": "35", ...}
"""

import json
import logging
import re
from pathlib import Path
from typing import Sequence

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

log = logging.getLogger(__name__)

MAX_LENGTH = 128

# Unit type keywords that can appear fused with their number (e.g. "Unit59", "Shop301").
# Title-cased. Order matters — longer matches checked first to avoid "Flat" matching inside
# "Flatette" etc. Listed longest-first within each logical group.
_UNIT_TYPE_KEYWORDS: Sequence[str] = [
    "Apartment", "Townhouse", "Penthouse", "Warehouse", "Basement",
    "Factory", "Studio", "Office", "Duplex", "Villa", "Room",
    "Shop", "Flat", "Unit", "Suite", "Shed",
]

# Level type keywords that can appear fused (e.g. "Level3", "Floor2").
_LEVEL_TYPE_KEYWORDS: Sequence[str] = [
    "Mezzanine", "Basement", "Rooftop", "Parking", "Podium",
    "Ground", "Floor", "Level",
]

# Pre-compiled regex patterns: (field, type_value, pattern)
# Each pattern matches the full fused value and captures (type_part, number_part).
_UNIT_FUSED_RE: list[tuple[str, re.Pattern[str]]] = [
    (kw, re.compile(rf"^({re.escape(kw)})(\w+)$", re.IGNORECASE))
    for kw in _UNIT_TYPE_KEYWORDS
]
_LEVEL_FUSED_RE: list[tuple[str, re.Pattern[str]]] = [
    (kw, re.compile(rf"^({re.escape(kw)})(\w+)$", re.IGNORECASE))
    for kw in _LEVEL_TYPE_KEYWORDS
]
_LOT_FUSED_RE = re.compile(r"^Lot(\w+)$", re.IGNORECASE)


def split_fused_tokens(result: dict[str, str | None]) -> dict[str, str | None]:
    """Split fused type+number tokens produced by the nospace permutation patterns.

    When the model sees "Unit59" as a single token it labels the whole thing as
    unit_number (unit_type is absent). This function detects those fused values
    and restores the canonical split: unit_type="Unit", unit_number="59".

    Safe to call on any parse result — values that are already split are unchanged.
    """
    result = dict(result)

    # unit_number fused: "Unit59" → unit_type="Unit", unit_number="59"
    unit_num = result.get("unit_number") or ""
    if unit_num and not result.get("unit_type"):
        for kw, pattern in _UNIT_FUSED_RE:
            m = pattern.match(unit_num)
            if m:
                result["unit_type"] = kw
                result["unit_number"] = m.group(2)
                break

    # level_number fused: "Level3" → level_type="Level", level_number="3"
    level_num = result.get("level_number") or ""
    if level_num and not result.get("level_type"):
        for kw, pattern in _LEVEL_FUSED_RE:
            m = pattern.match(level_num)
            if m:
                result["level_type"] = kw
                result["level_number"] = m.group(2)
                break

    # lot_number fused: "Lot163" → lot_number="163"
    lot_num = result.get("lot_number") or ""
    if lot_num:
        m = _LOT_FUSED_RE.match(lot_num)
        if m:
            result["lot_number"] = m.group(1)

    return result


class AddressParser:
    def __init__(self, model_dir: str | Path) -> None:
        model_dir = Path(model_dir)
        if not model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {model_dir}")

        log.info(f"Loading address parser from {model_dir}")
        self._tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        self._model = AutoModelForTokenClassification.from_pretrained(str(model_dir))
        self._model.eval()

        config_path = model_dir / "label_config.json"
        with open(config_path) as f:
            label_config = json.load(f)

        self._id_to_label: dict[int, str] = {
            int(k): v for k, v in label_config["id_to_label"].items()
        }
        log.info("Address parser ready.")

    def parse(self, address: str) -> dict[str, str | None]:
        """
        Parse a raw address string into structured fields.

        Input is normalised to title-case (consistent with training data) before
        tokenization. The model runs on CPU; typical latency is 20–50 ms.

        Returns a dict with any of these keys present (others absent if not found):
            building_name, unit_type, unit_number, level_type, level_number,
            lot_number, street_number, street_number_last, street_name,
            street_type, street_suffix, suburb, state, postcode
        """
        # Title-case normalisation matches the casing used during training.
        # distilbert-base-uncased lowercases internally, so casing doesn't
        # affect model predictions — but it does affect the reconstructed output.
        normalised = re.sub(r"\s+", " ", address.strip()).title()

        encoding = self._tokenizer(
            normalised,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
            return_offsets_mapping=True,
        )

        # offset_mapping is not a model input — remove before forward pass.
        offset_mapping: list[tuple[int, int]] = encoding.pop("offset_mapping")[0].tolist()

        with torch.no_grad():
            logits = self._model(**encoding).logits[0]  # shape: (seq_len, num_labels)

        predictions: list[int] = torch.argmax(logits, dim=1).tolist()

        # Token strings needed to detect true WordPiece continuation subwords (## prefix).
        # Adjacent punctuation tokens like "57", "/", "7" have no character gap but are NOT
        # subwords — only ## tokens should be merged into the preceding word.
        token_strings = self._tokenizer.convert_ids_to_tokens(
            encoding["input_ids"][0].tolist()
        )

        # ── Decode: reconstruct word-level tokens with their labels ──────────
        # Only the first subword of each word carries a reliable label
        # (continuation subwords were masked with -100 during training).

        words: list[tuple[str, str]] = []  # (word_text, label)
        current_text = ""
        current_label = "O"
        prev_end: int | None = None

        for i, ((t_start, t_end), pred_id) in enumerate(zip(offset_mapping, predictions)):
            if t_start == t_end:  # Special token ([CLS], [SEP]).
                # Flush any accumulated word.
                if current_text:
                    words.append((current_text, current_label))
                    current_text = ""
                    current_label = "O"
                prev_end = None
                continue

            token_text = normalised[t_start:t_end]
            predicted_label = self._id_to_label[pred_id]
            is_adjacent = prev_end is not None and prev_end == t_start
            is_continuation = is_adjacent and (
                token_strings[i].startswith("##")
                or (
                    # Adjacent non-subword token predicting the same field as the current
                    # word (e.g. "-" in "Ron-Penhaligon" after the model predicts
                    # B-STREET_NAME for both "ron" and "-"). Consecutive B- entries of the
                    # same field are merged rather than overwriting each other.
                    # This does NOT fire for "/" in "57/7" because "/" predicts O (a
                    # different field), so unit_number and street_number stay separate.
                    predicted_label != "O"
                    and current_label != "O"
                    and predicted_label.split("-", 1)[1] == current_label.split("-", 1)[1]
                )
            )

            if is_continuation:
                # Continuation: append text, keep the first token's label.
                current_text += token_text
            else:
                # New word: flush previous, start fresh.
                if current_text:
                    words.append((current_text, current_label))
                current_text = token_text
                current_label = predicted_label

            prev_end = t_end

        # Flush final word.
        if current_text:
            words.append((current_text, current_label))

        # ── Group consecutive same-field words into field values ─────────────
        field_words: dict[str, list[str]] = {}

        for word_text, label in words:
            if label == "O":
                continue

            prefix, field_name = label.split("-", 1)
            field_name = field_name.lower()

            if prefix == "B":
                field_words[field_name] = [word_text]
            elif prefix == "I":
                if field_name in field_words:
                    field_words[field_name].append(word_text)
                else:
                    # I- without preceding B- (rare model error) — treat as B-.
                    field_words[field_name] = [word_text]

        result = {field: " ".join(tokens) for field, tokens in field_words.items()}

        # lot_keyword captures the literal word "Lot" as its own IOB label (B-LOT_KEYWORD).
        # It is a display-only prefix — not a GNAF field — so we exclude it from output,
        # the same way "O" tokens are excluded. The model predicts it explicitly so it
        # can never be misclassified as BUILDING_NAME.
        result.pop("lot_keyword", None)

        # Split any fused type+number tokens produced by nospace input patterns
        # (e.g. "Unit59" → unit_type="Unit", unit_number="59").
        return split_fused_tokens(result)
