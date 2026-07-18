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
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from config import HISTORY_RETENTION_DAYS, SCORE_VERSION
from edgar.score_adapter import edgar_derived_fundamentals, merge_fundamentals

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
HISTORY_DIR = BASE_DIR / "data" / "history" / "scores"

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
        frozen_f = fundamentals.get(ticker, {})
        edgar_f = edgar_derived_fundamentals(ticker, ind.get("as_of"), ind["last_close"])
        f = merge_fundamentals(frozen=frozen_f, edgar=edgar_f)
        fundamentals_sources = f.get("_sources", {})
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
            "fundamentals_sources": fundamentals_sources,
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


CHECKLIST_CRITERIA = [
    "trend_intact", "earnings_growing", "valuation_attractive",
    "quality_solid", "risk_controlled", "not_overbought",
]
CHECKLIST_LABELS = {
    "trend_intact": "Tendència intacta (SMA20>SMA50>SMA200)",
    "earnings_growing": "Beneficis creixent",
    "quality_solid": "Qualitat sòlida",
    "valuation_attractive": "Valoració atractiva",
    "risk_controlled": "Risc controlat",
    "not_overbought": "Sense sobrecompra",
}


def build_checklist(row_sub: pd.Series, row_raw: pd.Series) -> dict:
    """Checklist de 6 criteris deterministes (mateixes dades que ja tenim,
    cap número nou). Falta de dades = criteri no complert (conservador)."""
    trend_alignment = row_raw.get("trend_alignment")
    earnings_growth = row_raw.get("earnings_growth")
    quality = row_sub.get("quality")
    valuation = row_sub.get("valuation")
    risk = row_sub.get("risk")
    rsi = row_raw.get("rsi_raw")

    checks = {
        "trend_intact": trend_alignment == 3,
        "earnings_growing": pd.notna(earnings_growth) and earnings_growth > 0,
        "quality_solid": pd.notna(quality) and quality >= 60,
        "valuation_attractive": pd.notna(valuation) and valuation >= 50,
        "risk_controlled": pd.notna(risk) and risk >= 40,
        "not_overbought": pd.notna(rsi) and rsi < 70,
    }
    passed = sum(1 for v in checks.values() if v)
    total = len(CHECKLIST_CRITERIA)

    if passed >= 5:
        semaforo = "verd"
    elif passed >= 3:
        semaforo = "groc"
    else:
        semaforo = "vermell"

    return {
        "items": [
            {"key": k, "label": CHECKLIST_LABELS[k], "ok": bool(checks[k])}
            for k in CHECKLIST_CRITERIA
        ],
        "passed": passed,
        "total": total,
        "semaforo": semaforo,
    }


def build_what_changed(row_sub: pd.Series, previous_result: dict | None) -> list:
    """Compara els subscores d'avui amb els d'ahir i retorna només els
    canvis significatius (≥3 punts), amb icona segons direcció."""
    if previous_result is None:
        return []
    prev_sub = previous_result.get("subscores", {})
    labels = {
        "momentum": "Momentum", "trend": "Tendència", "valuation": "Valoració",
        "quality": "Qualitat", "growth": "Creixement", "risk": "Risc",
    }
    changes = []
    for key, label in labels.items():
        today_val = row_sub.get(key)
        prev_val = prev_sub.get(key)
        if pd.isna(today_val) or prev_val is None:
            continue
        delta = round(today_val - prev_val, 1)
        if abs(delta) >= 3:
            icon = "✔" if delta > 0 else "⚠"
            sign = "+" if delta > 0 else ""
            changes.append(f"{icon} {label} {sign}{delta:.0f}")
    return changes


