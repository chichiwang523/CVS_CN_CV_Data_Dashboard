#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <domain>"
  echo "Example: $0 data.example.com"
  exit 1
fi

DOMAIN="$1"
APP_ROOT="/srv/china-cv-agent/app"

echo "[https] install certbot..."
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

echo "[https] issue certificate..."
sudo certbot certonly --nginx -d "$DOMAIN" --non-interactive --agree-tos -m admin@"$DOMAIN" || {
  echo "certbot 申请失败，请检查域名 DNS 解析是否已指向本机。"
  exit 1
}

echo "[https] generate nginx https conf..."
tmp_conf="$(mktemp)"
sed "s/your.domain.com/$DOMAIN/g" "$APP_ROOT/deploy/nginx/china-cv-agent.https.conf" > "$tmp_conf"
sudo mv "$tmp_conf" /etc/nginx/sites-available/china-cv-agent.conf
sudo ln -sf /etc/nginx/sites-available/china-cv-agent.conf /etc/nginx/sites-enabled/china-cv-agent.conf

echo "[https] validate and reload nginx..."
sudo nginx -t
sudo systemctl reload nginx

echo "[https] done: https://$DOMAIN"
