# src/material_scaleup/calculations/supply_evidence.py

from datetime import date

from material_scaleup.models.categories import AssessmentCategory
from material_scaleup.models.evidence import (
    Evidence,
    EvidenceScope,
    EvidenceValue,
)
from material_scaleup.models.supply import USGSCommodityObservation
from material_scaleup.providers.usgs import USGSCommodityProvider

__all__ = [
    "usgs_supply_evidence",
]


def usgs_supply_evidence(
    provider: USGSCommodityProvider,
    commodity: str,
) -> list[Evidence]:
    """
    Build availability and supply-chain evidence for a commodity.

    Args:
        provider (USGSCommodityProvider):
            The provider to fetch USGS commodity data from.

        commodity (str):
            The commodity to build evidence for.

    Returns:
        list[Evidence]:
            A list of evidence objects related to the commodity's availability
            and supply chain.
    """
    evidence: list[Evidence] = []

    world_production = provider.get_latest_world_production(commodity)

    if world_production is not None:
        evidence.append(
            _observation_evidence(
                world_production,
                category=AssessmentCategory.AVAILABILITY,
                claim=f"Latest reported world production for {commodity}",
                observation_type="world_production",
            )
        )

    world_reserves = provider.get_latest_world_reserves(commodity)

    if world_reserves is not None:
        evidence.append(
            _observation_evidence(
                world_reserves,
                category=AssessmentCategory.AVAILABILITY,
                claim=f"Latest reported world reserves for {commodity}",
                observation_type="world_reserves",
            )
        )

    import_reliance = provider.get_latest_net_import_reliance(commodity)

    for record in import_reliance:
        detail = _short_statistic_detail(record.statistic_detail)

        claim = f"U.S. net import reliance for {commodity}"

        if detail:
            claim = f"{claim}: {detail}"

        evidence.append(
            _observation_evidence(
                record,
                category=AssessmentCategory.SUPPLY_CHAIN,
                claim=claim,
                observation_type="net_import_reliance",
            )
        )

    country_production = provider.get_latest_country_production(commodity)

    concentration_evidence = _production_concentration_evidence(
        commodity=commodity,
        observations=country_production,
        world_total=world_production,
    )

    if concentration_evidence is not None:
        evidence.append(concentration_evidence)

    critical_status = provider.is_critical_mineral(commodity)

    if critical_status is not None:
        source = (
            world_production.source
            if world_production is not None
            else country_production[0].source
            if country_production
            else None
        )

        if source is not None:
            evidence.append(
                Evidence(
                    category=AssessmentCategory.SUPPLY_CHAIN,
                    claim=f"USGS 2025 critical-mineral designation for {commodity}",
                    reported_value=EvidenceValue(value=critical_status),
                    source=source,
                    notes=(
                        "A critical-mineral designation indicates "
                        "strategic supply importance; it is not by "
                        "itself a quantitative measure of scarcity."
                    ),
                    metadata={
                        "commodity": commodity,
                        "observation_type": "critical_mineral_status",
                    },
                )
            )

    return evidence


def _observation_evidence(
    observation: USGSCommodityObservation,
    *,
    category: AssessmentCategory,
    claim: str,
    observation_type: str,
) -> Evidence:
    """
    Convert one USGS observation into Evidence.

    Args:
        observation (USGSCommodityObservation):
            The USGS observation to convert.

        category (AssessmentCategory):
            The category of the evidence.

        claim (str):
            The claim associated with the evidence.

        observation_type (str):
            The type of observation being recorded.

    Returns:
        Evidence:
            The evidence object representing the observation.
    """
    reported_value = None

    if observation.value is not None:
        reported_value = EvidenceValue(
            value=observation.value,
            units=observation.units,
        )

    return Evidence(
        category=category,
        claim=claim,
        reported_value=reported_value,
        source=observation.source,
        scope=EvidenceScope(
            country=observation.country,
            effective_date=(None if observation.year is None else _year_start(observation.year)),
        ),
        notes=(f"USGS published value: {observation.raw_value}. {observation.notes or ''}").strip(),
        metadata={
            "commodity": observation.commodity,
            "observation_type": observation_type,
            "raw_value": observation.raw_value,
            "value_qualifier": observation.value_qualifier,
            "raw_year": observation.raw_year,
            "statistic_detail": observation.statistic_detail,
            "is_critical_mineral": observation.is_critical_mineral,
        },
    )


def _production_concentration_evidence(
    *,
    commodity: str,
    observations: list[USGSCommodityObservation],
    world_total: USGSCommodityObservation | None,
) -> Evidence | None:
    """
    Calculate the leading country's share of world production.

    This is a simple concentration indicator for the prototype.

    Args:
        commodity (str):
            The commodity for which the concentration is being calculated.

        observations (list[USGSCommodityObservation]):
            A list of USGS observations for different countries.

        world_total (USGSCommodityObservation | None):
            The USGS observation representing the world total production.

    Returns:
        Evidence | None:
            The evidence object representing the leading country's share of
            world production, or None if the calculation cannot be performed.
    """
    if (
        not observations
        or world_total is None
        or world_total.value is None
        or world_total.value <= 0
    ):
        return None

    usable = [
        observation
        for observation in observations
        if observation.value is not None and observation.value >= 0
    ]

    if not usable:
        return None

    leading = max(
        usable,
        key=lambda observation: observation.value if observation.value is not None else -1,
    )

    if leading.value is None:
        return None

    share = leading.value / world_total.value * 100

    return Evidence(
        category=AssessmentCategory.SUPPLY_CHAIN,
        claim=(f"Largest national share of reported world production for {commodity}"),
        reported_value=EvidenceValue(value=share, units="%"),
        source=world_total.source,
        scope=EvidenceScope(
            country=leading.country,
            effective_date=(None if world_total.year is None else _year_start(world_total.year)),
        ),
        notes=(
            f"{leading.country} reported {leading.raw_value} "
            f"{leading.units or ''} versus a reported world total of "
            f"{world_total.raw_value} {world_total.units or ''}. "
            "SyntheScale calculated the share from these values."
        ),
        metadata={
            "commodity": commodity,
            "country": leading.country,
            "observation_type": "largest_country_production_share",
            "world_total_raw_value": world_total.raw_value,
            "country_raw_value": leading.raw_value,
        },
    )


def _year_start(year: int):
    """Return January 1 of a reporting year."""
    return date(year, 1, 1)


def _short_statistic_detail(detail: str | None) -> str | None:
    """Remove redundant USGS statistic prefixes for display."""
    if detail is None:
        return None

    prefix = "Net import reliance as a percentage of apparent consumption:"

    if detail.startswith(prefix):
        return detail.removeprefix(prefix).strip()

    return detail
