# tests/providers/test_pubchem.py

from unittest.mock import Mock, patch

import pytest
import requests

from material_scaleup.providers.pubchem import ChemicalNotFoundError, PubChemProvider


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


@pytest.mark.parametrize(
    ("method", "identifier"),
    [
        ("get_by_name", "sodium fumerate"),
        ("get_by_cas_rn", "0000-00-0"),
        ("get_by_smiles", "invalid"),
    ],
)
def test_pubchem_reports_missing_compound(provider, method, identifier):
    response = Mock(status_code=404)
    with patch("material_scaleup.providers.pubchem.requests.get", return_value=response):
        with pytest.raises(ChemicalNotFoundError, match=identifier):
            getattr(provider, method)(identifier)
    response.json.assert_not_called()


def test_pubchem_reports_empty_compound_results(provider):
    response = Mock(status_code=200)
    response.json.return_value = {"PropertyTable": {"Properties": []}}
    with patch("material_scaleup.providers.pubchem.requests.get", return_value=response):
        with pytest.raises(ChemicalNotFoundError, match="sodium fumerate"):
            provider.get_by_name("sodium fumerate")


@pytest.mark.parametrize("status_code", [400, 429, 500, 503])
def test_pubchem_preserves_other_http_errors(provider, status_code):
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/test"
    with patch("material_scaleup.providers.pubchem.requests.get", return_value=response):
        with pytest.raises(requests.HTTPError) as error:
            provider.get_by_name("test")
    assert error.value.response.status_code == status_code


def test_pubchem_preserves_timeouts(provider):
    with patch(
        "material_scaleup.providers.pubchem.requests.get",
        side_effect=requests.Timeout("PubChem timed out"),
    ):
        with pytest.raises(requests.Timeout):
            provider.get_by_name("test")


def test_pubchem_successful_lookup_is_unchanged(provider):
    response = Mock(status_code=200)
    response.json.return_value = {
        "PropertyTable": {
            "Properties": [
                {
                    "CID": 14798,
                    "MolecularFormula": "HNaO",
                    "MolecularWeight": "39.997",
                    "ConnectivitySMILES": "[OH-].[Na+]",
                    "InChI": "test-inchi",
                    "InChIKey": "test-inchikey",
                }
            ]
        }
    }
    with patch("material_scaleup.providers.pubchem.requests.get", return_value=response) as get:
        chemical = provider.get_by_name("sodium hydroxide")
    response.raise_for_status.assert_called_once()
    assert chemical.pubchem_cid == 14798
    assert chemical.name == "sodium hydroxide"
    assert chemical.formula == "HNaO"
    assert chemical.molecular_weight == pytest.approx(39.997)
    get.assert_called_once_with(
        f"{provider.BASE_URL}/compound/name/sodium%20hydroxide/"
        f"property/{provider.PROPERTY_FIELDS}/JSON",
        timeout=provider.timeout,
    )
