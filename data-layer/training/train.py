"""
train.py — Fine-tune DistilBERT for Australian address token classification.

Loads the IOB2 dataset produced by prepare_iob.py, fine-tunes
distilbert-base-uncased with a token classification head, and saves the
trained model to disk. Designed for a single GPU (RTX 3060 or better).

Usage (run from data-layer/):
    python -m training.train
    python -m training.train --epochs 3 --batch-size 32
    python -m training.train --dataset training/data/iob_dataset \
                             --output  training/model

Typical runtime on RTX 3060 (12 GB): ~3–5 hours for 2–3 M examples, 3 epochs.
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
from datasets import load_from_disk
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
)

log = logging.getLogger(__name__)

TOKENIZER_NAME = "distilbert-base-uncased"
DEFAULT_DATASET = "training/data/iob_dataset"
DEFAULT_OUTPUT = "training/model"


# ── Metrics ───────────────────────────────────────────────────────────────────


def _make_compute_metrics(label_names: list[str]):
    """Return a compute_metrics function bound to the label list."""
    import evaluate  # lazy import — not needed until training starts

    seqeval = evaluate.load("seqeval")

    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=2)

        true_preds = [
            [label_names[p] for p, l in zip(pred_row, label_row) if l != -100]
            for pred_row, label_row in zip(predictions, labels)
        ]
        true_labels = [
            [label_names[l] for l in label_row if l != -100]
            for label_row in labels
        ]

        results = seqeval.compute(predictions=true_preds, references=true_labels)
        return {
            "precision": results["overall_precision"],
            "recall": results["overall_recall"],
            "f1": results["overall_f1"],
            "accuracy": results["overall_accuracy"],
        }

    return compute_metrics


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fine-tune DistilBERT for Australian address parsing"
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help="Path to the IOB2 DatasetDict produced by prepare_iob.py",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Directory to save the trained model and tokenizer",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Per-device train batch size. Effective batch = batch_size × gradient_accumulation_steps (default 2 → 64).",
    )
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument(
        "--no-fp16",
        action="store_true",
        help="Disable mixed-precision training (use if GPU doesn't support fp16)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── Load dataset ──────────────────────────────────────────────────────────

    log.info(f"Loading dataset from {args.dataset}")
    dataset = load_from_disk(args.dataset)

    config_path = Path(args.dataset) / "label_config.json"
    with open(config_path) as f:
        label_config = json.load(f)

    label_names: list[str] = label_config["label_names"]
    label_to_id: dict[str, int] = label_config["label_to_id"]
    id_to_label: dict[int, str] = {int(k): v for k, v in label_config["id_to_label"].items()}
    num_labels: int = label_config["num_labels"]

    log.info(f"Labels: {num_labels}  (e.g. {label_names[1:4]}...)")
    log.info(f"Train:      {len(dataset['train']):,} examples")
    log.info(f"Validation: {len(dataset['validation']):,} examples")

    # ── Model + tokenizer ─────────────────────────────────────────────────────

    log.info(f"Loading model: {TOKENIZER_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)
    model = AutoModelForTokenClassification.from_pretrained(
        TOKENIZER_NAME,
        num_labels=num_labels,
        id2label=id_to_label,
        label2id=label_to_id,
    )

    data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

    # ── Training arguments ────────────────────────────────────────────────────
    # Tuned for RTX 3060 12 GB:
    #   batch_size=32 × gradient_accumulation_steps=2 → effective batch 64
    #   fp16=True saves ~40% VRAM and speeds up training on Ampere GPUs

    output_dir = str(args.output)
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        gradient_accumulation_steps=2,
        learning_rate=args.lr,
        weight_decay=0.01,
        warmup_ratio=0.06,
        fp16=not args.no_fp16,
        eval_strategy="steps",
        eval_steps=2_000,
        save_strategy="steps",
        save_steps=2_000,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        logging_steps=500,
        report_to="none",           # Disable wandb / tensorboard
        dataloader_num_workers=4,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=_make_compute_metrics(label_names),
    )

    # ── Train ─────────────────────────────────────────────────────────────────

    log.info("Starting training...")
    trainer.train()

    # ── Save ──────────────────────────────────────────────────────────────────

    log.info(f"Saving model to {output_dir}")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Copy label config into the model directory so address_parser.py can load
    # everything it needs from a single directory.
    out_config = Path(output_dir) / "label_config.json"
    out_config.write_text(json.dumps(label_config, indent=2))

    log.info("Training complete.")
    log.info(f"Model saved to: {output_dir}")


if __name__ == "__main__":
    main()
