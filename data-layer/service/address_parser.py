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

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

log = logging.getLogger(__name__)

MAX_LENGTH = 128


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

        # Correct misclassification of "Lot <number>" addresses.
        #
        # After retraining the model will label both tokens as LOT_NUMBER
        # (B- + I-), producing lot_number="Lot 210" — strip the prefix.
        if "lot_number" in result:
            val = result["lot_number"]
            if val.lower().startswith("lot "):
                result["lot_number"] = val[4:].strip()

        # Current (pre-retrain) model bug: for "Lot 210 Melrose Dr ..."
        #   building_name = "Lot"
        #   street_number = "210"   ← the lot number, misclassified
        #   lot_number    = absent
        # Move street_number → lot_number and drop the spurious building_name.
        if result.get("building_name", "").lower() == "lot":
            del result["building_name"]
            if "lot_number" not in result and "street_number" in result:
                result["lot_number"] = result.pop("street_number")

        return result
