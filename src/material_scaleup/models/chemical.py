
# src/material_scaleup/models/chemical.py

from pydantic import BaseModel, Field, model_validator

__all__ = [
    "ChemicalIdentity",
    "MaterialComponent",
    "MaterialSpec",
]

class ChemicalIdentity(BaseModel):
    """
    Represents the identity of a chemical substance.

    Attributes:
        cas_rn (str | None):
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
    cas_rn: str | None = None
    name: str | None = None
    formula: str | None = None
    molecular_weight: float | None = None
    canonical_smiles: str | None = None
    inchi: str | None = None
    inchikey: str | None = None
    synonyms: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_at_least_one_identifier(self) -> "ChemicalIdentity":
        """Require enough information to identify the chemical."""

        identifiers = (
            self.cas_rn,
            self.name,
            self.formula,
            self.canonical_smiles,
            self.inchi,
            self.inchikey,
        )

        if not any(
            value is not None and value.strip()
            for value in identifiers
        ):
            raise ValueError(
                "At least one chemical identifier must be provided."
            )

        return self

class MaterialComponent(BaseModel):
    """
    A chemical component of a material or formulation.
    
    Attributes:
        chemical (ChemicalIdentity):
            The chemical identity of the component.

        role (str | None):
            The role of the chemical component within the material, if available.

        amount (float | None):
            The amount of the chemical component, if available.

        units (str | None):
            The units of the amount, if available.

        fraction (float | None):
            The fraction of the chemical component within the material, if
            available.
    """
    chemical: ChemicalIdentity
    role: str | None = None
    amount: float | None = Field(default=None, ge=0)
    units: str | None = None
    fraction: float | None = Field(default=None, ge=0, le=1)

class MaterialSpec(BaseModel):
    """
    A material submitted for scale-up assessment.

    A material may be a discrete chemical, mixture, composite, catalyst,
    formulation, polymer, or computationally proposed structure.

    Attributes:
        name (str):
            The name of the material.

        description (str | None):
            A description of the material, if available.

        formula (str | None):
            The chemical formula of the material, if available.

        canonical_smiles (str | None):
            The canonical SMILES representation of the material, if available.

        structure_reference (str | None):
            A reference to the structure of the material, if available.

        components (list[MaterialComponent]):
            A list of chemical components that make up the material.
    """
    name: str
    description: str | None = None
    formula: str | None = None
    canonical_smiles: str | None = None
    structure_reference: str | None = None
    components: list[MaterialComponent] = Field(default_factory=list)