def build_change_timeline(ticker: str, history_files: list, max_days: int = 7) -> list:
    """Reconstrueix un historial de canvis dia a dia (fins a max_days enrere)
    comparant cada snapshot amb l'anterior. Determinista, a partir de dades
    ja guardades — no calcula res nou, només diferències."""
    labels = {
        "momentum": "Momentum", "trend": "Tendència", "valuation": "Valoració",
        "quality": "Qualitat", "growth": "Creixement", "risk": "Risc",
    }
    timeline = []
    n = len(history_files)
    start_idx = max(1, n - max_days)

    for i in range(n - 1, start_idx - 1, -1):
        date_str, today_map = history_files[i]
        prev_date, prev_map = history_files[i - 1]
        today_r = today_map.get(ticker)
        prev_r = prev_map.get(ticker)
        if today_r is None:
            continue

        changes = []
        if prev_r is None:
            changes.append("🆕 Comença a seguir-se")
        else:
            today_score = today_r.get("scores", {}).get("mid_term")
            prev_score = prev_r.get("scores", {}).get("mid_term")
            if today_score is not None and prev_score is not None:
                delta = round(today_score - prev_score, 1)
                if abs(delta) >= 1:
                    arrow = "▲" if delta > 0 else "▼"
                    sign = "+" if delta > 0 else ""
                    changes.append(f"{arrow} Score {sign}{delta}")

            today_sub = today_r.get("subscores", {})
            prev_sub = prev_r.get("subscores", {})
            for key, label in labels.items():
                tv, pv = today_sub.get(key), prev_sub.get(key)
                if tv is None or pv is None:
                    continue
                d = round(tv - pv, 1)
                if abs(d) >= 3:
                    arrow = "▲" if d > 0 else "▼"
                    sign = "+" if d > 0 else ""
                    changes.append(f"{arrow} {label} {sign}{d:.0f}")

            today_rank = today_r.get("rank_mid_term")
            prev_rank = prev_r.get("rank_mid_term")
            if today_rank is not None and prev_rank is not None:
                if today_rank <= 10 and prev_rank > 10:
                    changes.append("🔥 Entra al Top 10")
                elif today_rank > 10 and prev_rank <= 10:
                    changes.append("📉 Surt del Top 10")

        if changes:
            timeline.append({"date": date_str, "changes": changes})

    return timeline


def build_recommendation_line(checklist: dict, row_sub: pd.Series) -> str:
    """Frase curta d'estat de la tesi (NO és un consell de compra/venda
    personalitzat, és un resum determinista del semàfor)."""
    semaforo = checklist["semaforo"]
    valuation = row_sub.get("valuation")
    if semaforo == "verd":
        if pd.notna(valuation) and valuation <= 30:
            return "🟢 No hi ha cap senyal que invalidi la tesi, però la valoració és exigent."
        return "🟢 No hi ha cap senyal que invalidi la tesi ara mateix."
    elif semaforo == "groc":
        return "🟡 La tesi es manté, però convé vigilar-la de prop."
    else:
        return "🔴 La tesi s'està deteriorant. Revisa-la abans d'ampliar posició."


