"""
ZF 商用车公告数据分析平台 -- 全局配置
"""
import os
from pathlib import Path

# ── 路径 ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "CVdata"
CACHE_DIR = PROJECT_ROOT / "cache"
OUTPUT_DIR = PROJECT_ROOT / "output"
CHARTS_DIR = OUTPUT_DIR / "charts"

RAW_PARQUET = CACHE_DIR / "all_batches_raw.parquet"
CLEANED_PARQUET = CACHE_DIR / "all_batches_cleaned.parquet"

BATCH_RANGE = (290, 388)

# ── 批次 -> 日期映射 ─────────────────────────────────
# 388 = 2025-12, 每批次 = 1个月, 向前推算
_ANCHOR_BATCH = 388
_ANCHOR_YEAR = 2025
_ANCHOR_MONTH = 12

def batch_to_date(batch: int) -> str:
    """返回 'YYYY-MM' 格式"""
    delta = _ANCHOR_BATCH - batch
    total_months = _ANCHOR_YEAR * 12 + _ANCHOR_MONTH - 1 - delta
    y, m = divmod(total_months, 12)
    return f"{y:04d}-{m + 1:02d}"

def batch_to_label(batch: int) -> str:
    """返回 '第XXX批 (YYYY-MM)'"""
    return f"第{batch}批 ({batch_to_date(batch)})"

BATCH_DATES = {b: batch_to_date(b) for b in range(BATCH_RANGE[0], BATCH_RANGE[1] + 1)}

# ── 能源类型映射 ──────────────────────────────────────
ENERGY_TYPE_MAP = {
    "Gasoline": "传统燃料",
    "BEV": "纯电动",
    "Hydrogen": "氢燃料电池",
    "Methanol": "甲醇",
    "PHEV": "插电混动",
    "Natural Gas": "天然气",
    "Hybrid": "混合动力",
    "Range Extender": "增程式",
}

ENERGY_TYPE_ORDER = [
    "传统燃料", "纯电动", "氢燃料电池", "插电混动",
    "增程式", "混合动力", "甲醇", "天然气", "未知",
]

# ── 竞争对手关键词 ────────────────────────────────────
COMPETITOR_KEYWORDS = {
    "ZF/采埃孚": ["威伯科", "采埃孚", "WABCO", "wabco", "ZF"],
    "Knorr/克诺尔": ["克诺尔", "Knorr", "knorr", "东科克诺尔"],
    "Bosch/博世": ["博世", "Bosch", "bosch"],
    "瑞立科密": ["瑞立科密", "瑞立"],
    "万安科技": ["万安"],
    "元丰股份": ["元丰"],
    "博瑞克": ["博瑞克"],
}

# 桥类企业关键词 — 用于判断电驱桥拓扑
AXLE_MAKER_KEYWORDS = ["车桥", "桥有限", "法士特齿轮", "德纳"]

# OEM 自研关键词
OEM_MAKER_KEYWORDS = [
    "汽车股份", "客车", "汽车有限", "汽车制造",
    "比亚迪", "吉利", "蔚来", "小鹏",
]

# ── 车辆类型大类映射 ──────────────────────────────────
VEHICLE_CATEGORY_RULES = [
    ("客车", ["客车"]),
    ("货车", ["载货", "自卸", "厢式运输", "仓栅", "冷藏", "平板运输", "翼开启", "封闭货车", "多用途货车", "越野货车", "轻型货车", "中型货车", "重型货车"]),
    ("牵引车", ["牵引"]),
    ("半挂车", ["半挂", "中置轴挂车", "全挂车"]),
    ("专用车", [
        "搅拌", "起重", "清障", "垃圾", "洒水", "消防", "救护", "邮政",
        "清洗", "扫路", "抑尘", "环卫", "供液", "油罐", "粉粒", "散装",
        "混凝土泵", "随车起重", "高空作业", "吸污", "吸粪", "运油",
        "加油", "检测车", "电源车", "工程车", "爆破器材", "畜禽运输",
        "气瓶运输", "车辆运输", "除雪", "养护", "售货", "吸尘",
        "防撞缓冲", "易燃液体", "医疗", "流动服务", "救险", "指挥车",
        "铝合金运油", "保温", "教练车", "商务车",
        "绿化喷洒", "通信车", "宿营车", "囚车", "腐蚀性物品", "修井",
        "沥青", "校车", "宣传车", "运钞", "巡逻", "压裂", "排水抢险",
        "勘察", "监测车", "殡仪", "罐车", "餐车", "检修", "运兵",
        "舞台车", "雏禽", "液体运输", "邮政", "特种车", "罐式运输",
        "抢修", "供水", "供气", "充电", "采血", "体检", "防化",
        "扫雪", "护栏清洗", "混凝土运输", "粉料", "饲料运输",
        "洗扫", "电视车", "装备车", "渣料", "污泥", "车厢可卸",
        "布料泵", "输送泵", "粮食运输", "水泥运输", "烟花爆竹",
        "化工液体", "砂浆运输", "图书馆", "厨余", "泵车",
    ]),
    ("旅居车", ["旅居"]),
    ("摩托车", ["摩托"]),
    ("轿车", ["轿车"]),
    ("乘用车", ["乘用车", "乘用"]),
]

