#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB設計スプレッドシートを生成する。

  python3 tools/build_db_spec.py

出力:
  docs/db/QuestOS_DB設計.xlsx   … タブ分けされたブック
  docs/db/csv/<タブ名>.csv       … git で差分が見えるようCSVも併置
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_spec_data import SHEETS  # noqa: E402
from xlsx_writer import write_xlsx  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(ROOT, "docs", "db")
CSV_DIR = os.path.join(DB_DIR, "csv")


def main():
    os.makedirs(CSV_DIR, exist_ok=True)

    for name, rows in SHEETS:
        if len(name) > 31:
            raise ValueError(f"シート名が31文字を超えています: {name}")
        path = os.path.join(CSV_DIR, f"{name}.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerows(rows)

    xlsx_path = os.path.join(DB_DIR, "QuestOS_DB設計.xlsx")
    write_xlsx(xlsx_path, SHEETS)

    total = sum(len(r) - 1 for _, r in SHEETS)
    print(f"CSV : {CSV_DIR} ({len(SHEETS)} files)")
    print(f"XLSX: {xlsx_path}")
    print(f"合計 {len(SHEETS)} タブ / {total} 行")


if __name__ == "__main__":
    main()
