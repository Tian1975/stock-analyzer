"""
backfill_full_year.py — Script D'UN SOL ÚS per reconstruir l'historial
complet de l'any (des de l'1 de gener) a data/history/scores/.

⚠️ IMPORTANT — llegeix això abans d'executar-lo:

- Els subscores TÈCNICS (Momentum, Tendència, Risc) i el score de CURT
  TERMINI són 100% fiables per a qualsevol dia de l'any: es calculen
  només a partir de preus històrics reals.

- Els subscores de FONAMENTALS (Valoració, Qualitat, Creixement), i per
  tant el score de MITJÀ/LLARG TERMINI, la checklist, el semàfor i la
  narrativa, es calculen amb els FONAMENTALS D'AVUI CONGELATS aplicats a
  TOTS els dies de l'any. Això és una aproximació, NO una reconstrucció
  real — si una empresa va publicar resultats trimestrals durant l'any,
  els dies anteriors a aquella publicació surten calculats amb dades que
  aleshores encara no existien. Cada dia reconstruït porta el camp
  "fundamentals_frozen": true perquè quedi constància.

Reutilitza les mateixes funcions pures d'indicators.py i score.py que ja
fem servir cada dia — no hi ha lògica nova ni duplicada.

Ús: python src/backfill_full_year.py
"""
import copy
import json
import logging
from datetime import datetime, timezone
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
log = logging.getLogger("backfill_year")

BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
HISTORY_DIR = BASE_DIR / "data" / "history" / "scores"

START_DATE = "2026-01-01"  # des de quan reconstruïm ("el que portem d'any")


def load_raw_records() -> list[dict]:
    records = []
    for path in sorted(RAW_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("ok"):
            records.append(data)
    return records


def truncate_up_to(record: dict, cutoff_date: str) -> dict | None:
    """Còpia del registre amb els preus retallats fins (i incloent) cutoff_date.
    Retorna None si aquest ticker no va cotitzar aquell dia (festiu local)."""
    dates = record["prices"]["dates"]
    if cutoff_date not in dates:
        return None
    idx = dates.index(cutoff_date)
    if idx < 199:  # MIN_SESSIONS de download.py; sense prou història encara
        return None

    truncated = copy.deepcopy(record)
    prices = truncated["prices"]
    for key in ("dates", "open", "high", "low", "close", "volume"):
        prices[key] = prices[key][: idx + 1]
    return truncated


def compute_snapshot_for_date(records: list[dict], date_str: str) -> dict | None:
    """Calcula el snapshot complet (indicadors + scores) per a un dia concret,
    seguint exactament el mateix flux que score.py normal."""
    truncated = []
    for r in records:
        t = truncate_up_to(r, date_str)
        if t is not None:
            truncated.append(t)
    if not truncated:
        return None

    indicators_data = {}
    for r in truncated:
        try:
            indicators_data[r["ticker"]] = compute_indicators_for_ticker(r)
        except Exception:
            continue

    fundamentals_data = {
        r["ticker"]: r["fundamentals"]
        for r in truncated
        if r.get("fundamentals_ok")
    }
    if not indicators_data:
        return None

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
            "what_changed": [],
        })

    results.sort(key=lambda r: (r["scores"]["mid_term"] is None, -(r["scores"]["mid_term"] or 0)))
    for i, r in enumerate(results, 1):
        r["rank_mid_term"] = i

    top10_tickers = {r["ticker"] for r in results[:10]}
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
        r["history_series"] = [{"date": date_str, "mid_term": r["scores"]["mid_term"], "rank": r["rank_mid_term"]}]
        r["days_in_top10"] = 1 if ticker in top10_tickers else 0
        r["score_change_7d"] = None
        r["score_change_30d"] = None
        r["best_score_period"] = r["scores"]["mid_term"]
        r["is_best_score_period"] = True
        r["recommendation_line"] = None
        r["change_timeline"] = []

    return {
        "generated_at": f"{date_str}T20:00:00+00:00",
        "duration_seconds": 0.0,
        "universe_size": len(results),
        "horizon_weights": HORIZON_WEIGHTS,
        "history_retention_days": None,
        "universe_daily_summary": [],
        "results": results,
        "is_backfilled": True,
        "fundamentals_frozen": True,  # marca honesta: fonamentals d'avui, no reals d'aquell dia
    }


def main():
    log.info("Carregant dades crues reals (data/raw/*.json)...")
    records = load_raw_records()
    log.info(f"{len(records)} tickers trobats")

    # Totes les dates de mercat presents a qualsevol ticker, dins la finestra
    all_dates = set()
    for r in records:
        for d in r["prices"]["dates"]:
            if d >= START_DATE:
                all_dates.add(d)
    all_dates = sorted(all_dates)
    log.info(f"{len(all_dates)} dates candidates des de {START_DATE}")

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    existing = {p.stem for p in HISTORY_DIR.glob("*.json")}
    log.info(f"{len(existing)} dates ja existents a l'historial (no es tocaran): {sorted(existing)}")

    written, skipped = 0, 0
    for i, date_str in enumerate(all_dates, 1):
        if date_str in existing:
            skipped += 1
            continue

        snapshot = compute_snapshot_for_date(records, date_str)
        if snapshot is None:
            log.warning(f"[{i}/{len(all_dates)}] {date_str}: sense prou dades, s'omet")
            continue

        out_path = HISTORY_DIR / f"{date_str}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False)
        written += 1

        if i % 20 == 0 or i == len(all_dates):
            log.info(f"[{i}/{len(all_dates)}] progrés: {written} escrits, {skipped} ja existents")

    log.info(f"Fet: {written} dies reconstruïts, {skipped} ja existien i no s'han tocat.")


if __name__ == "__main__":
    main()
