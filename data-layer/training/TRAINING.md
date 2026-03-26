# Address Parser — Training Guide

Fine-tunes `distilbert-base-uncased` on 2–3 M Australian address examples to produce a self-contained model used by the `POST /parse-address` API endpoint.

**Estimated time on RTX 3060 (12 GB):** ~3–5 hours total (data prep ~30 min + training ~3–4 hours).

---

## Overview

| Step | Script | Output |
|------|--------|--------|
| 1. Prepare IOB dataset | `prepare_iob.py` | `training/data/iob_dataset/` |
| 2. Train model | `train.py` | `training/model/` |
| 3. Serve | `service/main.py` | `POST /parse-address` |

---

## Option A — Native (recommended for local GPU)

### Prerequisites

- Python 3.11
- CUDA 11.8+ on the host (`nvidia-smi` to check)
- The existing `data-layer/venv`

### 1. Install PyTorch with CUDA

```bash
cd data-layer
venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cu118
```

Verify GPU is visible:
```bash
venv/bin/python -c "import torch; print(torch.cuda.get_device_name(0))"
# Expected: NVIDIA GeForce RTX 3060
```

### 2. Install training dependencies

```bash
venv/bin/pip install -r training/requirements-training.txt
```

### 3. Prepare the IOB dataset

Reads `training/data/address_training.parquet`, aligns field values to token spans,
and saves a HuggingFace DatasetDict to `training/data/iob_dataset/`.

```bash
cd data-layer
venv/bin/python -m training.prepare_iob
```

**Test run first (optional):** processes 50 000 rows in ~2 minutes to verify alignment is working before committing to the full run:

```bash
venv/bin/python -m training.prepare_iob --sample 50000
```

Expected output:
```
Total rows: 4,156,252
After permutation filter: ~3,100,000 rows (excluded ~1,000,000 abbreviated-format rows)
Prepared ~2,950,000 valid examples (skip rate ~5%)
train:      2,802,000 examples
validation:   148,000 examples
```

### 4. Train

```bash
venv/bin/python -m training.train
```

Checkpoints save to `training/model/` every 2 000 steps. Training resumes automatically from the last checkpoint if interrupted.

**To resume after interruption:**
```bash
venv/bin/python -m training.train
# Trainer detects the existing checkpoint directory and resumes.
```

**Custom options:**
```bash
venv/bin/python -m training.train --epochs 5 --batch-size 16 --lr 3e-5
```

Expected validation F1 after 3 epochs: **>0.97** on standard address formats.

---

## Option B — Docker (alternative)

Useful if you don't want to modify the venv, or are running on a different machine.

### Prerequisites

- Docker with GPU support:
  - **Linux:** [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
  - **Windows:** Docker Desktop with WSL2 backend + NVIDIA driver ≥ 527

### Build the image

```bash
cd data-layer
docker build -f training/Dockerfile.training -t address-parser-training .
```

### Step 1 — Prepare IOB dataset

```bash
docker run --gpus all \
  -v "$(pwd)/training/data:/app/training/data" \
  address-parser-training \
  python -m training.prepare_iob
```

### Step 2 — Train

```bash
docker run --gpus all \
  -v "$(pwd)/training/data:/app/training/data" \
  -v "$(pwd)/training/model:/app/training/model" \
  address-parser-training \
  python -m training.train
```

On Windows (PowerShell), replace `$(pwd)` with `${PWD}`.

---

## After Training

The trained model lands at `data-layer/training/model/`. It contains:

```
training/model/
├── config.json
├── model.safetensors      # ~260 MB
├── tokenizer.json
├── tokenizer_config.json
├── vocab.txt
└── label_config.json      # field label ↔ id mappings
```

### Start the service

```bash
cd data-layer
venv/bin/uvicorn service.main:app --port 8001 --reload
```

The service loads the model at startup (CPU, ~2–3 s). You'll see:
```
INFO  Loading address parser from training/model
INFO  Address parser ready.
```

### Test the endpoint

```bash
curl -s -X POST http://localhost:8001/parse-address \
  -H "Content-Type: application/json" \
  -d '{"address": "Unit 4, 35 Smallman Street, Bulimba QLD 4171"}' | python -m json.tool
```

Expected response:
```json
{
  "unit_type": "Unit",
  "unit_number": "4",
  "street_number": "35",
  "street_name": "Smallman",
  "street_type": "Street",
  "suburb": "Bulimba",
  "state": "Qld",
  "postcode": "4171"
}
```

---

## Overriding the model path

By default the service looks for the model at `training/model/` relative to the
working directory. Override with the `ADDRESS_MODEL_DIR` environment variable:

```bash
ADDRESS_MODEL_DIR=/absolute/path/to/model uvicorn service.main:app --port 8001
```

---

## Regenerating training data

If the parquet needs to be regenerated (e.g. after adding more GNAF addresses):

```bash
# From data-layer/ with the DB running:
venv/bin/python training/generate_address_data.py \
  --output training/data/address_training.parquet \
  --training --parquet

# Then re-run steps 3 and 4 above.
```
