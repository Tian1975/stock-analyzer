"""
lookup.py  (Capa 3 + Capa 4)
"""

import json

from .ticker_to_cik import PROJECT_ROOT

NORMALIZED_DIR = PROJECT_ROOT / "data" / "edgar" / "normalized"


def save_normalized(ticker: str, records: list[dict]) -> None:
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
    records = load_normalized(ticker)
    if not records:
        return {}

    best_per_concept: dict[str, dict] = {}

    for rec in records:
        filed = rec.get("filed")
        if filed is None or filed > date:
            continue

        concept = rec["concept"]
        current_best = best_per_concept.get(concept)

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


def get_latest_fy_value(ticker: str, concept: str, date: str) -> float | None:
    """
    Retorna el valor ANUAL (form 10-K, fp='FY') mes recent conegut
    fins a `date`, ignorant filings trimestrals (10-Q). Necessari
    per no barrejar magnituds trimestrals i anuals dins del mateix
    calcul (p.ex. dividir el preu per un EPS d'un sol trimestre).
    """
    records = [
        r for r in load_normalized(ticker)
        if r["concept"] == concept
        and r.get("fp") == "FY"
        and r.get("filed") is not None
        and r["filed"] <= date
        and r.get("fy") is not None
    ]
    if not records:
        return None

    by_fy = {}
    for r in records:
        fy = r["fy"]
        if fy not in by_fy or r["filed"] > by_fy[fy]["filed"]:
            by_fy[fy] = r

    latest_fy = max(by_fy.keys())
    return by_fy[latest_fy]["value"]


def yoy_growth(ticker: str, concept: str, date: str) -> float | None:
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
