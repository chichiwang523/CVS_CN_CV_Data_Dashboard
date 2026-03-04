#!/usr/bin/env bash
set -euo pipefail

echo "[bootstrap] update apt index..."
sudo apt update

echo "[bootstrap] install base packages..."
sudo apt install -y \
  python3.11 python3.11-venv python3-pip \
  git nginx curl unzip ca-certificates

echo "[bootstrap] create app user/directories..."
sudo useradd -m -s /bin/bash cvapp 2>/dev/null || true
sudo mkdir -p /srv/china-cv-agent /var/log/china-cv-agent
sudo chown -R cvapp:cvapp /srv/china-cv-agent /var/log/china-cv-agent

echo "[bootstrap] done."
echo "Next:"
echo "  1) clone repo to /srv/china-cv-agent/app"
echo "  2) create venv and pip install -r requirements.txt"
echo "  3) sync parquet data from OSS"
echo "  4) configure systemd + nginx"
