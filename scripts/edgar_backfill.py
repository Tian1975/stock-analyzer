"""
scripts/edgar_backfill.py

Script d'us MANUAL i separat del pipeline diari (tal com es va
decidir): descarrega, normalitza i guarda l'historic EDGAR per a
una llista de tickers de validacio. NO toca score.py ni cap altre
fitxer del pipeline existent.

Objectiu d'aquesta primera passada: validar amb diverses empreses
dels EUA (AAPL, MSFT, JNJ, JPM) que els 5 conceptes basics es
mapegen be, abans de decidir integrar-ho al workflow diari.

Execucio:
    python scripts/edgar_backfill.py

Despres de correr-lo, revisa el resum de conceptes que falten
(missing_concepts_report) per a cada empresa. Si algun concepte
fallar per a moltes empreses, cal afegir tags candidats nous a
concepts.py (no cal tocar res mes).
"""

import sys
from pathlib import Path

# __file__ apunta sempre a la ubicacio real d'aquest script,
# independentment de des d'on Pythonista el llanci. Aixo fa que
# funcioni igual tocant "play" des de l'editor com des d'un
# workflow de GitHub Actions.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from edgar.downloader import download_companyfacts
from edgar.normalizer import normalize_companyfacts, missing_concepts_report
from edgar.lookup import save_normalized
from edgar.providers import EdgarProvider, CompositeProvider, FundamentalsNotAvailable

# Univers de validacio: barreja de sectors per estressar el
# normalitzador amb taxonomies diferents (tech, salut, banca).
VALIDATION_TICKERS = ["AAPL", "MSFT", "JNJ", "JPM"]


def run_backfill(tickers: list[str]) -> None:
    print(f"=== Backfill EDGAR de validacio ({len(tickers)} tickers) ===\n")

    summary = {}

    for ticker in tickers:
        print(f"--- {ticker} ---")
        raw = download_companyfacts(ticker)
        if raw is None:
            print(f"  ⚠️  Sense dades a EDGAR, s'omet\n")
            summary[ticker] = "sense_cik_o_404"
            continue

        records = normalize_companyfacts(ticker, raw)
        save_normalized(ticker, records)

        missing = missing_concepts_report(ticker, raw)
        n_records = len(records)
        n_periods = len({r["period_end"] for r in records})

        print(f"  ✅ {n_records} registres normalitzats ({n_periods} periodes diferents)")
        if missing:
            print(f"  ⚠️  Conceptes NO trobats: {', '.join(missing)}")
        else:
            print(f"  ✅ Tots els 5 conceptes basics mapejats correctament")

        summary[ticker] = {
            "records": n_records,
            "periods": n_periods,
            "missing_concepts": missing,
        }
        print()

    print("=== Resum final ===")
    for ticker, result in summary.items():
        print(f"  {ticker}: {result}")

    print("\n=== Prova de lookup point-in-time (AAPL, 2023-06-15) ===")
    if "AAPL" in tickers:
        provider = CompositeProvider([EdgarProvider()])
        try:
            example = provider.lookup("AAPL", "2023-06-15")
            print(f"  Font: {example['_provider']}  (cobertura: {example['_coverage']}%)")
            for concept, value in example.items():
                if concept.startswith("_"):
                    continue
                filed = example.get("_as_of", {}).get(concept, {}).get("filed", "?")
                print(f"  {concept}: {value}  (segons filing de {filed})")
        except FundamentalsNotAvailable as e:
            print(f"  ⚠️  {e}")


if __name__ == "__main__":
    run_backfill(VALIDATION_TICKERS)
