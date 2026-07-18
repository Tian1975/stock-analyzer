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

# Retenció de l'historial diari de scores (per evolució, "dies al Top10",
# "millor score dels últims mesos", i auditoria retrospectiva del model
# -- vegeu ARCHITECTURE.md secció 9, Fase 3). 730 dies permet auditar
# retorns fins a l'horitzó llarg termini (180d) i comparar any contra
# any (estacionalitat). Un JSON diari de ~109 tickers és petit; el cost
# d'espai és irrellevant comparat amb el valor de no haver de tornar a
# esperar si es necessita més historial retrospectivament.
HISTORY_RETENTION_DAYS = 730

# URL pública de la PWA (per enllaçar directament a la fitxa d'un ticker
# des de les alertes). Sense barra final.
PWA_BASE_URL = "https://tian1975.github.io/stock-analyzer"

# Versió del motor de puntuació. Incrementar-la SEMPRE que canviï una
# fórmula, un pes d'horitzó, o quina font alimenta un subscore (p.ex.
# activar FEATURE_FLAGS["edgar_growth"] a score_adapter.py). Es grava
# a cada snapshot diari perquè, en una auditoria retrospectiva, es pugui
# saber amb quin motor es va generar cada dia d'historial -- sense
# aquesta marca, un canvi de fórmula futur invalidaria silenciosament
# les comparacions "abans/despres" del Model 2.
SCORE_VERSION = "1.0.0"
