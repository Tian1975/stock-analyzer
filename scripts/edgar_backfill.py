"""
scripts/edgar_backfill.py

Descarrega, normalitza i guarda l'historic EDGAR. Dos modes:

  python scripts/edgar_backfill.py
      -> Univers de VALIDACIO fix (AAPL, MSFT, JNJ, JPM). Es el mode
         que fa servir validate_providers.yml per a la Prova 5.

  python scripts/edgar_backfill.py --universe
      -> TOTS els tickers amb region=="US" llegits dinamicament de
         data/indicators.json (ja generat per indicators.py). Es el
         mode que fa servir daily_download.yml en producció.

  python scripts/edgar_backfill.py AAPL MSFT ...
      -> Llista explicita de tickers (us manual/depuracio).

Idempotencia: downloader.py ja cacheja el JSON cru per ticker
(data/edgar/raw/*.json) i no torna a descarregar si ja existeix
-- no hi ha crides redundants a EDGAR dins d'una mateixa execucio.

Resiliencia: un error en UN ticker (xarxa, format inesperat, etc.)
es registra com a warning i el backfill CONTINUA amb la resta. Un
problema temporal d'EDGAR mai ha de convertir-se en una fallada de
tot el pipeline -- score.py ja cau a Yahoo net si un ticker no te
dades normalitzades.
"""

import json
import sys
import traceback
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from edgar.downloader import download_companyfacts
from edgar.normalizer import normalize_companyfacts, missing_concepts_report
from edgar.lookup import save_normalized
from edgar.providers import EdgarProvider, CompositeProvider, FundamentalsNotAvailable

VALIDATION_TICKERS = ["AAPL", "MSFT", "JNJ", "JPM"]
INDICATORS_PATH = PROJECT_ROOT / "data" / "indicators.json"


def get_us_tickers_from_indicators() -> list[str]:
    """
    Llegeix data/indicators.json (ja generat per indicators.py abans
    d'aquest pas al pipeline diari) i retorna tots els tickers amb
    region=="US". Font unica de veritat: no cal duplicar la llista
    de l'univers US enlloc mes.
    """
    if not INDICATORS_PATH.exists():
        print(f"⚠️  {INDICATORS_PATH} no existeix -- s'omet backfill EDGAR")
        return []

    with open(INDICATORS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    tickers = [
        ticker for ticker, ind in data.get("data", {}).items()
        if ind.get("region") == "US"
    ]
    return sorted(tickers)


def run_backfill(tickers: list[str]) -> dict:
    print(f"=== Backfill EDGAR ({len(tickers)} tickers) ===\n")

    summary = {}

    for ticker in tickers:
        print(f"--- {ticker} ---")
        try:
            raw = download_companyfacts(ticker)
            if raw is None:
                print(f"  ⚠️  Sense dades a EDGAR (sense CIK o 404), s'omet\n")
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
                print(f"  ✅ Tots els conceptes basics mapejats correctament")

            summary[ticker] = {
                "records": n_records,
                "periods": n_periods,
                "missing_concepts": missing,
            }

        except Exception as e:
            # Resiliencia: un ticker problematic MAI atura la resta
            # del backfill, ni fa fallar el pipeline diari sencer.
            print(f"  🔴 ERROR inesperat amb {ticker}: {e}")
            traceback.print_exc()
            summary[ticker] = f"error: {e}"

        print()

    print("=== Resum final ===")
    ok_count = sum(1 for v in summary.values() if isinstance(v, dict))
    print(f"  {ok_count}/{len(tickers)} tickers backfillats correctament")
    for ticker, result in summary.items():
        print(f"  {ticker}: {result}")

    if "AAPL" in tickers and isinstance(summary.get("AAPL"), dict):
        print("\n=== Prova de lookup point-in-time (AAPL, 2023-06-15) ===")
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

    return summary


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--universe" in args:
        tickers = get_us_tickers_from_indicators()
        if not tickers:
            print("⚠️  Cap ticker US trobat a indicators.json -- s'omet backfill (no és un error fatal)")
            sys.exit(0)
    elif args:
        tickers = args
    else:
        tickers = VALIDATION_TICKERS

    run_backfill(tickers)
