"""
score.py — Combina indicadors tècnics (data/indicators.json) i fonamentals
(data/raw/*.json) en 6 subscores normalitzats (0-100) per ticker, i els
combina en 3 scores finals (curt/mig/llarg termini) amb pesos fixos.

Principi clau: els scores són 100% reproduïbles a partir de números — cap IA
decideix res aquí. Les explicacions es generen amb regles simples sobre els
mateixos valors, no s'inventen.

Normalització: cada mètrica es converteix en un percentil (0-100) respecte a
la resta de l'univers d'aquell dia. Això evita haver de fixar llindars
arbitraris (ex. "PER < 15 és bo") que varien molt entre sectors i moments.

Subscores (0-100 cadascun):
- Momentum: retorns 1m/3m/6m + MACD histograma + RSI (millor a la zona 50-70)
- Trend: alineació de mitjanes (close > SMA20 > SMA50 > SMA200) + distància a SMA200
- Valuation: PER, PEG, Price/Book (percentil invers: més barat = millor)
- Quality: ROE, marges, deute/equity (invers)
- Growth: creixement d'ingressos i beneficis
- Risk (= seguretat, 100 és més segur): volatilitat anualitzada, ATR relatiu, beta (inversos)

Pesos per horitzó:
  Curt:  70% Momentum, 20% Trend, 10% Risk
  Mitjà: 40% Trend, 30% Momentum, 20% Quality, 10% Valuation
  Llarg: 40% Quality, 30% Valuation, 20% Growth, 10% Risk

Ús: python src/score.py
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("score")

BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
INDICATORS_PATH = BASE_DIR / "data" / "indicators.json"
OUTPUT_PATH = BASE_DIR / "data" / "scores.json"

HORIZON_WEIGHTS = {
    "short_term": {"momentum": 0.70, "trend": 0.20, "risk": 0.10},
    "mid_term": {"trend": 0.40, "momentum": 0.30, "quality": 0.20, "valuation": 0.10},
    "long_term": {"quality": 0.40, "valuation": 0.30, "growth": 0.20, "risk": 0.10},
}


def load_data():
    with open(INDICATORS_PATH, encoding="utf-8") as f:
        indicators = json.load(f)["data"]

    fundamentals = {}
    for path in RAW_DIR.glob("*.json"):
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
        if rec.get("ok") and rec.get("fundamentals_ok"):
            fundamentals[rec["ticker"]] = rec["fundamentals"]

    return indicators, fundamentals


def percentile_rank(series: pd.Series, invert: bool = False) -> pd.Series:
    """Converteix una sèrie de valors en percentils 0-100. NaN es queda NaN
    (no participa al rànquing, es gestiona després a nivell de subscore)."""
    ranks = series.rank(pct=True, na_option="keep") * 100
    if invert:
        ranks = 100 - ranks
    return ranks


def rsi_shape_score(rsi: float | None) -> float | None:
    """RSI ideal cap a la zona 50-70 (tendència sana sense sobrecompra extrema).
    Penalitza tant la sobrevenda com la sobrecompra severa."""
    if rsi is None:
        return None
    target = 60
    return max(0.0, 100 - abs(rsi - target) * 2)


def safe_mean(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if not clean:
        return None
    return sum(clean) / len(clean)


def build_dataframe(indicators: dict, fundamentals: dict) -> pd.DataFrame:
    rows = []
    for ticker, ind in indicators.items():
        f = fundamentals.get(ticker, {})
        trend = ind["trend"]
        mom = ind["momentum"]
        vol = ind["volatility"]

        close = ind["last_close"]
        sma20, sma50, sma200 = trend["sma20"], trend["sma50"], trend["sma200"]

        # Alineació de tendència: quants dels 3 esglaons es compleixen
        trend_alignment = None
        if all(v is not None for v in [close, sma20, sma50, sma200]):
            trend_alignment = sum([close > sma20, sma20 > sma50, sma50 > sma200])

        trend_distance = None
        if close is not None and sma200 is not None and sma200 != 0:
            trend_distance = 100 * (close - sma200) / sma200

        macd_hist = mom["macd"]["histogram"] if mom.get("macd") else None
        atr_relative = None
        if vol["atr14"] is not None and close:
            atr_relative = 100 * vol["atr14"] / close

        rows.append({
            "ticker": ticker,
            "region": ind.get("region"),
            "as_of": ind.get("as_of"),
            "last_close": close,
            "sessions_available": ind.get("sessions_available"),
            # Momentum
            "ret_1m": mom["return_pct"].get("1m"),
            "ret_3m": mom["return_pct"].get("3m"),
            "ret_6m": mom["return_pct"].get("6m"),
            "macd_hist": macd_hist,
            "rsi_raw": mom["rsi14"],
            # Trend
            "trend_alignment": trend_alignment,
            "trend_distance_pct": trend_distance,
            # Valuation
            "pe_trailing": f.get("pe_trailing"),
            "peg_ratio": f.get("peg_ratio"),
            "price_to_book": f.get("price_to_book"),
            # Quality
            "roe": f.get("return_on_equity"),
            "profit_margin": f.get("profit_margin"),
            "debt_to_equity": f.get("debt_to_equity"),
            # Growth
            "revenue_growth": f.get("revenue_growth"),
            "earnings_growth": f.get("earnings_growth"),
            # Risk
            "volatility_pct": vol["annualized_volatility_pct"],
            "atr_relative_pct": atr_relative,
            "beta": f.get("beta"),
            "week52_position_pct": vol["week52_position_pct"],
        })

    return pd.DataFrame(rows).set_index("ticker")


def compute_subscores(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)

    # --- Momentum ---
    ret_score = pd.concat(
        [percentile_rank(df["ret_1m"]), percentile_rank(df["ret_3m"]), percentile_rank(df["ret_6m"])],
        axis=1,
    ).mean(axis=1, skipna=True)
    macd_score = percentile_rank(df["macd_hist"])
    rsi_score = df["rsi_raw"].apply(rsi_shape_score)
    out["momentum"] = pd.concat([ret_score, macd_score, rsi_score], axis=1).mean(axis=1, skipna=True)

    # --- Trend ---
    alignment_score = (df["trend_alignment"] / 3 * 100) if "trend_alignment" in df else np.nan
    distance_score = percentile_rank(df["trend_distance_pct"])
    out["trend"] = pd.concat([alignment_score, distance_score], axis=1).mean(axis=1, skipna=True)

    # --- Valuation (més barat = millor -> invertit) ---
    pe_score = percentile_rank(df["pe_trailing"], invert=True)
    peg_score = percentile_rank(df["peg_ratio"], invert=True)
    pb_score = percentile_rank(df["price_to_book"], invert=True)
    out["valuation"] = pd.concat([pe_score, peg_score, pb_score], axis=1).mean(axis=1, skipna=True)

    # --- Quality ---
    roe_score = percentile_rank(df["roe"])
    margin_score = percentile_rank(df["profit_margin"])
    debt_score = percentile_rank(df["debt_to_equity"], invert=True)
    out["quality"] = pd.concat([roe_score, margin_score, debt_score], axis=1).mean(axis=1, skipna=True)

    # --- Growth ---
    rev_growth_score = percentile_rank(df["revenue_growth"])
    earn_growth_score = percentile_rank(df["earnings_growth"])
    out["growth"] = pd.concat([rev_growth_score, earn_growth_score], axis=1).mean(axis=1, skipna=True)

    # --- Risk (= seguretat; 100 és més segur) ---
    vol_score = percentile_rank(df["volatility_pct"], invert=True)
    atr_score = percentile_rank(df["atr_relative_pct"], invert=True)
    beta_score = percentile_rank(df["beta"], invert=True)
    out["risk"] = pd.concat([vol_score, atr_score, beta_score], axis=1).mean(axis=1, skipna=True)

    return out


def compute_confidence(df: pd.DataFrame) -> pd.Series:
    """Percentatge de mètriques disponibles (no nul·les) sobre el total possible,
    com a mesura de consens/completesa — NO és una probabilitat real."""
    cols = [
        "ret_1m", "ret_3m", "ret_6m", "macd_hist", "rsi_raw",
        "trend_alignment", "trend_distance_pct",
        "pe_trailing", "peg_ratio", "price_to_book",
        "roe", "profit_margin", "debt_to_equity",
        "revenue_growth", "earnings_growth",
        "volatility_pct", "atr_relative_pct", "beta",
    ]
    available = df[cols].notna().sum(axis=1)
    return round(100 * available / len(cols), 1)


def horizon_scores(subscores: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=subscores.index)
    for horizon, weights in HORIZON_WEIGHTS.items():
        components = []
        weight_sum_per_row = pd.Series(0.0, index=subscores.index)
        weighted_sum = pd.Series(0.0, index=subscores.index)
        for subscore_name, w in weights.items():
            values = subscores[subscore_name]
            has_value = values.notna()
            weighted_sum = weighted_sum.add(values.fillna(0) * w * has_value, fill_value=0)
            weight_sum_per_row = weight_sum_per_row.add(w * has_value, fill_value=0)
        # Si falten components, redistribuïm sobre els pesos disponibles (no penalitzem
        # per manca de dades més enllà del que ja reflecteix `confidence`)
        out[horizon] = (weighted_sum / weight_sum_per_row.replace(0, np.nan)).round(1)
    return out


def risk_label(row) -> str:
    risk_score = row["risk"]
    if pd.isna(risk_score):
        return "desconegut"
    if risk_score >= 66:
        return "baix"
    elif risk_score >= 40:
        return "moderat"
    return "alt"


def build_explanation(ticker: str, row: pd.Series, raw: pd.Series) -> list[str]:
    """Explicació basada en regles simples sobre valors reals — no generativa."""
    lines = []

    trend_alignment = raw.get("trend_alignment")
    if pd.notna(trend_alignment):
        if trend_alignment == 3:
            lines.append("✔ SMA20 > SMA50 > SMA200 (tendència alcista alineada)")
        elif trend_alignment == 0:
            lines.append("⚠ Tendència baixista (SMA20 < SMA50 < SMA200)")

    rsi = raw.get("rsi_raw")
    if pd.notna(rsi):
        if rsi >= 70:
            lines.append(f"⚠ RSI = {rsi:.0f} (zona de sobrecompra)")
        elif rsi <= 30:
            lines.append(f"⚠ RSI = {rsi:.0f} (zona de sobrevenda)")
        else:
            lines.append(f"✔ RSI = {rsi:.0f} (sense sobrecompra)")

    macd_h = raw.get("macd_hist")
    if pd.notna(macd_h):
        lines.append(f"{'✔' if macd_h > 0 else '⚠'} MACD histograma {'positiu' if macd_h > 0 else 'negatiu'}")

    pe = raw.get("pe_trailing")
    if pd.notna(pe) and pe > 0:
        lines.append(f"PER: {pe:.1f}")

    growth = raw.get("earnings_growth")
    if pd.notna(growth):
        lines.append(f"{'✔' if growth > 0 else '⚠'} Creixement de beneficis: {growth*100:.1f}%")

    vol = raw.get("volatility_pct")
    if pd.notna(vol) and vol > 40:
        lines.append(f"⚠ Volatilitat elevada ({vol:.1f}% anualitzada)")

    return lines


def main():
    start = datetime.now(timezone.utc)
    log.info("Carregant indicadors i fonamentals...")
    indicators, fundamentals = load_data()
    log.info(f"{len(indicators)} tickers amb indicadors, {len(fundamentals)} amb fonamentals vàlids")

    df = build_dataframe(indicators, fundamentals)
    subscores = compute_subscores(df)
    confidence = compute_confidence(df)
    horizons = horizon_scores(subscores)

    results = []
    for ticker in df.index:
        row_sub = subscores.loc[ticker]
        row_raw = df.loc[ticker]
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
        })

    # Rànquing: ordenem per defecte pel score a mig termini (el més equilibrat)
    results.sort(key=lambda r: (r["scores"]["mid_term"] is None, -(r["scores"]["mid_term"] or 0)))
    for i, r in enumerate(results, 1):
        r["rank_mid_term"] = i

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round((datetime.now(timezone.utc) - start).total_seconds(), 2),
        "universe_size": len(results),
        "horizon_weights": HORIZON_WEIGHTS,
        "results": results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=None)

    log.info(f"Fet: {len(results)} tickers puntuats -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
