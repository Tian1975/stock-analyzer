"""
scripts/validate_providers.py

Prova 5: compara el pipeline de scoring COMPLET (Yahoo-only, tal com
funciona avui) contra el mateix pipeline amb els fonamentals fusionats
amb EDGAR, sobre l'univers REAL (109 tickers), per confirmar que
canviar la font de dades NO altera materialment el comportament del
model.

NO toca score.py. Reutilitza les seves funcions (build_dataframe,
compute_subscores, horizon_scores) important-les directament, aixi
que si algun dia la logica de score.py canvia, aquesta prova sempre
compara contra la logica REAL i actualitzada, no una copia que es
pugui desincronitzar.

Es reprodueix la percentil-normalitzacio correctament perque es
calcula sobre l'univers SENCER a totes dues passades -- no nomes
sobre els 4 tickers de validacio -- que es exactament com funciona
score.py en produccio.

Genera reports/edgar_validation.md amb el resultat, per poder-lo
tornar a executar en el futur com a regressio cada vegada que es
toqui el normalitzador o l'adaptador.

Us (GitHub Actions, workflow_dispatch manual):
    python scripts/validate_providers.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

import pandas as pd

from score import load_data, build_dataframe, compute_subscores, horizon_scores, HORIZON_WEIGHTS
from edgar.score_adapter import edgar_derived_fundamentals, merge_fundamentals

VALIDATION_TICKERS = ["AAPL", "MSFT", "JNJ", "JPM"]
REPORT_PATH = BASE_DIR / "reports" / "edgar_validation.md"

# Llindars acordats: <1 perfecte, 1-3 revisar, >=3 investigar abans de desplegar.
THRESHOLD_OK = 1.0
THRESHOLD_REVIEW = 3.0

RAW_FIELDS_TO_COMPARE = ["pe_trailing", "profit_margin", "revenue_growth", "earnings_growth"]


def build_patched_fundamentals(indicators: dict, frozen_fundamentals: dict) -> dict:
    """
    Per a CADA ticker de l'univers (no nomes els de validacio),
    calcula els fonamentals EDGAR (si n'hi ha) i els fusiona amb
    els frozen actuals. Cal fer-ho per tot l'univers perque els
    percentils es calculen relatius a tothom -- si nomes patchegem
    4 tickers pero calculem percentils sobre 109, el resultat no
    seria representatiu del que passaria realment en produccio.
    """
    patched = {}
    for ticker, ind in indicators.items():
        frozen = frozen_fundamentals.get(ticker, {})
        edgar = edgar_derived_fundamentals(ticker, ind.get("as_of"), ind.get("last_close"))
        patched[ticker] = merge_fundamentals(frozen=frozen, edgar=edgar) if edgar else frozen
    return patched


def compare_ticker(ticker: str, baseline_df, baseline_sub, baseline_hz,
                    patched_df, patched_sub, patched_hz) -> dict:
    row = {"ticker": ticker}

    for field in RAW_FIELDS_TO_COMPARE:
        b = baseline_df.loc[ticker, field] if ticker in baseline_df.index else None
        p = patched_df.loc[ticker, field] if ticker in patched_df.index else None
        row[field] = (b, p)

    for sub in ["quality", "valuation", "growth"]:
        b = baseline_sub.loc[ticker, sub] if ticker in baseline_sub.index else None
        p = patched_sub.loc[ticker, sub] if ticker in patched_sub.index else None
        row[f"subscore_{sub}"] = (b, p)

    for horizon in HORIZON_WEIGHTS:
        b = baseline_hz.loc[ticker, horizon] if ticker in baseline_hz.index else None
        p = patched_hz.loc[ticker, horizon] if ticker in patched_hz.index else None
        row[f"score_{horizon}"] = (b, p)

    return row


def compute_universe_deltas(baseline_hz, patched_hz) -> list:
    """
    Deltes de mid_term score per a TOT l'univers (no nomes els 4
    tickers de validacio), per distingir un outlier puntual d'una
    desviacio sistemica.
    """
    deltas = []
    for ticker in baseline_hz.index:
        b = baseline_hz.loc[ticker, "mid_term"]
        p = patched_hz.loc[ticker, "mid_term"] if ticker in patched_hz.index else None
        if b is None or p is None or pd.isna(b) or pd.isna(p):
            continue
        deltas.append(abs(p - b))
    return deltas


def compute_top10_overlap(baseline_hz, patched_hz) -> tuple:
    """
    Compara el Top10 per mid_term score abans i despres. Retorna
    (overlap_count, baseline_top10, patched_top10).
    """
    baseline_top10 = set(
        baseline_hz["mid_term"].dropna().sort_values(ascending=False).head(10).index
    )
    patched_top10 = set(
        patched_hz["mid_term"].dropna().sort_values(ascending=False).head(10).index
    )
    overlap = len(baseline_top10 & patched_top10)
    return overlap, baseline_top10, patched_top10


def format_delta(b, p) -> str:
    if b is None or p is None or pd.isna(b) or pd.isna(p):
        return "N/A"
    delta = p - b
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.2f}"


def run_validation() -> None:
    print("Carregant indicadors i fonamentals (univers complet)...")
    indicators, frozen_fundamentals = load_data()
    print(f"{len(indicators)} tickers a l'univers\n")

    print("Passada 1/2: pipeline BASELINE (Yahoo-only, tal com avui)...")
    baseline_df = build_dataframe(indicators, frozen_fundamentals)
    baseline_sub = compute_subscores(baseline_df)
    baseline_hz = horizon_scores(baseline_sub)

    print("Passada 2/2: pipeline PATCHED (EDGAR+Yahoo fusionat)...")
    patched_fundamentals = build_patched_fundamentals(indicators, frozen_fundamentals)
    patched_df = build_dataframe(indicators, patched_fundamentals)
    patched_sub = compute_subscores(patched_df)
    patched_hz = horizon_scores(patched_sub)

    print("\nComparant tickers de validacio...\n")

    lines = ["# Validació EDGAR vs Yahoo\n"]
    lines.append("```")
    lines.append("Provider validation")
    lines.append("===================")
    lines.append(f"Universe: {len(indicators)}")
    lines.append("(mètriques d'univers complet i resultat final al final d'aquest informe)")
    lines.append("```\n")

    mid_term_deltas = []

    for ticker in VALIDATION_TICKERS:
        if ticker not in indicators:
            print(f"⚠️  {ticker}: no és a l'univers, s'omet")
            continue

        row = compare_ticker(ticker, baseline_df, baseline_sub, baseline_hz,
                              patched_df, patched_sub, patched_hz)

        print(f"--- {ticker} ---")
        lines.append(f"\n## {ticker}\n")
        lines.append("| Mètrica | Yahoo | EDGAR+Yahoo | Δ |")
        lines.append("|---|---|---|---|")

        for field in RAW_FIELDS_TO_COMPARE:
            b, p = row[field]
            delta_str = format_delta(b, p)
            print(f"  {field:20s} Yahoo={b}  EDGAR+Yahoo={p}  Δ={delta_str}")
            lines.append(f"| {field} | {b} | {p} | {delta_str} |")

        for sub in ["quality", "valuation", "growth"]:
            b, p = row[f"subscore_{sub}"]
            delta_str = format_delta(b, p)
            print(f"  subscore_{sub:12s} Yahoo={b:.1f}  EDGAR+Yahoo={p:.1f}  Δ={delta_str}"
                  if b is not None and p is not None and not pd.isna(b) and not pd.isna(p)
                  else f"  subscore_{sub:12s} N/A")
            lines.append(f"| subscore_{sub} | {b:.1f} | {p:.1f} | {delta_str} |"
                          if b is not None and p is not None and not pd.isna(b) and not pd.isna(p)
                          else f"| subscore_{sub} | {b} | {p} | N/A |")

        b_mid, p_mid = row["score_mid_term"]
        delta_str = format_delta(b_mid, p_mid)
        print(f"  mid_term score      Yahoo={b_mid:.1f}  EDGAR+Yahoo={p_mid:.1f}  Δ={delta_str}\n")
        lines.append(f"| **mid_term score** | **{b_mid:.1f}** | **{p_mid:.1f}** | **{delta_str}** |")

        if b_mid is not None and p_mid is not None and not pd.isna(b_mid) and not pd.isna(p_mid):
            mid_term_deltas.append(abs(p_mid - b_mid))

    print("=" * 50)
    print("VALIDACIÓ D'UNIVERS COMPLET")
    print("=" * 50)

    universe_deltas = compute_universe_deltas(baseline_hz, patched_hz)
    n_gt1 = sum(1 for d in universe_deltas if d > 1.0)
    n_gt3 = sum(1 for d in universe_deltas if d > 3.0)
    n_gt5 = sum(1 for d in universe_deltas if d > 5.0)

    overlap, baseline_top10, patched_top10 = compute_top10_overlap(baseline_hz, patched_hz)

    if universe_deltas:
        mean_abs_universe = sum(universe_deltas) / len(universe_deltas)
        max_abs_universe = max(universe_deltas)
    else:
        mean_abs_universe = max_abs_universe = 0.0

    print(f"Universe: {len(indicators)}")
    print(f"Mean delta (mid_term, tot l'univers): {mean_abs_universe:.2f}")
    print(f"Max delta (tot l'univers): {max_abs_universe:.2f}")
    print(f"Tickers amb Δ > 1.0: {n_gt1}")
    print(f"Tickers amb Δ > 3.0: {n_gt3}")
    print(f"Tickers amb Δ > 5.0: {n_gt5}")
    print(f"Top10 overlap: {overlap}/10")

    lines.append("\n---\n\n## Validació d'univers complet\n")
    lines.append(f"- Universe: {len(indicators)}")
    lines.append(f"- Mean delta (mid_term, tot l'univers): {mean_abs_universe:.2f}")
    lines.append(f"- Max delta (tot l'univers): {max_abs_universe:.2f}")
    lines.append(f"- Tickers amb Δ > 1.0: {n_gt1}")
    lines.append(f"- Tickers amb Δ > 3.0: {n_gt3}")
    lines.append(f"- Tickers amb Δ > 5.0: {n_gt5}")
    lines.append(f"- Top10 overlap: {overlap}/10")
    lines.append(f"  - Top10 Yahoo: {sorted(baseline_top10)}")
    lines.append(f"  - Top10 EDGAR+Yahoo: {sorted(patched_top10)}")

    print("\n" + "=" * 50)
    print("RESUM (tickers de validació)")
    print("=" * 50)
    if mid_term_deltas:
        mean_abs = sum(mid_term_deltas) / len(mid_term_deltas)
        max_abs = max(mid_term_deltas)
    else:
        mean_abs = max_abs = 0.0

    # El PASS/REVIEW/FAIL es decideix sobre l'univers COMPLET, no
    # nomes els 4 tickers de validacio -- es la mesura mes honesta
    # de si hi ha una desviacio sistemica introduida pel patch.
    if max_abs_universe < THRESHOLD_OK and n_gt3 == 0:
        status = "✅ PASS"
    elif max_abs_universe < THRESHOLD_REVIEW and n_gt5 == 0:
        status = "⚠️  REVISAR"
    else:
        status = "🔴 INVESTIGAR ABANS DE DESPLEGAR"

    print(f"Mean absolute delta (tickers validació): {mean_abs:.2f}")
    print(f"Max delta (tickers validació): {max_abs:.2f}")
    print(f"Tickers comparats (validació): {len(mid_term_deltas)}")
    print(f"Estat: {status}")

    lines.append("\n## Resum final\n")
    lines.append(f"- Mean absolute delta (tickers validació): {mean_abs:.2f}")
    lines.append(f"- Max delta (tickers validació): {max_abs:.2f}")
    lines.append(f"- Tickers comparats (validació): {len(mid_term_deltas)}")
    lines.append(f"- **RESULTAT: {status}**")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nInforme guardat a {REPORT_PATH}")


if __name__ == "__main__":
    run_validation()
