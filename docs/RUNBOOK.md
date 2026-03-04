# 运维手册（Runbook）

## 1. 服务管理

```bash
sudo systemctl status cv-dashboard --no-pager
sudo systemctl status cv-api --no-pager
sudo systemctl restart cv-dashboard
sudo systemctl restart cv-api
```

日志查看:

```bash
sudo journalctl -u cv-dashboard -n 200 --no-pager
sudo journalctl -u cv-api -n 200 --no-pager
tail -n 200 /var/log/china-cv-agent/dashboard.log
tail -n 200 /var/log/china-cv-agent/api.log
```

## 2. 发布更新流程

```bash
cd /srv/china-cv-agent/app
git pull
source .venv/bin/activate
pip install -r requirements.txt
python scripts/sync_data.py --bucket oss://your-bucket/china-cv-agent --mode only_cache
sudo systemctl restart cv-dashboard cv-api
```

可使用 `scripts/deploy_update.sh` 一键执行。

## 3. 数据同步策略

- 日常: 仅同步 `cache/all_batches_cleaned.parquet`
- 大版本: 同步 `cache/` + `CVdata/`
- 同步后重启服务，确保新数据生效

## 4. 备份策略

- 每日增量: `cache/`、`output/`
- 每周全量: `cache/`、`output/`、`configs/`
- 保留周期: 7-14 天

可使用 `scripts/backup_to_oss.sh` 执行。

## 5. 监控建议（阿里云云监控）

至少配置以下告警规则:

- ECS CPU > 80% 持续 5 分钟
- ECS 内存 > 85% 持续 5 分钟
- 磁盘使用率 > 80%
- 端口存活检查:
  - `127.0.0.1:8501`（dashboard）
  - `127.0.0.1:8000`（api）
- Nginx 5xx 比例告警

## 6. 健康检查命令

```bash
curl -f http://127.0.0.1:8501/ >/dev/null && echo "dashboard ok"
curl -f http://127.0.0.1:8000/docs >/dev/null && echo "api ok"
curl -f http://127.0.0.1:8000/api/statistics/energy_distribution >/dev/null && echo "stats api ok"
```

## 7. 定时任务示例（crontab）

```cron
# 每天 02:30 同步最新 parquet 并重启服务
30 2 * * * /srv/china-cv-agent/app/scripts/deploy_update.sh >> /var/log/china-cv-agent/deploy_update.log 2>&1

# 每天 03:30 备份到 OSS
30 3 * * * /srv/china-cv-agent/app/scripts/backup_to_oss.sh oss://your-bucket/china-cv-agent/backup >> /var/log/china-cv-agent/backup.log 2>&1
```
