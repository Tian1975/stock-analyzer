"""
Biblioteca del projecte per consultar l'historial de snapshots
(data/history/scores/*.json). Es el fonament del Model 2.

Tres responsabilitats separades:

    loader.py   -- sap trobar i llegir fitxers. Cap logica de negoci.
    queries.py  -- consultes sobre snapshots ja carregats (rank, score,
                   top_n, historial d'un ticker). Encara no calcula
                   estadistiques.
    metrics.py  -- (Sprint 2.2+) aqui viuen les preguntes d'evidencia:
                   distribucions, retorns futurs, taxes d'encert...

Aquesta biblioteca es independent de com es fara servir despres
(Pythonista, scripts, GitHub Actions, PWA, notebooks). No coneix res
de EDGAR ni Yahoo -- nomes llegeix el que score.py ja ha calculat i
guardat.
"""

from .loader import SnapshotIndex, load_snapshot, load_snapshots, latest_snapshot
from .queries import get_ticker_history, get_rank, get_score, top_n, list_dates
from .metrics import make_evidence, score_distribution, top10_turnover
