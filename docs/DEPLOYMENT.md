# 阿里云 ECS 部署手册

本文档用于将本项目部署到阿里云 ECS，并通过公网对用户提供看板访问能力。

## 0. 目标架构

- Streamlit: `127.0.0.1:8501`
- FastAPI: `127.0.0.1:8000`
- Nginx: `80/443` 反向代理入口
- 数据来源: OSS（推荐）+ 本地 Parquet 缓存

## 1. 前置条件

- ECS: 32GB RAM / 1TB 磁盘（已满足）
- OS: Ubuntu 22.04 LTS（推荐）
- 安全组已放行:
  - `22`（SSH）
  - `80`（HTTP）
  - `443`（HTTPS，后续启用）
- 已准备:
  - GitHub 仓库地址
  - 阿里云 OSS Bucket（含数据）

## 2. 基础初始化

可直接执行 `deploy/ecs_bootstrap.sh`，或手工执行下面命令:

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx curl unzip
sudo useradd -m -s /bin/bash cvapp || true
sudo mkdir -p /srv/china-cv-agent /var/log/china-cv-agent
sudo chown -R cvapp:cvapp /srv/china-cv-agent /var/log/china-cv-agent
```

## 3. 代码部署

```bash
sudo -u cvapp -H bash -lc '
cd /srv/china-cv-agent
git clone <your_repo_url> app
cd app
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
'
```

## 4. 数据部署（推荐 OSS 拉取）

推荐至少拉取:

- `cache/all_batches_cleaned.parquet`

可选拉取（用于重建缓存）:

- `CVdata/` 原始数据目录

同步方式见 `docs/RUNBOOK.md` 与 `scripts/sync_data.py`。

## 5. 启动服务（临时手工验证）

```bash
# Streamlit
sudo -u cvapp -H bash -lc '
cd /srv/china-cv-agent/app
source .venv/bin/activate
streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
'

# FastAPI
sudo -u cvapp -H bash -lc '
cd /srv/china-cv-agent/app
source .venv/bin/activate
uvicorn api.main:app --host 127.0.0.1 --port 8000
'
```

## 6. Nginx 反向代理

复制 `deploy/nginx/china-cv-agent.http.conf` 到:

- `/etc/nginx/sites-available/china-cv-agent.conf`

并启用:

```bash
sudo ln -sf /etc/nginx/sites-available/china-cv-agent.conf /etc/nginx/sites-enabled/china-cv-agent.conf
sudo nginx -t
sudo systemctl reload nginx
```

## 7. systemd 托管（推荐）

复制以下文件:

- `deploy/systemd/cv-dashboard.service` -> `/etc/systemd/system/`
- `deploy/systemd/cv-api.service` -> `/etc/systemd/system/`

启用:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cv-dashboard cv-api
sudo systemctl status cv-dashboard --no-pager
sudo systemctl status cv-api --no-pager
```

## 8. HTTPS（生产）

1. 域名解析到 ECS 公网 IP
2. 安装 certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

3. 申请证书:

```bash
sudo certbot --nginx -d your.domain.com
```

4. 校验:

```bash
curl -I https://your.domain.com
```

## 9. 验证清单

- `http://<公网IP>/` 可打开看板
- `http://<公网IP>/docs` 可打开 API 文档
- `systemctl status cv-dashboard` 为 `active (running)`
- `systemctl status cv-api` 为 `active (running)`
- `nginx -t` 无报错

## 10. 常见问题

- 页面能打开但数据为空: 检查 `cache/all_batches_cleaned.parquet` 是否存在
- 502 Bad Gateway: 检查 Streamlit/Uvicorn 是否监听在 `127.0.0.1`
- 每次重启丢服务: 检查 `systemctl enable` 是否已执行
