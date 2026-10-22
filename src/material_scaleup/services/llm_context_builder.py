# src/material_scaleup/services/llm_context_builder.py

import re
from collections import defaultdict
from datetime import date
from typing import Any

from material_scaleup.models.categories import AssessmentCategory
from material_scaleup.models.context import AssessmentContext
from material_scaleup.models.evidence import Evidence
from material_scaleup.models.llm_context import (
    ChemicalSafetySummary,
    CommodityImportReliance,
    CommodityMarketSummary,
    CommoditySupplySummary,
    LLMChemicalInput,
    LLMContext,
    LLMScenarioSummary,
    LLMSource,
)
from material_scaleup.models.source import Source

__all__ = [
    "build_llm_context",
]


_HAZARD_STATEMENT_PATTERN = re.compile(
    r"^(H\d{3})"
    r"(?:\s*\([^)]*\))?"
    r"\s*:\s*"
    r"(.+?)"
    r"(?:\s*\[[^\]]+\])?"
    r"$",
    flags=re.IGNORECASE,
)


def build_llm_context(context: AssessmentContext) -> LLMContext:
    """
    Create compact language-model context from full evidence.

    Args:
        context (AssessmentContext):
            The full assessment context containing scenario, evidence,
            assumptions, and data gaps.

    Returns:
        LLMContext:
            A compact language-model context derived from the full evidence.
    """

    safety = _build_safety_summaries(context.evidence)

    formulas = _scenario_chemical_formulas(context)

    for summary in safety:
        summary.formula = formulas.get(
            summary.chemical.casefold(),
            summary.formula,
        )

    return LLMContext(
        scenario=_build_scenario_summary(context),
        safety=safety,
        markets=_build_market_summaries(context.evidence),
        supply=_build_supply_summaries(context.evidence),
        trade_availability=[
            result.model_copy(
                update={
                    "observations": [],
                    "years": [
                        year.model_copy(update={"partners": year.partners[:3]})
                        for year in result.years
                    ],
                }
            )
            for result in context.trade_availability
        ],
        assumptions=_deduplicate(context.assumptions),
        data_gaps=_deduplicate(context.data_gaps),
    )


def _scenario_chemical_formulas(context: AssessmentContext) -> dict[str, str]:
    """
    Map scenario chemical names to formulas.

    Args:
        context (AssessmentContext):
            The full assessment context containing the scenario.

    Returns:
        dict[str, str]:
            A mapping from chemical names (case-insensitive) to their formulas.
    """

    route = context.scenario.synthesis_route

    if route is None:
        return {}

    result: dict[str, str] = {}

    for process_input in route.inputs:
        chemical = process_input.chemical

        if chemical.name and chemical.formula:
            result[chemical.name.casefold()] = chemical.formula

    return result


def _build_scenario_summary(context: AssessmentContext) -> LLMScenarioSummary:
    """
    Create a compact summary of the assessment scenario.

    Args:
        context (AssessmentContext):
            The full assessment context containing scenario, evidence,
            assumptions, and data gaps.

    Returns:
        LLMScenarioSummary:
            A compact summary of the assessment scenario.
    """

    scenario = context.scenario

    application = None

    if scenario.application is not None:
        application = scenario.application.name

    location = None

    if scenario.production_location is not None:
        location_parts = [
            scenario.production_location.locality,
            scenario.production_location.region,
            scenario.production_location.country,
        ]

        location = ", ".join(part for part in location_parts if part) or None

    target_amount = None
    target_units = None
    target_period = None

    if scenario.production_target is not None:
        target_amount = scenario.production_target.amount
        target_units = scenario.production_target.units
        target_period = scenario.production_target.period

    route_name = None
    chemical_inputs: list[LLMChemicalInput] = []

    if scenario.synthesis_route is not None:
        route_name = scenario.synthesis_route.name

        for process_input in scenario.synthesis_route.inputs:
            chemical = process_input.chemical

            chemical_inputs.append(
                LLMChemicalInput(
                    name=_chemical_label(chemical),
                    formula=chemical.formula,
                    role=process_input.role,
                    amount=process_input.amount,
                    units=process_input.units,
                )
            )

    return LLMScenarioSummary(
        material_name=scenario.material.name,
        material_description=scenario.material.description,
        application=application,
        production_location=location,
        production_target_amount=target_amount,
        production_target_units=target_units,
        production_target_period=target_period,
        synthesis_route=route_name,
        chemical_inputs=chemical_inputs,
    )


