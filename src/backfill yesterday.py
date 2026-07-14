"""
backfill_yesterday.py — Script D'UN SOL ÚS per reconstruir el snapshot
d'"ahir" a data/history/scores/, perquè la propera execució normal ja tingui
un dia anterior real amb què comparar (deltes, is_new_top10, etc.).

Com funciona: agafa els preus històrics REALS que download.py ja ha guardat
a data/raw/*.json (2 anys de preus), treu l'última sessió de cada ticker
(simulant "com estava el mercat un dia abans"), i torna a calcular
indicadors + scores amb aquestes dades retallades. Els FONAMENTALS (PER,
creixement, ROE...) es mantenen els d'avui, perquè en 24 hores no canvien
de manera rellevant — és una aproximació segura només per a 1 dia enrere,
NO s'ha de fer servir per reconstruir setmanes o mesos (aleshores sí que
els fonamentals podrien haver canviat de veritat).

Aquest script NOMÉS escriu un fitxer d'historial (un dia sintètic al
passat) — mai toca data/scores.json ni cap altra dada d'avui.

Ús: python src/backfill_yesterday.py
"""
import copy
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from indicators import compute_indicators_for_ticker
from score import (
    build_dataframe, compute_subscores, compute_confidence, horizon_scores,
    build_checklist, build_explanation, risk_label, build_narrative,
    build_watch_list, HORIZON_WEIGHTS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("backfill")

BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
HISTORY_DIR = BASE_DIR / "data" / "history" / "scores"


def load_raw_records() -> list[dict]:
    records = []
    for path in sorted(RAW_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("ok"):
            records.append(data)
    return records


def truncate_last_session(record: dict) -> dict | None:
    """Retorna una còpia del registre amb l'última sessió de preus eliminada
    (simula 'com estava el mercat un dia abans'). Fonamentals intactes."""
    truncated = copy.deepcopy(record)
    prices = truncated["prices"]
    if len(prices["dates"]) < 2:
        return None
    for key in ("dates", "open", "high", "low", "close", "volume"):
        prices[key] = prices[key][:-1]
    return truncated


def main():
    log.info("Carregant dades crues reals (data/raw/*.json)...")
    records = load_raw_records()
    log.info(f"{len(records)} tickers trobats")

    truncated_records = []
    for r in records:
        t = truncate_last_session(r)
        if t is not None:
            truncated_records.append(t)
    log.info(f"{len(truncated_records)} tickers amb prou sessions per retallar")

    # --- Recalcular indicadors amb la sèrie retallada ---
    indicators_data = {}
    for r in truncated_records:
        try:
            indicators_data[r["ticker"]] = compute_indicators_for_ticker(r)
        except Exception as e:
            log.warning(f"{r['ticker']}: no s'ha pogut recalcular indicadors ({e})")

    fundamentals_data = {
        r["ticker"]: r["fundamentals"]
        for r in truncated_records
        if r.get("fundamentals_ok")
    }
    log.info(f"{len(indicators_data)} amb indicadors, {len(fundamentals_data)} amb fonamentals")

    # --- Recalcular scores (reutilitzant les funcions pures de score.py) ---
    df = build_dataframe(indicators_data, fundamentals_data)
    subscores = compute_subscores(df)
    confidence = compute_confidence(df)
    horizons = horizon_scores(subscores)

    results = []
    for ticker in df.index:
        row_sub = subscores.loc[ticker]
        row_raw = df.loc[ticker]
        checklist = build_checklist(row_sub, row_raw)
        results.append({
            "ticker": ticker,
            "region": row_raw.get("region"),
            "as_of": row_raw.get("as_of"),
            "last_close": row_raw.get("last_close"),
            "subscores": {
                k: (None if pd.isna(v) else round(float(v), 1)) for k, v in row_sub.items()
            },
            "scores": {
                h: (None if pd.isna(horizons.loc[ticker, h]) else float(horizons.loc[ticker, h]))
                for h in HORIZON_WEIGHTS
            },
            "risk_label": risk_label(row_sub),
            "confidence_pct": float(confidence.loc[ticker]),
            "explanation": build_explanation(ticker, row_sub, row_raw),
            "checklist": checklist,
            "what_changed": [],  # no hi ha res anterior amb què comparar
        })

    # Rànquing
    results.sort(key=lambda r: (r["scores"]["mid_term"] is None, -(r["scores"]["mid_term"] or 0)))
    for i, r in enumerate(results, 1):
        r["rank_mid_term"] = i

    top10_tickers = {r["ticker"] for r in results[:10]}

    # Camps que normalment depenen de l'historial: com que aquest és el
    # primer punt (sintètic) de tot l'historial, es comporten com un "dia 1"
    for r in results:
        ticker = r["ticker"]
        row_sub = subscores.loc[ticker]
        row_raw = df.loc[ticker]
        r["narrative"] = build_narrative(ticker, row_sub, row_raw, r["checklist"], r["rank_mid_term"])
        r["watch_list"] = build_watch_list(row_sub, row_raw, r["scores"]["mid_term"], r["checklist"]["semaforo"])
        r["rank_change"] = None
        r["score_change_mid_term"] = None
        r["is_new_entry"] = True
        r["is_new_top10"] = ticker in top10_tickers
        r["history_series"] = [{"date": None, "mid_term": r["scores"]["mid_term"], "rank": r["rank_mid_term"]}]
        r["days_in_top10"] = 1 if ticker in top10_tickers else 0
        r["score_change_7d"] = None
        r["score_change_30d"] = None
        r["best_score_period"] = r["scores"]["mid_term"]
        r["is_best_score_period"] = True
        r["recommendation_line"] = None
        r["change_timeline"] = []

    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    yesterday_label = yesterday.strftime("%Y-%m-%d")
    for r in results:
        r["history_series"][0]["date"] = yesterday_label

    output = {
        "generated_at": yesterday.isoformat(),
        "duration_seconds": 0.0,
        "universe_size": len(results),
        "horizon_weights": HORIZON_WEIGHTS,
        "history_retention_days": None,
        "universe_daily_summary": [],
        "results": results,
        "is_backfilled": True,  # marca honesta: aquest dia és reconstruït, no real
    }

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    out_path = HISTORY_DIR / f"{yesterday_label}.json"
    if out_path.exists():
        log.warning(f"{out_path} ja existeix — no el sobreescric. Esborra'l manualment si vols refer-ho.")
        return

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    log.info(f"Fet: {len(results)} tickers reconstruïts -> {out_path}")


if __name__ == "__main__":
    main()
