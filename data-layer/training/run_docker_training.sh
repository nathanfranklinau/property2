#!/usr/bin/env bash
# run_docker_training.sh — Address parser training pipeline.
#
# Steps:
#   1. build     — Build the Docker training image
#   2. prepare   — Tokenise + IOB2-label the parquet (Docker, CPU)
#   3. train     — Fine-tune DistilBERT (Docker, GPU)
#
# Prerequisites:
#   address_training.parquet must already exist in training/data/.
#   Generate it with: python -m training.generate_address_data
#
# Usage (run from data-layer/):
#   bash training/run_docker_training.sh [STEPS] [OPTIONS]
#
# Steps (one or more, run in order):
#   --build            Step 1 — build Docker image
#   --prepare          Step 2 — tokenise + IOB2-label parquet → iob_dataset/
#   --train            Step 3 — fine-tune DistilBERT
#
# Examples:
#
#   # Parquet already exists — build image, prepare IOB, then train:
#   bash training/run_docker_training.sh --build --prepare --train
#
#   # Image already built, iob_dataset ready — just train:
#   bash training/run_docker_training.sh --train

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_LAYER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE="address-parser-training"

# ── Parse args ────────────────────────────────────────────────────────────────
DO_BUILD=0
DO_PREPARE=0
DO_TRAIN=0
if [[ $# -eq 0 ]]; then
  sed -n '2,/^set -/{ /^set -/d; s/^# \{0,1\}//; p }' "$0"
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case $1 in
    --build)         DO_BUILD=1 ;;
    --prepare)       DO_PREPARE=1 ;;
    --train)         DO_TRAIN=1 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

if [[ $DO_BUILD -eq 0 && $DO_PREPARE -eq 0 && $DO_TRAIN -eq 0 ]]; then
  echo "ERROR: No steps specified. Pass at least one of: --build --prepare --train"
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

# ── --build ───────────────────────────────────────────────────────────────────
if [[ $DO_BUILD -eq 1 ]]; then
  echo ""
  echo "==> Building Docker image: $IMAGE"
  docker build -f training/Dockerfile.training -t "$IMAGE" .
fi

# ── --prepare ─────────────────────────────────────────────────────────────────
if [[ $DO_PREPARE -eq 1 ]]; then
  if [[ ! -f training/data/address_training.parquet ]]; then
    echo "ERROR: training/data/address_training.parquet not found. Run generate_address_data.py first."
    exit 1
  fi

  echo ""
  echo "==> Preparing IOB dataset"
  echo "    Input:  training/data/address_training.parquet"
  echo "    Output: training/data/iob_dataset/"
  echo ""

  docker run --rm \
    --shm-size=2g \
    -v "$(pwd)/training/data:/app/training/data" \
    "$IMAGE" \
    python -m training.prepare_iob

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
    -v "$(pwd)/training/data/iob_dataset:/app/training/data/iob_dataset:ro" \
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
