# ZF 商用车公告数据分析平台

基于中国商用车公告数据（第290-388批次，82万+车型记录）的专业分析平台，面向 ZF 管理层决策。

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. （推荐）从 OSS 同步数据
# python scripts/sync_data.py --bucket oss://your-bucket/china-cv-agent --mode only_cache

# 3. 构建数据缓存（首次运行，约60秒；若已有 cleaned parquet 可跳过）
python scripts/build_cache.py

# 4. 启动 Streamlit 看板
streamlit run dashboard/app.py

# 5. 启动 FastAPI 接口（可选）
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## 看板页面

| 页面 | 内容 |
|------|------|
| 管理层概览 | KPI卡片、能源结构趋势、Top10主机厂、BEV趋势、EBS渗透率 |
| 市场趋势 | 主机厂份额变化、车辆类型结构、质量分布、品牌集中度 |
| 电动化分析 | BEV趋势、电驱桥vs集中驱动、电机供应商、电池化学/供应商 |
| 制动系统 | ABS供应商份额、ZF vs Bosch vs Knorr趋势、EBS渗透率 |
| 变速箱分析 | 变速箱类型分布、覆盖率趋势 |
| 竞争对手 | 三方提及率趋势、按车辆类型/主机厂配套分析 |
| 供应链 | 发动机/电机/电池/桥供应商分析 |
| 数据查询 | 多维筛选、列选择、分页、CSV导出 |

## 离线脚本

```bash
# 数据质量检查
python scripts/quality_check.py

# 生成批次PNG图表
python scripts/generate_batch_charts.py --batch 388 387

# 导出Excel（含统计工作表）
python scripts/export_excel.py --start 380 --end 388
```

## API 接口

- `GET /api/vehicles/` — 车辆查询（筛选/分页）
- `GET /api/statistics/energy_distribution` — 能源类型分布
- `GET /api/statistics/top_manufacturers` — 主机厂排名
- `GET /api/statistics/abs_market_share` — ABS市场份额
- `GET /api/statistics/bev_analysis` — BEV深度分析
- `GET /api/statistics/competitor_mentions` — 竞争对手提及统计

API 文档: http://localhost:8000/docs

## 服务器部署（ECS）

- 部署手册: `docs/DEPLOYMENT.md`
- 运维手册: `docs/RUNBOOK.md`
- 初始化脚本: `deploy/ecs_bootstrap.sh`
- 服务配置脚本: `deploy/setup_services.sh`
- HTTPS 启用脚本: `deploy/enable_https.sh`
- 数据同步脚本: `scripts/sync_data.py`
- 自动更新脚本: `scripts/deploy_update.sh`
- 备份脚本: `scripts/backup_to_oss.sh`

## 项目结构

```
├── CVdata/              # 原始数据（99批JSON + XLSX）
├── cache/               # Parquet缓存
├── src/
│   ├── config.py        # 配置（路径、批次映射、竞争对手）
│   ├── data_loader.py   # 数据加载与缓存
│   ├── data_cleaner.py  # 数据清洗流水线
│   ├── remarks_parser.py # 备注文本结构化
│   ├── charts.py        # Plotly图表工厂
│   └── analysis/        # 6个分析模块
├── dashboard/           # Streamlit看板（8个页面）
├── api/                 # FastAPI接口
├── scripts/             # 离线脚本
└── output/charts/       # 生成的PNG图表
```
