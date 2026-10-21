# tests/providers/test_pubchem.py

import pytest

from material_scaleup.providers.pubchem import PubChemProvider


@pytest.fixture
def provider() -> PubChemProvider:
    return PubChemProvider()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("name", "expected_formula"),
    [
        ("sodium hydroxide", "HNaO"),
        ("sodium silicate", "Na2O3Si"),
        ("sodium aluminate", "AlNaO2"),
        ("water", "H2O"),
        ("aluminum sulfate", "Al2O12S3"),
    ],
)
def test_pubchem_resolves_common_raw_materials(
    provider: PubChemProvider,
    name: str,
    expected_formula: str,
):
    chemical = provider.get_by_name(name)

    assert chemical.formula == expected_formula
    assert chemical.inchikey is not None
    assert chemical.canonical_smiles is not None
    assert chemical.pubchem_cid is not None


@pytest.mark.integration
def test_pubchem_resolves_by_cas_rn(
    provider: PubChemProvider,
):
    chemical = provider.get_by_cas_rn("1310-73-2")

    assert chemical.formula == "HNaO"
    assert chemical.cas_rn == "1310-73-2"
    assert chemical.pubchem_cid == 14798
    assert chemical.inchikey == "HEMHJVSKTPXQMS-UHFFFAOYSA-M"


@pytest.mark.integration
def test_pubchem_resolves_by_smiles(
    provider: PubChemProvider,
):
    chemical = provider.get_by_smiles("CC(=O)O")

    assert chemical.formula == "C2H4O2"
    assert chemical.inchikey is not None
    assert chemical.canonical_smiles is not None


@pytest.mark.integration
def test_pubchem_resolves_sodium_aluminosilicate(
    provider: PubChemProvider,
):
    chemical = provider.get_by_name("sodium aluminosilicate")

    assert chemical.formula is not None
