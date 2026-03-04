#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <oss_backup_path>"
  echo "Example: $0 oss://your-bucket/china-cv-agent/backup"
  exit 1
fi

BACKUP_PATH="$1"
APP_DIR="${APP_DIR:-/srv/china-cv-agent/app}"
DATE_TAG="$(date +%F_%H%M%S)"
SNAPSHOT="${BACKUP_PATH%/}/${DATE_TAG}"

if ! command -v ossutil >/dev/null 2>&1; then
  echo "ossutil not found. Please install and config first."
  exit 1
fi

echo "[backup] snapshot => ${SNAPSHOT}"

ossutil sync -u "${APP_DIR}/cache/" "${SNAPSHOT}/cache/"
ossutil sync -u "${APP_DIR}/output/" "${SNAPSHOT}/output/"

echo "[backup] done"
