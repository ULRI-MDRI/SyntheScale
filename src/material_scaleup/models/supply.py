# src/material_scaleup/models/supply.py

from pydantic import BaseModel

from material_scaleup.models.source import Source

__all__ = [
    "USGSCommodityObservation",
]


class USGSCommodityObservation(BaseModel):
    """
    One commodity statistic reported by USGS.

    Attributes:
        commodity (str):
            The name of the commodity.

        country (str):
            The name of the country.

        section (str):
            The section of the USGS report.

        statistic (str):
            The type of statistic reported.

        statistic_detail (str | None):
            Additional details about the statistic, if available.

        year (int | None):
            The year the statistic pertains to.

        raw_year (str):
            The raw year string as reported by USGS.

        value (float | None):
            The numeric value of the statistic.

        raw_value (str):
            The raw value string as reported by USGS.

        units (str | None):
            The units of the reported value, if applicable.

        notes (str | None):
            Any notes associated with the observation.

        other_notes (str | None):
            Additional notes, if any.

        is_critical_mineral (bool | None):
            Indicates if the commodity is a critical mineral.

        source (Source):
            The source of the observation.

        value_qualifier (str | None):
            Any qualifier associated with the value, if applicable.
    """

    commodity: str
    country: str
    section: str
    statistic: str
    statistic_detail: str | None = None
    year: int | None = None
    raw_year: str
    value: float | None = None
    raw_value: str
    units: str | None = None
    notes: str | None = None
    other_notes: str | None = None
    is_critical_mineral: bool | None = None
    source: Source
    value_qualifier: str | None = None

    @staticmethod
    def parse_value_qualifier(value: str) -> str | None:
        """Extract a published numeric qualifier."""
        normalized = value.strip()

        if normalized.startswith(">="):
            return ">="

        if normalized.startswith("<="):
            return "<="

        if normalized.startswith(">"):
            return ">"

        if normalized.startswith("<"):
            return "<"

        return None
