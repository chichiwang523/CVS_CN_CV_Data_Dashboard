"""构建 Parquet 缓存 + 全量清洗"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import build_raw_parquet
from src.data_cleaner import run_full_clean

if __name__ == "__main__":
    print("=== 步骤 1: 构建原始 Parquet ===")
    build_raw_parquet(force=True)
    print("\n=== 步骤 2: 执行数据清洗 ===")
    run_full_clean(force=True)
    print("\n=== 完成 ===")
