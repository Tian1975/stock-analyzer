"""
ticker_to_cik.py

Converteix tickers (AAPL, MSFT...) al CIK de 10 digits que
necessiten els endpoints d'EDGAR. Fa servir el fitxer oficial
company_tickers.json, que es gratuit i no requereix clau.

El fitxer es cacheja localment a data/edgar/company_tickers.json
i nomes es torna a descarregar si te mes de CACHE_DAYS dies,
per no fer-hi una crida cada execucio.
"""

import json
import time
from pathlib import Path

import requests

# Arrel del projecte = dues carpetes amunt d'aquest fitxer
# (src/edgar/ticker_to_cik.py -> ... -> edgar_connector/).
# Aixo fa que el path sigui absolut i no depengui de des d'on
# s'executi l'script (Pythonista, terminal, GitHub Actions...).
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
CACHE_PATH = PROJECT_ROOT / "data" / "edgar" / "company_tickers.json"
CACHE_DAYS = 7

# Obligatori per EDGAR: identificar-se amb nom + contacte real.
# Substitueix l'email per un de teu abans d'executar-ho en producció.
USER_AGENT = "stock-analyzer (contact: replace-with-your-email@example.com)"


def _download_ticker_map() -> dict:
    resp = requests.get(
        SEC_TICKERS_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _load_cached_or_download() -> dict:
    if CACHE_PATH.exists():
        age_days = (time.time() - CACHE_PATH.stat().st_mtime) / 86400
        if age_days < CACHE_DAYS:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)

    data = _download_ticker_map()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def build_ticker_index() -> dict:
    """
    Retorna un dict {TICKER: cik_padded_10_digits}.
    El JSON original ve indexat per numero arbitrari, no per ticker,
    per aixo cal reindexar-lo un cop.
    """
    raw = _load_cached_or_download()
    index = {}
    for entry in raw.values():
        ticker = entry["ticker"].upper()
        cik = str(entry["cik_str"]).zfill(10)
        index[ticker] = cik
    return index


def ticker_to_cik(ticker: str) -> str | None:
    """
    Retorna el CIK (10 digits, amb zeros) per a un ticker donat,
    o None si no es troba (p.ex. tickers que no fitxen a EDGAR,
    com la majoria d'europees no-ADR).

    Nota: els tickers d'aquest projecte porten sufix de mercat
    (AAPL, BBVA.MC, SAP.DE...). EDGAR nomes coneix el ticker "net"
    EUA/ADR, aixi que cal netejar el sufix abans de cercar.
    """
    clean = ticker.split(".")[0].upper()
    index = build_ticker_index()
    return index.get(clean)


if __name__ == "__main__":
    for t in ["AAPL", "MSFT", "JNJ", "JPM", "BBVA.MC", "SAP.DE"]:
        print(t, "->", ticker_to_cik(t))
