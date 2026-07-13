# Stock Analyzer — v1.0.0

Anàlisi diària automàtica del mercat borsari amb rànquing multi-horitzó,
100% gratuït, sense servidor ni base de dades.

```
GitHub Actions (cada dia, 20:00 UTC dl-dv)
      │
      ▼
download.py       preus + fonamentals (Yahoo Finance) → data/raw/*.json
      │
      ▼
indicators.py      SMA/EMA/RSI/MACD/ATR/volatilitat → data/indicators.json
      │
      ▼
score.py            6 subscores + 3 horitzons + deltes → data/scores.json
      │
      ▼
GitHub Pages         app/ + data/scores.json es desplega automàticament
      │
      ▼
PWA (instal·lable a l'iPhone)
```

## Project status

- ✅ Download engine (79-80/80 tickers, validat amb dades reals)
- ✅ Indicators (SMA/EMA/RSI/MACD/ATR/momentum/volatilitat)
- ✅ Scoring (tècnic + fonamental, 6 subscores, 3 horitzons, deltes dia a dia)
- ✅ PWA (inici amb favorits, rànquing filtrable, detall amb explicació)
- ✅ Alertes Fase 1: GitHub Issues (favorits + descoberta global)
- ✅ Historial 30 dies (evolució de score/rànquing, dies al Top10, sparkline)
- ⬜ Alertes Fase 2: Web Push natiu a la PWA

Documentació detallada de cada mòdul: `docs/download.md`, `docs/score.md`.

## Estructura del repo

```
stock-analyzer/
├── .github/workflows/
│   ├── daily_download.yml    descàrrega + indicadors + scores, cada dia
│   └── deploy_pages.yml      publica app/ + scores.json a GitHub Pages
├── src/
│   ├── universe.py           80 tickers (EUA/Europa/Espanya)
│   ├── config.py             paràmetres centralitzats
│   ├── download.py           preus + fonamentals
│   ├── indicators.py         indicadors tècnics
│   └── score.py               motor de puntuació
├── app/                      PWA (HTML/CSS/JS sense frameworks)
├── data/                     generat automàticament, no editar a mà
└── docs/                     documentació per mòdul
```

## Posar-ho en marxa

1. **Repo**: puja tot el contingut a un repo de GitHub (privat o públic)
2. **Descàrrega diària**: comprova a "Actions" que `daily_download.yml`
   s'executa correctament (`workflow_dispatch` per provar-ho manualment)
3. **PWA**: a "Settings → Pages" → "Source" tria **GitHub Actions**
   (no "Deploy from a branch"). El workflow `deploy_pages.yml` farà la resta.
4. La PWA quedarà a `https://<usuari>.github.io/stock-analyzer/`

> ⚠️ Fitxers que comencen per punt (`.github/...`, `.gitignore`) no es veuen
> ni s'extreuen bé des de l'app Fitxers d'iOS. Si puges des de l'iPhone,
> crea'ls manualment des de la web de GitHub amb el nom complet.

## Notes de manteniment

- **`ROG.SW` (o qualsevol ticker puntual)**: si falla de forma aïllada, és
  normal (Yahoo Finance). Si falla sistemàticament diversos dies seguits,
  buscar un símbol alternatiu a `src/universe.py`.
- **`success_rate_pct` < 90%**: el job de descàrrega falla expressament
  (`sys.exit(1)`) per evitar processar dades incompletes silenciosament.
- **Barrejar mercats en un bulk download**: cal fer sempre `dropna()` per
  ticker abans de validar (festius locals ≠ dades corruptes) — ja resolt a
  `download.py`, documentat a `docs/download.md`.
