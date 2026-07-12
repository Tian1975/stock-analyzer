"""
Univers d'actius a seguir. Organitzat per regió per facilitar-ne l'ampliació futura.
Format de tickers: Yahoo Finance (sufixos .MC=Madrid, .PA=Paris, .DE=Frankfurt,
.AS=Amsterdam, .SW=Suïssa).
"""

US_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM", "V",
    "UNH", "XOM", "JNJ", "WMT", "MA", "PG", "HD", "CVX", "MRK", "ABBV",
    "KO", "PEP", "COST", "AVGO", "ADBE", "CRM", "BAC", "MCD", "TMO", "CSCO",
    "ACN", "ABT", "LIN", "DHR", "WFC", "TXN", "NEE", "PM", "ORCL", "NKE",
    "DIS", "VZ", "CMCSA", "INTC", "AMD", "QCOM", "IBM", "GE", "CAT", "BA",
]

EUROPE_STOCKS = [
    "ASML.AS", "SAP.DE", "MC.PA", "SIE.DE", "TTE.PA", "OR.PA", "SAN.PA", "AIR.PA",
    "ALV.DE", "DTE.DE", "NESN.SW", "NOVN.SW", "ROG.SW", "RMS.PA", "AI.PA",
    "ADYEN.AS", "IBE.MC", "BBVA.MC", "ITX.MC", "REP.MC",
]

SPAIN_STOCKS = [
    "TEF.MC", "FER.MC", "AMS.MC", "ACS.MC", "ELE.MC",
    "CLNX.MC", "GRF.MC", "NTGY.MC", "CABK.MC", "AENA.MC",
]

ALL_TICKERS = US_STOCKS + EUROPE_STOCKS + SPAIN_STOCKS

REGION_MAP = {t: "US" for t in US_STOCKS}
REGION_MAP.update({t: "EU" for t in EUROPE_STOCKS})
REGION_MAP.update({t: "ES" for t in SPAIN_STOCKS})

if __name__ == "__main__":
    print(f"Total tickers: {len(ALL_TICKERS)}")
    assert len(ALL_TICKERS) == len(set(ALL_TICKERS)), "Hi ha tickers duplicats!"
    print("Sense duplicats. OK.")