def _build_safety_summaries(
    evidence: list[Evidence],
) -> list[ChemicalSafetySummary]:
    """
    Group and deduplicate PubChem safety evidence by chemical.

    Args:
        evidence (list[Evidence]):
            A list of safety evidence items to be grouped and summarized.

    Returns:
        list[ChemicalSafetySummary]:
            A list of compact safety summaries for each chemical.
    """

    grouped: dict[str, list[Evidence]] = defaultdict(list)

    for item in evidence:
        if item.category != AssessmentCategory.SAFETY:
            continue

        chemical = _metadata_string(item, "chemical")

        if chemical is None:
            continue

        grouped[chemical].append(item)

    summaries: list[ChemicalSafetySummary] = []

    for chemical, records in sorted(grouped.items()):
        signal_words: set[str] = set()
        pictograms: set[str] = set()
        hazard_statements: dict[str, str] = {}
        uncoded_statements: set[str] = set()
        sources: list[LLMSource] = []

        formula = _scenario_formula_for_chemical(chemical, records)

        pubchem_cid = _metadata_int(records[0], "pubchem_cid")

        for item in records:
            value = _evidence_value(item)

            if value is None:
                continue

            claim = item.claim.casefold()

            if "signal word" in claim:
                signal_words.add(value)

            elif "pictogram" in claim:
                pictograms.add(value)

            elif "hazard statement" in claim:
                normalized = _normalize_hazard_statement(value)

                if normalized is None:
                    continue

                hazard_code, statement = normalized

                if hazard_code is None:
                    uncoded_statements.add(statement)
                else:
                    hazard_statements[hazard_code] = statement

            if item.source is not None:
                sources.append(_compact_source(item.source))

        combined_hazards = [hazard_statements[code] for code in sorted(hazard_statements)]

        combined_hazards.extend(sorted(uncoded_statements))

        summaries.append(
            ChemicalSafetySummary(
                chemical=chemical,
                formula=formula,
                pubchem_cid=pubchem_cid,
                signal_words=sorted(signal_words),
                pictograms=sorted(pictograms),
                hazard_statements=combined_hazards,
                sources=_deduplicate_sources(sources),
            )
        )

    return summaries


def _build_market_summaries(
    evidence: list[Evidence],
) -> list[CommodityMarketSummary]:
    """
    Group World Bank market evidence by commodity.

    Args:
        evidence (list[Evidence]):
            A list of market evidence items to be grouped and summarized.

    Returns:
        list[CommodityMarketSummary]:
            A list of compact market summaries for each commodity.
    """

    grouped: dict[str, list[Evidence]] = defaultdict(list)

    for item in evidence:
        observation_type = _metadata_string(item, "observation_type")

        if observation_type not in {
            "latest_price",
            "price_change",
            "annualized_volatility",
        }:
            continue

        commodity = _metadata_string(item, "commodity")

        if commodity is not None:
            grouped[commodity].append(item)

    summaries: list[CommodityMarketSummary] = []

    for commodity, records in sorted(grouped.items()):
        values: dict[str, Evidence] = {}
        sources: list[LLMSource] = []

        for item in records:
            observation_type = _metadata_string(item, "observation_type")

            if observation_type is not None:
                values[observation_type] = item

            if item.source is not None:
                sources.append(_compact_source(item.source))

        latest = values.get("latest_price")
        change = values.get("price_change")
        volatility = values.get("annualized_volatility")

        latest_price, latest_units = _numeric_evidence_value(latest)
        change_value, _ = _numeric_evidence_value(change)
        volatility_value, _ = _numeric_evidence_value(volatility)

        period_source = volatility or change

        summaries.append(
            CommodityMarketSummary(
                commodity=commodity,
                latest_price=latest_price,
                latest_price_units=latest_units,
                latest_price_date=_scope_effective_date(latest),
                analysis_period_start=_scope_period_start(period_source),
                analysis_period_end=_scope_period_end(period_source),
                number_of_observations=_metadata_int(
                    period_source,
                    "number_of_observations",
                ),
                price_change_percent=(None if change_value is None else round(change_value, 2)),
                annualized_volatility_percent=(
                    None if volatility_value is None else round(volatility_value, 2)
                ),
                sources=_deduplicate_sources(sources),
            )
        )

    return summaries


