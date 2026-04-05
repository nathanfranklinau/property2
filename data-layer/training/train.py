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
    python -m training.train --gh200
    python -m training.train --l40s
    python -m training.train --a100
    python -m training.train --a40

Typical runtime on RTX 3060 (12 GB):  ~1–2 hours for 600k IOB examples, 1 epoch with early stopping.
Typical runtime on GH200 (96 GB):     ~10–20 minutes for 600k IOB examples.
Typical runtime on L40S (48 GB):      ~15–30 minutes for 600k IOB examples.
Typical runtime on A100 PCIe (80 GB): ~15–30 minutes for 600k IOB examples.
Typical runtime on A40 (48 GB):       ~20–40 minutes for 600k IOB examples.
"""

import argparse
import json
import logging
import os
import signal
from pathlib import Path

import torch
import numpy as np
from datasets import load_from_disk
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    EarlyStoppingCallback,
    Trainer,
    TrainerCallback,
    TrainerControl,
    TrainerState,
    TrainingArguments,
)

log = logging.getLogger(__name__)

TOKENIZER_NAME = "distilbert-base-uncased"

# ── Graceful stop (Ctrl+C) ─────────────────────────────────────────────────────

_stop_requested = False


def _handle_sigint(signum, frame) -> None:
    global _stop_requested
    _stop_requested = True
    print("\n[Training] Ctrl+C received — stopping after this step and saving best model.")


signal.signal(signal.SIGINT, _handle_sigint)


class GracefulStopCallback(TrainerCallback):
    """Checks the _stop_requested flag each step and triggers a clean stop."""

    def on_step_end(
        self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs
    ) -> TrainerControl:
        if _stop_requested:
            control.should_training_stop = True
        return control
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
        default=64,
        help="Per-device train batch size. Effective batch = batch_size × gradient_accumulation_steps (default 1 → 64).",
    )
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument(
        "--no-fp16",
        action="store_true",
        help="Disable mixed-precision training (use if GPU doesn't support fp16)",
    )
    parser.add_argument(
        "--gh200",
        action="store_true",
        help=(
            "Optimise for NVIDIA GH200 Grace Hopper (96 GB HBM3e, Hopper arch). "
            "Enables bf16, batch_size=512, torch.compile, and persistent workers. "
            "Workers auto-scaled to cpu_count (ceiling 32). Overrides --batch-size and --no-fp16."
        ),
    )
    parser.add_argument(
        "--l40s",
        action="store_true",
        help=(
            "Optimise for NVIDIA L40S (48 GB GDDR6, Ada Lovelace arch). "
            "Enables bf16, batch_size=256, torch.compile, and persistent workers. "
            "Workers auto-scaled to cpu_count (ceiling 16). Overrides --batch-size and --no-fp16."
        ),
    )
    parser.add_argument(
        "--a100",
        action="store_true",
        help=(
            "Optimise for NVIDIA A100 PCIe (80 GB HBM2e, Ampere arch). "
            "Enables bf16, batch_size=512, torch.compile, and persistent workers. "
            "Workers auto-scaled to cpu_count (ceiling 16). Overrides --batch-size and --no-fp16. "
            "For 40 GB variant, use --batch-size 256 instead."
        ),
    )
    parser.add_argument(
        "--a40",
        action="store_true",
        help=(
            "Optimise for NVIDIA A40 (48 GB GDDR6, Ampere arch). "
            "Enables bf16, batch_size=256, torch.compile, and persistent workers. "
            "Workers auto-scaled to cpu_count (ceiling 16). Overrides --batch-size and --no-fp16."
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── CUDA check — fail fast rather than silently training on CPU ───────────
    if not torch.cuda.is_available():
        raise RuntimeError(
            f"No CUDA device found. torch={torch.__version__}, "
            f"CUDA built={torch.version.cuda}. "
            "Check nvidia-smi and that torch was installed with the correct --index-url."
        )
    log.info(f"CUDA device: {torch.cuda.get_device_name(0)}")

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
    # Default: tuned for RTX 3060 12 GB:
    #   batch_size=64, fp16=True, eval every 2,000 steps
    #
    # GPU presets set batch/precision/compile settings for their architecture.
    # max_workers is a per-preset ceiling; actual workers = min(cpu_count-2, ceiling).
    # This keeps workers correct across cloud instances with varying vCPU counts.
    #
    # --gh200: Hopper arch — bf16, batch=512, torch_compile, eval every 500 steps
    # --l40s:  Ada arch    — bf16, batch=256, torch_compile, eval every 500 steps
    # --a100:  Ampere arch — bf16, batch=512, torch_compile, eval every 500 steps
    # --a40:   Ampere arch — bf16, batch=256, torch_compile, eval every 500 steps

    if args.gh200:
        train_batch = 512
        eval_batch = 1024
        use_fp16 = False
        use_bf16 = True
        max_workers = 32  # Grace CPU has 72 Neoverse V2 cores
        persistent_workers = True
        torch_compile = True
        eval_steps = 500
        save_steps = 500
        logging_steps = 100
    elif args.l40s:
        # L40S: 48 GB GDDR6, 864 GB/s, Ada Lovelace 4th-gen Tensor Cores
        # Native BF16 at 366.7 TFLOPS; FP8 Transformer Engine available
        train_batch = 256
        eval_batch = 512
        use_fp16 = False
        use_bf16 = True
        max_workers = 16
        persistent_workers = True
        torch_compile = True
        eval_steps = 500
        save_steps = 500
        logging_steps = 100
    elif args.a100:
        # A100 PCIe: 80 GB HBM2e, 2 TB/s, Ampere 3rd-gen Tensor Cores, 312 TFLOPS BF16
        train_batch = 512
        eval_batch = 1024
        use_fp16 = False
        use_bf16 = True
        max_workers = 16
        persistent_workers = True
        torch_compile = True
        eval_steps = 500
        save_steps = 500
        logging_steps = 100
    elif args.a40:
        # A40: 48 GB GDDR6, 696 GB/s, Ampere 3rd-gen Tensor Cores, ~150 TFLOPS BF16
        # Same VRAM as L40S but GDDR6 (lower bandwidth) — batch 256 is correct
        train_batch = 256
        eval_batch = 512
        use_fp16 = False
        use_bf16 = True
        max_workers = 16
        persistent_workers = True
        torch_compile = True
        eval_steps = 500
        save_steps = 500
        logging_steps = 100
    else:
        train_batch = args.batch_size
        eval_batch = args.batch_size * 2
        use_fp16 = not args.no_fp16
        use_bf16 = False
        max_workers = 8
        persistent_workers = False
        torch_compile = False
        eval_steps = 2_000
        save_steps = 2_000
        logging_steps = 500

    # Auto-scale workers to the actual vCPU count, capped at the preset ceiling.
    # Leaves 2 cores for the main training loop and OS.
    num_workers = max(1, min((os.cpu_count() or 4) - 2, max_workers))

    gpu_preset = next(
        (p for p in ("gh200", "l40s", "a100", "a40") if getattr(args, p, False)), "default"
    )
    log.info(
        f"GPU preset: {gpu_preset} | bf16={use_bf16} fp16={use_fp16} "
        f"batch={train_batch} workers={num_workers}/{max_workers} compile={torch_compile}"
    )

    output_dir = str(args.output)
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=train_batch,
        per_device_eval_batch_size=eval_batch,
        gradient_accumulation_steps=1,
        learning_rate=args.lr,
        weight_decay=0.01,
        warmup_ratio=0.06,
        fp16=use_fp16,
        bf16=use_bf16,
        torch_compile=torch_compile,
        eval_strategy="steps",
        eval_steps=eval_steps,
        save_strategy="steps",
        save_steps=save_steps,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        logging_steps=logging_steps,
        report_to="none",           # Disable wandb / tensorboard
        dataloader_num_workers=num_workers,
        dataloader_persistent_workers=persistent_workers,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=_make_compute_metrics(label_names),
        callbacks=[
            EarlyStoppingCallback(
                early_stopping_patience=5,
                early_stopping_threshold=0.0,
            ),
            GracefulStopCallback(),
        ],
    )

    # ── Train ─────────────────────────────────────────────────────────────────

    # Resume from the latest checkpoint if one exists (e.g. after a crash)
    last_checkpoint = None
    output_path = Path(output_dir)
    checkpoints = sorted(output_path.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1]))
    if checkpoints:
        last_checkpoint = str(checkpoints[-1])
        log.info(f"Resuming from checkpoint: {last_checkpoint}")

    log.info("Starting training...")
    try:
        trainer.train(resume_from_checkpoint=last_checkpoint)
    except KeyboardInterrupt:
        log.info("Training interrupted — loading best checkpoint before saving.")
        if trainer.state.best_model_checkpoint:
            trainer._load_best_model()

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
