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


def get_latest_fy
