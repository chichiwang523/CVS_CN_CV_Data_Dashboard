"""批量生成 PNG 图表 — 每批次的分布图"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from src.data_loader import load_cleaned
from src.config import OUTPUT_DIR, CHARTS_DIR, BATCH_DATES
from src.data_cleaner import _display_name

plt.rcParams["font.sans-serif"] = ["SimHei", "WenQuanYi Micro Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

CHARTS_DIR.mkdir(parents=True, exist_ok=True)


def _save_bar_chart(series, title, filename, n=15, figsize=(10, 6)):
    top = series.value_counts().head(n)
    if len(top) == 0:
        return
    fig, ax = plt.subplots(figsize=figsize)
    top.plot(kind="barh", ax=ax, color="#003399")
    ax.set_title(title, fontsize=14)
    ax.invert_yaxis()
    plt.tight_layout()
    fig.savefig(CHARTS_DIR / filename, dpi=150)
    plt.close(fig)


def _save_pie_chart(series, title, filename, figsize=(8, 8)):
    counts = series.value_counts()
    if len(counts) == 0:
        return
    fig, ax = plt.subplots(figsize=figsize)
    counts.plot(kind="pie", ax=ax, autopct="%1.1f%%")
    ax.set_title(title, fontsize=14)
    ax.set_ylabel("")
    plt.tight_layout()
    fig.savefig(CHARTS_DIR / filename, dpi=150)
    plt.close(fig)


def generate_for_batch(df_batch, batch_num):
    date = BATCH_DATES.get(batch_num, "")
    label = f"第{batch_num}批 ({date})"

    _save_bar_chart(
        df_batch["manufacturer_display"],
        f"生产企业 Top 10 — {label}",
        f"manufacturer_top10_batch_{batch_num}.png", n=10,
    )
    _save_bar_chart(
        df_batch["engine_maker_display"],
        f"发动机/电机企业 Top 15 — {label}",
        f"engine_maker_top15_batch_{batch_num}.png", n=15,
    )
    _save_pie_chart(
        df_batch["energy_clean"],
        f"能源类型分布 — {label}",
        f"energy_distribution_batch_{batch_num}.png",
    )

    bev = df_batch[df_batch["energy_clean"] == "纯电动"]
    if len(bev) > 0:
        _save_bar_chart(
            bev["engine_maker_display"],
            f"BEV 电机企业 Top 10 — {label}",
            f"bev_motor_top10_batch_{batch_num}.png", n=10,
        )

    power = df_batch[df_batch["power_kw"].notna() & (df_batch["power_kw"] > 0)]["power_kw"]
    if len(power) > 10:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        power.plot(kind="hist", bins=30, ax=ax1, color="#003399", alpha=0.7)
        ax1.set_title(f"功率分布 (直方图) — {label}")
        ax1.set_xlabel("功率 (kW)")
        power.plot(kind="box", ax=ax2)
        ax2.set_title(f"功率分布 (箱线图)")
        plt.tight_layout()
        fig.savefig(CHARTS_DIR / f"power_distribution_batch_{batch_num}.png", dpi=150)
        plt.close(fig)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, nargs="*", help="指定批次，不指定则全部")
    args = parser.parse_args()

    df = load_cleaned()
    batches_to_run = args.batch if args.batch else sorted(df["batch"].unique())

    for b in batches_to_run:
        batch_df = df[df["batch"] == b]
        if len(batch_df) == 0:
            continue
        print(f"Generating charts for batch {b} ({len(batch_df)} records)...")
        generate_for_batch(batch_df, b)

    print(f"Charts saved to {CHARTS_DIR}")
