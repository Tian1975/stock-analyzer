"""
downloader.py  (Capa 1)

Nomes descarrega. No interpreta res. Si SEC canvia etiquetes o
afegeix conceptes nous, aquesta capa continua funcionant igual,
perque guarda el JSON tal qual el retorna l'API.

Rate limit oficial d'EDGAR: 10 req/segon per IP. Amb el nostre
univers (desenes de tickers, 1 crida cadascun) mai ens hi acostem,
pero es deixa un marge de cortesia (REQUEST_DELAY_SECONDS) per no
carregar el servei public sense necessitat.
"""

import json
import time
from pathlib import Path

import requests

from .ticker_to_cik import USER_AGENT, ticker_to_cik, PROJECT_ROOT

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
RAW_DIR = PROJECT_ROOT / "data" / "edgar" / "raw"
REQUEST_DELAY_SECONDS = 0.5


def download_companyfacts(ticker: str, force: bool = False) -> dict | None:
    """
    Descarrega (o llegeix de cache local) el JSON complet de
    companyfacts per a un ticker. Retorna None si el ticker no
    te CIK conegut a EDGAR (p.ex. moltes europees no-ADR).
    """
    cik = ticker_to_cik(ticker)
    if cik is None:
        print(f"[edgar.downloader] {ticker}: sense CIK a EDGAR (s'omet)")
        return None

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"{ticker.replace('.', '_')}.json"

    if raw_path.exists() and not force:
        with open(raw_path, "r", encoding="utf-8") as f:
            return json.load(f)

    url = COMPANYFACTS_URL.format(cik=cik)
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)

    if resp.status_code == 404:
        print(f"[edgar.downloader] {ticker}: 404 a EDGAR (CIK {cik}, sense companyfacts)")
        return None

    resp.raise_for_status()
    data = resp.json()

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    time.sleep(REQUEST_DELAY_SECONDS)
    return data


def download_universe(tickers: list[str]) -> dict[str, dict]:
    """
    Descarrega companyfacts per a una llista de tickers.
    Retorna nomes els que s'han pogut obtenir (skip silenciós
    dels que no tenen CIK o donen 404).
    """
    results = {}
    for ticker in tickers:
        data = download_companyfacts(ticker)
        if data is not None:
            results[ticker] = data
    return results


if __name__ == "__main__":
    test_tickers = ["AAPL", "MSFT", "JNJ", "JPM"]
    out = download_universe(test_tickers)
    print(f"Descarregats {len(out)}/{len(test_tickers)} tickers")
