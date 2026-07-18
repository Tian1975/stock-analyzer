"""
src/history/metrics.py

Encara BUIT (Sprint 2.2). Aqui viuran les preguntes d'evidencia:

    score_distribution(date)
    ranking_changes(start_date, end_date)
    subscore_volatility(ticker, start_date, end_date)
    future_returns(date, score_threshold)   -- Sprint 2.3, quan hi
                                                hagi prou historial
    accuracy(...)                           -- Sprint 2.3
    top10_turnover(start_date, end_date)

Principi (acordat abans de comencar aquest modul): el Model 2 no
existeix per generar senyals d'inversio; existeix per generar
confianca (o desconfianca) en el Model 1. Cada metrica hauria
d'anar acompanyada de la seva propia força d'evidencia (nombre
d'observacions, periode cobert, si la mostra es encara massa
petita per treure conclusions) -- no nomes el resultat en si.
"""
