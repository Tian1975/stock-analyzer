# alerts.py

## Responsabilitat

Comparar `data/scores.json` (avui) amb l'historial (`data/history/scores/`,
ahir) i la llista de favorits (`config/favorites.txt`), detectar condicions
d'alerta, i crear una GitHub Issue si n'hi ha alguna.

## Important: dues llistes de favorits diferents

- **Favorits de la PWA** (★ dins l'app): es guarden al `localStorage` del
  teu mòbil. Només serveixen per l'apartat "Favorits" de la pantalla d'inici.
- **`config/favorites.txt`**: llista separada, guardada al repo, que
  `alerts.py` llegeix des de GitHub Actions (que no té accés al teu mòbil).
  Edita aquest fitxer manualment des de la web de GitHub per afegir/treure
  tickers de la vigilància d'alertes.

## Condicions comprovades (només per tickers de `favorites.txt`)

| Condició | Llindar |
|---|---|
| Entra al Top 10 | `rank_mid_term` ≤ 10, abans no ho estava |
| Entra al Top 3 | `rank_mid_term` ≤ 3 (substitueix l'alerta de Top 10) |
| Surt del Top 10 | abans ≤ 10, ara > 10 |
| RSI sobrecomprat/sobrevenut | ≥70 / ≤30 (`config.ALERT_RSI_*`) |
| Trencament de tendència | SMA20 < SMA50 < SMA200 |
| Caiguda de score 🟡 | ≥5 punts (`config.ALERT_SCORE_DROP_WATCH`) |
| Caiguda de score 🔴 | ≥10 punts (`config.ALERT_SCORE_DROP_ALERT`) |
| Confiança baixa | <90% (`config.ALERT_MIN_CONFIDENCE_PCT`) |

## Condició global (no restringida a favorits)

- **Descoberta**: qualsevol ticker que entra al Top 10 per primera vegada
  i NO és a `favorites.txt` — per detectar oportunitats que no seguies.

## Sortida

Si hi ha alguna alerta, crida l'API de GitHub (`GITHUB_TOKEN` disponible
automàticament dins l'Action) i crea una Issue amb l'etiqueta
`alerta-automatica`. Si tens notificacions de GitHub activades al mòbil
(app oficial o email), t'arriba com qualsevol altra notificació.

Si no hi ha `GITHUB_TOKEN`/`GITHUB_REPOSITORY` (execució local), només ho
mostra per consola — útil per provar-ho sense crear issues de veritat.

## Pròxims passos (pendents, fora d'abast d'aquesta entrega)

- Push notifications natives a la PWA (Web Push + VAPID)
- Configurar la llista de favorits per alertes des de dins la mateixa PWA
- Historial d'alertes dels últims 30 dies
