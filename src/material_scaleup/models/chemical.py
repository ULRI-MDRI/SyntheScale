
# src/material_scaleup/models/chemical.py

from pydantic import BaseModel, Field

__all__ = [
    "ChemicalIdentity",
]

class ChemicalIdentity(BaseModel):
    """
    Represents the identity of a chemical substance.

    Attributes:
        cas_rn (str):
            The CAS Registry Number of the chemical.

        name (str | None):
            The common name of the chemical.

        formula (str | None):
            The chemical formula.

        molecular_weight (float | None):
            The molecular weight.

        canonical_smiles (str | None):
            The canonical SMILES representation.

        inchi (str | None):
            The InChI representation.

        inchikey (str | None):
            The InChIKey representation.

        synonyms (list[str]):
            A list of synonyms for the chemical.
    """
    cas_rn: str
    name: str | None = None
    formula: str | None = None
    molecular_weight: float | None = None
    canonical_smiles: str | None = None
    inchi: str | None = None
    inchikey: str | None = None
    synonyms: list[str] = Field(default_factory=list)
