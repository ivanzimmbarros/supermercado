"""Registry de providers — só instancia mercados habilitados na config."""

from __future__ import annotations

from supermercado.providers.base import PriceProvider
from supermercado.providers.continente import ContinenteProvider
from supermercado.providers.pingo_doce import PingoDoceProvider

_PROVIDER_CTORS = {
    "continente": ContinenteProvider,
    "pingo_doce": PingoDoceProvider,
}


class DisabledProvider:
    def __init__(self, market_id: str):
        self.market_id = market_id

    def search(self, query, geo):  # type: ignore[no-untyped-def]
        return []

    def get_by_ean(self, ean, geo):  # type: ignore[no-untyped-def]
        return []

    def healthcheck(self):  # type: ignore[no-untyped-def]
        from supermercado.providers.base import ProviderStatus

        return ProviderStatus(self.market_id, False, "Provider ainda não implementado (v2)", False)


def build_providers(enabled_market_ids: list[str]) -> list[PriceProvider]:
    providers: list[PriceProvider] = []
    for market_id in enabled_market_ids:
        ctor = _PROVIDER_CTORS.get(market_id)
        if ctor:
            providers.append(ctor())
        else:
            providers.append(DisabledProvider(market_id))  # type: ignore[arg-type]
    return providers
