#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_LAYER_DIR="$(cd "$TRAINING_DIR/.." && pwd)"
ZIP_PATH="$SCRIPT_DIR/training.zip"


#VULTR_PLAN=vc2-1c-1gb

#.49/hour
#VULTR_PLAN=vcg-a16-6c-64g-16vram

# 2.49
#VULTR_PLAN=vbm-72c-480gb-gh200-gpu

#2.39
VULTR_PLAN=vcg-a100-12c-120g-80vram

#REGION=atl
#REGION=syd
REGION=nrt

# ---------------------------------------------------------------------------
# 1. Create zip of training directory (excluding automation/ and model2-5/)
# ---------------------------------------------------------------------------
echo "--- Creating training bundle ---"
cd "$DATA_LAYER_DIR"
# rm -f "$ZIP_PATH"
# zip -r "$ZIP_PATH" training/ \
#   -x "training/automation/*" \
#   -x "training/model/*" \
#   -x "training/model2/*" \
#   -x "training/model3/*" \
#   -x "training/model4/*" \
#   -x "training/model5/*" \
#   -x "training/__pycache__/*" \
#   -x "training/*.pyc" \
#   -x "training/data/*.csv" \
#   -x "training/data/*.parquet"
# echo "Bundle created: $ZIP_PATH ($(du -sh "$ZIP_PATH" | cut -f1))"

# ---------------------------------------------------------------------------
# 2. Deploy Vultr instance
# ---------------------------------------------------------------------------
echo "--- Deploying Vultr instance ---"
INSTANCE_JSON=$(vultr-cli instance create \
  --region $REGION \
  --os 2284 \
  --label "Ubuntu Training" \
  --plan $VULTR_PLAN \
  --ssh-keys b47e0a48-f861-48db-be7f-9a3f8190d166 \
  --script-id cf17c02e-3e65-48fa-ab8a-5ee8532665db \
  --auto-backup false \
  -o json)

# ---------------------------------------------------------------------------
# 3. Extract instance ID
# ---------------------------------------------------------------------------
INSTANCE_ID=$(echo "$INSTANCE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['instance']['id'])")
echo "Instance ID: $INSTANCE_ID"

# ---------------------------------------------------------------------------
# 4. Sleep 30 seconds for instance to initialise
# ---------------------------------------------------------------------------
echo "--- Waiting 30s for instance to initialise ---"
sleep 30

# ---------------------------------------------------------------------------
# 5 & 6. Poll until we have a main IP
# ---------------------------------------------------------------------------
echo "--- Fetching instance details ---"
INSTANCE_DETAILS=$(vultr-cli instance get "$INSTANCE_ID" -o json)
IP=$(echo "$INSTANCE_DETAILS" | python3 -c "import sys,json; print(json.load(sys.stdin)['instance']['main_ip'])")
echo "Instance IP: $IP"

SSH_OPTS="-n -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes"

# ---------------------------------------------------------------------------
# 7. Wait until SSH is reachable
# ---------------------------------------------------------------------------
echo "--- Waiting for SSH on $IP ---"
until ssh $SSH_OPTS root@"$IP" "exit 0" 2>/dev/null; do
  echo "  Not ready, retrying in 10s..."
  sleep 10
done
echo "SSH is up."

# ---------------------------------------------------------------------------
# 8. (Implicitly exited after connectivity check above)
# 9. SCP zip and setup script to server
# ---------------------------------------------------------------------------
echo "--- Copying files to server ---"
ssh $SSH_OPTS root@"$IP" "mkdir -p /app"
scp -o StrictHostKeyChecking=no "$ZIP_PATH" root@"$IP":/app/training.zip
scp -o StrictHostKeyChecking=no "$SCRIPT_DIR/server_setup.sh" root@"$IP":/app/server_setup.sh

# ---------------------------------------------------------------------------
# 10-14. Launch setup in background (detached so SSH can exit safely)
# ---------------------------------------------------------------------------
echo "--- Launching server setup in background ---"
ssh $SSH_OPTS root@"$IP" "chmod +x /app/server_setup.sh && nohup /app/server_setup.sh > /app/setup.log 2>&1 &"
echo "Training started on $IP (instance $INSTANCE_ID). Monitoring..."

# ---------------------------------------------------------------------------
# 15. Monitor until training completes
# ---------------------------------------------------------------------------
while true; do
  if ssh $SSH_OPTS root@"$IP" "test -f /app/training.done" 2>/dev/null; then
    echo "Training completed successfully ($(date))."
    STATUS="done"
    break
  elif ssh $SSH_OPTS root@"$IP" "test -f /app/training.failed" 2>/dev/null; then
    echo "Training FAILED ($(date)). Check /app/setup.log on the server."
    STATUS="failed"
    break
  fi
  echo "  Still training... ($(date))"
  sleep 60
done

# ---------------------------------------------------------------------------
# 16. Copy trained model back locally
# ---------------------------------------------------------------------------
echo "--- Copying setup.log back ---"
scp -o StrictHostKeyChecking=no root@"$IP":/app/setup.log "$SCRIPT_DIR/setup.log"
echo "Log saved to: $SCRIPT_DIR/setup.log"

if [ "$STATUS" = "done" ]; then
  echo "--- Copying model back ---"
  MODEL_DEST="$TRAINING_DIR/model_$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$MODEL_DEST"
  scp -r -o StrictHostKeyChecking=no root@"$IP":/app/training/model/ "$MODEL_DEST/"
  echo "Model saved to: $MODEL_DEST"
fi

# # ---------------------------------------------------------------------------
# # 17. Destroy instance
# # ---------------------------------------------------------------------------
# echo "--- Destroying instance $INSTANCE_ID ---"
# vultr-cli instance delete "$INSTANCE_ID"
# echo "Instance destroyed."
