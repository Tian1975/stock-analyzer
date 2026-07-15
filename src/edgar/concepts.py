"""
concepts.py

Mapeig entre conceptes "canonics" (el llenguatge que parla score.py)
i els tags XBRL reals que SEC EDGAR fa servir (que varien entre
empreses i han canviat al llarg dels anys).

Cada concepte canonic te una llista ORDENADA de tags candidats.
El normalitzador prova el primer tag; si l'empresa no l'ha fet servir
mai, prova el seguent, etc. Aixo es necessari perque, per exemple,
"Revenue" es diu "Revenues" en unes empreses i
"RevenueFromContractWithCustomerExcludingAssessedTax" en altres
(sobretot despres del canvi d'estandard comptable ASC 606, ~2018).

Fase 1 (aquest fitxer): nomes els 5 conceptes imprescindibles.
Ampliar aquesta llista es la unica feina necessaria per afegir
conceptes nous — la resta del pipeline no cal tocar-lo.
"""

# taxonomia -> llista de tags candidats, en ordre de preferencia
CANONICAL_CONCEPTS = {
    "revenue": {
        "taxonomy": "us-gaap",
        "tags": [
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "SalesRevenueNet",
        ],
        "unit": "USD",
    },
    "net_income": {
        "taxonomy": "us-gaap",
        "tags": [
            "NetIncomeLoss",
            "ProfitLoss",
            "NetIncomeLossAvailableToCommonStockholdersBasic",
        ],
        "unit": "USD",
    },
    "eps_basic": {
        "taxonomy": "us-gaap",
        "tags": [
            "EarningsPerShareBasic",
            "EarningsPerShareBasicAndDiluted",
        ],
        "unit": "USD/shares",
    },
    "operating_income": {
        "taxonomy": "us-gaap",
        "tags": [
            "OperatingIncomeLoss",
        ],
        "unit": "USD",
    },
    "shares_outstanding": {
        "taxonomy": "dei",
        "tags": [
            "EntityCommonStockSharesOutstanding",
        ],
        "unit": "shares",
    },
}

# Conceptes previstos per a fases posteriors (no implementats encara,
# nomes documentats aqui perque quan arribi el moment nomes cal afegir
# l'entrada i el normalitzador ja els recollira sense mes canvis).
FUTURE_CONCEPTS = {
    "operating_cash_flow": {
        "taxonomy": "us-gaap",
        "tags": ["NetCashProvidedByUsedInOperatingActivities"],
        "unit": "USD",
    },
    "capital_expenditures": {
        "taxonomy": "us-gaap",
        "tags": ["PaymentsToAcquirePropertyPlantAndEquipment"],
        "unit": "USD",
    },
    "total_debt": {
        "taxonomy": "us-gaap",
        "tags": ["DebtCurrent", "LongTermDebtNoncurrent"],
        "unit": "USD",
    },
    "cash": {
        "taxonomy": "us-gaap",
        "tags": ["CashAndCashEquivalentsAtCarryingValue"],
        "unit": "USD",
    },
    "equity": {
        "taxonomy": "us-gaap",
        "tags": ["StockholdersEquity"],
        "unit": "USD",
    },
}
