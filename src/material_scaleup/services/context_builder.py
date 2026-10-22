# src/material_scaleup/services/context_builder.py

from datetime import date

from material_scaleup.calculations.market_evidence import (
    commodity_market_evidence,
)
from material_scaleup.calculations.supply_evidence import (
    usgs_supply_evidence,
)
from material_scaleup.models.categories import AssessmentCategory
from material_scaleup.models.context import AssessmentContext
from material_scaleup.models.evidence import Evidence, EvidenceScope, EvidenceValue
from material_scaleup.models.scenario import ScaleUpScenario
from material_scaleup.models.trade import AvailabilityResult
from material_scaleup.providers.pubchem_safety import PubChemSafetyProvider
from material_scaleup.providers.usgs import USGSCommodityProvider
from material_scaleup.providers.world_bank import WorldBankCommodityProvider
from material_scaleup.resolvers.commodity import CommodityResolver

__all__ = [
    "AssessmentContextBuilder",
]


class AssessmentContextBuilder:
    """Assemble source-grounded evidence for a scale-up scenario."""

    # Non-commodity inputs that should be excluded from commodity-based
    # assessments. This can be expanded to include other non-commodity inputs
    # as needed.
    NON_COMMODITY_INPUTS = {
        "water",
    }

    def __init__(
        self,
        *,
        commodity_resolver: CommodityResolver,
        safety_provider: PubChemSafetyProvider,
        world_bank_provider: WorldBankCommodityProvider,
        usgs_provider: USGSCommodityProvider,
        market_history_months: int = 60,
    ) -> None:
        self.commodity_resolver = commodity_resolver
        self.safety_provider = safety_provider
        self.world_bank_provider = world_bank_provider
        self.usgs_provider = usgs_provider
        self.market_history_months = market_history_months

    def build(
        self,
        scenario: ScaleUpScenario,
        *,
        trade_availability: list[AvailabilityResult] | None = None,
    ) -> AssessmentContext:
        """
        Build the complete assessment context.

        Args:
            scenario (ScaleUpScenario):
                The scale-up scenario for which to build the assessment context.

            trade_availability (list[AvailabilityResult] | None):
                Previously retrieved, confirmed country/input trade evidence.

        Returns:
            AssessmentContext:
                The assembled assessment context containing evidence, assumptions,
                and data gaps.
        """

        evidence: list[Evidence] = []
        assumptions: list[str] = []
        data_gaps: list[str] = []
        trade_results = trade_availability or []
        route_inputs = scenario.synthesis_route.inputs if scenario.synthesis_route else []
        route_names = {
            name.strip().casefold()
            for process_input in route_inputs
            for name in (
                process_input.chemical.name,
                process_input.chemical.cas_rn,
                *process_input.chemical.synonyms,
            )
            if name
        }
        for result in trade_results:
            if (
                scenario.production_location is None
                or scenario.production_location.country != result.country.name
            ):
                raise ValueError("Trade evidence country must match the production country.")
            if result.match.requires_confirmation and not result.confirmed:
                raise ValueError("Trade evidence requires confirmed product classification.")
            if result.match.requested_material.strip().casefold() not in route_names:
                raise ValueError("Trade evidence material must match a synthesis input.")
            data_gaps.extend(result.data_gaps)
            for year in result.years:
                for field, value, units, category in (
                    (
                        "import_value_usd",
                        year.import_value_usd,
                        "USD",
                        AssessmentCategory.AVAILABILITY,
                    ),
                    (
                        "largest_partner_share_percent",
                        year.largest_partner_share_percent,
                        "%",
                        AssessmentCategory.SUPPLY_CHAIN,
                    ),
                    (
                        "unit_value_usd_per_kg",
                        year.unit_value_usd_per_kg,
                        "USD/kg",
                        AssessmentCategory.COST,
                    ),
                ):
                    if value is None:
                        continue
                    evidence.append(
                        Evidence(
                            category=category,
                            claim=(
                                f"{result.match.requested_material}: {field} for "
                                f"HS code {result.match.product.code}, {year.year}; "
                                "reported revision "
                                f"{', '.join(year.reported_classifications) or 'unverified'}"
                            ),
                            reported_value=EvidenceValue(value=value, units=units),
                            source=result.source,
                            scope=EvidenceScope(
                                country=result.country.name,
                                period_start=date(year.year, 1, 1),
                                period_end=date(year.year, 12, 31),
                            ),
                            notes=" ".join([result.match.reason, *year.warnings]),
                            metadata={
                                "observation_type": f"trade_{field}",
                                "material": result.match.requested_material,
                                "hs_code": result.match.product.code,
                                "catalog_classification": result.match.product.classification,
                                "query_classification": result.query_classification,
                                "reported_classifications":
                                    ", ".join(year.reported_classifications) or None,
                                "classification_matches_catalog": (
                                    year.classification_matches_catalog
                                ),
                                "match_relationship": result.match.relationship,
                                "year": year.year,
                            },
                        )
                    )

        # Safety evidence originates at the individual chemical level.
        evidence.extend(self.safety_provider.get_evidence(scenario))

        route = scenario.synthesis_route

        if route is None:
            data_gaps.append(
                "No synthesis route was provided, so raw-material "
                "commodity exposures could not be assessed."
            )

            return AssessmentContext(
                scenario=scenario,
                evidence=evidence,
                assumptions=assumptions,
                data_gaps=data_gaps,
                trade_availability=trade_results,
            )

        assessed_commodities: set[str] = set()

        for process_input in route.inputs:
            chemical = process_input.chemical

            exposures = self.commodity_resolver.resolve(chemical)

            if not exposures:
                chemical_label = (
                    chemical.name or chemical.formula or chemical.cas_rn or "unknown chemical"
                )

                if chemical_label.casefold() in self.NON_COMMODITY_INPUTS:
                    continue

                data_gaps.append(
                    f"No underlying commodity exposure could be resolved for {chemical_label}."
                )

                continue

            for exposure in exposures:
                commodity = exposure.commodity

                # Avoid repeatedly analyzing the same commodity when
                # several process inputs map to it.
                if commodity in assessed_commodities:
                    continue

                assessed_commodities.add(commodity)

                self._add_world_bank_evidence(
                    commodity=commodity,
                    evidence=evidence,
                    data_gaps=data_gaps,
                )

                self._add_usgs_evidence(
                    commodity=commodity,
                    evidence=evidence,
                    data_gaps=data_gaps,
                )

        assumptions.append(
            "Commodity-market prices represent upstream market "
            "exposure and are not direct purchase prices for "
            "specific chemical precursors."
        )

        assumptions.append(
            "Chemical-to-commodity exposures use curated prototype mappings, "
            "not a complete chemical-to-commodity ontology. Provider commodity "
            "names use curated aliases, exact catalog lookup, and conservative "
            "lexical matching; name similarity does not establish chemical equivalence."
        )

        return AssessmentContext(
            scenario=scenario,
            evidence=evidence,
            assumptions=assumptions,
            data_gaps=self._deduplicate(data_gaps),
            trade_availability=trade_results,
        )

    def _add_world_bank_evidence(
        self,
        *,
        commodity: str,
        evidence: list[Evidence],
        data_gaps: list[str],
    ) -> None:
        """
        Add World Bank price and volatility evidence.

        Args:
            commodity (str):
                The name of the commodity for which to add World Bank evidence.

            evidence (list[Evidence]):
                The list to which World Bank evidence will be appended.

            data_gaps (list[str]):
                The list to which data gap messages will be appended.
        """

        provider_name = self.world_bank_provider.resolve_commodity_name(commodity)

        if provider_name is None:
            data_gaps.append(f"No World Bank commodity-price series is mapped for {commodity}.")
            return

        try:
            history = self.world_bank_provider.get_price_history(
                provider_name,
                months=self.market_history_months,
            )

        except LookupError:
            data_gaps.append(f"World Bank commodity-price data were not found for {commodity}.")
            return

        evidence.extend(commodity_market_evidence(history))

    def _add_usgs_evidence(
        self,
        *,
        commodity: str,
        evidence: list[Evidence],
        data_gaps: list[str],
    ) -> None:
        """Add USGS availability and supply-chain evidence."""

        provider_name = self.usgs_provider.resolve_commodity_name(commodity)

        if provider_name is None:
            data_gaps.append(f"No USGS commodity mapping is available for {commodity}.")
            return

        commodity_evidence = usgs_supply_evidence(
            self.usgs_provider,
            provider_name,
        )

        if not commodity_evidence:
            data_gaps.append(f"USGS supply-chain data were not found for {commodity}.")
            return

        evidence.extend(commodity_evidence)

    @staticmethod
    def _deduplicate(values: list[str]) -> list[str]:
        """Deduplicate strings while preserving order."""
        return list(dict.fromkeys(values))
