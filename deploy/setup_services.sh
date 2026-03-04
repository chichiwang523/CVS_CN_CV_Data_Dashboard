#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/srv/china-cv-agent/app"

echo "[setup] install systemd services..."
sudo cp "$APP_ROOT/deploy/systemd/cv-dashboard.service" /etc/systemd/system/
sudo cp "$APP_ROOT/deploy/systemd/cv-api.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cv-dashboard cv-api

echo "[setup] install nginx site..."
sudo cp "$APP_ROOT/deploy/nginx/china-cv-agent.http.conf" /etc/nginx/sites-available/china-cv-agent.conf
sudo ln -sf /etc/nginx/sites-available/china-cv-agent.conf /etc/nginx/sites-enabled/china-cv-agent.conf
sudo nginx -t
sudo systemctl reload nginx

echo "[setup] done."
echo "Check:"
echo "  systemctl status cv-dashboard --no-pager"
echo "  systemctl status cv-api --no-pager"
