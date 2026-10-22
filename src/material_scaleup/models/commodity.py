# src/material_scaleup/models/commodity.py

from pydantic import BaseModel

from material_scaleup.models.chemical import ChemicalIdentity

__all__ = [
    "CommodityExposure",
]


class CommodityExposure(BaseModel):
    """
    Links a chemical or feedstock to an underlying commodity market.

    The exposure indicates economic or supply-chain relevance. It does
    not imply that the commodity price is the purchase price of the
    chemical itself.

    Attributes:
        chemical (ChemicalIdentity):
            The chemical or feedstock linked to the commodity.

        commodity (str):
            The underlying commodity market.

        reason (str):
            The rationale for the exposure.

        confidence (float | None):
            The confidence level in the exposure assessment, if available.
    """

    chemical: ChemicalIdentity
    commodity: str
    reason: str
    confidence: float | None = None
