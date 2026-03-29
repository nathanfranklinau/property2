# Address Parser — Training Guide

Fine-tunes `distilbert-base-uncased` on Australian address examples to produce the model used by `POST /parse-address`.

**Estimated time on RTX 3060 (12 GB):** ~1 hour generate + ~1 hour prepare + ~6–10 hours train.

---

## Overview

Training runs on a Windows machine in WSL2 (native Linux filesystem). The generate step runs on Mac (needs DB access), then the parquet is copied to WSL for prepare + train.

---

## Step 1 — Generate training data (Mac)

Queries GNAF from PostgreSQL and writes permuted address examples to a parquet file. Run from `data-layer/`:

```bash
venv/bin/python training/generate_address_data.py \
  --output training/data/address_training.parquet \
  --states QLD
```

Output: `training/data/address_training.parquet` (~12M rows for QLD, ~2 GB)

To limit scope during development:
```bash
venv/bin/python training/generate_address_data.py \
  --output training/data/address_training.parquet \
  --states QLD \
  --limit 500000
```

---

## Step 2 — Copy to WSL

Copy the parquet and training scripts to the WSL machine's native filesystem. Using `/mnt/` is significantly slower — use the native Linux filesystem (`~/`):

```bash
# Example — adjust paths to match your setup
scp data-layer/training/data/address_training.parquet wsl-machine:~/property2/training/data/
```

Or copy the entire `data-layer/training/` directory if setting up from scratch.

---

## Step 3 — Set up Python environment (WSL)

Run from the `data-layer/` directory on the WSL machine:

```bash
python3 -m venv venv
venv/bin/pip install -r training/requirements-training.txt
```

---

## Step 4 — Prepare IOB dataset (WSL)

Tokenises the parquet with the DistilBERT tokeniser and assigns IOB2 labels. Writes intermediate parquet shards to avoid OOM, then saves a HuggingFace DatasetDict. Run from `data-layer/`:

```bash
venv/bin/python -m training.prepare_iob
```

Output: `training/data/iob_dataset/` (~9.3M examples, 3 train shards + 1 validation shard)

**Expected output:**
```
Prepared 9,320,386 examples (7.0% rows skipped due to alignment failures)
  train:      8,854,366 examples
  validation:   466,020 examples
```

Smoke-test on 50k rows (~2 min):
```bash
venv/bin/python -m training.prepare_iob --sample 50000
```

---

## Step 5 — Train (WSL, GPU)

Fine-tunes DistilBERT on the IOB dataset. Requires a CUDA-capable GPU. Run from `data-layer/`:

```bash
venv/bin/python -m training.train
```

Output: `training/model/` (~260 MB)

Training saves checkpoints every 2,000 steps. If interrupted, re-running resumes from the last checkpoint automatically.

**Expected validation F1 after 3 epochs: > 0.97**

---

## Step 6 — Copy model back to Mac

```bash
# Example — adjust paths to match your setup
scp -r wsl-machine:~/property2/training/model/ data-layer/training/model/
```

---

## After training

The model lands at `data-layer/training/model/`:

```
training/model/
├── config.json
├── model.safetensors      # ~260 MB
├── tokenizer.json
├── tokenizer_config.json
├── vocab.txt
└── label_config.json
```

Start the service (Mac):

```bash
cd data-layer
venv/bin/uvicorn service.main:app --port 8001 --reload
```

The model loads at startup (CPU, ~2–3 s). Test it:

```bash
curl -s -X POST http://localhost:8001/parse-address \
  -H "Content-Type: application/json" \
  -d '{"address": "Unit 4, 35 Smallman Street, Bulimba QLD 4171"}' | python -m json.tool
```

Expected:
```json
{
  "unit_type": "Unit",
  "unit_number": "4",
  "street_number": "35",
  "street_name": "Smallman",
  "street_type": "Street",
  "suburb": "Bulimba",
  "state": "QLD",
  "postcode": "4171"
}
```

To override the model path:
```bash
ADDRESS_MODEL_DIR=/path/to/model venv/bin/uvicorn service.main:app --port 8001
```

---

## Regenerating training data

If GNAF is updated or you want to expand to more states, repeat Steps 1–6:

```bash
# Mac — regenerate
venv/bin/python training/generate_address_data.py \
  --output training/data/address_training.parquet \
  --states QLD,NSW

# Copy to WSL, then in WSL:
venv/bin/python -m training.prepare_iob
venv/bin/python -m training.train
```
