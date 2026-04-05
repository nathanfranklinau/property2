#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/app"
ZIP_FILE="$APP_DIR/training.zip"

# Write failure marker if the script exits unexpectedly (pip fail, unzip fail, etc.)
trap 'echo "failed" > /app/training.failed' ERR

echo "--- Extracting training bundle ---"
cd "$APP_DIR"
unzip -q "$ZIP_FILE"

TRAIN_DIR="$APP_DIR/training"
cd "$TRAIN_DIR"

sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update -qq
sudo apt-get install -y -qq python3.11 python3.11-venv python3.11-distutils python3.11-dev

echo "--- Creating Python 3.11 venv ---"
python3.11 -m venv venv --without-pip
curl -sS https://bootstrap.pypa.io/get-pip.py | venv/bin/python3.11

echo "--- Installing dependencies ---"
. venv/bin/activate
pip install --quiet -r requirements-training.txt
pip install --quiet --force-reinstall torch --index-url https://download.pytorch.org/whl/cu124

echo "--- Starting training ---"
# - - gh200
if python train.py --a100 --dataset data/iob_dataset; then
  echo "done" > /app/training.done
else
  echo "failed" > /app/training.failed
fi
