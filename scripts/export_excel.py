"""Excel 导出 — 带能源类型统计工作表"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.data_loader import load_cleaned
from src.config import OUTPUT_DIR


def export_excel(batch_start: int = None, batch_end: int = None, output_path: str = None):
    df = load_cleaned()
    if batch_start and batch_end:
        df = df[df["batch"].between(batch_start, batch_end)]

    export_cols = [
        "batch", "batch_date", "model_code", "brand", "vehicle_type",
        "vehicle_category", "manufacturer", "manufacturer_display",
        "energy_clean", "mass_class", "total_mass", "curb_weight",
        "power_kw", "displacement",
        "engine_model", "engine_maker_display",
        "ABS_model", "abs_maker_display",
        "transmission_type", "bridge_maker_clean",
        "parsed_has_abs", "parsed_has_ebs", "parsed_optional_ebs",
        "parsed_zf_mention", "parsed_bosch_mention", "parsed_knorr_mention",
        "parsed_battery_chemistry", "parsed_drive_topology",
        "parsed_battery_kwh",
    ]
    cols = [c for c in export_cols if c in df.columns]

    if not output_path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        tag = f"{batch_start}-{batch_end}" if batch_start else "all"
        output_path = OUTPUT_DIR / f"vehicle_data_export_{tag}.xlsx"

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df[cols].to_excel(writer, sheet_name="全量车型数据", index=False)

        energy_stats = df.groupby("energy_clean").agg(
            数量=("energy_clean", "size"),
        ).reset_index().rename(columns={"energy_clean": "能源类型"})
        energy_stats["占比"] = (energy_stats["数量"] / energy_stats["数量"].sum() * 100).round(2)
        energy_stats = energy_stats.sort_values("数量", ascending=False)
        energy_stats.to_excel(writer, sheet_name="能源类型统计", index=False)

        abs_stats = pd.DataFrame({
            "指标": ["提及ABS", "提及EBS", "选装EBS", "ZF/威伯科提及", "Bosch提及", "Knorr提及"],
            "数量": [
                df["parsed_has_abs"].sum(),
                df["parsed_has_ebs"].sum(),
                df["parsed_optional_ebs"].sum(),
                df["parsed_zf_mention"].sum(),
                df["parsed_bosch_mention"].sum(),
                df["parsed_knorr_mention"].sum(),
            ],
        })
        abs_stats["占总量比"] = (abs_stats["数量"] / len(df) * 100).round(2)
        abs_stats.to_excel(writer, sheet_name="ABS_EBS统计", index=False)

    print(f"Excel exported to {output_path} ({len(df)} records)")
    return output_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    export_excel(args.start, args.end, args.output)
