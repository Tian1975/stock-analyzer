"""
scripts/history_metrics_demo.py

Primer "client" del Model 2. No es un test formal ni una eina de
producció -- es simplement el primer consumidor real de
src/history/, per detectar incomoditats de l'API abans que creixi
(el mateix paper que va fer validate_providers.py abans d'integrar
EDGAR a producció).

Us:
    python scripts/history_metrics_demo.py

No necessita arguments: fa servir automaticament les dues dates
disponibles mes recents de data/history/scores/.
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from history import (
    SnapshotIndex,
    get_ticker_history,
    top_n,
    score_distribution,
    top10_turnover,
)


def main():
    index = SnapshotIndex()
    print(f"Snapshots disponibles: {index}\n")

    if len(index) == 0:
        print("Cap snapshot trobat a data/history/scores/. Res a mostrar.")
        return

    last_date = index.last_date()
    prev_dates = index.dates()
    prev_date = prev_dates[-2] if len(prev_dates) >= 2 else last_date

    print(f"=== Top 10 (mid_term) — {last_date} ===")
    for rank, (ticker, score) in enumerate(top_n(last_date, score_field="mid_term", n=10), start=1):
        print(f"  {rank:>2}. {ticker:<10} {score:.1f}")

    print(f"\n=== Distribució de scores (mid_term) — {last_date} ===")
    dist = score_distribution(last_date, score_field="mid_term")
    print(json.dumps(dist, indent=2, ensure_ascii=False))

    print(f"\n=== Top10 turnover — {prev_date} → {last_date} ===")
    turnover = top10_turnover(prev_date, last_date, score_field="mid_term")
    print(json.dumps(turnover, indent=2, ensure_ascii=False))

    # Historial d'un ticker concret, com a exemple d'us de queries.py
    example_ticker = "AAPL"
    print(f"\n=== Historial de {example_ticker} (tots els snapshots disponibles) ===")
    history = get_ticker_history(example_ticker)
    if not history:
        print(f"  ({example_ticker} no apareix a cap snapshot disponible)")
    else:
        for point in history:
            print(f"  {point['date']}  mid_term={point['score_mid_term']}  rank={point['rank_mid_term']}")


if __name__ == "__main__":
    main()
