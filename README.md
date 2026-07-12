# Stock Analyzer — v1.0.0

Pipeline: `download.py` → `indicators.py` → `fundamentals.py` → `scoring.py` →
`explanations.py` → `alerts.py` → PWA

## Project status

- ✅ Download engine
- ⬜ Indicators
- ⬜ Fundamentals scoring
- ⬜ Scoring
- ⬜ Alerts
- ⬜ PWA

**Aquesta entrega conté només el primer mòdul: la descàrrega de dades.**
Documentació detallada de cada mòdul a `docs/`.

## Novetats v0.3 (final)

- `download_summary.json` ara inclou `git_commit`, `python_version`,
  `yfinance_version`, `pandas_version` — traçabilitat per relacionar
  incidències futures amb versions concretes.
- Nou fitxer `data/sanity_report.json`: preus/fonamentals absents, tickers
  duplicats, i rang de dates (`oldest_price_date` / `newest_price_date`) sense
  haver d'obrir cap JSON individual.

## Detalls tècnics anteriors

- `get_fundamentals()` retorna un **esquema intern propi** (camps en anglès
  genèric: `long_name`, `pe_trailing`, etc.), no els noms crus de Yahoo. Si
  demà canviem de proveïdor, només es toca el mapeig dins d'aquesta funció.
- Validació de preus explícita i completa: ordre cronològic, sense NaN,
  longituds coherents, preus estrictament positius, volum no negatiu.
- Logging (`logging` en comptes de `print`) amb nivells INFO/WARNING/ERROR,
  llegible directament als logs de GitHub Actions.
- `download_summary.json` inclou `success_rate_pct` i `tickers_failed` amb
  motiu de cada fallada.
- Workflow: `git pull --rebase origin main || true` ABANS del commit (evita
  conflictes si el repo canvia durant l'execució).

## Pla de validació abans de continuar (recomanat)

Abans de començar `indicators.py`:
1. Executa el workflow manualment 3-5 vegades (`workflow_dispatch`)
2. Revisa `data/download_summary.json` cada vegada
3. Confirma quins tickers fallen de manera recurrent (no puntual)
4. Objectiu: **>95% d'èxit consistent** abans de construir la resta del pipeline

## Com pujar-ho a GitHub

1. Crea un repo nou (privat o públic, com prefereixis) a github.com
2. Al teu ordinador o des de GitHub web, puja tot el contingut d'aquesta carpeta
   (`stock-analyzer/`) mantenint l'estructura de carpetes intacta
3. Ves a la pestanya **Actions** del repo → hauries de veure el workflow
   "Descàrrega diària de dades"
4. Fes clic a **Run workflow** (botó manual, gràcies a `workflow_dispatch`) per
   provar-ho ara mateix sense esperar al cron diari
5. Quan acabi (uns 2-3 minuts per 80 tickers), revisa:
   - `data/download_summary.json` → veuràs quants tickers han anat bé
   - `data/raw/*.json` → un fitxer per ticker amb preus + fonamentals

## Si algun ticker falla

És normal que 1-2 dels 80 fallin puntualment (Yahoo Finance canvia dades
fonamentals sovint). El resum et dirà quins i per què. Si un ticker falla
sistemàticament, cal revisar si el símbol és correcte.

## Següent pas

Un cop confirmat que `data/raw/*.json` es genera correctament, seguim amb
`indicators.py` (mitjanes mòbils, RSI, MACD, ATR) i `fundamentals.py`
(normalització dels ràtios ja descarregats).