def build_narrative(ticker: str, row_sub: pd.Series, row_raw: pd.Series, checklist: dict, rank: int) -> str:
    """Paràgraf explicatiu generat per plantilla a partir de valors reals
    — NO és text generat per IA, és concatenació de frases fixes segons
    condicions numèriques ja calculades."""
    trend_alignment = row_raw.get("trend_alignment")
    earnings_growth = row_raw.get("earnings_growth")
    valuation = row_sub.get("valuation")
    pe = row_raw.get("pe_trailing")
    rsi = row_raw.get("rsi_raw")
    macd_hist = row_raw.get("macd_hist")

    # --- Obertura: posició dins l'univers, ponderada per la qualitat (semàfor) ---
    semaforo = checklist["semaforo"]
    if rank <= 10 and semaforo == "verd":
        if rank <= 3:
            opening = f"{ticker} és una de les millors opcions de tot l'univers ara mateix"
        else:
            opening = f"{ticker} continua entre les millors oportunitats de l'univers"
    elif semaforo == "verd":
        opening = f"{ticker} manté una tesi sòlida encara que no destaqui al capdamunt del rànquing"
    elif semaforo == "vermell":
        opening = f"{ticker} falla la majoria de criteris de la tesi ara mateix"
    else:
        opening = f"{ticker} té un perfil mixt, amb llums i ombres"

    # --- Motiu principal (tendència + creixement) ---
    reasons = []
    if trend_alignment == 3:
        reasons.append("la tendència continua sent molt forta")
    elif trend_alignment == 0:
        reasons.append("la tendència s'ha girat baixista")
    if pd.notna(earnings_growth):
        pct = earnings_growth * 100
        if pct > 0:
            reasons.append(f"els beneficis creixen un {pct:.0f}%")
        else:
            reasons.append(f"els beneficis cauen un {abs(pct):.0f}%")

    reason_text = " i ".join(reasons) if reasons else "els indicadors tècnics es mantenen estables"

    # --- Principal inconvenient (un de sol, el més rellevant) ---
    drawback = None
    if pd.notna(valuation) and valuation <= 30 and pd.notna(pe):
        drawback = f"una valoració exigent (PER {pe:.0f})"
    elif pd.notna(rsi) and rsi >= 70:
        drawback = "està en zona de sobrecompra"
    elif pd.notna(macd_hist) and macd_hist < 0:
        drawback = "el MACD encara mostra pèrdua de momentum"

    sentence = f"{opening} perquè {reason_text}."
    if drawback:
        sentence += f" El principal inconvenient és {drawback}."
    sentence += f" Compleix {checklist['passed']} de {checklist['total']} criteris de la tesi."

    return sentence[0].upper() + sentence[1:]


def build_watch_list(row_sub: pd.Series, row_raw: pd.Series, mid_term_score, semaforo: str) -> list:
    """Genera la llista de "què vigilar": condicions actualment favorables
    que, si es giressin, deteriorarien la tesi. Determinista, no IA."""
    items = []
    trend_alignment = row_raw.get("trend_alignment")
    rsi = row_raw.get("rsi_raw")
    macd_hist = row_raw.get("macd_hist")

    if trend_alignment == 3:
        items.append("Que trenqui la tendència (preu per sota de SMA50)")
    if pd.notna(rsi) and rsi < 70:
        items.append(f"Que el RSI superi 70 (ara és {rsi:.0f})")
    if pd.notna(macd_hist) and macd_hist > 0:
        items.append("Que el MACD es torni negatiu")
    if mid_term_score is not None and semaforo in ("verd", "groc"):
        threshold = 66 if semaforo == "verd" else 40
        if mid_term_score > threshold:
            items.append(f"Que el score de mig termini baixi de {threshold}")

    return items


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


def load_previous_scores() -> dict | None:
    """Carrega l'últim scores.json històric anterior a avui (si n'hi ha) per
    calcular deltes de rànquing i puntuació. Retorna None si és la primera
    execució o no hi ha historial encara."""
    if not HISTORY_DIR.exists():
        return None
    files = sorted(HISTORY_DIR.glob("*.json"))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        prev = json.load(f)
    return {r["ticker"]: r for r in prev.get("results", [])}


