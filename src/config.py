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
