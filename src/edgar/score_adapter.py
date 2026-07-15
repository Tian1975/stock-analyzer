"""
score_adapter.py
"""

from .lookup import yoy_growth, get_latest_fy_value

EDGAR_DERIVABLE_FIELDS = [
    "pe_trailing",
    "profit_margin",
    "revenue_growth",
    "earnings_growth",
]

ALL_FUNDAMENTAL_FIELDS = [
    "pe_trailing",
    "peg_ratio",
    "price_to_book",
    "return_on_equity",
    "profit_margin",
    "debt_to_equity",
    "revenue_growth",
    "earnings_growth",
    "beta",
]


def edgar_derived_fundamentals(ticker: str, date: str, last_close: float | None) -> dict:
    """
    Nomes dades ANUALS (FY), mai barrejant trimestral amb anual.
    profit_margin/revenue_growth/earnings_growth com a FRACCIO
    (0.24 = 24%), no percentatge, per coincidir amb Yahoo.
    """
    eps_fy = get_latest_fy_value(ticker, "eps_basic", date)
    net_income_fy = get_latest_fy_value(ticker, "net_income", date)
    revenue_fy = get_latest_fy_value(ticker, "revenue", date)

    out = {}

    if eps_fy and last_close is not None and eps_fy != 0:
        out["pe_trailing"] = round(last_close / eps_fy, 2)

    if net_income_fy is not None and revenue_fy:
        out["profit_margin"] = round(net_income_fy / revenue_fy, 4)

    rev_growth = yoy_growth(ticker, "revenue", date)
    if rev_growth is not None:
        out["revenue_growth"] = round(rev_growth / 100, 4)

    earn_growth = yoy_growth(ticker, "net_income", date)
    if earn_growth is not None:
        out["earnings_growth"] = round(earn_growth / 100, 4)

    return out


def merge_fundamentals(frozen: dict, edgar: dict) -> dict:
    result = dict(frozen)
    sources = {}

    for key in ALL_FUNDAMENTAL_FIELDS:
        if frozen.get(key) is not None:
            sources[key] = "Yahoo"

    for key, value in edgar.items():
        if value is None:
            continue
        result[key] = value
        sources[key] = "EDGAR"

    result["_sources"] = sources
    return result


def audit_fundamentals(ticker: str, date: str, last_close: float | None, frozen: dict) -> dict:
    edgar = edgar_derived_fundamentals(ticker, date, last_close)
    merged = merge_fundamentals(frozen, edgar)
    sources = merged.get("_sources", {})

    derived = [k for k in ALL_FUNDAMENTAL_FIELDS if sources.get(k) == "EDGAR"]
    fallback = [k for k in ALL_FUNDAMENTAL_FIELDS if sources.get(k) == "Yahoo"]
    still_missing = [k for k in ALL_FUNDAMENTAL_FIELDS if merged.get(k) is None]

    return {
        "ticker": ticker,
        "provider": "EDGAR" if edgar else "cap dada EDGAR",
        "coverage": round(len(derived) / len(ALL_FUNDAMENTAL_FIELDS), 2),
        "derived": derived,
        "fallback": fallback,
        "still_missing": still_missing,
    }