def prune_old_history():
    """Esborra snapshots de fa més de HISTORY_RETENTION_DAYS dies perquè el
    repo no creixi indefinidament."""
    if not HISTORY_DIR.exists():
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=HISTORY_RETENTION_DAYS)
    for path in HISTORY_DIR.glob("*.json"):
        try:
            file_date = datetime.strptime(path.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if file_date < cutoff:
            path.unlink()
            log.info(f"Historial podat: {path.name} (fora de la finestra de {HISTORY_RETENTION_DAYS} dies)")


def load_history_files() -> list:
    """Carrega tots els snapshots d'historial disponibles (ordenats per
    data), ja podats a la finestra de retenció."""
    if not HISTORY_DIR.exists():
        return []
    files = sorted(HISTORY_DIR.glob("*.json"))
    loaded = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        date_str = path.stem
        loaded.append((date_str, {r["ticker"]: r for r in data.get("results", [])}))
    return loaded


def compute_evolution_metrics(ticker: str, history_files: list) -> dict:
    """A partir de l'historial ja carregat (fins a 180 dies), calcula per a
    un ticker:
    - history_series: [{date, mid_term, rank}] truncat als últims 30 dies
      (per al gràfic; l'historial complet es fa servir només pel càlcul
      de "millor score del període")
    - days_in_top10: dies consecutius (comptant enrere des d'avui) al Top10
    - score_change_7d / rank_change_7d: comparat amb ~7 execucions enrere
    - score_change_30d: comparat amb ~30 execucions enrere
    - best_score_period / is_best_score_period: el millor score de mig
      termini dels últims 180 dies, i si avui l'iguala o supera
    """
    full_series = []
    for date_str, tickers_map in history_files:
        r = tickers_map.get(ticker)
        if r is not None:
            full_series.append({
                "date": date_str,
                "mid_term": r.get("scores", {}).get("mid_term"),
                "rank": r.get("rank_mid_term"),
            })

    series = full_series[-30:]  # només per al sparkline

    days_in_top10 = 0
    for point in reversed(full_series):
        if point["rank"] is not None and point["rank"] <= 10:
            days_in_top10 += 1
        else:
            break

    def change_n_back(n_back: int):
        if len(full_series) < n_back + 1:
            return None, None
        ref = full_series[-(n_back + 1)]
        today_point = full_series[-1]
        score_change = None
        rank_change = None
        if ref["mid_term"] is not None and today_point["mid_term"] is not None:
            score_change = round(today_point["mid_term"] - ref["mid_term"], 1)
        if ref["rank"] is not None and today_point["rank"] is not None:
            rank_change = ref["rank"] - today_point["rank"]
        return score_change, rank_change

    score_change_7d, rank_change_7d = change_n_back(7)
    score_change_30d, _ = change_n_back(30)

    valid_scores = [p["mid_term"] for p in full_series if p["mid_term"] is not None]
    best_score_period = max(valid_scores) if valid_scores else None
    today_score = full_series[-1]["mid_term"] if full_series else None
    is_best_score_period = (
        best_score_period is not None
        and today_score is not None
        and today_score >= best_score_period
    )

    return {
        "history_series": series,
        "days_in_top10": days_in_top10,
        "score_change_7d": score_change_7d,
        "rank_change_7d": rank_change_7d,
        "score_change_30d": score_change_30d,
        "best_score_period": best_score_period,
        "is_best_score_period": is_best_score_period,
    }


def save_history_snapshot(output: dict):
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(HISTORY_DIR / f"{today}.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)


def build_universe_daily_summary(results: list, max_events: int = 8) -> list:
    """Resum d'esdeveniments rellevants a nivell de tot l'univers (per a la
    pantalla d'inici): entrades al Top10, grans salts de rànquing, grans
    canvis de score. Un sol esdeveniment per ticker (el més significatiu)."""
    best_per_ticker = {}

    def consider(ticker, weight, text):
        if ticker not in best_per_ticker or weight > best_per_ticker[ticker][0]:
            best_per_ticker[ticker] = (weight, text)

    for r in results:
        ticker = r["ticker"]
        if r.get("is_new_top10"):
            consider(ticker, 100, f"🔥 **{ticker}** entra al Top 10")

        rc = r.get("rank_change")
        if rc is not None and abs(rc) >= 10:
            arrow = "▲" if rc > 0 else "▼"
            verb = "puja" if rc > 0 else "baixa"
            consider(ticker, abs(rc), f"{arrow} **{ticker}** {verb} {abs(rc)} posicions")

        sc = r.get("score_change_mid_term")
        if sc is not None and abs(sc) >= 8:
            arrow = "▲" if sc > 0 else "▼"
            consider(ticker, abs(sc) * 2, f"{arrow} **{ticker}** score {'+' if sc > 0 else ''}{sc:.1f}")

    ranked = sorted(best_per_ticker.values(), key=lambda x: -x[0])
    return [text for _, text in ranked[:max_events]]


def main():
    start = datetime.now(timezone.utc)
    log.info("Carregant indicadors i fonamentals...")
    indicators, fundamentals = load_data()
    log.info(f"{len(indicators)} tickers amb indicadors, {len(fundamentals)} amb fonamentals vàlids")

    df = build_dataframe(indicators, fundamentals)
    subscores = compute_subscores(df)
    confidence = compute_confidence(df)
    horizons = horizon_scores(subscores)

    previous = load_previous_scores()  # carregat abans per usar-lo també en checklist/canvis

    results = []
    raw_lookup = {}
    sub_lookup = {}
    for ticker in df.index:
        row_sub = subscores.loc[ticker]
        row_raw = df.loc[ticker]
        raw_lookup[ticker] = row_raw
        sub_lookup[ticker] = row_sub
        checklist = build_checklist(row_sub, row_raw)
        previous_result = previous.get(ticker) if previous else None
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
            "what_changed": build_what_changed(row_sub, previous_result),
            "fundamentals_sources": row_raw.get("fundamentals_sources") or {},
        })

    # Rànquing: ordenem per defecte pel score a mig termini (el més equilibrat)
    results.sort(key=lambda r: (r["scores"]["mid_term"] is None, -(r["scores"]["mid_term"] or 0)))
    for i, r in enumerate(results, 1):
        r["rank_mid_term"] = i

    # Narrativa i "què vigilar": necessiten el rànquing final, per això es
    # calculen en un segon pas (després d'ordenar).
    for r in results:
        ticker = r["ticker"]
        r["narrative"] = build_narrative(
            ticker, sub_lookup[ticker], raw_lookup[ticker], r["checklist"], r["rank_mid_term"]
        )
        r["watch_list"] = build_watch_list(
            sub_lookup[ticker], raw_lookup[ticker], r["scores"]["mid_term"], r["checklist"]["semaforo"]
        )

    # Deltes respecte a l'última execució (per mostrar ▲/▼/🆕 a la PWA)
    top10_tickers_today = {r["ticker"] for r in results[:10]}
    for r in results:
        prev_r = previous.get(r["ticker"]) if previous else None
        if prev_r is None:
            r["rank_change"] = None
            r["score_change_mid_term"] = None
            r["is_new_entry"] = True
        else:
            prev_rank = prev_r.get("rank_mid_term")
            prev_score = prev_r.get("scores", {}).get("mid_term")
            r["rank_change"] = (
                (prev_rank - r["rank_mid_term"]) if prev_rank is not None else None
            )
            r["score_change_mid_term"] = (
                round(r["scores"]["mid_term"] - prev_score, 1)
                if (prev_score is not None and r["scores"]["mid_term"] is not None)
                else None
            )
            r["is_new_entry"] = False
        prev_top10 = (
            {t for t, v in previous.items() if v.get("rank_mid_term", 999) <= 10}
            if previous else set()
        )
        r["is_new_top10"] = r["ticker"] in top10_tickers_today and r["ticker"] not in prev_top10

    # Evolució (historial 30 dies): poda l'historial vell, carrega el que queda,
    # hi afegim el snapshot d'avui (encara no desat a disc) i calculem mètriques.
    prune_old_history()
    history_files = load_history_files()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    history_files.append((today_str, {r["ticker"]: r for r in results}))
    for r in results:
        r.update(compute_evolution_metrics(r["ticker"], history_files))
        r["change_timeline"] = build_change_timeline(r["ticker"], history_files)
        r["recommendation_line"] = build_recommendation_line(r["checklist"], sub_lookup[r["ticker"]])

    universe_daily_summary = build_universe_daily_summary(results)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round((datetime.now(timezone.utc) - start).total_seconds(), 2),
        "universe_size": len(results),
        "horizon_weights": HORIZON_WEIGHTS,
        "history_retention_days": HISTORY_RETENTION_DAYS,
        "score_version": SCORE_VERSION,
        "universe_daily_summary": universe_daily_summary,
        "results": results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=None)

    save_history_snapshot(output)

    log.info(f"Fet: {len(results)} tickers puntuats -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
