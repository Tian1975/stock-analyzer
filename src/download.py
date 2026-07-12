"""
download.py — Descarrega preus (en bloc) i fonamentals (per ticker) per a tot l'univers.

v0.3:
- get_fundamentals() retorna un ESQUEMA INTERN propi (Fundamentals), no els noms
  crus de Yahoo. Si demà canviem de proveïdor, només cal reescriure el mapeig
  intern d'aquesta funció; la resta del pipeline (indicators/scoring/etc.) mai
  coneix els noms de camp originals de cap proveïdor.
- validate_prices() comprova explícitament: ordre cronològic, absència de NaN,
  longituds coherents, preus estrictament positius, volum no negatiu.
- Logging en comptes de print (nivells INFO/WARNING/ERROR, format llegible a
  GitHub Actions).
- Resum amb detall de fallits (ticker + motiu) ja inclòs.

Ús: python src/download.py
"""
import json
import logging
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from universe import ALL_TICKERS, REGION_MAP
from config import HISTORY_PERIOD, MAX_RETRIES, REQUEST_DELAY, PROVIDER, VERSION, MIN_SESSIONS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("download")

BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
HISTORY_DIR = BASE_DIR / "data" / "history" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Esquema intern de fonamentals (independent del proveïdor). Si es canvia de
# proveïdor de dades, només cal reescriure com s'omplen aquests camps.
FUNDAMENTALS_SCHEMA = [
    "long_name", "sector", "industry", "market_cap",
    "pe_trailing", "pe_forward", "peg_ratio", "price_to_book",
    "debt_to_equity", "return_on_equity", "revenue_growth", "earnings_growth",
    "gross_margin", "operating_margin", "profit_margin", "beta",
    "dividend_yield", "week52_high", "week52_low", "currency",
]


