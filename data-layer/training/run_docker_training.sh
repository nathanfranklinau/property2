#!/usr/bin/env bash
# run_docker_training.sh — Full address parser training pipeline.
#
# Steps:
#   1. generate  — Extract GNAF addresses from DB and write address_training.parquet
#                  (runs natively via venv — requires DB connection)
#   2. prepare   — Tokenise + IOB2-label the parquet (Docker, CPU)
#   3. train     — Fine-tune DistilBERT (Docker, GPU)
#
# Usage (run from data-layer/):
#   bash training/run_docker_training.sh [OPTIONS]
#
# Options:
#   --skip-generate    Skip step 1 (address_training.parquet already exists)
#   --skip-prepare     Skip step 2 (iob_dataset already exists)
#   --skip-build       Skip docker build (image already up to date)
#   --limit N          Max GNAF addresses to process (default: all)
#   --states S         Comma-separated states to include (default: QLD, e.g. QLD,NSW)
#   --sample N         Prepare IOB on N rows only — fast smoke-test before full run
#
# Examples:
#   # Full pipeline from scratch:
#   bash training/run_docker_training.sh
#
#   # Regenerate parquet for QLD only, then re-prepare and train:
#   bash training/run_docker_training.sh --states QLD
#
#   # Skip generate (parquet is fine), redo prepare + train:
#   bash training/run_docker_training.sh --skip-generate
#
#   # Skip generate + prepare (iob_dataset ready), just train:
#   bash training/run_docker_training.sh --skip-generate --skip-prepare
#
#   # Quick smoke-test — prepare 50k rows, then train on that sample:
#   bash training/run_docker_training.sh --skip-generate --sample 50000

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_LAYER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE="address-parser-training"

# ── Parse args ────────────────────────────────────────────────────────────────
SKIP_GENERATE=0
SKIP_PREPARE=0
SKIP_BUILD=0
LIMIT=""
STATES="QLD"
SAMPLE=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-generate) SKIP_GENERATE=1 ;;
    --skip-prepare)  SKIP_PREPARE=1 ;;
    --skip-build)    SKIP_BUILD=1 ;;
    --limit)         LIMIT="$2"; shift ;;
    --states)        STATES="$2"; shift ;;
    --sample)        SAMPLE="$2"; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

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

# ── Step 1: Generate address training data ────────────────────────────────────
if [[ $SKIP_GENERATE -eq 0 ]]; then
  echo ""
  echo "==> Step 1: Generating address training parquet from GNAF"
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
else
  echo "==> Skipping generate (--skip-generate)"
  if [[ ! -f training/data/address_training.parquet ]]; then
    echo "ERROR: training/data/address_training.parquet not found. Remove --skip-generate to generate it."
    exit 1
  fi
fi

# ── Build Docker image ────────────────────────────────────────────────────────
if [[ $SKIP_BUILD -eq 0 ]]; then
  echo ""
  echo "==> Building Docker image: $IMAGE"
  docker build -f training/Dockerfile.training -t "$IMAGE" .
else
  echo "==> Skipping build (--skip-build)"
fi

# ── Step 2: Prepare IOB dataset ───────────────────────────────────────────────
if [[ $SKIP_PREPARE -eq 0 ]]; then
  echo ""
  echo "==> Step 2: Preparing IOB dataset"
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
else
  echo "==> Skipping prepare_iob (--skip-prepare)"
  if [[ ! -d training/data/iob_dataset ]]; then
    echo "ERROR: training/data/iob_dataset not found. Remove --skip-prepare to generate it."
    exit 1
  fi
fi

# ── Step 3: Train ─────────────────────────────────────────────────────────────
echo ""
echo "==> Step 3: Training model"
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
