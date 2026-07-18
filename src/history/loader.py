"""
src/history/loader.py

Responsabilitat UNICA: trobar, llegir i validar snapshots
(data/history/scores/*.json). NO calcula res, NO interpreta res --
aixo es feina de queries.py i metrics.py.

Un snapshot es simplement el dict JSON tal com el va escriure
score.py::save_history_snapshot(). Aquest modul no assumeix res
mes enlla que:
    - el fitxer es diu "YYYY-MM-DD.json"
    - conte una clau "results" (llista de dicts, un per ticker)
"""

import json
from pathlib import Path
from datetime import date as _date

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HISTORY_DIR = PROJECT_ROOT / "data" / "history" / "scores"


def _parse_date_from_filename(path: Path) -> str | None:
    """
    Retorna el string 'YYYY-MM-DD' del nom de fitxer si es valid,
    o None si el fitxer no segueix la convencio esperada (es
    ignora silenciosament -- pot haver-hi altres fitxers a la
    carpeta en el futur).
    """
    stem = path.stem
    try:
        _date.fromisoformat(stem)
    except ValueError:
        return None
    return stem


class SnapshotIndex:
    """
    Coneix quins snapshots existeixen SENSE haver de tornar a
    escanejar el directori a cada consulta. Es construeix un cop
    (per exemple a l'inici d'un script o una sessio de Pythonista)
    i es reutilitza.

    Us:
        index = SnapshotIndex()
        index.dates()          # ['2026-07-14', '2026-07-15', ...]
        index.first_date()     # '2026-07-14'
        index.last_date()      # data mes recent disponible
        index.has('2026-07-16')
        index.path_for('2026-07-16')
    """

    def __init__(self, history_dir: Path = HISTORY_DIR):
        self.history_dir = history_dir
        self._dates: list[str] = []
        self.refresh()

    def refresh(self) -> None:
        """Torna a escanejar el directori. Cridar-ho nomes si es
        sap que hi ha hagut canvis (p.ex. un nou dia de pipeline)."""
        if not self.history_dir.exists():
            self._dates = []
            return

        found = []
        for path in self.history_dir.glob("*.json"):
            date_str = _parse_date_from_filename(path)
            if date_str is not None:
                found.append(date_str)

        self._dates = sorted(found)

    def dates(self) -> list[str]:
        """Totes les dates disponibles, ordenades ascendent."""
        return list(self._dates)

    def first_date(self) -> str | None:
        return self._dates[0] if self._dates else None

    def last_date(self) -> str | None:
        return self._dates[-1] if self._dates else None

    def has(self, date_str: str) -> bool:
        return date_str in self._dates

    def path_for(self, date_str: str) -> Path:
        return self.history_dir / f"{date_str}.json"

    def dates_in_range(self, start_date: str | None = None, end_date: str | None = None) -> list[str]:
        """
        Retorna les dates disponibles dins de [start_date, end_date]
        (tots dos inclosos). None significa "sense limit" en aquell
        extrem.
        """
        result = self._dates
        if start_date is not None:
            result = [d for d in result if d >= start_date]
        if end_date is not None:
            result = [d for d in result if d <= end_date]
        return result

    def __len__(self) -> int:
        return len(self._dates)

    def __repr__(self) -> str:
        if not self._dates:
            return "SnapshotIndex(buit)"
        return f"SnapshotIndex({len(self._dates)} snapshots, {self.first_date()}..{self.last_date()})"


def load_snapshot(date_str: str, history_dir: Path = HISTORY_DIR) -> dict:
    """
    Carrega un snapshot concret. Llança FileNotFoundError amb un
    missatge clar si no existeix -- millor fallar explicit que
    retornar silenciosament un dict buit.
    """
    path = history_dir / f"{date_str}.json"
    if not path.exists():
        raise FileNotFoundError(f"No hi ha snapshot per a la data {date_str} ({path})")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "results" not in data:
        raise ValueError(f"Snapshot {date_str} no te la clau 'results' esperada")

    return data


def load_snapshots(
    start_date: str | None = None,
    end_date: str | None = None,
    index: SnapshotIndex | None = None,
) -> list[tuple[str, dict]]:
    """
    Carrega tots els snapshots dins de [start_date, end_date]
    (tots dos inclosos, format 'YYYY-MM-DD'). None = sense limit.

    Retorna una llista de (date_str, snapshot_dict) ordenada
    cronologicament ascendent.

    Es pot reutilitzar un SnapshotIndex ja construit (per exemple
    si ja se n'ha creat un per fer altres consultes) per no tornar
    a escanejar el directori.
    """
    idx = index or SnapshotIndex()
    dates = idx.dates_in_range(start_date, end_date)
    return [(d, load_snapshot(d, idx.history_dir)) for d in dates]


def latest_snapshot(index: SnapshotIndex | None = None) -> tuple[str, dict] | None:
    """
    Retorna (date_str, snapshot_dict) del snapshot mes recent
    disponible, o None si no n'hi ha cap.
    """
    idx = index or SnapshotIndex()
    last = idx.last_date()
    if last is None:
        return None
    return last, load_snapshot(last, idx.history_dir)
