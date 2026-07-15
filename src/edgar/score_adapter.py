"""
score_adapter.py

Pont entre el connector EDGAR (primitives: revenue, net_income,
eps_basic, operating_income, shares_outstanding) i el format que
score.py ja consumeix avui (ratios ja calculades: pe_trailing,
profit_margin, revenue_growth, earnings_growth, return_on_equity,
price_to_book, debt_to_equity, peg_ratio, beta).

Tres responsabilitats separades, cadascuna testejable pel seu
compte:

    1. edgar_derived_fundamentals()  -- primitives EDGAR -> ratios
    2. merge_fundamentals()          -- fusiona dues fonts, camp a camp
    3. audit_fundamentals()          -- fotografia de dependencia per font

score.py NO es modifica en la seva logica: continua rebent un dict
pla amb les mateixes claus de sempre (f["profit_margin"], etc.) i no
necessita saber que existeix EDGAR.
"""

from .providers import EdgarProvider, CompositeProvider, FundamentalsNotAvailable
from .lookup import yoy_growth

_edgar_provider = CompositeProvider([EdgarProvider()])

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
    Responsabilitat UNICA: convertir primitives EDGAR en ratios.
    No sap res de Yahoo ni de fusio de fonts.
    """
    try:
        f = _edgar_provider.lookup(ticker, date)
    except FundamentalsNotAvailable:
        return {}

    out = {}

    eps = f.get("eps_basic")
    if eps and last_close is not None and eps != 0:
        out["pe_trailing"] = round(last_close / eps, 2)

    net_income = f.get("net_income")
    revenue = f.get("revenue")
    if net_income is not None and revenue:
        out["profit_margin"] = round(100 * net_income / revenue, 2)

    rev_growth = yoy_growth(ticker, "revenue", date)
    if rev_growth is not None:
        out["revenue_growth"] = rev_growth

    earn_growth = yoy_growth(ticker, "net_income", date)
    if earn_growth is not None:
        out["earnings_growth"] = earn_growth

    return out


def merge_fundamentals(frozen: dict, edgar: dict) -> dict:
    """
    Responsabilitat UNICA: fusionar dues fonts, camp a camp,
    SENSE perdre mai una dada valida de `frozen` nomes perque
    `edgar` existeix pero no cobreix aquell camp concret.

    Afegeix "_sources": {clau: "EDGAR"|"Yahoo"} per a auditoria.
    """
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
    """
    No afecta el pipeline ni el score. Fotografia de quant depenem
    encara de Yahoo per a aquest ticker/data.
    """
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
