"""数据质量检查 — 批内/跨批重复、字段完整度"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.data_loader import load_cleaned


def run_quality_check():
    df = load_cleaned()
    total = len(df)
    print(f"===== 数据质量报告 =====")
    print(f"总记录数: {total:,}")
    print(f"批次范围: {df['batch'].min()}-{df['batch'].max()} ({df['batch'].nunique()} 批次)")
    print()

    # 1) 批内 model_code 重复
    print("--- 批内车型代号重复 ---")
    dup_within = df.groupby("batch").apply(
        lambda g: g["model_code"].duplicated().sum(), include_groups=False
    ).reset_index(name="duplicates")
    dup_within = dup_within[dup_within["duplicates"] > 0]
    if len(dup_within) > 0:
        print(f"有 {len(dup_within)} 个批次存在批内重复:")
        for _, row in dup_within.iterrows():
            print(f"  批次 {row['batch']}: {row['duplicates']} 条重复")
    else:
        print("  无批内重复")
    print()

    # 2) 跨批重复
    print("--- 跨批车型代号重复 ---")
    cross_dup = df["model_code"].duplicated(keep=False)
    cross_count = cross_dup.sum()
    unique_codes_dup = df[cross_dup]["model_code"].nunique()
    print(f"  跨批重复记录: {cross_count:,} ({cross_count/total:.1%})")
    print(f"  涉及 {unique_codes_dup:,} 个不同车型代号")
    print()

    # 3) 字段完整度
    print("--- 关键字段完整度 ---")
    key_fields = [
        "model_code", "brand", "vehicle_type", "manufacturer",
        "engine_model", "engine_maker", "energy_type", "power_kw",
        "total_mass", "ABS_model", "ABS_maker", "transmission_type",
        "motor_model", "battery_type", "_remarks_raw",
    ]
    for f in key_fields:
        if f not in df.columns:
            continue
        non_null = df[f].notna() & (df[f] != "") & (df[f] != "<NA>")
        rate = non_null.sum() / total
        print(f"  {f:25s}: {non_null.sum():>8,} / {total:,} ({rate:6.1%})")
    print()

    # 4) 能源类型分布
    print("--- 能源类型分布 ---")
    for etype, cnt in df["energy_clean"].value_counts().items():
        print(f"  {etype:12s}: {cnt:>8,} ({cnt/total:6.1%})")
    print()

    # 5) ABS/EBS 统计
    print("--- ABS/EBS 统计 ---")
    print(f"  提及 ABS: {df['parsed_has_abs'].sum():,} ({df['parsed_has_abs'].mean():.1%})")
    print(f"  提及 EBS: {df['parsed_has_ebs'].sum():,} ({df['parsed_has_ebs'].mean():.1%})")
    print(f"  ZF/采埃弗 提及: {df['parsed_zf_mention'].sum():,} ({df['parsed_zf_mention'].mean():.1%})")
    print(f"  Bosch 提及: {df['parsed_bosch_mention'].sum():,} ({df['parsed_bosch_mention'].mean():.1%})")
    print(f"  Knorr 提及: {df['parsed_knorr_mention'].sum():,} ({df['parsed_knorr_mention'].mean():.1%})")


if __name__ == "__main__":
    run_quality_check()
