# MODEL2.md — Model 2 (Auditor)

> Contracte del Model 2, igual que ARCHITECTURE.md ho és per al
> projecte sencer. Es actualitza cada vegada que s'afegeix o es
> madura una metrica.

## 1. Objectiu

El Model 2 existeix per validar empiricament el Model 1. **No**
calcula nous scores ni genera recomanacions d'inversio. La seva
unica funcio es mesurar si el Model 1 es comporta com s'espera,
amb evidencia observable sobre l'historial real de snapshots.

El Model 2 existeix per generar confianca (o desconfianca) en el
Model 1 -- mai per generar senyals.

## 2. Principis

- **No modifica snapshots.** Nomes els llegeix. `data/history/scores/`
  es propietat exclusiva del Model 1 (`score.py`).
- **Nomes consumeix dades historiques.** No fa crides a Yahoo, EDGAR
  ni cap altre proveidor -- si una dada no es al snapshot, no hi es.
- **Les metriques han de ser reproduibles.** La mateixa consulta,
  sobre el mateix rang de dates, dona sempre el mateix resultat.
- **Cada metrica informa de la mida de la mostra.** Cap resultat
  numeric sense el seu `sample_size` i el periode cobert (`from`/`to`).
  Format comu: `make_evidence()` (`src/history/metrics.py`). Cap
  metrica retorna un diccionari construit "a ma".
- **Les metriques no impliquen causalitat.** "Quan score>80, retorn
  mitja +18%" es una observacio correlacional sobre el passat, no
  una prediccio ni una garantia de comportament futur.
- **Separacio query / metric:**
  - *query* respon "que hi ha?" (`queries.py`) -- score d'un ticker,
    Top10, historial.
  - *metric* respon "que significa?" (`metrics.py`) -- distribucions,
    canvis, volatilitat, retorns.
  `metrics.py` nomes fa servir l'API publica de `queries.py`, mai
  toca snapshots ni funcions privades directament.

## 3. Arquitectura

```
data/history/scores/*.json  (propietat del Model 1)
          │
          ▼
   loader.py    (SnapshotIndex, load_snapshot, load_snapshots)
          │
          ▼
   queries.py   (get_score, get_rank, top_n, get_ticker_history)
          │
          ▼
   metrics.py   (score_distribution, top10_turnover, make_evidence...)
          │
          ▼
   consumidors: scripts/history_metrics_demo.py, futur Evidence
   Dashboard, futurs informes (reports/), notebooks d'investigacio
```

## 4. Estat de maduresa

| Estat | Mètrica | Descripció | Requereix historial |
|---|---|---|---|
| ✅ | `score_distribution` | Histograma + min/max/mean/median d'un dia | No (1 snapshot) |
| ✅ | `top10_turnover` | Entrades/sortides del Top10 entre dues dates | No (2 snapshots) |
| ⏳ | `ranking_changes` | Canvis de posició d'un ticker/univers entre dates | No |
| ⏳ | `subscore_volatility` | Variabilitat d'un subscore al llarg del temps | Uns mesos |
| ⏳ | `future_returns` | Retorn mitjà N dies després d'un score/checklist concret | Mesos (idealment 6-12) |
| ⏳ | `accuracy` | Taxa d'encert de la tesi (semàfor verd → manté's positiu?) | Mesos |

## 5. Consumidors actuals

- `scripts/history_metrics_demo.py` — primer client, exploratori,
  sense lògica pròpia (només crida l'API i imprimeix resultats)

## 6. Consumidors previstos (no construïts encara)

- Evidence Dashboard (consumeix objectes `make_evidence()`)
- `reports/` (Sprint futur: `weekly_report.py`, `model_health.py`
  — combinen diverses mètriques, no viuen dins de `metrics.py`)
