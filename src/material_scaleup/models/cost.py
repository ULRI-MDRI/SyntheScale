# src/material_scaleup/models/cost.py

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from material_scaleup.models.chemical import ChemicalIdentity
from material_scaleup.models.source import Source

__all__ = [
    "PriceBasis",
    "PriceQuote",
    "RawMaterialCost",
    "RawMaterialCostEstimate",
    "CommodityPriceObservation",
]


class PriceBasis(StrEnum):
    """Basis from which a raw-material price was obtained."""

    VENDOR = "vendor"
    COMMODITY = "commodity"
    USER_PROVIDED = "user_provided"
    ESTIMATED = "estimated"


class PriceQuote(BaseModel):
    """
    Price observation for a chemical or commodity.

    Attributes:
        chemical (ChemicalIdentity):
            Chemical identity of the material for which the price is quoted.

        price (float):
            Observed price for the specified quantity of the material.

        currency (str):
            Currency in which the price is quoted.

        quantity (float):
            Quantity of the material for which the price is quoted.

        quantity_units (str):
            Units of the quoted quantity.

        basis (PriceBasis):
            Basis from which the price was obtained.

        supplier (str | None):
            Supplier providing the price quote, if applicable.

        region (str | None):
            Geographic region relevant to the price quote, if applicable.

        source (Source):
            Source of the price information.
    """

    chemical: ChemicalIdentity
    price: float = Field(ge=0)
    currency: str = "USD"
    quantity: float = Field(gt=0)
    quantity_units: str
    basis: PriceBasis
    supplier: str | None = None
    region: str | None = None
    source: Source


class RawMaterialCost(BaseModel):
    """
    Cost contribution from one raw material.

    Attributes:
        chemical (ChemicalIdentity):
            Chemical identity of the raw material.

        required_quantity (float):
            Quantity of the raw material required for the target product amount.

        quantity_units (str):
            Units of the required quantity.

        unit_cost (float):
            Cost per unit of the raw material.

        unit_cost_units (str):
            Units of the unit cost.

        cost_contribution (float):
            Contribution of this raw material to the total raw material cost.

        currency (str):
            Currency in which the cost is expressed.

        price_quote (PriceQuote):
            Price quote associated with this raw material.
    """

    chemical: ChemicalIdentity
    required_quantity: float = Field(ge=0)
    quantity_units: str
    unit_cost: float = Field(ge=0)
    unit_cost_units: str
    cost_contribution: float = Field(ge=0)
    currency: str = "USD"
    price_quote: PriceQuote


class RawMaterialCostEstimate(BaseModel):
    """
    Estimated raw-material cost for a target amount of product.

    Processing, labor, capital, utilities, overhead, and other
    manufacturing costs are excluded.

    Attributes:
        product_amount (float):
            Target amount of the product for which the raw-material cost is
            estimated.

        product_units (str):
            Units of the target product amount.

        input_costs (list[RawMaterialCost]):
            List of raw material cost contributions.

        total_raw_material_cost (float):
            Total raw material cost for the target product amount.

        currency (str):
            Currency in which the cost is expressed.

        cost_per_product_mass (float | None):
            Estimated raw material cost per unit mass of the product, if
            pplicable.

        cost_per_product_mass_units (str | None):
            Units of the cost per product mass, if applicable.

        assumptions (list[str]):
            List of assumptions underlying the cost estimate.
    """

    product_amount: float = Field(gt=0)
    product_units: str
    input_costs: list[RawMaterialCost] = Field(default_factory=list)
    total_raw_material_cost: float = Field(ge=0)
    currency: str = "USD"
    cost_per_product_mass: float | None = Field(default=None, ge=0)
    cost_per_product_mass_units: str | None = None
    assumptions: list[str] = Field(default_factory=list)


class CommodityPriceObservation(BaseModel):
    """
    Observed commodity price for one month.

    Attributes:
        commodity (str):
            Name of the commodity.

        date (date):
            Date of the observation.

        price (float):
            Observed price of the commodity.

        currency (str):
            Currency in which the price is expressed.

        units (str):
            Units of the observed price.

        source (Source):
            Source of the price observation.
    """

    commodity: str
    date: date
    price: float = Field(gt=0)
    currency: str = "USD"
    units: str
    source: Source
