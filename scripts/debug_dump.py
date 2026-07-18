"""
scripts/debug_dump.py

Script de DIAGNOSTIC temporal (no forma part del pipeline). Bolca
tots els registres FY (revenue, net_income, eps_basic) d'un ticker,
tal com estan guardats a data/edgar/normalized/, per investigar
anomalies com el revenue_growth negatiu inesperat d'AAPL.

Us:
    python scripts/debug_dump.py AAPL
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from edgar.lookup import load_normalized

TICKERS = sys.argv[1:] if len(sys.argv) > 1 else ["AAPL", "MSFT"]
CONCEPTS = ["revenue", "net_income", "eps_basic"]

for ticker in TICKERS:
    print(f"\n{'=' * 60}")
    print(f"{ticker} — registres FY (form 10-K)")
    print("=" * 60)

    records = load_normalized(ticker)
    print(f"Total registres (tots els conceptes/formularis): {len(records)}")

    for concept in CONCEPTS:
        fy_records = [r for r in records if r["concept"] == concept and r.get("fp") == "FY"]
        fy_records.sort(key=lambda r: (r.get("fy") or 0, r.get("filed") or ""))

        print(f"\n--- {concept} (FY) — {len(fy_records)} registres ---")
        for r in fy_records:
            print(f"  fy={r.get('fy')}  filed={r.get('filed')}  "
                  f"period_end={r.get('period_end')}  value={r.get('value')}  "
                  f"tag={r.get('tag')}  form={r.get('form')}")
