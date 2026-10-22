from datetime import UTC, date, datetime

from material_scaleup.models.chemical import ChemicalIdentity
from material_scaleup.models.domestic import DomesticProductionResult
from material_scaleup.providers.usgs import USGSCommodityProvider
from material_scaleup.resolvers.commodity import CuratedCommodityResolver

DOMESTIC_LIMITATION = (
    "USGS observations describe upstream commodities, not verified production, capacity, "
    "inventory or availability of the requested precursor/grade. Direct material production "
    "has not been checked. Missing, withheld or zero records do not establish material scarcity. "
    "Production series may overlap; do not sum them or combine them with precursor trade "
    "to calculate import dependence. No domestic-availability risk score is calculated."
)

# Exact aliases only: never fuzzy-match countries or map territories to parent states.
COUNTRY_ALIASES = {
    "usa": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "russian federation": "Russia",
}


class DomesticProductionService:
    def __init__(
        self,
        provider: USGSCommodityProvider | None,
        *,
        source_error: str | None = None,
    ) -> None:
        self.provider = provider
        self.source_error = source_error

    def lookup(self, chemical: ChemicalIdentity, country: str) -> DomesticProductionResult:
        result = DomesticProductionResult(
            material=chemical.name or chemical.cas_rn or chemical.formula or "Unnamed material",
            requested_country=country,
            checked_at=datetime.now(UTC),
            status="not_checked",
            limitations=[DOMESTIC_LIMITATION],
        )
        if self.source_error:
            result.status = "error"
            result.limitations.append(self.source_error)
            return result
        if self.provider is None:
            result.limitations.append(
                "Optional USGS dataset is missing; run python scripts/download_data.py --usgs."
            )
            return result
        exposures = CuratedCommodityResolver().resolve(chemical)
        result.upstream_commodities = sorted({item.commodity for item in exposures})
        if not exposures:
            result.limitations.append(
                "No reviewed upstream USGS commodity mapping for this material."
            )
            return result
        source_country = COUNTRY_ALIASES.get(country.strip().casefold(), country.strip())
        if source_country.casefold() in {"world", "world total", "other countries"}:
            result.limitations.append("An individual country is required, not an aggregate.")
            return result
        result.source_country = source_country
        for commodity in result.upstream_commodities:
            # Domestic evidence uses exact curated aliases, not fuzzy commodity substitutions.
            source_commodity = self.provider.COMMODITY_ALIASES.get(commodity)
            if source_commodity is None:
                result.limitations.append(f"No reviewed USGS production mapping for {commodity}.")
                continue
            result.status = "not_available"
            records = self.provider.get_records(
                source_commodity, statistic="Production", country=source_country
            )
            eligible = [
                record
                for record in records
                if record.year is not None and record.year < date.today().year
            ]
            if not eligible:
                result.limitations.append(
                    f"No completed-year {source_commodity} production records found for "
                    f"{source_country}; this is not evidence of zero production."
                )
                continue
            latest = max(record.year for record in eligible if record.year is not None)
            latest_records = [record for record in eligible if record.year == latest]
            result.observations.extend(latest_records)
            if latest < date.today().year - 1:
                result.limitations.append(
                    f"{source_commodity}: latest country observation is {latest}; "
                    "it does not describe current production."
                )
            if any(record.value is None for record in latest_records):
                result.limitations.append(
                    f"{source_commodity}: some production values are withheld/non-numeric; "
                    "consult the raw published values and notes."
                )
        if any(record.value is not None for record in result.observations):
            result.status = "available"
        return result