def _build_supply_summaries(
    evidence: list[Evidence],
) -> list[CommoditySupplySummary]:
    """
    Group USGS availability and supply evidence by commodity.

    Args:
        evidence (list[Evidence]):
            A list of supply evidence items to be grouped and summarized.

    Returns:
        list[CommoditySupplySummary]:
            A list of compact supply summaries for each commodity.
    """

    supported_types = {
        "world_production",
        "world_reserves",
        "net_import_reliance",
        "largest_country_production_share",
        "critical_mineral_status",
    }

    grouped: dict[str, list[Evidence]] = defaultdict(list)

    for item in evidence:
        observation_type = _metadata_string(item, "observation_type")

        if observation_type not in supported_types:
            continue

        commodity = _metadata_string(item, "commodity")

        if commodity is not None:
            grouped[commodity].append(item)

    summaries: list[CommoditySupplySummary] = []

    for commodity, records in sorted(grouped.items()):
        world_production = None
        world_reserves = None
        production_concentration = None
        critical_status = None

        import_reliance: list[CommodityImportReliance] = []

        sources: list[LLMSource] = []

        for item in records:
            observation_type = _metadata_string(item, "observation_type")

            if observation_type == "world_production":
                world_production = item

            elif observation_type == "world_reserves":
                world_reserves = item

            elif observation_type == "largest_country_production_share":
                production_concentration = item

            elif observation_type == "critical_mineral_status":
                critical_status = item

            elif observation_type == "net_import_reliance":
                value, units = _numeric_evidence_value(item)

                import_reliance.append(
                    CommodityImportReliance(
                        detail=_short_statistic_detail(_metadata_string(item, "statistic_detail")),
                        value=value,
                        value_qualifier=_metadata_string(item, "value_qualifier"),
                        raw_value=_metadata_string(item, "raw_value") or "",
                        units=units,
                        year=_metadata_string(item, "raw_year"),
                    )
                )

            if item.source is not None:
                sources.append(_compact_source(item.source))

        production_value, production_units = _numeric_evidence_value(world_production)

        reserves_value, reserves_units = _numeric_evidence_value(world_reserves)

        concentration_value, _ = _numeric_evidence_value(production_concentration)

        critical_value = _boolean_evidence_value(critical_status)

        summaries.append(
            CommoditySupplySummary(
                commodity=commodity,
                world_production=production_value,
                world_production_units=production_units,
                world_production_raw_value=(_metadata_string(world_production, "raw_value")),
                world_reserves=reserves_value,
                world_reserves_units=reserves_units,
                world_reserves_raw_value=(_metadata_string(world_reserves, "raw_value")),
                leading_producer=(_metadata_string(production_concentration, "country")),
                leading_producer_share_percent=(
                    None if concentration_value is None else round(concentration_value, 2)
                ),
                import_reliance=import_reliance,
                is_us_critical_mineral=critical_value,
                sources=_deduplicate_sources(sources),
            )
        )

    return summaries


