#!/usr/bin/env bash
# run_docker_training.sh — Address parser training pipeline.
#
# Steps:
#   1. generate  — Extract GNAF addresses from DB and write address_training.parquet
#                  (runs natively via venv — requires DB connection)
#   2. build     — Build the Docker training image
#   3. prepare   — Tokenise + IOB2-label the parquet (Docker, CPU)
#   4. train     — Fine-tune DistilBERT (Docker, GPU)
#
# Usage (run from data-layer/):
#   bash training/run_docker_training.sh [STEPS] [OPTIONS]
#
# Steps (one or more, run in order):
#   --generate-data    Step 1 — generate address_training.parquet from DB
#   --build            Step 2 — build Docker image
#   --prepare          Step 3 — tokenise + IOB2-label parquet → iob_dataset/
#   --train            Step 4 — fine-tune DistilBERT
#
# Options:
#   --limit N          Max GNAF addresses to process (default: all)
#   --states S         Comma-separated states to include (default: QLD, e.g. QLD,NSW)
#   --sample N         Prepare IOB on N rows only — fast smoke-test before full run
#
# Examples:
#   # Full pipeline from scratch:
#   bash training/run_docker_training.sh --generate-data --build --prepare --train
#
#   # Parquet already exists — build image, prepare IOB, then train:
#   bash training/run_docker_training.sh --build --prepare --train
#
#   # Image already built, iob_dataset ready — just train:
#   bash training/run_docker_training.sh --train
#
#   # Quick smoke-test on 50k rows:
#   bash training/run_docker_training.sh --build --prepare --train --sample 50000

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_LAYER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE="address-parser-training"

# ── Parse args ────────────────────────────────────────────────────────────────
DO_GENERATE=0
DO_BUILD=0
DO_PREPARE=0
DO_TRAIN=0
LIMIT=""
STATES="QLD"
SAMPLE=""

if [[ $# -eq 0 ]]; then
  sed -n '2,/^set -/{ /^set -/d; s/^# \{0,1\}//; p }' "$0"
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case $1 in
    --generate-data) DO_GENERATE=1 ;;
    --build)         DO_BUILD=1 ;;
    --prepare)       DO_PREPARE=1 ;;
    --train)         DO_TRAIN=1 ;;
    --limit)         LIMIT="$2"; shift ;;
    --states)        STATES="$2"; shift ;;
    --sample)        SAMPLE="$2"; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

if [[ $DO_GENERATE -eq 0 && $DO_BUILD -eq 0 && $DO_PREPARE -eq 0 && $DO_TRAIN -eq 0 ]]; then
  echo "ERROR: No steps specified. Pass at least one of: --generate-data --build --prepare --train"
  exit 1
fi

# ── Filesystem warning (WSL2 /mnt/ penalty) ───────────────────────────────────
if [[ "$DATA_LAYER_DIR" == /mnt/* ]]; then
  echo ""
  echo "WARNING: Running from $DATA_LAYER_DIR"
  echo "  This is a Windows filesystem mount (9P bridge) — Docker I/O will be"
  echo "  3-5x slower than the native WSL2 filesystem."
  echo "  For best performance, copy to WSL2 native filesystem first:"
  echo "    cp -r $DATA_LAYER_DIR ~/property2/data-layer"
  echo "    cd ~/property2/data-layer && bash training/run_docker_training.sh"
  echo ""
  read -r -p "Continue anyway? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
fi

cd "$DATA_LAYER_DIR"

# ── --generate-data ───────────────────────────────────────────────────────────
if [[ $DO_GENERATE -eq 1 ]]; then
  echo ""
  echo "==> Generating address training parquet from GNAF"
  echo "    States: $STATES"
  [[ -n "$LIMIT" ]] && echo "    Limit:  $LIMIT addresses"
  echo "    Output: training/data/address_training.parquet"
  echo ""

  if [[ ! -f venv/bin/python ]]; then
    echo "ERROR: venv not found at $DATA_LAYER_DIR/venv"
    echo "  Create it with: python3.11 -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
  fi

  GENERATE_ARGS=(
    --output training/data/address_training.parquet
    --states "$STATES"
    --parquet
    --training
  )
  [[ -n "$LIMIT" ]] && GENERATE_ARGS+=(--limit "$LIMIT")

  venv/bin/python training/generate_address_data.py "${GENERATE_ARGS[@]}"
  echo ""
  echo "==> Parquet ready."
fi

# ── --build ───────────────────────────────────────────────────────────────────
if [[ $DO_BUILD -eq 1 ]]; then
  echo ""
  echo "==> Building Docker image: $IMAGE"
  docker build -f training/Dockerfile.training -t "$IMAGE" .
fi

# ── --prepare ─────────────────────────────────────────────────────────────────
if [[ $DO_PREPARE -eq 1 ]]; then
  if [[ ! -f training/data/address_training.parquet ]]; then
    echo "ERROR: training/data/address_training.parquet not found. Run with --generate-data first."
    exit 1
  fi

  echo ""
  echo "==> Preparing IOB dataset"
  echo "    Input:  training/data/address_training.parquet"
  echo "    Output: training/data/iob_dataset/"
  [[ -n "$SAMPLE" ]] && echo "    Sample: $SAMPLE rows (smoke-test mode)"
  echo ""

  PREPARE_ARGS=()
  [[ -n "$SAMPLE" ]] && PREPARE_ARGS+=(--sample "$SAMPLE")

  docker run --rm \
    --shm-size=2g \
    -v "$(pwd)/training/data:/app/training/data" \
    "$IMAGE" \
    python -m training.prepare_iob "${PREPARE_ARGS[@]}"

  echo ""
  echo "==> IOB dataset ready."
fi

# ── --train ───────────────────────────────────────────────────────────────────
if [[ $DO_TRAIN -eq 1 ]]; then
  if [[ ! -d training/data/iob_dataset ]]; then
    echo "ERROR: training/data/iob_dataset not found. Run with --prepare first."
    exit 1
  fi

  echo ""
  echo "==> Training model"
  echo "    Dataset: training/data/iob_dataset/"
  echo "    Output:  training/model/"
  echo ""

  docker run --rm --gpus all \
    --shm-size=2g \
    -v "$(pwd)/training/data:/app/training/data" \
    -v "$(pwd)/training/model:/app/training/model" \
    "$IMAGE" \
    python -m training.train

  echo ""
  echo "==> Training complete. Model saved to training/model/"
  echo ""
  echo "    Start the service:"
  echo "      cd $DATA_LAYER_DIR"
  echo "      venv/bin/uvicorn service.main:app --port 8001 --reload"
fi