def classify_vehicle(vtype: str) -> str:
    if not vtype:
        return "其他"
    for category, keywords in VEHICLE_CATEGORY_RULES:
        if any(kw in vtype for kw in keywords):
            return category
    return "其他"

# ── ZF CVS 市场分组 ───────────────────────────────────
# ZF 商用车核心市场：客车、中重卡、牵引车、挂车、专用车
ZF_MARKET_SEGMENTS = {
    "ZF 核心市场 (全部)": ["客车", "货车", "牵引车", "半挂车", "专用车"],
    "客车": ["客车"],
    "货车 (载货/自卸/厢式等)": ["货车"],
    "牵引车": ["牵引车"],
    "半挂车/挂车": ["半挂车"],
    "专用车": ["专用车"],
    "全部车型 (含非商用车)": None,  # None = 不筛选
}

# 与 ZF 业务无关的车辆类别
NON_ZF_CATEGORIES = {"摩托车", "轿车", "乘用车", "旅居车"}

# ── 质量分级（吨） ────────────────────────────────────
def classify_mass(mass_kg) -> str:
    if mass_kg is None or mass_kg != mass_kg:
        return "未知"
    t = mass_kg / 1000
    if t <= 3.5:
        return "微型/轻型 (≤3.5t)"
    if t <= 12:
        return "中型 (3.5-12t)"
    if t <= 25:
        return "重型 (12-25t)"
    return "超重型 (>25t)"

# ── ZF 蓝色主题 Plotly ─────────────────────────────────
ZF_BLUE = "#003399"
ZF_COLORS = [
    "#003399", "#0066CC", "#3399FF", "#66BBFF", "#99DDFF",
    "#E63946", "#F4A261", "#2A9D8F", "#264653", "#E9C46A",
    "#606060", "#909090", "#C0C0C0",
]

PLOTLY_LAYOUT = dict(
    font=dict(family="Microsoft YaHei, SimHei, Arial", size=13),
    paper_bgcolor="white",
    plot_bgcolor="#FAFAFA",
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

# ── Dashboard 列裁剪 ─────────────────────────────────
# 64 列中仅 46 列被 dashboard 实际使用；预加载时裁剪可节省 ~30% IO + ~35% 内存
DASHBOARD_COLUMNS: list[str] = [
    "batch", "model_code", "brand", "vehicle_type", "manufacturer",
    "total_mass", "curb_weight", "length", "width", "emission_standard",
    "engine_maker", "displacement", "power_kw",
    "ABS_model", "ABS_maker", "transmission_type", "transmission_model",
    "bridge_maker", "_remarks_raw",
    "batch_date", "energy_clean",
    "engine_maker_display", "manufacturer_display",
    "vehicle_category", "mass_class",
    "abs_maker_clean", "abs_maker_display", "bridge_maker_clean",
    "parsed_abs_makers", "parsed_abs_models",
    "parsed_has_abs", "parsed_has_ebs", "parsed_optional_ebs",
    "parsed_zf_mention", "parsed_bosch_mention", "parsed_knorr_mention",
    "parsed_motor_rated_kw", "parsed_motor_peak_kw",
    "parsed_battery_chemistry", "parsed_battery_cell_makers",
    "parsed_battery_pack_makers", "parsed_battery_kwh",
    "parsed_tz_number", "parsed_tz_suffix_type", "parsed_tz_maker_code",
    "parsed_drive_topology",
]

# ── 认证 ──────────────────────────────────────────────
AUTH_DOMAIN = "zf.com"
ADMIN_EMAILS: list[str] = ["xingchi.wang@zf.com"]
USERS_JSON = PROJECT_ROOT / "data" / "users.json"

# SMTP — 阿里云 DirectMail（从环境变量读取，未配置则降级为仅面板审批）
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
