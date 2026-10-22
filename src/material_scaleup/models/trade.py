"""Country-specific historical trade, not live procurement availability."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from material_scaleup.models.source import Source


class TradeCountry(BaseModel):
    code: int = Field(gt=0)
    name: str


class TradeProduct(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    description: str
    classification: Literal["H6"] = "H6"


class TradeMatch(BaseModel):
    requested_material: str
    product: TradeProduct
    relationship: Literal["direct", "broader", "candidate"]
    reason: str

    @property
    def requires_confirmation(self) -> bool:
        return self.relationship != "direct"


class TradeObservation(BaseModel):
    year: int
    partner_code: int
    partner_name: str
    value_usd: float = Field(ge=0, allow_inf_nan=False)
    net_weight_kg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    weight_estimated: bool = False
    reported_classification: str | None = None


class TradeYear(BaseModel):
    year: int
    status: Literal["available", "no_reported_trade", "insufficient_data", "error"]
    reported_classifications: list[str] = Field(default_factory=list)
    classification_matches_catalog: bool = False
    import_value_usd: float | None = None
    reported_net_weight_kg: float | None = None
    largest_partner_share_percent: float | None = None
    top_three_share_percent: float | None = None
    hhi: float | None = None
    unit_value_usd_per_kg: float | None = None
    usable_weight_value_coverage_percent: float | None = None
    unit_value_basis: str | None = None
    partners: list[TradeObservation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AvailabilityResult(BaseModel):
    country: TradeCountry
    match: TradeMatch
    confirmed: bool
    status: Literal["available", "no_reported_trade", "insufficient_data", "error"]
    retrieved_at: datetime
    source: Source
    trade_flow: Literal["imports"] = "imports"
    frequency: Literal["annual"] = "annual"
    query_classification: Literal["HS"] = "HS"
    years: list[TradeYear] = Field(default_factory=list)
    observations: list[TradeObservation] = Field(default_factory=list)
    value_change_percent: float | None = None
    trend_period: str | None = None
    data_gaps: list[str] = Field(default_factory=list)
    score: None = None
    score_status: Literal["not_scored"] = "not_scored"
    domestic_supply_status: Literal["not_checked"] = "not_checked"
    restrictions_status: Literal["not_checked"] = "not_checked"
    logistics_status: Literal["not_checked"] = "not_checked"
