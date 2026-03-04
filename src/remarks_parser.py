"""
备注文本 (_remarks_raw) + battery_type 结构化提取
从非结构化文本中提取 ABS/EBS/变速箱/电机功率/电池/竞争对手 信息
"""
from __future__ import annotations

import re
from typing import Optional

import pandas as pd
import numpy as np


# ── ABS / EBS 提取 ───────────────────────────────────

_ABS_MODEL_PATTERN = re.compile(
    r'ABS[^:：]*?(?:型号|产品型号)[/／]?[^:：]*?[:：]\s*'
    r'([A-Za-z0-9\-\s/]+)',
    re.IGNORECASE,
)

_ABS_MAKER_PATTERN = re.compile(
    r'ABS[^.;；。]*?(?:生产企业|生产厂家|厂家)[：:]\s*'
    r'([^,，;；.\n]+?(?:有限公司|股份有限公司))',
)

_ABS_PAIR_PATTERN = re.compile(
    r'([A-Za-z0-9\-\s/]{2,40}?)\s*/\s*'
    r'([^,，;；.\n]+?(?:有限公司|股份有限公司))',
)

_EBS_PATTERN = re.compile(r'EBS', re.IGNORECASE)
_OPTIONAL_EBS_PATTERN = re.compile(r'选装[^.;；。]{0,10}EBS', re.IGNORECASE)


def _extract_abs_makers_from_text(text: str) -> list[str]:
    """从备注文本中提取所有 ABS 相关企业名。"""
    if not text:
        return []
    makers = set()
    for m in _ABS_MAKER_PATTERN.finditer(text):
        makers.add(m.group(1).strip())
    abs_section = ""
    for seg in re.split(r'[.。]', text):
        if "ABS" in seg.upper():
            abs_section += seg + "."
    if abs_section:
        for m in _ABS_PAIR_PATTERN.finditer(abs_section):
            maker = m.group(2).strip()
            if len(maker) > 4:
                makers.add(maker)
    return list(makers)


def _extract_abs_models_from_text(text: str) -> list[str]:
    if not text:
        return []
    models = set()
    for seg in re.split(r'[.。]', text):
        if "ABS" not in seg.upper():
            continue
        for m in _ABS_PAIR_PATTERN.finditer(seg):
            model = m.group(1).strip()
            if model and len(model) >= 2:
                models.add(model)
    return list(models)


# ── 竞争对手识别 ──────────────────────────────────────

_ZF_KEYWORDS = re.compile(r'威伯科|采埃孚|WABCO|wabco', re.IGNORECASE)
_BOSCH_KEYWORDS = re.compile(r'博世|Bosch|bosch', re.IGNORECASE)
_KNORR_KEYWORDS = re.compile(r'克诺尔|Knorr|knorr|东科克诺尔', re.IGNORECASE)


def _extract_competitor_mentions(text: str) -> dict:
    if not text:
        return {"zf": [], "bosch": [], "knorr": []}
    result = {"zf": [], "bosch": [], "knorr": []}
    for m in _ZF_KEYWORDS.finditer(text):
        ctx = text[max(0, m.start() - 30):min(len(text), m.end() + 60)]
        result["zf"].append(ctx.strip())
    for m in _BOSCH_KEYWORDS.finditer(text):
        ctx = text[max(0, m.start() - 30):min(len(text), m.end() + 60)]
        result["bosch"].append(ctx.strip())
    for m in _KNORR_KEYWORDS.finditer(text):
        ctx = text[max(0, m.start() - 30):min(len(text), m.end() + 60)]
        result["knorr"].append(ctx.strip())
    return result


# ── 电机功率提取 ──────────────────────────────────────

_RATED_POWER_PATTERN = re.compile(
    r'额定功率[：:]\s*(\d+[\.\d]*)\s*[kK][wW]', re.IGNORECASE
)
_PEAK_POWER_PATTERN = re.compile(
    r'峰值功率[：:]\s*(\d+[\.\d]*)\s*[kK][wW]', re.IGNORECASE
)


# ── 电池信息提取 ──────────────────────────────────────

