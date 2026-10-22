# src/material_scaleup/providers/pubchem.py

from urllib.parse import quote

import requests

from material_scaleup.models.chemical import ChemicalIdentity
from material_scaleup.providers.base import ChemicalIdentityProvider


class ChemicalNotFoundError(LookupError):
    """PubChem could not resolve the submitted chemical identifier."""

    def __init__(self, identifier: str) -> None:
        super().__init__(
            f"PubChem could not find a compound for {identifier!r}. "
            "Check the spelling or try a recognized chemical name or CAS number. "
            "No chemical has been substituted; the assessment was not completed."
        )


class PubChemProvider(ChemicalIdentityProvider):
    """Resolve chemical identities using PubChem PUG REST."""

    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    PROPERTY_FIELDS = ",".join(
        [
            "MolecularFormula",
            "MolecularWeight",
            "CanonicalSMILES",
            "InChI",
            "InChIKey",
        ]
    )

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def get_by_name(self, name: str) -> ChemicalIdentity:
        return self._get_by_identifier(namespace="name", identifier=name)

    def get_by_smiles(self, smiles: str) -> ChemicalIdentity:
        return self._get_by_identifier(namespace="smiles", identifier=smiles)

    def get_by_cas_rn(self, cas_rn: str) -> ChemicalIdentity:
        return self._get_by_identifier(namespace="name", identifier=cas_rn)

    def _get_by_identifier(
        self,
        namespace: str,
        identifier: str,
    ) -> ChemicalIdentity:
        encoded_identifier = quote(identifier, safe="")

        url = (
            f"{self.BASE_URL}/compound/{namespace}/{encoded_identifier}/"
            f"property/{self.PROPERTY_FIELDS}/JSON"
        )

        response = requests.get(url, timeout=self.timeout)
        if response.status_code == 404:
            raise ChemicalNotFoundError(identifier)
        response.raise_for_status()

        payload = response.json()

        properties = payload["PropertyTable"]["Properties"]

        if not properties:
            raise ChemicalNotFoundError(identifier)

        record = properties[0]

        return ChemicalIdentity(
            pubchem_cid=record.get("CID"),
            cas_rn=self._infer_cas_rn(identifier),
            name=identifier if namespace == "name" else None,
            formula=record.get("MolecularFormula"),
            molecular_weight=self._parse_float(record.get("MolecularWeight")),
            canonical_smiles=record.get("ConnectivitySMILES"),
            inchi=record.get("InChI"),
            inchikey=record.get("InChIKey"),
        )

    @staticmethod
    def _infer_cas_rn(identifier: str) -> str | None:
        parts = identifier.split("-")

        if len(parts) == 3 and all(part.isdigit() for part in parts):
            return identifier

        return None

    @staticmethod
    def _parse_float(value: object) -> float | None:
        if value is None:
            return None

        return float(value)  # pyright: ignore[reportArgumentType]