def _normalize_hazard_statement(value: str) -> tuple[str | None, str] | None:
    """
    Normalize PubChem hazard statements.

    Percentage annotations and bracketed classification details are
    removed so repeated records collapse to one H-code statement.

    Args:
        value (str):
            The raw hazard statement text to be normalized.

    Returns:
        tuple[str | None, str] | None:
            A tuple containing the normalized hazard code and description,
            or None if the statement should be skipped.
    """

    cleaned = " ".join(value.split())

    match = _HAZARD_STATEMENT_PATTERN.match(cleaned)

    if match is not None:
        code = match.group(1).upper()
        description = match.group(2).strip()

        return code, f"{code}: {description}"

    if cleaned.casefold() == "not classified":
        return None, "Not classified under the reported GHS data"

    # Skip long contributor-reporting commentary. It remains available
    # in the authoritative AssessmentContext.
    if "reported as not meeting ghs hazard criteria" in cleaned.casefold():
        return None

    return None, cleaned


def _evidence_value(evidence: Evidence) -> str | None:
    """
    Return an evidence value as text.

    Args:
        evidence (Evidence):
            The evidence item from which to extract the value.

    Returns:
        str | None:
            The evidence value as a stripped string, or None if not available.
    """

    if evidence.reported_value is None:
        return None

    value = evidence.reported_value.value

    if isinstance(value, str):
        return value.strip() or None

    return str(value)


def _numeric_evidence_value(
    evidence: Evidence | None,
) -> tuple[float | None, str | None]:
    """
    Return numeric evidence value and units.

    Args:
        evidence (Evidence | None):
            The evidence item from which to extract the numeric value and units.

    Returns:
        tuple[float | None, str | None]:
            A tuple containing the numeric value (or None if not available)
            and the associated units (or None if not available).
    """

    if evidence is None or evidence.reported_value is None:
        return None, None

    value = evidence.reported_value.value

    if isinstance(value, bool):
        return None, evidence.reported_value.units

    if isinstance(value, int | float):
        return float(value), evidence.reported_value.units

    return None, evidence.reported_value.units


def _boolean_evidence_value(evidence: Evidence | None) -> bool | None:
    """
    Return a Boolean evidence value.

    Args:
        evidence (Evidence | None):
            The evidence item from which to extract the Boolean value.

    Returns:
        bool | None:
            The Boolean evidence value, or None if not available.
    """

    if evidence is None or evidence.reported_value is None:
        return None

    value = evidence.reported_value.value

    return value if isinstance(value, bool) else None


def _metadata_string(evidence: Evidence | None, key: str) -> str | None:
    """
    Return a metadata value as a string.

    Args:
        evidence (Evidence | None):
            The evidence item from which to extract the metadata value.
        key (str):
            The key of the metadata item to retrieve.

    Returns:
        str | None:
            The metadata value as a stripped string, or None if not available.
    """

    if evidence is None:
        return None

    value = evidence.metadata.get(key)

    if value is None:
        return None

    text = str(value).strip()

    return text or None


def _metadata_int(evidence: Evidence | None, key: str) -> int | None:
    """
    Return an integer metadata value.

    Args:
        evidence (Evidence | None):
            The evidence item from which to extract the metadata value.
        key (str):
            The key of the metadata item to retrieve.

    Returns:
        int | None:
            The metadata value as an integer, or None if not available
            or not an integer.
    """

    if evidence is None:
        return None

    value = evidence.metadata.get(key)

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float) and value.is_integer():
        return int(value)

    return None


def _scope_effective_date(evidence: Evidence | None) -> date | None:
    """
    Return the effective date of the scope associated with the evidence.

    Args:
        evidence (Evidence | None):
            The evidence item from which to extract the scope effective date.

    Returns:
        date | None:
            The effective date of the scope, or None if not available.
    """

    if evidence is None or evidence.scope is None:
        return None

    return evidence.scope.effective_date


