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

from edgar.lookup import load_normalized, _annual_records
from datetime import date as _date

TICKERS = sys.argv[1:] if len(sys.argv) > 1 else ["AAPL", "MSFT"]
CONCEPTS = ["revenue", "net_income", "eps_basic"]

for ticker in TICKERS:
    print(f"\n{'=' * 60}")
    print(f"{ticker} — registres FY (form 10-K)")
    print("=" * 60)

    records = load_normalized(ticker)
    print(f"Total registres (tots els conceptes/formularis): {len(records)}")

    for concept in CONCEPTS:
        all_records = [r for r in records if r["concept"] == concept]
        print(f"\n--- {concept} — {len(all_records)} registres totals (abans de filtrar) ---")

        annual = _annual_records(ticker, concept, "2099-01-01")  # tots, sense limit de data
        print(f"--- {concept} — {len(annual)} registres REALMENT ANUALS (~365 dies) despres del fix ---")
        for r in annual:
            start = r.get("period_start")
            end = r.get("period_end")
            try:
                days = (_date.fromisoformat(end) - _date.fromisoformat(start)).days
            except (TypeError, ValueError):
                days = "?"
            print(f"  start={start}  end={end}  days={days}  filed={r.get('filed')}  "
                  f"value={r.get('value')}  tag={r.get('tag')}  form={r.get('form')}")
