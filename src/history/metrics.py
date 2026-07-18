"""
src/history/metrics.py

Sprint 2.2. Aqui comencen les preguntes d'evidencia -- la diferencia
respecte a queries.py es la seguent:

    query   respon "que hi ha?"        (score d'AAPL, Top10, historial)
    metric  respon "que significa?"    (quants canvis al Top10 aquesta
                                         setmana, distribucio dels scores)

Principi acordat abans de comencar aquest modul: el Model 2 no
existeix per generar senyals d'inversio; existeix per generar
confianca (o desconfianca) en el Model 1. Per aixo, TOTA metrica
retorna la mateixa forma comuna (vegeu make_evidence()), perque mai
es pugui llegir un resultat sense veure tambe la seva força
d'evidencia (mostra, periode cobert).

Aquest modul NOMES fa servir l'API publica de queries.py -- mai
toca snapshots ni funcions privades directament. Aixo garanteix que,
si algun dia canvia el format intern dels snapshots, nomes cal
actualitzar queries.py.
"""

import statistics

from .queries import top_n, list_dates


def make_evidence(metric: str, value, sample_size: int, from_date: str, to_date: str, note: str | None = None) -> dict:
    """
    Forma comuna de TOTA metrica d'evidencia. `value` pot ser
    qualsevol estructura (numero, dict, llista) -- el que es fixe
    es que sempre va acompanyat de sample_size i del periode cobert.

    `note` es per a advertencies explicites quan la mostra es
    encara massa petita per treure conclusions (p.ex. "nomes 2
    observacions, resultat merament orientatiu").
    """
    return {
        "metric": metric,
        "value": value,
        "sample_size": sample_size,
        "from": from_date,
        "to": to_date,
        "note": note,
    }


def _histogram(values: list[float], bins: int = 10, range_min: float = 0.0, range_max: float = 100.0) -> list[dict]:
    """
    Histograma senzill amb bins d'amplada fixa dins de
    [range_min, range_max] (els scores ja son 0-100 per disseny).
    Retorna una llista de {"from": x, "to": y, "count": n}.
    """
    width = (range_max - range_min) / bins
    counts = [0] * bins

    for v in values:
        if v < range_min or v > range_max:
            continue
        idx = int((v - range_min) / width)
        if idx == bins:  # el valor exacte range_max cau a l'ultim bin
            idx = bins - 1
        counts[idx] += 1

    return [
        {
            "from": round(range_min + i * width, 1),
            "to": round(range_min + (i + 1) * width, 1),
            "count": counts[i],
        }
        for i in range(bins)
    ]


def score_distribution(date_str: str, score_field: str = "mid_term", bins: int = 10) -> dict:
    """
    Com es distribueixen els scores de tot l'univers en una data
    concreta. Es la metrica mes simple i tambe la que detecta bugs
    mes facilment (p.ex. tots els scores identics, o concentrats
    de manera sospitosa a un extrem).
    """
    scored = top_n(date_str, score_field=score_field, n=None)
    values = [s for _ticker, s in scored]

    if not values:
        return make_evidence(
            metric="score_distribution",
            value=None,
            sample_size=0,
            from_date=date_str,
            to_date=date_str,
            note="Cap dada disponible per a aquesta data/score_field",
        )

    value = {
        "histogram": _histogram(values, bins=bins),
        "min": round(min(values), 1),
        "max": round(max(values), 1),
        "mean": round(statistics.mean(values), 1),
        "median": round(statistics.median(values), 1),
    }

    note = None
    if len(values) < 20:
        note = f"Mostra petita ({len(values)} tickers) -- interpretar amb cautela"

    return make_evidence(
        metric="score_distribution",
        value=value,
        sample_size=len(values),
        from_date=date_str,
        to_date=date_str,
        note=note,
    )


def top10_turnover(date_from: str, date_to: str, score_field: str = "mid_term") -> dict:
    """
    Quants membres del Top10 canvien entre dues dates (poden ser
    consecutives). No necessita mesos d'historial -- nomes dos
    snapshots -- i diu molt sobre l'estabilitat del model: un
    turnover molt alt dia a dia suggeriria un model massa sensible
    al soroll; un turnover proper a zero durant mesos podria indicar
    l'invers (massa rigid, o poca varietat a l'univers).
    """
    top_from = [t for t, _s in top_n(date_from, score_field=score_field, n=10)]
    top_to = [t for t, _s in top_n(date_to, score_field=score_field, n=10)]

    set_from = set(top_from)
    set_to = set(top_to)

    if not set_from or not set_to:
        return make_evidence(
            metric="top10_turnover",
            value=None,
            sample_size=0,
            from_date=date_from,
            to_date=date_to,
            note="Top10 buit en almenys una de les dues dates -- comprova que els snapshots existeixen",
        )

    entered = sorted(set_to - set_from)
    exited = sorted(set_from - set_to)
    kept = sorted(set_from & set_to)

    value = {
        "turnover_pct": round(100 * len(entered) / 10, 1),
        "entered": entered,
        "exited": exited,
        "kept": kept,
    }

    note = None
    if date_from == date_to:
        note = "date_from i date_to son la mateixa data -- el resultat sera sempre 0% turnover"

    return make_evidence(
        metric="top10_turnover",
        value=value,
        sample_size=10,  # mida del Top10, no de l'univers
        from_date=date_from,
        to_date=date_to,
        note=note,
    )
