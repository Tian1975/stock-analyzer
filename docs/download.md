# download.py

## Responsabilitat

Descarregar preus històrics (en bloc) i dades fonamentals (per ticker) de
Yahoo Finance per a tot l'univers definit a `src/universe.py`, validar-les, i
desar-les com JSON a `data/raw/` (últim estat) i `data/history/raw/{data}/`
(historial diari).

## Esquema de sortida (`data/raw/{TICKER}.json`)

```json
{
  "ok": true,
  "ticker": "AAPL",
  "region": "US",
  "downloaded_at": "ISO 8601 UTC",
  "prices": {
    "dates": ["YYYY-MM-DD", ...],
    "open": [...], "high": [...], "low": [...], "close": [...], "volume": [...]
  },
  "fundamentals": {
    "ok": true,
    "long_name": "...", "sector": "...", "pe_trailing": ...,
    "... (esquema intern, independent del proveïdor)"
  },
  "fundamentals_ok": true
}
```

Si `ok: false`, el ticker no ha passat la validació de preus i **no** té
`prices` ni `fundamentals` — cal reintentar-lo a la següent execució.

## Esquema intern de fonamentals

Definit a `FUNDAMENTALS_SCHEMA` dins `download.py`. Els noms de camp són
propis del projecte (`long_name`, `pe_trailing`, `market_cap`...), no els noms
crus de Yahoo (`longName`, `trailingPE`...). Si es canvia de proveïdor de
dades en el futur, només cal reescriure el mapeig dins `get_fundamentals()`;
la resta del pipeline (`indicators.py`, `scoring.py`...) no coneixerà mai els
noms originals de cap proveïdor.

## Validacions aplicades (`validate_prices`)

- Mínim de sessions (`config.MIN_SESSIONS`)
- Totes les columnes OHLCV presents i amb la mateixa longitud
- Sense NaN a Open/High/Low/Close
- Preus estrictament positius
- Volum no negatiu
- Dates en ordre cronològic

## Fitxers generats a `data/`

| Fitxer | Contingut |
|---|---|
| `data/raw/*.json` | Últim estat de cada ticker |
| `data/history/raw/{YYYY-MM-DD}/*.json` | Còpia de cada execució diària |
| `data/download_summary.json` | Resum: èxit/fallats, traçabilitat (versions, commit) |
| `data/sanity_report.json` | Incidències ràpides: preus/fonamentals absents, duplicats, rang de dates |

## Estat del projecte

Veure secció "Project status" al README principal.
