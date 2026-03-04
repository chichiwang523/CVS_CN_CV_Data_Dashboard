#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/srv/china-cv-agent/app"
BUCKET="${OSS_BUCKET:-oss://your-bucket-name/china-cv-agent}"
MODE="${SYNC_MODE:-only_cache}"

cd "$APP_DIR"
echo "[update] pull latest code..."
git pull

echo "[update] install requirements..."
source .venv/bin/activate
pip install -r requirements.txt

echo "[update] sync latest data from OSS..."
python scripts/sync_data.py --bucket "$BUCKET" --mode "$MODE" --project-root "$APP_DIR"

echo "[update] restart services..."
sudo systemctl restart cv-dashboard cv-api

echo "[update] done"
