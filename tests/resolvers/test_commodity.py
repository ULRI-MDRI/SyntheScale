# tests/resolvers/test_commodity.py

from material_scaleup.models.chemical import ChemicalIdentity
from material_scaleup.resolvers.commodity import (
    CuratedCommodityResolver,
)


def test_resolves_sodium_aluminate_to_aluminum():
    resolver = CuratedCommodityResolver()

    chemical = ChemicalIdentity(
        name="sodium aluminate",
        formula="AlNaO2",
    )

    exposures = resolver.resolve(chemical)

    assert len(exposures) == 1
    assert exposures[0].commodity == "aluminum"


def test_resolves_sodium_silicate_to_silicon():
    resolver = CuratedCommodityResolver()

    chemical = ChemicalIdentity(
        name="sodium silicate",
        formula="Na2O3Si",
    )

    exposures = resolver.resolve(chemical)

    assert len(exposures) == 1
    assert exposures[0].commodity == "silicon"


def test_unmapped_chemical_returns_empty():
    resolver = CuratedCommodityResolver()

    chemical = ChemicalIdentity(name="unobtainium oxide")

    assert resolver.resolve(chemical) == []
