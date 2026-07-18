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


from datetime import date as _date


def _parse_iso_date(s: str):
    try:
        return _date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def _annual_records(ticker: str, concept: str, as_of_date: str) -> list[dict]:
    """
    Filtra els registres d'un concepte que cobreixen un periode
    REALMENT anual (~365 dies), basant-se en period_start/period_end
    -- NO en els camps fy/fp d'EDGAR, que indiquen de quin informe
    prove el punt (el filing), no quin periode cobreix aquell punt
    concret. Un mateix 10-K conte punts trimestrals i anuals amb el
    MATEIX fy/fp, aixi que cal la durada real per distingir-los.

    Deduplica per period_end, quedant-se amb el filing mes recent
    per a cada periode anual concret.
    """
    candidates = []
    for r in load_normalized(ticker):
        if r["concept"] != concept:
            continue
        filed = r.get("filed")
        if filed is None or filed > as_of_date:
            continue

        start = _parse_iso_date(r.get("period_start"))
        end = _parse_iso_date(r.get("period_end"))
        if start is None or end is None:
            continue

        duration_days = (end - start).days
        if not (350 <= duration_days <= 380):
            continue  # no es un periode anual (es trimestral, YTD parcial, etc.)

        candidates.append(r)

    by_period_end: dict[str, dict] = {}
    for r in candidates:
        key = r["period_end"]
        current = by_period_end.get(key)
        if current is None or r["filed"] > current["filed"]:
            by_period_end[key] = r

    return sorted(by_period_end.values(), key=lambda r: r["period_end"])


def get_latest_fy_value(ticker: str, concept: str, date: str) -> float | None:
    """
    Retorna el valor del darrer periode REALMENT anual (~365 dies)
    conegut fins a `date`, identificat per durada real del periode
    (period_end - period_start), no pel camp fy/fp d'EDGAR.
    """
    records = _annual_records(ticker, concept, date)
    if not records:
        return None
    return records[-1]["value"]


def fy_yoy_growth(ticker: str, concept: str, date: str) -> float | None:
    """
    Creixement interanual (%) EXERCICI FISCAL COMPLET vs EXERCICI
    FISCAL COMPLET ANTERIOR (FY-a-FY), identificats per durada real
    del periode, no pel camp fy/fp d'EDGAR.

    ANOMENAT EXPLÍCITAMENT "fy_yoy_growth" (no "yoy_growth" a seques)
    perque aquesta NO es la mateixa magnitud que "growth" a Yahoo:
    Yahoo sembla calcular-ho sobre una base trimestral/TTM, que es
    molt mes suau que la comparacio FY-a-FY anual. Per a empreses
    amb despeses extraordinaries puntuals en un exercici concret
    (p.ex. JNJ amb litigis de talc el 2024), el FY-a-FY pot mostrar
    oscil·lacions molt grans (+90% o mes) que son CORRECTES pero no
    comparables amb la xifra de Yahoo. Vegeu FEATURE_FLAGS a
    score_adapter.py -- aquesta funcio es manté aqui per a us futur
    (auditoria historica, model probabilistic, grafics FY vs TTM),
    pero desconnectada del pipeline principal per ara.

    Retorna None si no hi ha almenys 2 periodes anuals coneguts.
    """
    records = _annual_records(ticker, concept, date)
    if len(records) < 2:
        return None

    latest = records[-1]
    prior = records[-2]

    if not prior["value"]:
        return None

    return round(100 * (latest["value"] - prior["value"]) / prior["value"], 1)


if __name__ == "__main__":
    example = lookup_fundamentals("AAPL", "2023-06-15")
    print(json.dumps(example, indent=2))
