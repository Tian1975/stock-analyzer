"""
alerts.py — Llegeix data/scores.json (avui) + l'històric (ahir) + la llista
de favorits (config/favorites.txt) i detecta condicions d'alerta. Si n'hi ha
alguna, crea una GitHub Issue (que arriba per email/notificació si tens les
notificacions de GitHub activades al mòbil).

Condicions comprovades:
- Favorit entra al Top 10 / Top 3
- Favorit surt del Top 10
- RSI > 70 (sobrecompra) o < 30 (sobrevenda) en un favorit
- Trencament de tendència (SMA20 < SMA50 < SMA200) en un favorit
- Caiguda de score (mig termini): 🟡 ≥5 punts, 🔴 ≥10 punts
- Confiança de dades < 90% en un favorit
- (Global, no només favorits) Qualsevol ticker entra al Top 10 per primera
  vegada — descoberta d'oportunitat nova

Ús: python src/alerts.py
Variables d'entorn esperades (ja disponibles automàticament a GitHub Actions):
  GITHUB_TOKEN, GITHUB_REPOSITORY
"""
import json
import logging
import os
from pathlib import Path

import requests

from config import (
    ALERT_SCORE_DROP_WATCH,
    ALERT_SCORE_DROP_ALERT,
    ALERT_RSI_OVERBOUGHT,
    ALERT_RSI_OVERSOLD,
    ALERT_MIN_CONFIDENCE_PCT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("alerts")

BASE_DIR = Path(__file__).parent.parent
SCORES_PATH = BASE_DIR / "data" / "scores.json"
INDICATORS_PATH = BASE_DIR / "data" / "indicators.json"
HISTORY_DIR = BASE_DIR / "data" / "history" / "scores"
FAVORITES_PATH = BASE_DIR / "config" / "favorites.txt"


def load_favorites() -> set:
    if not FAVORITES_PATH.exists():
        return set()
    favorites = set()
    with open(FAVORITES_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                favorites.add(line.upper())
    return favorites


def load_today_scores() -> dict:
    with open(SCORES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {r["ticker"]: r for r in data["results"]}


def load_today_indicators() -> dict:
    with open(INDICATORS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["data"]


def load_yesterday_scores() -> dict:
    """L'últim snapshot de l'historial ANTERIOR a l'actual (score.py ja en
    desa un cada dia a data/history/scores/)."""
    if not HISTORY_DIR.exists():
        return {}
    files = sorted(HISTORY_DIR.glob("*.json"))
    if len(files) < 2:
        return {}
    # L'últim (files[-1]) és el d'avui (ja desat per score.py abans que
    # s'executi alerts.py); el penúltim és el d'ahir.
    with open(files[-2], encoding="utf-8") as f:
        data = json.load(f)
    return {r["ticker"]: r for r in data.get("results", [])}


def check_ticker_alerts(ticker: str, today: dict, yesterday: dict, indicators: dict, is_favorite: bool) -> list:
    """Retorna una llista de missatges d'alerta per a un ticker concret."""
    alerts = []
    ind = indicators.get(ticker, {})
    prev = yesterday.get(ticker)

    rank_today = today.get("rank_mid_term")
    rank_prev = prev.get("rank_mid_term") if prev else None

    # --- Entrada/sortida de Top10 i Top3 (només té sentit per favorits, per
    # no saturar amb els 79 tickers; la descoberta global es tracta a part) ---
    if is_favorite:
        if rank_today is not None and rank_today <= 10 and (rank_prev is None or rank_prev > 10):
            if rank_today <= 3:
                alerts.append(f"🚀 **{ticker}** entra al **Top 3** (posició #{rank_today})")
            else:
                alerts.append(f"📈 **{ticker}** entra al **Top 10** (posició #{rank_today})")
        elif rank_prev is not None and rank_prev <= 10 and (rank_today is None or rank_today > 10):
            alerts.append(f"📉 **{ticker}** surt del **Top 10** (ara #{rank_today})")

        # --- RSI ---
        rsi = ind.get("momentum", {}).get("rsi14")
        if rsi is not None:
            if rsi >= ALERT_RSI_OVERBOUGHT:
                alerts.append(f"⚠️ **{ticker}**: RSI = {rsi:.0f} (zona de sobrecompra)")
            elif rsi <= ALERT_RSI_OVERSOLD:
                alerts.append(f"⚠️ **{ticker}**: RSI = {rsi:.0f} (zona de sobrevenda)")

        # --- Trencament de tendència ---
        trend = ind.get("trend", {})
        close = ind.get("last_close")
        sma20, sma50, sma200 = trend.get("sma20"), trend.get("sma50"), trend.get("sma200")
        if all(v is not None for v in [close, sma20, sma50, sma200]):
            if sma20 < sma50 < sma200:
                alerts.append(f"⚠️ **{ticker}**: tendència baixista (SMA20 < SMA50 < SMA200)")

        # --- Caiguda de score (dos nivells) ---
        score_change = today.get("score_change_mid_term")
        if score_change is not None and score_change < 0:
            drop = abs(score_change)
            if drop >= ALERT_SCORE_DROP_ALERT:
                alerts.append(f"🔴 **{ticker}**: score de mig termini cau {drop:.1f} punts — revisa-la")
            elif drop >= ALERT_SCORE_DROP_WATCH:
                alerts.append(f"🟡 **{ticker}**: score de mig termini cau {drop:.1f} punts — vigila-la")

        # --- Confiança de dades ---
        confidence = today.get("confidence_pct")
        if confidence is not None and confidence < ALERT_MIN_CONFIDENCE_PCT:
            alerts.append(f"ℹ️ **{ticker}**: confiança de dades baixa ({confidence:.0f}%, falten fonamentals)")

    return alerts


def check_global_discoveries(today_scores: dict, favorites: set) -> list:
    """Qualsevol ticker (favorit o no) que entra al Top 10 per primera
    vegada — útil per descobrir oportunitats que no seguies encara."""
    alerts = []
    for ticker, r in today_scores.items():
        if r.get("is_new_top10") and ticker not in favorites:
            alerts.append(f"🔥 **{ticker}** entra al Top 10 per primera vegada (posició #{r['rank_mid_term']}) — no el segueixes encara")
    return alerts


def create_github_issue(title: str, body: str) -> bool:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")  # format "usuari/repo"
    if not token or not repo:
        log.warning("GITHUB_TOKEN o GITHUB_REPOSITORY no disponibles; no es crea la issue (execució local?)")
        return False

    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {"title": title, "body": body, "labels": ["alerta-automatica"]}

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code == 201:
        log.info(f"Issue creada: {resp.json().get('html_url')}")
        return True
    else:
        log.error(f"Error creant la issue ({resp.status_code}): {resp.text[:300]}")
        return False


def main():
    favorites = load_favorites()
    log.info(f"Favorits configurats per alertes: {sorted(favorites) or '(cap)'}")

    today_scores = load_today_scores()
    yesterday_scores = load_yesterday_scores()
    indicators = load_today_indicators()

    all_alerts = []
    for ticker in favorites:
        if ticker not in today_scores:
            continue
        all_alerts.extend(
            check_ticker_alerts(ticker, today_scores[ticker], yesterday_scores, indicators, is_favorite=True)
        )

    all_alerts.extend(check_global_discoveries(today_scores, favorites))

    if not all_alerts:
        log.info("Cap alerta avui.")
        return

    log.info(f"{len(all_alerts)} alertes detectades:")
    for a in all_alerts:
        log.info(f"  - {a}")

    body_lines = ["## Alertes d'avui\n"] + [f"- {a}" for a in all_alerts]
    body_lines.append("\n---\n*Generat automàticament per `alerts.py`. No és cap consell d'inversió.*")
    body = "\n".join(body_lines)

    create_github_issue(f"📊 Alertes Stock Analyzer — {len(all_alerts)} avisos", body)


if __name__ == "__main__":
    main()
