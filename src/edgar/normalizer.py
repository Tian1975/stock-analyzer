"""
normalizer.py  (Capa 2)

Converteix el JSON cru d'EDGAR (centenars de tags XBRL, un per
empresa amb les seves variants) al "llenguatge unic" que fa
servir la resta del sistema: els 5 (i despres mes) conceptes
canonics definits a concepts.py.

Cada registre normalitzat inclou traçabilitat completa perque,
d'aqui uns anys, si una empresa canvia de taxonomia o un valor
sembla estrany, es pugui reconstruir exactament d'on ha sortit.
"""

from .concepts import CANONICAL_CONCEPTS


def _extract_concept_series(raw_facts: dict, taxonomy: str, tags: list[str], unit: str) -> list[tuple[dict, str]]:
    """
    A diferencia d'una versio anterior (que es quedava nomes amb el
    PRIMER tag candidat que trobava dades), aquesta fusiona TOTS els
    tags candidats que l'empresa hagi fet servir. Aixo es necessari
    perque moltes empreses canvien de tag al llarg del temps -- per
    exemple, Apple va reportar 'Revenues' fins a ~2018 i despres va
    passar a 'RevenueFromContractWithCustomerExcludingAssessedTax'
    arran del canvi d'estandard comptable ASC 606. Si nomes agafem
    el primer tag amb dades, ens quedem "enganxats" amb la serie
    vella i perdem tots els periodes posteriors al canvi.

    Retorna una llista de (punt, tag_que_lha_produit).
    """
    taxonomy_facts = raw_facts.get("facts", {}).get(taxonomy, {})
    combined = []

    for tag in tags:
        concept = taxonomy_facts.get(tag)
        if concept is None:
            continue
        units = concept.get("units", {})
        series = units.get(unit)
        if not series:
            continue
        for point in series:
            combined.append((point, tag))

    return combined


def normalize_companyfacts(ticker: str, raw_facts: dict) -> list[dict]:
    """
    Retorna una llista plana de registres normalitzats, un per
    cada (concepte, periode, filing) reportat. Si dos tags
    candidats reporten el mateix (period_end, filed, val) -- cosa
    que passa sovint en el periode de transicio entre taxonomies --
    es dedupliquen, quedant-nos amb un sol registre.

    Format de cada registre:

    {
        "ticker": "AAPL",
        "concept": "revenue",          # nom canonic
        "tag": "Revenues",             # tag XBRL real que s'ha fet servir
        "value": 383285000000,
        "unit": "USD",
        "period_end": "2023-09-30",
        "fy": 2023,
        "fp": "FY",
        "form": "10-K",
        "filed": "2023-11-03",         # CLAU per al lookup point-in-time
        "accession": "0000320193-23-000106",
        "source": "SEC",
    }
    """
    records = []
    seen = set()

    for canonical_name, spec in CANONICAL_CONCEPTS.items():
        combined = _extract_concept_series(
            raw_facts, spec["taxonomy"], spec["tags"], spec["unit"]
        )

        for point, matched_tag in combined:
            dedup_key = (canonical_name, point.get("end"), point.get("filed"), point.get("val"))
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            records.append({
                "ticker": ticker,
                "concept": canonical_name,
                "tag": matched_tag,
                "value": point.get("val"),
                "unit": spec["unit"],
                "period_end": point.get("end"),
                "fy": point.get("fy"),
                "fp": point.get("fp"),
                "form": point.get("form"),
                "filed": point.get("filed"),
                "accession": point.get("accn"),
                "source": "SEC",
            })

    return records


def missing_concepts_report(ticker: str, raw_facts: dict) -> list[str]:
    """
    Utilitat de validacio: diu quins conceptes canonics NO s'han
    pogut mapejar per a aquesta empresa (cap dels tags candidats
    hi era present). Util per detectar-ho durant la validacio amb
    diverses empreses (AAPL, MSFT, JNJ, JPM...).
    """
    missing = []
    for canonical_name, spec in CANONICAL_CONCEPTS.items():
        combined = _extract_concept_series(
            raw_facts, spec["taxonomy"], spec["tags"], spec["unit"]
        )
        if not combined:
            missing.append(canonical_name)
    return missing