def _scope_period_start(evidence: Evidence | None) -> date | None:
    """
    Return the start date of the period associated with the scope of the evidence.

    Args:
        evidence (Evidence | None):
            The evidence item from which to extract the scope period start date.

    Returns:
        date | None:
            The start date of the scope period, or None if not available.
    """

    if evidence is None or evidence.scope is None:
        return None

    return evidence.scope.period_start


def _scope_period_end(evidence: Evidence | None) -> date | None:
    """
    Return the end date of the period associated with the scope of the evidence.

    Args:
        evidence (Evidence | None):
            The evidence item from which to extract the scope period end date.

    Returns:
        date | None:
            The end date of the scope period, or None if not available.
    """

    if evidence is None or evidence.scope is None:
        return None

    return evidence.scope.period_end


def _compact_source(source: Source) -> LLMSource:
    """
    Convert a provenance source into a compact citation.

    Args:
        source (Source):
            The provenance source to convert.

    Returns:
        LLMSource:
            The compact citation representation of the source.
    """

    return LLMSource(
        name=source.name,
        publisher=source.publisher,
        url=source.url,
        doi=source.doi,
    )


def _deduplicate_sources(sources: list[LLMSource]) -> list[LLMSource]:
    """
    Deduplicate citations while preserving order.

    Args:
        sources (list[LLMSource]):
            The list of citations to deduplicate.

    Returns:
        list[LLMSource]:
            The deduplicated list of citations, preserving the original order.
    """

    seen: set[tuple[str, str | None, str | None]] = set()
    result: list[LLMSource] = []

    for source in sources:
        key = (source.name, source.url, source.doi)

        if key in seen:
            continue

        seen.add(key)
        result.append(source)

    return result


def _deduplicate(values: list[str]) -> list[str]:
    """
    Deduplicate strings while preserving order.

    Args:
        values (list[str]):
            The list of strings to deduplicate.

    Returns:
        list[str]:
            The deduplicated list of strings, preserving the original order.
    """

    return list(dict.fromkeys(values))


def _chemical_label(chemical: Any) -> str:
    """
    Return a readable label from a ChemicalIdentity-like object.

    Args:
        chemical (Any):
            The chemical identity object from which to extract a label.

    Returns:
        str:
            A human-readable label for the chemical, or "unknown chemical"
            if no label is available.
    """

    return (
        chemical.name
        or chemical.formula
        or chemical.cas_rn
        or chemical.inchikey
        or "unknown chemical"
    )


def _scenario_formula_for_chemical(
    chemical: str,
    records: list[Evidence],
) -> str | None:
    """
    Return a formula when present in evidence metadata.

    Current PubChem safety evidence does not include formula metadata,
    so this remains optional. Scenario input formulas are added later
    by the scenario-enrichment pass.

    Args:
        chemical (str):
            The chemical label for which to find a scenario formula.

        records (list[Evidence]):
            The list of evidence records to search for a formula.

    Returns:
        str | None:
            The formula associated with the chemical in the evidence metadata,
            or None if no formula is found.
    """

    for record in records:
        formula = _metadata_string(record, "formula")

        if formula:
            return formula

    return None


def _short_statistic_detail(detail: str | None) -> str | None:
    """
    Remove a redundant USGS import-reliance prefix.

    Args:
        detail (str | None):
            The detail string potentially containing the redundant prefix.

    Returns:
        str | None:
            The detail string with the redundant prefix removed,
            or None if the detail is empty or only contains the prefix.
    """

    if detail is None:
        return None

    prefix = "Net import reliance as a percentage of apparent consumption:"

    if detail.startswith(prefix):
        return detail.removeprefix(prefix).strip()

    if detail == "Net import reliance as a percentage of apparent consumption":
        return None

    return detail
