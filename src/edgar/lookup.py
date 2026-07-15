"""
lookup.py  (Capa 3 + Capa 4)

Aquesta es la peca "magica" que menciona la conversa: en lloc de
guardar nomes l'ultim valor de cada concepte, guardem tota la serie
temporal amb la data real de publicacio (`filed`). Aixo permet
preguntar "que sabiem d'AAPL el 2023-06-15?" i obtenir nomes els
valors que ja eren publics aquell dia — mai els d'un filing futur.

score.py nomes hauria de parlar amb aquest fitxer. No necessita
saber res d'EDGAR, tags XBRL, ni taxonomies.
"""

import json

from .ticker_to_cik import PROJECT_ROOT

NORMALIZED_DIR = PROJECT_ROOT / "data" / "edgar" / "normalized"


def save_normalized(ticker: str, records: list[dict]) -> None:
    """Guarda la serie normalitzada completa d'un ticker a disc."""
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    path = NORMALIZED_DIR / f"{ticker.replace('.', '_')}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def load_normalized(ticker: str) -> list[dict]:
    path = NORMALIZED_DIR / f"{ticker.replace('.', '_')}.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def lookup_fundamentals(ticker: str, date: str) -> dict:
    """
    Retorna els fonamentals "coneguts" per a un ticker en una data
    donada: per a cada concepte canonic, el valor mes recent el
    'filed' del qual sigui <= date. Mai un valor d'un filing
    posterior a `date` (aixo es el que garanteix que sigui
    point-in-time i no "trampa amb dades del futur").

    date ha de ser un string ISO "YYYY-MM-DD".

    Retorna un dict pla, per exemple:
    {
        "eps_basic": 6.11,
        "revenue": 394328000000,
        "net_income": 99803000000,
        "shares_outstanding": 15728700000,
        "operating_income": 114301000000,
        "_as_of": {
            "eps_basic": {"filed": "2023-05-05", "form": "10-Q", "accession": "..."},
            ...
        }
    }

    Si no hi ha cap dada disponible per a un concepte abans de
    `date` (p.ex. la data demanada es anterior a la primera dada
    de l'empresa a EDGAR), aquell concepte simplement no apareix
    al resultat.
    """
    records = load_normalized(ticker)
    if not records:
        return {}

    best_per_concept: dict[str, dict] = {}

    for rec in records:
        filed = rec.get("filed")
        if filed is None or filed > date:
            continue  # encara no era public en aquesta data

        concept = rec["concept"]
        current_best = best_per_concept.get(concept)

        # ens quedem amb el filing mes RECENT que segueixi complint filed <= date
        if current_best is None or filed > current_best["filed"]:
            best_per_concept[concept] = rec

    if not best_per_concept:
        return {}

    result = {}
    provenance = {}
    for concept, rec in best_per_concept.items():
        result[concept] = rec["value"]
        provenance[concept] = {
            "filed": rec["filed"],
            "form": rec["form"],
            "fy": rec["fy"],
            "fp": rec["fp"],
            "accession": rec["accession"],
            "tag": rec["tag"],
        }

    result["_as_of"] = provenance
    return result


def yoy_growth(ticker: str, concept: str, date: str) -> float | None:
    """
    Creixement interanual (%) d'un concepte, comparant els DOS últims
    filings ANUALS (form 10-K, fp='FY') coneguts fins a `date`.

    Es fa servir nomes FY (no trimestral) per simplicitat i perque
    aixi es comparable amb com Yahoo sol reportar "earnings growth"
    / "revenue growth" (interanual, no intertrimestral).

    Retorna None si no hi ha prou historial (calen almenys 2 anys
    fiscals coneguts abans de `date`).
    """
    records = [
        r for r in load_normalized(ticker)
        if r["concept"] == concept
        and r.get("fp") == "FY"
        and r.get("filed") is not None
        and r["filed"] <= date
        and r.get("fy") is not None
    ]
    if len(records) < 2:
        return None

    # un mateix any fiscal pot apareixer diverses vegades (tags
    # diferents que es solapen); ens quedem amb el filing mes
    # recent per a cada fy.
    by_fy = {}
    for r in records:
        fy = r["fy"]
        if fy not in by_fy or r["filed"] > by_fy[fy]["filed"]:
            by_fy[fy] = r

    years = sorted(by_fy.keys())
    if len(years) < 2:
        return None

    latest = by_fy[years[-1]]
    prior = by_fy[years[-2]]

    if not prior["value"]:
        return None

    return round(100 * (latest["value"] - prior["value"]) / prior["value"], 1)


if __name__ == "__main__":
    example = lookup_fundamentals("AAPL", "2023-06-15")
    print(json.dumps(example, indent=2))
