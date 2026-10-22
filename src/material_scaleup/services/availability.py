from datetime import UTC, date, datetime

from material_scaleup.calculations.trade import summarize_trade_year
from material_scaleup.models.source import Source
from material_scaleup.models.trade import AvailabilityResult, TradeCountry, TradeMatch, TradeYear
from material_scaleup.providers.comtrade import ComtradeError, ComtradeProvider

TRADE_LIMITATIONS = (
    "Historical trade is not live inventory, spare capacity or verified exact-grade availability. "
    "Low imports may reflect domestic production. Import unit values are not supplier quotations "
    "or delivered procurement costs. Domestic supply, restrictions and logistics were not checked. "
    "Do not assign a numerical availability or supply-chain score from these pilot indicators."
)


class AvailabilityService:
    def __init__(self, provider: ComtradeProvider) -> None:
        self.provider = provider

    def lookup(
        self, country: TradeCountry, match: TradeMatch, *, confirmed: bool = False
    ) -> AvailabilityResult:
        if match.requires_confirmation and not confirmed:
            raise ValueError("Confirm the trade-category candidate before retrieving its evidence.")
        lookup_time = datetime.now(UTC)
        result = AvailabilityResult(
            country=country,
            match=match,
            confirmed=confirmed,
            status="insufficient_data",
            retrieved_at=lookup_time,
            source=Source(
                name="UN Comtrade annual imports (reported HS; revision varies)",
                publisher="United Nations Statistics Division",
                url="https://comtradeplus.un.org/",
                accessed_at=lookup_time,
            ),
            data_gaps=[TRADE_LIMITATIONS],
        )
        try:
            years = self.provider.available_years(country)
        except ComtradeError as error:
            result.status = "error"
            result.data_gaps.append(str(error))
            return result
        if not years:
            result.data_gaps.append(
                "No completed annual reporting periods are available for the HS query."
            )
            return result
        if len(years) < 5:
            result.data_gaps.append(
                f"Only {len(years)} of five requested annual periods are available."
            )
        missing = sorted(set(range(min(years), date.today().year)) - set(years))
        if missing:
            result.data_gaps.append(
                f"Unreported/unselected years through last calendar year: {missing}."
            )
        failures = 0
        for year in years:
            try:
                observations = self.provider.observations(country, match.product, year)
            except ComtradeError as error:
                failures += 1
                result.years.append(
                    TradeYear(year=year, status="error", warnings=[str(error)])
                )
                continue
            result.observations.extend(observations)
            summary = summarize_trade_year(year, observations)
            summary.reported_classifications = sorted(
                {
                    row.reported_classification
                    for row in observations
                    if row.reported_classification
                }
            )
            summary.classification_matches_catalog = bool(observations) and all(
                row.reported_classification == match.product.classification for row in observations
            )
            if not summary.classification_matches_catalog:
                warning = (
                    "HS query results are not verified against the selected "
                    "HS2022 catalog category. "
                    "Returned revision(s): "
                    f"{', '.join(summary.reported_classifications) or 'not provided'}. "
                    "Product-code equivalence across revisions is not established; "
                    "these indicators describe the returned trade code, "
                    "not verified material supply."
                )
                summary.warnings.append(warning)
                result.data_gaps.append(f"{year}: {warning}")
            result.years.append(summary)
        usable = [row for row in result.years if row.status == "available"]
        if failures == len(years):
            result.status = "error"
        elif usable:
            result.status = "available"
        elif all(row.status == "no_reported_trade" for row in result.years):
            result.status = "no_reported_trade"
        else:
            result.status = "insufficient_data"
        if any(row.status in ("insufficient_data", "error") for row in result.years):
            result.data_gaps.append("Some requested annual results are incomplete or failed.")
        chronological = sorted(result.years, key=lambda row: row.year)
        if len(chronological) >= 2:
            first, last = chronological[0], chronological[-1]
            if (
                first.import_value_usd is not None
                and first.import_value_usd > 0
                and last.import_value_usd is not None
                and all(row.classification_matches_catalog for row in chronological)
            ):
                result.value_change_percent = (
                    last.import_value_usd / first.import_value_usd - 1
                ) * 100
                result.trend_period = f"{first.year}-{last.year} (nominal USD, not quantity)"
            elif not all(row.classification_matches_catalog for row in chronological):
                result.data_gaps.append(
                    "Cross-year trend withheld: classification equivalence is not verified."
                )
        return result
