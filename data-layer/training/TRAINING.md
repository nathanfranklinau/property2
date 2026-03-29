# Address Parser — Training Guide

Fine-tunes `distilbert-base-uncased` on Australian address examples to produce the model used by `POST /parse-address`.

**Estimated time on RTX 3060 (12 GB):** ~1 hour generate + ~1 hour prepare + ~6–10 hours train.

---

## Prerequisites

- **Docker** with GPU support
  - Linux: [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
  - Windows: Docker Desktop + WSL2 backend + NVIDIA driver ≥ 527
- **Python venv** at `data-layer/venv` (only needed for generate step — reads from DB)
- **PostgreSQL** running with GNAF data loaded (only needed for generate step)

> **WSL2 users:** Run from the native Linux filesystem (`~/`), **not** from `/mnt/e/` or any Windows-mounted drive. Docker I/O through `/mnt/` is 3–5× slower due to the 9P bridge. Copy your working directory if needed:
> ```bash
> cp -r /mnt/e/Projects/property2/data-layer ~/property2/data-layer
> cd ~/property2/data-layer
> ```

---

## The Pipeline

All steps are driven by a single script. Run from `data-layer/`:

```
bash training/run_docker_training.sh [STEPS] [OPTIONS]
```

| Step flag | What it does | Needs |
|---|---|---|
| `--generate-data` | Query GNAF → `address_training.parquet` | DB + venv |
| `--build` | Build Docker image `address-parser-training` | Docker |
| `--prepare` | Tokenise + IOB2-label parquet → `iob_dataset/` | Docker + parquet |
| `--train` | Fine-tune DistilBERT → `training/model/` | Docker GPU + iob_dataset |

Options:

| Option | Default | Description |
|---|---|---|
| `--states S` | `QLD` | Comma-separated states, e.g. `QLD,NSW` |
| `--limit N` | all | Max GNAF addresses to process |
| `--sample N` | all | Prepare IOB on N rows — fast smoke-test |

---

## Step 1 — Generate training data

Queries GNAF from PostgreSQL and writes permuted address examples to a parquet file. Requires the DB to be running and the venv to have `psycopg2` installed.

```bash
bash training/run_docker_training.sh --generate-data
```

Output: `training/data/address_training.parquet` (~12M rows for QLD, ~2 GB)

To limit scope during development:
```bash
bash training/run_docker_training.sh --generate-data --limit 500000
```

---

## Step 2 — Build the Docker image

Only needed once, or after changes to `Dockerfile.training` or `requirements-training.txt`.

```bash
bash training/run_docker_training.sh --build
```

---

## Step 3 — Prepare IOB dataset

Tokenises the parquet with the DistilBERT tokeniser and assigns IOB2 labels. Runs in Docker (CPU). Writes intermediate parquet shards to avoid OOM, then saves a HuggingFace DatasetDict.

```bash
bash training/run_docker_training.sh --prepare
```

Output: `training/data/iob_dataset/` (~9.3M examples, 3 train shards + 1 validation shard)

**Expected output:**
```
Prepared 9,320,386 examples (7.0% rows skipped due to alignment failures)
  train:      8,854,366 examples
  validation:   466,020 examples
```

Smoke-test first on 50k rows (~2 min):
```bash
bash training/run_docker_training.sh --prepare --sample 50000
```

---

## Step 4 — Train

Fine-tunes DistilBERT on the IOB dataset. Requires a CUDA-capable GPU.

```bash
bash training/run_docker_training.sh --train
```

Output: `training/model/` (~260 MB)

Training saves checkpoints every 2,000 steps. If interrupted, re-running `--train` resumes from the last checkpoint automatically.

**Expected validation F1 after 3 epochs: > 0.97**

---

## Common combinations

```bash
# Everything from scratch:
bash training/run_docker_training.sh --generate-data --build --prepare --train

# Parquet already exists — build + prepare + train:
bash training/run_docker_training.sh --build --prepare --train

# Image already built, iob_dataset ready — just train:
bash training/run_docker_training.sh --train

# Rebuild image and retrain (iob_dataset unchanged):
bash training/run_docker_training.sh --build --train

# Smoke-test the full pipeline on 50k rows:
bash training/run_docker_training.sh --build --prepare --train --sample 50000
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

Start the service:

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

If GNAF is updated or you want to expand to more states:

```bash
bash training/run_docker_training.sh --generate-data --states QLD,NSW
# Then re-prepare and retrain:
bash training/run_docker_training.sh --build --prepare --train
```
