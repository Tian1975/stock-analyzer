"""
src/history/queries.py

Responsabilitat UNICA: consultes sobre snapshots (rank, score,
historial d'un ticker, top_n). Treballa SEMPRE sobre snapshots ja
carregats via loader.py -- aquest modul no sap on viuen els fitxers.

Encara no hi ha estadistiques aqui (mitjanes, distribucions,
retorns...). Aixo viura a metrics.py quan comenci el Sprint 2.2.

Camps de score disponibles a cada snapshot (score.py::HORIZON_WEIGHTS):
    "short_term", "mid_term", "long_term"

Nomes "mid_term" te un rank precalculat (rank_mid_term) dins de cada
snapshot -- es el rank per defecte que fa servir score.py per al
rànquing principal de la PWA. Per a "short_term"/"long_term", el rank
es calcula aqui mateix ordenant els resultats del snapshot.
"""

from .loader import SnapshotIndex, load_snapshot, load_snapshots, HISTORY_DIR

VALID_SCORE_FIELDS = ("short_term", "mid_term", "long_term")


def _validate_score_field(score_field: str) -> None:
    if score_field not in VALID_SCORE_FIELDS:
        raise ValueError(
            f"score_field ha de ser un de {VALID_SCORE_FIELDS}, rebut: {score_field!r}"
        )


def _get_ticker_result(snapshot: dict, ticker: str) -> dict | None:
    """Busca el dict d'un ticker concret dins de snapshot['results']."""
    for r in snapshot.get("results", []):
        if r.get("ticker") == ticker:
            return r
    return None


def list_dates(
    start_date: str | None = None,
    end_date: str | None = None,
    index: SnapshotIndex | None = None,
) -> list[str]:
    """Dates disponibles dins de [start_date, end_date] (inclosos)."""
    idx = index or SnapshotIndex()
    return idx.dates_in_range(start_date, end_date)


def get_score(date_str: str, ticker: str, score_field: str = "mid_term") -> float | None:
    """
    Score d'un ticker concret en una data concreta, o None si el
    ticker no existia aquell dia o el valor era null.
    """
    _validate_score_field(score_field)
    snapshot = load_snapshot(date_str)
    result = _get_ticker_result(snapshot, ticker)
    if result is None:
        return None
    return result.get("scores", {}).get(score_field)


def _ranked_tickers(snapshot: dict, score_field: str) -> list[tuple[str, float]]:
    """
    Privada. Tots els tickers d'un snapshot ja carregat, ordenats
    descendent per score_field. Els que tenen score null es
    descarten (no participen al rànquing). Punt UNIC on viu la
    logica d'ordenacio -- si en el futur es guarden rank_short_term/
    rank_long_term precalculats, nomes cal tocar _rank(), no aquesta
    funcio ni les que la fan servir.
    """
    scored = [
        (r["ticker"], r.get("scores", {}).get(score_field))
        for r in snapshot.get("results", [])
    ]
    scored = [(t, s) for t, s in scored if s is not None]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored


def _rank(snapshot: dict, ticker: str, score_field: str) -> int | None:
    """
    Privada. Posicio (1 = millor) d'un ticker dins d'un snapshot ja
    carregat. Per "mid_term" reutilitza rank_mid_term (ja precalculat
    per score.py); per la resta, es calcula ordenant amb
    _ranked_tickers(). Si en el futur els snapshots guarden tots els
    ranks precalculats, aquest es l'UNIC lloc a canviar.
    """
    result = _get_ticker_result(snapshot, ticker)
    if result is None:
        return None

    if score_field == "mid_term" and result.get("rank_mid_term") is not None:
        return result["rank_mid_term"]

    for i, (t, _score) in enumerate(_ranked_tickers(snapshot, score_field), start=1):
        if t == ticker:
            return i
    return None


def get_rank(date_str: str, ticker: str, score_field: str = "mid_term") -> int | None:
    """
    Posicio (1 = millor) d'un ticker dins de l'univers, per a un
    score_field concret, en una data concreta.
    """
    _validate_score_field(score_field)
    snapshot = load_snapshot(date_str)
    return _rank(snapshot, ticker, score_field)


def top_n(
    date_str: str,
    score_field: str = "mid_term",
    n: int | None = 10,
) -> list[tuple[str, float]]:
    """
    Els N tickers amb millor score_field en una data concreta,
    ordenats descendent. n=None retorna l'univers sencer ordenat
    (util per calcular get_rank() de qualsevol horitzo, o per a
    metriques que necessiten totes les puntuacions).

    Retorna una llista de (ticker, score). Els tickers amb score
    null per aquell camp es descarten.
    """
    _validate_score_field(score_field)
    snapshot = load_snapshot(date_str)
    ranked = _ranked_tickers(snapshot, score_field)
    return ranked if n is None else ranked[:n]


def get_ticker_history(
    ticker: str,
    start_date: str | None = None,
    end_date: str | None = None,
    index: SnapshotIndex | None = None,
) -> list[dict]:
    """
    Serie temporal completa d'un ticker dins de [start_date, end_date]
    (tots dos inclosos, None = sense limit). API general: qualsevol
    finestra (per exemple "ultims 30 dies") es construeix calculant
    start_date = avui - 30 dies i cridant aquesta mateixa funcio.

    Retorna una llista ordenada cronologicament de dicts:
        {
            "date": "2026-07-18",
            "last_close": 333.74,
            "score_short_term": 83.7,
            "score_mid_term": 78.3,
            "score_long_term": 50.2,
            "rank_mid_term": 5,
            "subscores": {...},
            "checklist": {...},
        }

    Dies en que el ticker no apareixia al snapshot (encara no
    seguit, o descartat aquell dia) simplement no generen entrada
    -- no s'omple amb None per no confondre "no hi era" amb
    "hi era pero sense score".
    """
    idx = index or SnapshotIndex()
    snapshots = load_snapshots(start_date, end_date, index=idx)

    history = []
    for date_str, snapshot in snapshots:
        result = _get_ticker_result(snapshot, ticker)
        if result is None:
            continue

        scores = result.get("scores", {})
        history.append({
            "date": date_str,
            "last_close": result.get("last_close"),
            "score_short_term": scores.get("short_term"),
            "score_mid_term": scores.get("mid_term"),
            "score_long_term": scores.get("long_term"),
            "rank_mid_term": result.get("rank_mid_term"),
            "subscores": result.get("subscores", {}),
            "checklist": result.get("checklist", {}),
        })

    return history
