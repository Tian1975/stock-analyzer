"""
config.py — Configuració centralitzada. Canviar aquí, no dins de la lògica.
"""

HISTORY_PERIOD = "2y"
MAX_RETRIES = 3
REQUEST_DELAY = 0.5
PROVIDER = "Yahoo Finance"
VERSION = "1.0.0"

# Validació mínima de dades abans de desar un ticker com a vàlid
MIN_SESSIONS = 200  # ~2 anys de sessions bursàtils sol donar ~500, marge ampli però segur

# Llindar mínim d'èxit global perquè el job es consideri fallit de veritat.
# Un o dos tickers puntuals (ex. ROG.SW sense dades un dia concret) són normals
# i no han de fer caure el workflow. Un percentatge molt baix (com el 0% que
# vam detectar amb el bug de festius desalineats) SÍ ha de fer-lo fallar.
MIN_SUCCESS_RATE_PCT = 90.0

# Llindars d'alertes (score.py + alerts.py)
ALERT_SCORE_DROP_WATCH = 5.0   # 🟡 "vigila aquesta empresa"
ALERT_SCORE_DROP_ALERT = 10.0  # 🔴 "canvi important, revisa-la"
ALERT_RSI_OVERBOUGHT = 70
ALERT_RSI_OVERSOLD = 30
ALERT_MIN_CONFIDENCE_PCT = 90.0