def get_fundamentals(tk: yf.Ticker, ticker: str) -> dict:
    """Mapeja les dades cru del proveïdor a l'esquema intern propi.
    Aïllat perquè un fallo aquí no faci perdre les dades de preus, ja descarregades."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            info = tk.info
            if not info:
                raise ValueError("info buit")
            return {
                "ok": True,
                "long_name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "pe_trailing": info.get("trailingPE"),
                "pe_forward": info.get("forwardPE"),
                "peg_ratio": info.get("trailingPegRatio"),
                "price_to_book": info.get("priceToBook"),
                "debt_to_equity": info.get("debtToEquity"),
                "return_on_equity": info.get("returnOnEquity"),
                "revenue_growth": info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "gross_margin": info.get("grossMargins"),
                "operating_margin": info.get("operatingMargins"),
                "profit_margin": info.get("profitMargins"),
                "beta": info.get("beta"),
                "dividend_yield": info.get("dividendYield"),
                "week52_high": info.get("fiftyTwoWeekHigh"),
                "week52_low": info.get("fiftyTwoWeekLow"),
                "currency": info.get("currency"),
            }
        except Exception as e:
            if attempt == MAX_RETRIES:
                log.warning(f"{ticker}: fonamentals fallits després de {MAX_RETRIES} intents ({e})")
                return {"ok": False, "error": str(e), **{k: None for k in FUNDAMENTALS_SCHEMA}}
            time.sleep(REQUEST_DELAY * attempt)
    return {"ok": False, "error": "unreachable"}


def validate_prices(ticker: str, df: pd.DataFrame):
    """Comprovacions explícites abans de confiar en les dades d'un ticker:
    ordre cronològic, sense NaN, longituds coherents, preus > 0, volum >= 0."""
    if df is None or df.empty:
        return False, "no_price_data"

    n = len(df)
    if n < MIN_SESSIONS:
        return False, f"insufficient_sessions ({n} < {MIN_SESSIONS})"

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in df.columns for c in required_cols):
        return False, f"missing_columns (té: {list(df.columns)})"

    lengths = {c: df[c].dropna().shape[0] for c in required_cols}
    if len(set(lengths.values())) > 1:
        return False, f"inconsistent_lengths {lengths}"

    ohlc = df[["Open", "High", "Low", "Close"]]
    if ohlc.isna().any().any():
        return False, "nan_in_ohlc"

    if (ohlc <= 0).any().any():
        return False, "non_positive_price"

    if (df["Volume"] < 0).any():
        return False, "negative_volume"

    if not df.index.is_monotonic_increasing:
        return False, "dates_not_sorted"

    return True, "ok"


def build_ticker_record(ticker: str, prices_df: pd.DataFrame, tk: yf.Ticker) -> dict:
    valid, reason = validate_prices(ticker, prices_df)
    if not valid:
        return {"ok": False, "ticker": ticker, "error": reason}

    prices = {
        "dates": [d.strftime("%Y-%m-%d") for d in prices_df.index],
        "open": prices_df["Open"].round(4).tolist(),
        "high": prices_df["High"].round(4).tolist(),
        "low": prices_df["Low"].round(4).tolist(),
        "close": prices_df["Close"].round(4).tolist(),
        "volume": prices_df["Volume"].astype(int).tolist(),
    }

    fundamentals = get_fundamentals(tk, ticker)

    return {
        "ok": True,
        "ticker": ticker,
        "region": REGION_MAP.get(ticker, "UNKNOWN"),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "prices": prices,
        "fundamentals": fundamentals,
        "fundamentals_ok": fundamentals.get("ok", False),
    }


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def build_sanity_report(all_records: list[dict]) -> dict:
    """Recorre tots els registres ja generats i produeix un informe ràpid
    d'incidències, sense haver d'obrir els JSON individuals a mà."""
    missing_prices = [r["ticker"] for r in all_records if not r.get("ok")]
    missing_fundamentals = [
        r["ticker"] for r in all_records if r.get("ok") and not r.get("fundamentals_ok")
    ]

    tickers_seen = [r["ticker"] for r in all_records]
    duplicate_tickers = sorted({t for t in tickers_seen if tickers_seen.count(t) > 1})

    all_dates = []
    for r in all_records:
        if r.get("ok"):
            all_dates.extend(r["prices"]["dates"])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "missing_prices": missing_prices,
        "missing_fundamentals": missing_fundamentals,
        "duplicate_tickers": duplicate_tickers,
        "oldest_price_date": min(all_dates) if all_dates else None,
        "newest_price_date": max(all_dates) if all_dates else None,
    }


def main():
    start = time.time()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_history_dir = HISTORY_DIR / today
    today_history_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"Descarregant preus en bloc per {len(ALL_TICKERS)} tickers...")
    bulk = yf.download(
        ALL_TICKERS,
        period=HISTORY_PERIOD,
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )

    results_summary = {"ok": [], "failed": []}
    all_records = []

    for i, ticker in enumerate(ALL_TICKERS, 1):
        log.info(f"[{i}/{len(ALL_TICKERS)}] Processant {ticker}...")
        try:
            df = bulk[ticker] if len(ALL_TICKERS) > 1 else bulk
        except Exception:
            df = pd.DataFrame()

        tk = yf.Ticker(ticker)
        record = build_ticker_record(ticker, df, tk)
        all_records.append(record)

        out_path = RAW_DIR / f"{ticker.replace('.', '_')}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)

        hist_path = today_history_dir / f"{ticker.replace('.', '_')}.json"
        with open(hist_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)

        if record["ok"]:
            results_summary["ok"].append(ticker)
            if not record["fundamentals_ok"]:
                log.warning(f"{ticker}: preus OK, fonamentals fallits")
        else:
            results_summary["failed"].append({"ticker": ticker, "reason": record.get("error")})
            log.error(f"{ticker}: {record.get('error')}")

        time.sleep(REQUEST_DELAY)

    duration = round(time.time() - start, 1)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": duration,
        "provider": PROVIDER,
        "version": VERSION,
        "git_commit": get_git_commit(),
        "python_version": platform.python_version(),
        "yfinance_version": yf.__version__,
        "pandas_version": pd.__version__,
        "processed": len(ALL_TICKERS),
        "ok": len(results_summary["ok"]),
        "failed": len(results_summary["failed"]),
        "success_rate_pct": round(100 * len(results_summary["ok"]) / len(ALL_TICKERS), 1),
        "tickers_failed": results_summary["failed"],
    }

    summary_path = RAW_DIR.parent / "download_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    sanity_report = build_sanity_report(all_records)
    sanity_path = RAW_DIR.parent / "sanity_report.json"
    with open(sanity_path, "w", encoding="utf-8") as f:
        json.dump(sanity_report, f, ensure_ascii=False, indent=2)

    log.info(f"Fet en {duration}s: {summary['ok']}/{summary['processed']} correctes "
              f"({summary['success_rate_pct']}%).")
    if results_summary["failed"]:
        log.warning(f"Fallits: {[f['ticker'] for f in results_summary['failed']]}")


if __name__ == "__main__":
    main()
