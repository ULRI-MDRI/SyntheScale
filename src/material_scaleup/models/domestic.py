"""Domestic production context is not proof of precursor availability."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from material_scaleup.models.supply import USGSCommodityObservation


class DomesticProductionResult(BaseModel):
    material: str
    requested_country: str
    source_country: str | None = None
    checked_at: datetime
    status: Literal["available", "not_available", "not_checked", "error"]
    relationship: Literal["upstream"] = "upstream"
    direct_material_status: Literal["not_checked"] = "not_checked"
    upstream_commodities: list[str] = Field(default_factory=list)
    observations: list[USGSCommodityObservation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