def _extract_battery_chemistry(text: str) -> str:
    if not text:
        return "未知"
    if "磷酸铁锂" in text:
        return "磷酸铁锂"
    if "三元" in text:
        return "三元锂"
    if "锰酸锂" in text:
        return "锰酸锂"
    if "钠离子" in text:
        return "钠离子"
    if "铅酸" in text:
        return "铅酸"
    return "未知"


_BATTERY_MAKER_PATTERN = re.compile(
    r'(?:储能装置|动力蓄电池|蓄电池|电池)[^:：]{0,20}?'
    r'(?:生产企业|单体[^:：]{0,10}企业|总成[^:：]{0,10}企业)[：:]\s*'
    r'([^,，;；\n]+?(?:有限公司|股份有限公司))',
)

_CAPACITY_KWH_PATTERN = re.compile(r'(\d+[\.\d]*)\s*[kK][wW][hH]')
_CAPACITY_AH_PATTERN = re.compile(r'(?:容量|Ah)[：:]?\s*(\d+[\.\d]*)\s*[aA][hH]|(\d+[\.\d]*)\s*[aA][hH]')


def _extract_battery_cell_makers(text: str) -> list[str]:
    if not text:
        return []
    makers = set()
    for m in _BATTERY_MAKER_PATTERN.finditer(text):
        maker = m.group(1).strip()
        if len(maker) > 4:
            makers.add(maker)
    general = re.findall(
        r'(?:单体|电芯)[^:：]{0,15}?(?:生产企业|企业)[：:]\s*'
        r'([^,，;；\n]+?(?:有限公司|股份有限公司))',
        text,
    )
    for g in general:
        if len(g.strip()) > 4:
            makers.add(g.strip())
    return list(makers)


def _extract_battery_pack_makers(text: str) -> list[str]:
    if not text:
        return []
    makers = set()
    pack_pattern = re.compile(
        r'(?:总成)[^:：]{0,15}?(?:生产企业|企业)[：:]\s*'
        r'([^,，;；\n]+?(?:有限公司|股份有限公司))',
    )
    for m in pack_pattern.finditer(text):
        maker = m.group(1).strip()
        if len(maker) > 4:
            makers.add(maker)
    return list(makers)


def _extract_capacity_kwh(text: str) -> Optional[float]:
    if not text:
        return None
    m = _CAPACITY_KWH_PATTERN.search(text)
    if m:
        val = float(m.group(1))
        if 1 < val < 2000:
            return val
    return None


def _extract_capacity_ah(text: str) -> Optional[float]:
    if not text:
        return None
    m = _CAPACITY_AH_PATTERN.search(text)
    if m:
        val = float(m.group(1) or m.group(2))
        if 1 < val < 10000:
            return val
    return None


# ── TZ 电机型号解析 ───────────────────────────────────

_TZ_PATTERN = re.compile(r'TZ(\d+)(XS|XY|XD)?[\-_]?([A-Za-z0-9]*)')


def _parse_tz_model(engine_model: str) -> dict:
    result = {"tz_number": None, "tz_suffix_type": None, "tz_maker_code": None}
    if not engine_model:
        return result
    m = _TZ_PATTERN.search(engine_model)
    if m:
        result["tz_number"] = int(m.group(1))
        result["tz_suffix_type"] = m.group(2) or ""
        code = m.group(3) or ""
        for prefix in ["HD", "DN", "SZF", "SF", "TPG", "LKM", "CDW", "ZQV", "YTC", "SYM", "LGE", "ICS", "KL"]:
            if code.upper().startswith(prefix):
                result["tz_maker_code"] = prefix
                break
        if not result["tz_maker_code"] and code:
            result["tz_maker_code"] = code[:6]
    return result


# ── 电驱拓扑推断 ──────────────────────────────────────

_AXLE_KW = ["车桥", "桥有限", "法士特齿轮", "德纳"]
_OEM_KW = ["汽车股份", "客车", "汽车有限", "汽车制造", "比亚迪", "吉利", "蔚来", "小鹏"]


