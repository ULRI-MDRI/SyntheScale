# src/material_scaleup/calculations/market_evidence.py

from material_scaleup.calculations.volatility import (
    annualized_price_volatility,
    price_change,
)
from material_scaleup.models.categories import AssessmentCategory
from material_scaleup.models.cost import CommodityPriceObservation
from material_scaleup.models.evidence import (
    Evidence,
    EvidenceScope,
    EvidenceValue,
)

__all__ = [
    "commodity_market_evidence",
]


def commodity_market_evidence(
    observations: list[CommodityPriceObservation],
) -> list[Evidence]:
    """
    Convert a commodity price history into scale-up evidence.

    Produces evidence describing:
        1. The latest observed commodity price.
        2. Price change across the supplied observation window.
        3. Annualized volatility of monthly logarithmic returns.

    The observations must all describe the same commodity.

    Args:
        observations (list[CommodityPriceObservation]):
            A list of commodity price observations, all for the same commodity.

    Returns:
        list[Evidence]:
            A list of evidence objects derived from the commodity price
            observations.
    """
    if not observations:
        return []

    ordered = sorted(
        observations,
        key=lambda observation: observation.date,
    )

    _validate_single_commodity(ordered)

    commodity = ordered[0].commodity
    latest = ordered[-1]
    first = ordered[0]

    evidence: list[Evidence] = [
        Evidence(
            category=AssessmentCategory.COST,
            claim=f"Latest reference commodity price for {commodity}",
            reported_value=EvidenceValue(value=latest.price, units=latest.units),
            source=latest.source,
            scope=EvidenceScope(
                effective_date=latest.date,
                market_basis="World Bank commodity reference price",
            ),
            notes=(
                "This is a commodity-market reference price and must "
                "not be interpreted as the purchase price of a "
                "specific chemical precursor."
            ),
            metadata={
                "commodity": commodity,
                "observation_type": "latest_price",
            },
        )
    ]

    change = price_change(ordered)

    if change is not None:
        evidence.append(
            Evidence(
                category=AssessmentCategory.MARKET_VOLATILITY,
                claim=(f"Price change for {commodity} across the available analysis window"),
                reported_value=EvidenceValue(value=change * 100, units="%"),
                source=latest.source,
                scope=EvidenceScope(
                    period_start=first.date,
                    period_end=latest.date,
                    market_basis="World Bank monthly commodity prices",
                ),
                notes=(
                    "Calculated by SyntheScale from the first and "
                    "last prices in the supplied observation window."
                ),
                metadata={
                    "commodity": commodity,
                    "observation_type": "price_change",
                    "number_of_observations": len(ordered),
                },
            )
        )

    volatility = annualized_price_volatility(ordered)

    if volatility is not None:
        evidence.append(
            Evidence(
                category=AssessmentCategory.MARKET_VOLATILITY,
                claim=(f"Annualized historical price volatility for {commodity}"),
                reported_value=EvidenceValue(value=volatility * 100, units="%"),
                source=latest.source,
                scope=EvidenceScope(
                    period_start=first.date,
                    period_end=latest.date,
                    market_basis=("Monthly logarithmic returns from World Bank commodity prices"),
                ),
                notes=(
                    "Calculated by SyntheScale as the standard "
                    "deviation of monthly logarithmic returns, "
                    "annualized by multiplying by the square root of 12."
                ),
                metadata={
                    "commodity": commodity,
                    "observation_type": "annualized_volatility",
                    "number_of_observations": len(ordered),
                },
            )
        )

    return evidence


def _validate_single_commodity(
    observations: list[CommodityPriceObservation],
) -> None:
    """Require all observations to represent the same commodity."""

    commodities = {observation.commodity.casefold() for observation in observations}

    if len(commodities) != 1:
        raise ValueError(
            "Commodity market evidence requires observations for exactly one commodity."
        )
