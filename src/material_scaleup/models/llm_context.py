
# src/material_scaleup/models/llm_context.py

from datetime import date

from pydantic import BaseModel, Field

__all__ = [
    "ChemicalSafetySummary",
    "CommodityImportReliance",
    "CommodityMarketSummary",
    "CommoditySupplySummary",
    "LLMChemicalInput",
    "LLMContext",
    "LLMScenarioSummary",
    "LLMSource",
]


class LLMSource(BaseModel):
    """
    Compact citation supplied to the language model.
    
    Attributes:
        name (str):
            Compact name of the source.

        publisher (str | None):
            Name of the publisher, if available.

        url (str | None):
            URL of the source, if available.

        doi (str | None):
            DOI of the source, if available.
    """

    name: str
    publisher: str | None = None
    url: str | None = None
    doi: str | None = None


class LLMChemicalInput(BaseModel):
    """
    Compact representation of one synthesis input.

    Attributes:
        name (str):
            Name of the chemical input.

        formula (str | None):
            Chemical formula, if available.

        role (str | None):
            Role of the chemical in the synthesis.

        amount (float | None):
            Amount of the chemical used, if specified.

        units (str | None):
            Units for the amount, if specified.
    """

    name: str
    formula: str | None = None
    role: str | None = None
    amount: float | None = None
    units: str | None = None


class LLMScenarioSummary(BaseModel):
    """
    Compact scenario information relevant to assessment.
    
    Attributes:
        material_name (str):
            Name of the material.

        material_description (str | None):
            Description of the material, if available.

        application (str | None):
            Application of the material, if specified.

        production_location (str | None):
            Location where the material is produced, if specified.

        production_target_amount (float | None):
            Target amount of production, if specified.

        production_target_units (str | None):
            Units for the production target, if specified.

        production_target_period (str | None):
            Time period for the production target, if specified.

        synthesis_route (str | None):
            Description of the synthesis route, if available.

        chemical_inputs (list[LLMChemicalInput]):
            List of chemical inputs for the synthesis.
    """

    material_name: str
    material_description: str | None = None
    application: str | None = None
    production_location: str | None = None
    production_target_amount: float | None = None
    production_target_units: str | None = None
    production_target_period: str | None = None
    synthesis_route: str | None = None
    chemical_inputs: list[LLMChemicalInput] = Field(default_factory=list)


class ChemicalSafetySummary(BaseModel):
    """
    Deduplicated safety information for one chemical.
    
    Attributes:
        chemical (str):
            Name of the chemical.

        formula (str | None):
            Chemical formula, if available.

        pubchem_cid (int | None):
            PubChem CID for the chemical, if available.

        signal_words (list[str]):
            List of signal words associated with the chemical's safety.

        pictograms (list[str]):
            List of pictograms associated with the chemical's safety.

        hazard_statements (list[str]):
            List of hazard statements associated with the chemical's safety.

        sources (list[LLMSource]):
            List of sources for the safety information.
    """

    chemical: str
    formula: str | None = None
    pubchem_cid: int | None = None
    signal_words: list[str] = Field(default_factory=list)
    pictograms: list[str] = Field(default_factory=list)
    hazard_statements: list[str] = Field(default_factory=list)
    sources: list[LLMSource] = Field(default_factory=list)


class CommodityMarketSummary(BaseModel):
    """
    Commodity-price and volatility information.

    Attributes:
        commodity (str):
            Name of the commodity.

        latest_price (float | None):
            Most recent price of the commodity, if available.

        latest_price_units (str | None):
            Units for the latest price, if specified.

        latest_price_date (date | None):
            Date of the latest price observation, if available.

        analysis_period_start (date | None):
            Start date of the analysis period, if specified.

        analysis_period_end (date | None):
            End date of the analysis period, if specified.

        number_of_observations (int | None):
            Number of observations used in the analysis, if available.

        price_change_percent (float | None):
            Percentage change in price over the analysis period, if available.

        annualized_volatility_percent (float | None):
            Annualized volatility of the commodity's price, if available.

        sources (list[LLMSource]):
            List of sources for the market information.
    """

    commodity: str
    latest_price: float | None = None
    latest_price_units: str | None = None
    latest_price_date: date | None = None
    analysis_period_start: date | None = None
    analysis_period_end: date | None = None
    number_of_observations: int | None = None
    price_change_percent: float | None = None
    annualized_volatility_percent: float | None = None
    sources: list[LLMSource] = Field(default_factory=list)


class CommodityImportReliance(BaseModel):
    """
    One USGS import-reliance statistic.

    Attributes:
        detail (str | None):
            Description of the import-reliance statistic, if available.

        value (float | None):
            Numeric value of the import-reliance statistic, if available.

        value_qualifier (str | None):
            Qualifier for the value, if specified.

        raw_value (str):
            Raw representation of the value.

        units (str | None):
            Units for the value, if specified.

        year (str | None):
            Year of the import-reliance statistic, if available.
    """

    detail: str | None = None
    value: float | None = None
    value_qualifier: str | None = None
    raw_value: str
    units: str | None = None
    year: str | None = None


class CommoditySupplySummary(BaseModel):
    """
    Availability and supply-chain information for one commodity.

    Attributes:
        commodity (str):
            Name of the commodity.

        world_production (float | None):
            Total world production of the commodity, if available.

        world_production_units (str | None):
            Units for the world production value, if specified.

        world_production_raw_value (str | None):
            Raw representation of the world production value.

        world_reserves (float | None):
            Total world reserves of the commodity, if available.

        world_reserves_units (str | None):
            Units for the world reserves value, if specified.

        world_reserves_raw_value (str | None):
            Raw representation of the world reserves value.

        leading_producer (str | None):
            Name of the leading producer of the commodity, if available.

        leading_producer_share_percent (float | None):
            Market share of the leading producer, if available.

        import_reliance (list[CommodityImportReliance]):
            List of import-reliance statistics for the commodity.

        is_us_critical_mineral (bool | None):
            Indicates whether the commodity is considered a US critical mineral.

        sources (list[LLMSource]):
            List of sources for the supply information.
    """

    commodity: str
    world_production: float | None = None
    world_production_units: str | None = None
    world_production_raw_value: str | None = None
    world_reserves: float | None = None
    world_reserves_units: str | None = None
    world_reserves_raw_value: str | None = None
    leading_producer: str | None = None
    leading_producer_share_percent: float | None = None
    import_reliance: list[CommodityImportReliance] = Field(default_factory=list)
    is_us_critical_mineral: bool | None = None
    sources: list[LLMSource] = Field(default_factory=list)


class LLMContext(BaseModel):
    """
    Compact, decision-relevant context supplied to the language model.

    The complete AssessmentContext remains the authoritative provenance
    record. This model intentionally removes repeated and low-value data.

    Attributes:
        scenario (LLMScenarioSummary):
            Summary of the scenario being evaluated.

        safety (list[ChemicalSafetySummary]):
            List of chemical safety summaries relevant to the scenario.

        markets (list[CommodityMarketSummary]):
            List of commodity market summaries relevant to the scenario.

        supply (list[CommoditySupplySummary]):
            List of commodity supply summaries relevant to the scenario.

        assumptions (list[str]):
            List of assumptions made in the context.

        data_gaps (list[str]):
            List of identified data gaps in the context.
    """

    scenario: LLMScenarioSummary
    safety: list[ChemicalSafetySummary] = Field(default_factory=list)
    markets: list[CommodityMarketSummary] = Field(default_factory=list)
    supply: list[CommoditySupplySummary] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