def _infer_drive_topology(engine_maker: str, energy_type: str) -> str:
    """参考性推断: 电驱桥 / 集中驱动 / OEM自研 / 未知"""
    if energy_type not in ("BEV", "纯电动"):
        return ""
    if not engine_maker:
        return "未知"
    parts = re.split(r'(?<=有限公司)', engine_maker)
    has_axle = any(any(kw in p for kw in _AXLE_KW) for p in parts if p.strip())
    if has_axle:
        return "电驱桥(参考)"
    is_oem = all(any(kw in p for kw in _OEM_KW) for p in parts if p.strip())
    if is_oem:
        return "OEM自研(参考)"
    return "集中驱动(参考)"


# ── 主函数: 对 DataFrame 做全量解析 ────────────────────

def parse_remarks(df: pd.DataFrame) -> pd.DataFrame:
    """
    对传入 DataFrame 添加 parsed_* 列。
    要求 df 包含 _remarks_raw, battery_type, engine_model, engine_maker, energy_type 列。
    """
    n = len(df)
    remarks = df["_remarks_raw"].fillna("").astype(str)
    bt = df["battery_type"].fillna("").astype(str) if "battery_type" in df.columns else pd.Series([""] * n)
    combined_text = remarks + " " + bt

    em = df["engine_model"].fillna("").astype(str) if "engine_model" in df.columns else pd.Series([""] * n)
    emk = df["engine_maker"].fillna("").astype(str) if "engine_maker" in df.columns else pd.Series([""] * n)
    et = df["energy_type"].fillna("").astype(str) if "energy_type" in df.columns else pd.Series([""] * n)

    # ABS / EBS
    parsed_abs_makers = remarks.apply(_extract_abs_makers_from_text)
    parsed_abs_models = remarks.apply(_extract_abs_models_from_text)
    df["parsed_abs_makers"] = parsed_abs_makers.apply(lambda x: "|".join(x) if x else "")
    df["parsed_abs_models"] = parsed_abs_models.apply(lambda x: "|".join(x) if x else "")
    df["parsed_has_abs"] = remarks.str.contains("ABS", case=False, na=False)
    df["parsed_has_ebs"] = remarks.str.contains("EBS", case=False, na=False)
    df["parsed_optional_ebs"] = remarks.apply(lambda t: bool(_OPTIONAL_EBS_PATTERN.search(t)))

    # 竞争对手
    comp = remarks.apply(_extract_competitor_mentions)
    df["parsed_zf_mention"] = comp.apply(lambda c: len(c["zf"]) > 0)
    df["parsed_bosch_mention"] = comp.apply(lambda c: len(c["bosch"]) > 0)
    df["parsed_knorr_mention"] = comp.apply(lambda c: len(c["knorr"]) > 0)

    # 电机功率
    df["parsed_motor_rated_kw"] = combined_text.apply(
        lambda t: float(m.group(1)) if (m := _RATED_POWER_PATTERN.search(t)) else np.nan
    )
    df["parsed_motor_peak_kw"] = combined_text.apply(
        lambda t: float(m.group(1)) if (m := _PEAK_POWER_PATTERN.search(t)) else np.nan
    )

    # 电池
    df["parsed_battery_chemistry"] = combined_text.apply(_extract_battery_chemistry)
    df["parsed_battery_cell_makers"] = combined_text.apply(
        lambda t: "|".join(_extract_battery_cell_makers(t))
    )
    df["parsed_battery_pack_makers"] = combined_text.apply(
        lambda t: "|".join(_extract_battery_pack_makers(t))
    )
    df["parsed_battery_kwh"] = combined_text.apply(_extract_capacity_kwh)
    df["parsed_battery_ah"] = combined_text.apply(_extract_capacity_ah)

    # TZ 电机型号解析
    tz_parsed = em.apply(_parse_tz_model)
    df["parsed_tz_number"] = tz_parsed.apply(lambda d: d["tz_number"])
    df["parsed_tz_suffix_type"] = tz_parsed.apply(lambda d: d["tz_suffix_type"] or "")
    df["parsed_tz_maker_code"] = tz_parsed.apply(lambda d: d["tz_maker_code"] or "")

    # 电驱拓扑推断
    df["parsed_drive_topology"] = [
        _infer_drive_topology(mk, e) for mk, e in zip(emk, et)
    ]

    return df
