# ARCHITECTURE.md — Stock Analyzer

> Document de referència. No és un manual d'ús; és l'explicació de
> per què el projecte està fet així, perquè d'aquí a un any (o
> quan calgui prendre una decisió similar) no calgui reconstruir
> mentalment el raonament.

## 1. Objectiu del projecte

Sistema d'anàlisi borsària 100% gratuït i automàtic: GitHub Actions
descarrega dades cada dia, calcula indicadors i puntuacions, i una
PWA les mostra amb notificacions push natives a l'iPhone. Sense
servidor propi ni base de dades — tot viu com a fitxers al repo i
GitHub Pages.

## 2. No objectius

Aquest projecte no intenta:
- predir el mercat mitjançant IA generativa;
- substituir un terminal professional (Bloomberg, FactSet...);
- optimitzar backtests amb look-ahead bias;
- mantenir una base de dades pròpia.

## 3. Principis de disseny

- **Cap número inventat.** Tot score és 100% reproduïble a partir
  de dades primitives i fórmules fixes. La "IA" (quan s'usa) només
  genera text explicatiu a partir de valors ja calculats — mai
  decideix el score en si.
- **Determinisme sobre interpretació.** El score és sempre el
  mateix donades les mateixes dades d'entrada. La narrativa és
  només una lectura d'aquest número, no una font d'informació nova.
- **No harmonitzar artificialment.** Quan dues fonts discrepen per
  definició (GAAP vs ajustat, FY vs TTM), no es força una
  equivalència. Cada mètrica usa la font més coherent
  metodològicament, i la discrepància es documenta, no s'amaga.
- **Validar l'impacte real, no només que "el codi no falla".**
  Qualsevol canvi a les fonts de dades es valida mesurant l'efecte
  sobre el producte final (scores, rànquing), no només amb tests
  unitaris.

## 4. Flux de dades

```
Mercats
  │
  ├── Yahoo Finance (yfinance)
  ├── SEC EDGAR (data.sec.gov, gratuït, sense clau)
  └── (Europe Provider — futur, no implementat)
          │
          ▼
   CompositeProvider  (src/edgar/providers.py)
          │
          ▼
   score_adapter      (src/edgar/score_adapter.py)
          │
          ▼
   score.py           (src/score.py)
          │
          ▼
   scores.json + data/history/scores/*.json
          │
          ▼
   PWA (GitHub Pages)
```

Pipeline diari (`daily_download.yml`, dilluns-divendres 20:00 UTC):
`download.py` → `indicators.py` → `score.py` → `alerts.py` → deploy
automàtic de la PWA.

## 5. Responsabilitat de cada mòdul

| Mòdul | Responsabilitat | NO fa |
|---|---|---|
| `download.py` | Descarrega preus+fonamentals de Yahoo | No calcula res |
| `indicators.py` | SMA/EMA/RSI/MACD/ATR/volatilitat | No coneix fonamentals |
| `src/edgar/downloader.py` | Descarrega JSON cru d'EDGAR (Capa 1) | No interpreta tags |
| `src/edgar/normalizer.py` | Tags XBRL → conceptes canònics, detecta període real per durada (Capa 2) | No calcula ratios |
| `src/edgar/lookup.py` | Històric + `lookup_fundamentals(date)` point-in-time (Capa 3+4) | No sap res de Yahoo |
| `src/edgar/providers.py` | Interfície comuna (`FundamentalsProvider`, `CompositeProvider`) | No calcula ratios |
| `src/edgar/score_adapter.py` | Primitives EDGAR → ratios; fusiona EDGAR+Yahoo camp a camp | No decideix el score |
| `score.py` | 6 subscores, 3 horitzons, checklist, narrativa | No sap d'on vénen els fonamentals |
| `scripts/validate_providers.py` | Compara pipeline Yahoo-only vs EDGAR+Yahoo sobre l'univers complet | No es crida en producció |

## 6. Fonts de dades i criteris de selecció

| Mètrica | Font | Motiu |
|---|---|---|
| `pe_trailing` | EDGAR | EPS GAAP anual, reproduïble |
| `profit_margin` | EDGAR | `net_income/revenue` GAAP |
| `revenue_growth`, `earnings_growth` | Yahoo | Yahoo usa base TTM/trimestral; EDGAR FY-a-FY és una magnitud diferent (vegeu `docs/providers.md`) |
| `peg_ratio`, `price_to_book`, `return_on_equity`, `debt_to_equity`, `beta` | Yahoo | Encara no implementats a EDGAR (Fase 1 només té 5 conceptes primitius) |

Detall complet i el cas JNJ (GAAP vs ajustat): `docs/providers.md`.

## 7. Filosofia del score

6 subscores (0-100, percentil respecte a l'univers del dia):
Momentum, Tendència, Valoració, Qualitat, Creixement, Risc. 3
horitzons amb pesos fixos (curt/mig/llarg termini). Checklist de 6
criteris deterministes → semàfor verd/groc/vermell. Narrativa i
"què vigilar" generats per plantilla sobre valors ja calculats, mai
per un model generatiu lliure.

## 8. Estratègia de validació

Cap canvi de proveïdor entra en producció sense demostrar
quantitativament que no altera de manera significativa el
comportament del model.

Abans d'integrar qualsevol canvi a les fonts de fonamentals:

1. Validar el connector aïllat (backfill manual, `edgar_backfill.py`)
2. Validar l'adaptador amb proves unitàries pures (merge, audit)
3. **Validar l'efecte sobre el pipeline complet** amb
   `scripts/validate_providers.py`: compara Yahoo-only vs
   EDGAR+Yahoo sobre l'univers sencer (mean/max delta, tickers amb
   Δ>1/3/5, overlap del Top10)
4. Nomes amb resultat ✅ PASS (o REVISAR justificat) s'aplica el
   patch a `score.py`

`validate_providers.yml` és una prova de regressió permanent:
tornar a córrer-la després de qualsevol canvi al normalitzador,
l'adaptador o l'ampliació de conceptes.

## 9. Roadmap

**Fase 1 — Motor de puntuació fiable.** ✅ Completada.

**Fase 2 — Millorar les dades.**
- EuropeProvider (font encara per determinar — Europa no té
  equivalent unificat a EDGAR; primera sessió ha de ser exploratòria)
- Ampliar conceptes EDGAR (cash flow, deute, equity) només quan hi
  hagi un consumidor real
- Reconstrucció point-in-time completa per a auditoria històrica

**Fase 3 — Auditar el model.** No canviar el score; mesurar quan
encerta, quan falla, quines condicions funcionen millor. Base del
"Model 2" (motor probabilístic).

**Fase 4 — Models predictius** (només si la Fase 3 demostra que hi
ha prou historial i qualitat de dades).

## 10. Decisions que semblen petites però no ho són

- `fy`/`fp` d'EDGAR indiquen de quin *filing* prové un punt, no
  quin període cobreix. La detecció de període anual real es fa
  per durada (`period_end - period_start` ≈ 365 dies), mai per
  aquests camps.
- `revenue_growth`/`earnings_growth` calculats amb EDGAR existeixen
  (`fy_yoy_growth()` a `lookup.py`) però estan darrere
  `FEATURE_FLAGS["edgar_growth"] = False` — no eliminats, només
  desconnectats, perquè seran útils per a l'auditoria històrica.
- L'app Fitxers d'iOS amaga carpetes/fitxers que comencen per punt
  (`.github`) — els zips de lliurament fan servir el truc de
  renombrar-les sense punt per poder-los pujar.

## 11. Principis que no s'han de trencar

Quan es modifiqui el projecte, preservar sempre:
- score determinista;
- separació entre dades, càlcul i presentació;
- traçabilitat de cada mètrica;
- absència de look-ahead bias;
- validació quantitativa abans de desplegar.
