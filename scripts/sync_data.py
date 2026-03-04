#!/usr/bin/env python3
"""
从阿里云 OSS 同步数据到本地目录。

依赖:
  - ossutil 已安装并完成 `ossutil config`

用法:
  python scripts/sync_data.py --bucket oss://your-bucket/china-cv-agent --mode only_cache
  python scripts/sync_data.py --bucket oss://your-bucket/china-cv-agent --mode full
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("[sync] run:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def ensure_ossutil() -> str:
    binary = shutil.which("ossutil")
    if not binary:
        raise SystemExit(
            "未找到 ossutil。请先安装并执行 `ossutil config` 完成认证。"
        )
    return binary


def sync_cache(ossutil: str, bucket: str, project_root: Path) -> None:
    cache_dir = project_root / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    # 优先同步核心 parquet
    run([
        ossutil,
        "cp",
        "-u",
        f"{bucket}/cache/all_batches_cleaned.parquet",
        str(cache_dir / "all_batches_cleaned.parquet"),
    ])
    # 若有原始 parquet，也拉取
    run([
        ossutil,
        "cp",
        "-u",
        f"{bucket}/cache/all_batches_raw.parquet",
        str(cache_dir / "all_batches_raw.parquet"),
    ])


def sync_full(ossutil: str, bucket: str, project_root: Path) -> None:
    run([ossutil, "sync", "-u", f"{bucket}/cache/", str(project_root / "cache")])
    run([ossutil, "sync", "-u", f"{bucket}/CVdata/", str(project_root / "CVdata")])


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync project data from OSS")
    parser.add_argument("--bucket", required=True, help="OSS bucket path, e.g. oss://xxx/china-cv-agent")
    parser.add_argument(
        "--mode",
        choices=["only_cache", "full"],
        default="only_cache",
        help="only_cache: 仅同步 cache parquet；full: 同步 cache + CVdata",
    )
    parser.add_argument(
        "--project-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="项目根目录（默认当前仓库根目录）",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    if not project_root.exists():
        raise SystemExit(f"项目目录不存在: {project_root}")

    ossutil = ensure_ossutil()
    print(f"[sync] project_root={project_root}")
    print(f"[sync] mode={args.mode}")
    print(f"[sync] bucket={args.bucket}")

    if args.mode == "only_cache":
        sync_cache(ossutil, args.bucket.rstrip("/"), project_root)
    else:
        sync_full(ossutil, args.bucket.rstrip("/"), project_root)

    print("[sync] done")


if __name__ == "__main__":
    main()
