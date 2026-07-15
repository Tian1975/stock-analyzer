"""
providers.py

Interficie comuna per a qualsevol font de fonamentals (EDGAR, Yahoo,
un futur proveidor europeu...). score.py NOMES hauria de parlar amb
aquesta interficie — mai amb EDGAR, Yahoo o qualsevol altra font
directament.

    provider = CompositeProvider([
        EdgarProvider(),
        EuropeProvider(),
        YahooProvider(),
    ])
    fundamentals = provider.lookup(ticker, date)

Cada resposta be marcada amb la seva procedencia (_provider, _filed,
_coverage) per traçabilitat i depuracio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .lookup import lookup_fundamentals as _edgar_lookup_fundamentals

# Conceptes que es consideren "requerits" per calcular la cobertura
# (_coverage). Ha de coincidir amb els conceptes canonics de Fase 1
# definits a concepts.py; si s'amplien alla, ampliar-ho tambe aqui.
REQUIRED_CONCEPTS = [
    "revenue",
    "net_income",
    "eps_basic",
    "operating_income",
    "shares_outstanding",
]


class FundamentalsNotAvailable(Exception):
    """
    Excepcio comuna que ha de llançar qualsevol provider quan no te
    cap dada util per a (ticker, date). Aixo evita anar comprovant
    None a cada nivell i deixa el CompositeProvider decidir que fer
    (provar el seguent provider de la llista).
    """
    pass


def _coverage(fundamentals: dict) -> float:
    """
    Percentatge (0-100) dels REQUIRED_CONCEPTS que el resultat
    conte realment. Ignora claus internes (les que comencen amb '_').
    """
    if not fundamentals:
        return 0.0
    present = sum(1 for c in REQUIRED_CONCEPTS if c in fundamentals)
    return round(100 * present / len(REQUIRED_CONCEPTS), 1)


class FundamentalsProvider(ABC):
    """
    Interficie que ha d'implementar qualsevol font de fonamentals.
    """

    name: str = "unknown"

    @abstractmethod
    def _raw_lookup(self, ticker: str, date: str) -> dict:
        """
        Implementacio especifica de cada provider. Ha de retornar
        un dict pla de conceptes canonics (pot ser buit si no hi ha
        dades) o llançar FundamentalsNotAvailable directament.
        No cal que afegeixi metadades (_provider, _coverage...);
        aixo ho fa el metode public `lookup()`.
        """
        raise NotImplementedError

    def lookup(self, ticker: str, date: str) -> dict:
        """
        Metode public que fan servir els consumidors (score.py,
        CompositeProvider...). Afegeix metadades i llança
        FundamentalsNotAvailable si el resultat es buit, perque
        el contracte sigui identic per a tots els providers.
        """
        raw = self._raw_lookup(ticker, date)

        # buidem-nos de metadades internes abans de mesurar cobertura
        clean = {k: v for k, v in raw.items() if not k.startswith("_")}

        if not clean:
            raise FundamentalsNotAvailable(
                f"{self.name}: sense dades per a {ticker} a {date}"
            )

        coverage = _coverage(clean)
        result = dict(clean)
        result["_provider"] = self.name
        result["_coverage"] = coverage

        # si el provider ja informava de la data de filing (com fa
        # EdgarProvider via lookup_fundamentals), la conservem
        if "_as_of" in raw:
            result["_as_of"] = raw["_as_of"]

        return result

    def health(self) -> dict:
        """
        Indicador basic de salut del provider. Les subclasses poden
        sobreescriure-ho per fer una comprovacio real (p.ex. un ping
        a l'API). Per defecte, nomes indica que esta configurat.
        """
        return {"provider": self.name, "status": "unknown"}


class EdgarProvider(FundamentalsProvider):
    """
    Embolcall de l'actual lookup_fundamentals() (SEC EDGAR) darrere
    la interficie comuna. No canvia la logica existent — nomes la
    reempaqueta.
    """

    name = "EDGAR"

    def _raw_lookup(self, ticker: str, date: str) -> dict:
        return _edgar_lookup_fundamentals(ticker, date)

    def health(self) -> dict:
        # EDGAR nomes cobreix EUA i alguns ADRs; no fem cap crida real
        # aqui per no gastar quota sense necessitat.
        return {"provider": self.name, "status": "configured", "coverage_scope": "US + ADRs"}


class YahooProvider(FundamentalsProvider):
    """
    Esquelet. Encara no implementat: avui els fonamentals no-EDGAR
    es gestionen amb 'fundamentals_frozen' dins score.py, tal com
    ja esta documentat al PROJECT_STATUS. Quan es vulgui connectar
    Yahoo com a provider real, nomes cal omplir _raw_lookup().
    """

    name = "Yahoo"

    def _raw_lookup(self, ticker: str, date: str) -> dict:
        raise FundamentalsNotAvailable(
            "YahooProvider encara no implementat"
        )

    def health(self) -> dict:
        return {"provider": self.name, "status": "not_implemented"}


class EuropeProvider(FundamentalsProvider):
    """
    Esquelet per a un futur proveidor europeu (CNMV o equivalent).
    Es deixa preparat perque, el dia que es trobi una font viable,
    nomes calgui omplir _raw_lookup() sense tocar score.py ni el
    CompositeProvider.
    """

    name = "Europe"

    def _raw_lookup(self, ticker: str, date: str) -> dict:
        raise FundamentalsNotAvailable(
            "EuropeProvider encara no implementat"
        )

    def health(self) -> dict:
        return {"provider": self.name, "status": "not_implemented"}


class CompositeProvider(FundamentalsProvider):
    """
    Prova una llista de providers, en ordre, i es queda amb el
    primer que respongui amb dades. No hi ha cap 'if ticker.endswith'
    ni 'if region ==' — cada provider decideix per si mateix (via
    FundamentalsNotAvailable) si te alguna cosa util a oferir.
    """

    name = "Composite"

    def __init__(self, providers: list[FundamentalsProvider]):
        self._providers = providers

    def _raw_lookup(self, ticker: str, date: str) -> dict:
        # No s'arriba a fer servir directament: sobreescrivim lookup()
        # sencer perque cal preservar quin provider concret ha respost.
        raise NotImplementedError

    def lookup(self, ticker: str, date: str) -> dict:
        errors = []
        for provider in self._providers:
            try:
                return provider.lookup(ticker, date)
            except FundamentalsNotAvailable as e:
                errors.append(str(e))
                continue

        raise FundamentalsNotAvailable(
            f"Cap provider ha tingut dades per a {ticker} a {date}. "
            f"Detall: {'; '.join(errors)}"
        )

    def health(self) -> dict:
        return {
            "provider": self.name,
            "members": [p.health() for p in self._providers],
        }


# ---------------------------------------------------------------------
# Compatibilitat: es manté disponible la funció original tal qual,
# ara construïda per sobre del nou sistema de providers. score.py NO
# necessita cap canvi avui; quan es vulgui injectar un provider
# diferent (tests, benchmarking...), ja estarà preparat.
# ---------------------------------------------------------------------

_default_provider = CompositeProvider([
    EdgarProvider(),
    EuropeProvider(),
    YahooProvider(),
])


def lookup_fundamentals(ticker: str, date: str) -> dict:
    """
    Substitueix (amb la mateixa signatura) la funció original de
    lookup.py. Avui nomes EDGAR respon de veritat; els altres dos
    providers son esquelets que sempre delegaran cap avall fins que
    s'implementin.
    """
    try:
        return _default_provider.lookup(ticker, date)
    except FundamentalsNotAvailable:
        return {}
