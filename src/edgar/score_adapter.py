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

from .lookup import get_latest_fy_value, fy_yoy_growth

# Feature flags: portes d'entrada explicites per a funcionalitat
# EXPERIMENTAL que existeix, esta testejada, pero encara NO forma
# part del calcul real de fonamentals. Activar-les no hauria de
# petar res (el pipeline sencer continua funcionant igual), pero
# tampoc s'ha de fer sense revisar-ho abans amb la Prova 5.
FEATURE_FLAGS = {
    # revenue_growth/earnings_growth calculats FY-a-FY amb EDGAR.
    # Desactivat: Yahoo sembla mesurar "growth" amb una altra base
    # temporal (TTM/trimestral), molt mes suau que la comparacio
    # FY-a-FY anual. Per a empreses amb despeses extraordinaries en
    # un exercici concret (p.ex. JNJ, litigis de talc 2024), el
    # FY-a-FY pot oscil·lar +90% o mes -- correcte pero no
    # comparable amb Yahoo sota el mateix percentil. Antes
    # d'activar-ho caldria decidir com exposar-ho (potser com a
    # camps nous "revenue_growth_fy"/"earnings_growth_fy" en lloc
    # de sobreescriure els de Yahoo).
    "edgar_growth": False,
}

EDGAR_DERIVABLE_FIELDS = [
    "pe_trailing",
    "profit_margin",
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

    IMPORTANT: tots els calculs es fan nomes amb dades ANUALS (FY),
    identificades per durada real del periode, mai barrejant
    trimestral amb anual.

    Nomes pe_trailing i profit_margin son actius per defecte (Fase
    1b). El bloc de "growth" es experimental i nomes s'activa amb
    FEATURE_FLAGS["edgar_growth"] = True -- vegeu docstring de
    fy_yoy_growth() a lookup.py per l'explicacio completa.
    """
    eps_fy = get_latest_fy_value(ticker, "eps_basic", date)
    net_income_fy = get_latest_fy_value(ticker, "net_income", date)
    revenue_fy = get_latest_fy_value(ticker, "revenue", date)

    out = {}

    if eps_fy and last_close is not None and eps_fy != 0:
        out["pe_trailing"] = round(last_close / eps_fy, 2)

    if net_income_fy is not None and revenue_fy:
        out["profit_margin"] = round(net_income_fy / revenue_fy, 4)

    if FEATURE_FLAGS["edgar_growth"]:
        rev_growth = fy_yoy_growth(ticker, "revenue", date)
        if rev_growth is not None:
            out["revenue_growth"] = round(rev_growth / 100, 4)

        earn_growth = fy_yoy_growth(ticker, "net_income", date)
        if earn_growth is not None:
            out["earnings_growth"] = round(earn_growth / 100, 4)

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
