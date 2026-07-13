# score.py

## Responsabilitat

Combinar `data/indicators.json` (tècnic) i els fonamentals de `data/raw/*.json`
en 6 subscores normalitzats (0-100) per ticker, i combinar-los en 3 scores
finals (curt/mig/llarg termini) segons pesos fixos i documentats.

## Principi de disseny

Els scores són **100% reproduïbles**: cap IA decideix res dins d'aquest
mòdul. La normalització és per **percentil respecte a la resta de l'univers**
del dia (no llindars fixos com "PER < 15 = bo", que varien molt per sector).

## Subscores

| Subscore | Mètriques | Normalització |
|---|---|---|
| Momentum | retorn 1m/3m/6m, MACD histograma, RSI (ideal zona 50-70) | percentil |
| Trend | alineació SMA20>SMA50>SMA200, distància a SMA200 | percentil |
| Valuation | PER, PEG, Price/Book | percentil invers (més barat = millor) |
| Quality | ROE, marge net, deute/equity | percentil (deute invers) |
| Growth | creixement ingressos, creixement beneficis | percentil |
| Risk (=seguretat) | volatilitat anualitzada, ATR relatiu, beta | percentil invers |

## Pesos per horitzó

```
Curt termini:  70% Momentum, 20% Trend, 10% Risk
Mitjà termini: 40% Trend, 30% Momentum, 20% Quality, 10% Valuation
Llarg termini: 40% Quality, 30% Valuation, 20% Growth, 10% Risk
```

Si a un ticker li falta algun subscore (ex. sense fonamentals), es
redistribueix el pes entre els subscores disponibles — no es penalitza dues
vegades (ja queda reflectit a `confidence_pct`).

## Camps de sortida (`data/scores.json` → `results[]`)

- `subscores`: els 6 valors 0-100 (o `null` si no calculable)
- `scores`: `short_term`, `mid_term`, `long_term`
- `risk_label`: "baix" / "moderat" / "alt" / "desconegut" — separat del score, mai barrejat
- `confidence_pct`: % de mètriques disponibles (NO és una probabilitat real, és consens/completesa)
- `explanation`: llista de frases generades per regles simples sobre valors reals
- `rank_mid_term`: posició al rànquing (ordenat per `mid_term` per defecte)

## Estat del projecte

Veure secció "Project status" al README principal.
