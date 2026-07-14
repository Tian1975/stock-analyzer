"""
Univers d'actius a seguir. Organitzat per regió per facilitar-ne l'ampliació futura.
Format de tickers: Yahoo Finance (sufixos .MC=Madrid, .PA=Paris, .DE=Frankfurt,
.AS=Amsterdam, .SW=Suïssa, .L=Londres, .MI=Milà, .ST=Estocolm, .CO=Copenhaguen,
.BR=Brussel·les, .HE=Hèlsinki, .T=Tòquio, .HK=Hong Kong, .TW=Taiwan, .KS=Corea del Sud).
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
    # Ampliació: Regne Unit, Itàlia, Països Baixos, Suècia, Dinamarca, Bèlgica, Finlàndia
    "SHEL.L", "AZN.L", "HSBA.L", "ULVR.L", "BP.L", "RIO.L",
    "INGA.AS", "ENI.MI", "ISP.MI", "UCG.MI",
    "VOLV-B.ST", "ATCO-A.ST", "NOVO-B.CO", "ABI.BR", "NOKIA.HE",
]

SPAIN_STOCKS = [
    "TEF.MC", "FER.MC", "AMS.MC", "ACS.MC", "ELE.MC",
    "CLNX.MC", "GRF.MC", "NTGY.MC", "CABK.MC", "AENA.MC",
]

ASIA_STOCKS = [
    # Japó
    "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "9432.T", "6098.T",
    # Hong Kong
    "0700.HK", "9988.HK", "0941.HK", "1299.HK", "3690.HK",
    # Taiwan
    "2330.TW",
    # Corea del Sud
    "005930.KS", "000660.KS",
]

ALL_TICKERS = US_STOCKS + EUROPE_STOCKS + SPAIN_STOCKS + ASIA_STOCKS

REGION_MAP = {t: "US" for t in US_STOCKS}
REGION_MAP.update({t: "EU" for t in EUROPE_STOCKS})
REGION_MAP.update({t: "ES" for t in SPAIN_STOCKS})
REGION_MAP.update({t: "ASIA" for t in ASIA_STOCKS})

if __name__ == "__main__":
    print(f"Total tickers: {len(ALL_TICKERS)}")
    assert len(ALL_TICKERS) == len(set(ALL_TICKERS)), "Hi ha tickers duplicats!"
    print("Sense duplicats. OK.")
