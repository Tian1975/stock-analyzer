"""
Connector EDGAR reutilitzable.

Us RECOMANAT des de score.py (o qualsevol altre consumidor), a
traves de la interficie de providers (permet afegir Yahoo, Europa,
etc. sense tocar score.py):

    from edgar.providers import lookup_fundamentals

    fundamentals = lookup_fundamentals("AAPL", "2023-06-15")
    # fundamentals["_provider"] -> "EDGAR"
    # fundamentals["_coverage"] -> 100.0

Per a us avançat (injectar un provider concret, tests, etc.):

    from edgar.providers import EdgarProvider, CompositeProvider

    provider = CompositeProvider([EdgarProvider()])
    fundamentals = provider.lookup("AAPL", "2023-06-15")

La funcio original (nomes EDGAR, sense metadades de provider) segueix
disponible a edgar.lookup per compatibilitat interna:

    from edgar.lookup import lookup_fundamentals as edgar_only_lookup
"""
