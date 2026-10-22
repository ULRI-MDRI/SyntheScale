
# app.py

from pathlib import Path

import pandas as pd
import streamlit as st

from material_scaleup.models.categories import (
    AssessmentStatus,
    RouteOrigin,
)
from material_scaleup.models.chemical import MaterialSpec
from material_scaleup.models.generated_assessment import (
    GeneratedAssessment,
)
from material_scaleup.models.scenario import (
    LocationSpec,
    ProcessInput,
    ProductionTarget,
    ScaleUpScenario,
    SynthesisRoute,
)
from material_scaleup.providers.comtrade import ComtradeError
from material_scaleup.providers.pubchem import ChemicalNotFoundError, PubChemProvider
from material_scaleup.providers.pubchem_safety import (
    PubChemSafetyProvider,
)
from material_scaleup.providers.usgs import USGSCommodityProvider
from material_scaleup.providers.world_bank import (
    WorldBankCommodityProvider,
)
from material_scaleup.resolvers.commodity import (
    CuratedCommodityResolver,
)
from material_scaleup.services.context_builder import (
    AssessmentContextBuilder,
)
from material_scaleup.services.llm_context_builder import (
    build_llm_context,
)
from material_scaleup.ui.availability import (
    render_availability_lookup,
    render_domestic_production,
    render_trade_results,
    render_trade_selection,
    select_country,
    trade_catalogs,
)

REPOSITORY_ROOT = Path(__file__).resolve().parent

WORLD_BANK_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "raw"
    / "world_bank"
    / "CMO-Historical-Data-Monthly.xlsx"
)

USGS_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "raw"
    / "usgs"
    / "mcs2026"
    / "MCS2026_Commodities_Data.csv"
)


DEFAULT_INPUTS = pd.DataFrame(
    [
        {
            "Chemical": "sodium aluminate",
            "Role": "aluminum source",
        },
        {
            "Chemical": "sodium silicate",
            "Role": "silicon source",
        },
        {
            "Chemical": "sodium hydroxide",
            "Role": "mineralizer",
        },
        {
            "Chemical": "water",
            "Role": "solvent",
        },
    ]
)


def configure_page() -> None:
    """Configure the Streamlit page."""

    st.set_page_config(
        page_title="SyntheScale",
        page_icon="⚗️",
        layout="wide",
    )


@st.cache_resource
def get_identity_provider() -> PubChemProvider:
    """Create and cache the PubChem identity provider."""

    return PubChemProvider()


@st.cache_resource
def get_context_builder() -> AssessmentContextBuilder:
    """Create and cache the evidence context builder."""

    return AssessmentContextBuilder(
        commodity_resolver=CuratedCommodityResolver(),
        safety_provider=PubChemSafetyProvider(),
        world_bank_provider=WorldBankCommodityProvider(
            WORLD_BANK_PATH
        ),
        usgs_provider=USGSCommodityProvider(
            USGS_PATH
        ),
        market_history_months=60,
    )


@st.cache_resource
def get_assessment_generator():
    """Create and cache the configured LLM generator."""

    from material_scaleup.services.openai_client import (
        create_assessment_generator_from_environment,
    )

    return create_assessment_generator_from_environment()


def build_scenario(
    *,
    material_name: str,
    material_description: str,
    country: str,
    region: str,
    target_amount: float,
    target_units: str,
    route_name: str,
    route_description: str,
    inputs: pd.DataFrame,
) -> ScaleUpScenario:
    """Build a typed scenario from the Streamlit form."""

    identity_provider = get_identity_provider()

    process_inputs: list[ProcessInput] = []

    for _, row in inputs.iterrows():
        chemical_name = str(
            row.get("Chemical", "")
        ).strip()

        role = str(
            row.get("Role", "")
        ).strip()

        if not chemical_name:
            continue

        chemical = identity_provider.get_by_name(
            chemical_name
        )

        process_inputs.append(
            ProcessInput(
                chemical=chemical,
                role=role or None,
            )
        )

    if not process_inputs:
        raise ValueError(
            "At least one chemical input is required."
        )

    return ScaleUpScenario(
        material=MaterialSpec(
            name=material_name.strip(),
            description=(
                material_description.strip()
                or None
            ),
        ),
        production_location=LocationSpec(
            country=country.strip() or None,
            region=region.strip() or None,
        ),
        production_target=ProductionTarget(
            amount=target_amount,
            units=target_units,
        ),
        synthesis_route=SynthesisRoute(
            name=route_name.strip(),
            origin=RouteOrigin.USER_PROVIDED,
            description=(
                route_description.strip()
                or None
            ),
            inputs=process_inputs,
        ),
    )


def assessment_status_label(
    status: AssessmentStatus,
) -> str:
    """Return a readable assessment-status label."""

    labels = {
        AssessmentStatus.ASSESSED: "Assessed",
        AssessmentStatus.INSUFFICIENT_DATA: (
            "Insufficient data"
        ),
        AssessmentStatus.NOT_APPLICABLE: (
            "Not applicable"
        ),
        AssessmentStatus.ERROR: "Error",
    }

    return labels[status]


def render_assessment(
    assessment: GeneratedAssessment,
) -> None:
    """Render the structured AI assessment."""

    st.header("Assessment")

    st.info(assessment.executive_summary)

    if assessment.overall_score is None:
        st.metric(
            "Overall assessment",
            "Not scored",
        )

        st.caption(
            "The available evidence does not support a "
            "defensible overall numerical score."
        )

    else:
        st.metric(
            "Overall risk score",
            f"{assessment.overall_score:.0f} / 100",
        )

        if assessment.overall_confidence is not None:
            st.caption(
                "Overall confidence: "
                f"{assessment.overall_confidence:.0%}"
            )

    st.subheader("Category assessments")

    for category in assessment.category_assessments:
        title = category.category.value.replace(
            "_",
            " ",
        ).title()

        if category.score is None:
            metric_value = assessment_status_label(
                category.status
            )
        else:
            metric_value = (
                f"{category.score:.0f} / 100"
            )

        with st.container(border=True):
            left, right = st.columns(
                [3, 1]
            )

            with left:
                st.markdown(f"### {title}")
                st.write(category.summary)

            with right:
                st.metric(
                    "Risk",
                    metric_value,
                )

                if category.confidence is not None:
                    st.caption(
                        "Confidence: "
                        f"{category.confidence:.0%}"
                    )

            if category.supporting_facts:
                with st.expander(
                    "Supporting facts"
                ):
                    for fact in category.supporting_facts:
                        st.markdown(f"- {fact}")

            if category.data_gaps:
                with st.expander(
                    "Category data gaps"
                ):
                    for gap in category.data_gaps:
                        st.markdown(f"- {gap}")

            if category.recommendations:
                with st.expander(
                    "Recommendations"
                ):
                    for recommendation in (
                        category.recommendations
                    ):
                        st.markdown(
                            f"- {recommendation}"
                        )

    if assessment.major_barriers:
        st.subheader("Major barriers")

        for barrier in assessment.major_barriers:
            with st.container(border=True):
                st.markdown(
                    f"### {barrier.title}"
                )

                col1, col2 = st.columns(2)

                with col1:
                    st.metric(
                        "Severity",
                        f"{barrier.severity:.0f} / 100",
                    )

                with col2:
                    if barrier.confidence is not None:
                        st.metric(
                            "Confidence",
                            f"{barrier.confidence:.0%}",
                        )

                st.write(barrier.description)

                if barrier.supporting_facts:
                    for fact in barrier.supporting_facts:
                        st.markdown(f"- {fact}")

    if assessment.strengths:
        st.subheader("Strengths")

        for strength in assessment.strengths:
            st.markdown(f"- {strength}")

    if assessment.validation_actions:
        st.subheader("Highest-value next steps")

        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }

        actions = sorted(
            assessment.validation_actions,
            key=lambda action: priority_order.get(
                action.priority.value,
                99,
            ),
        )

        for action in actions:
            priority = action.priority.value.upper()

            with st.container(border=True):
                st.markdown(
                    f"**{priority}**"
                )
                st.markdown(
                    f"### {action.question}"
                )

                st.write(action.rationale)

                if action.suggested_method:
                    st.markdown(
                        "**Suggested method**"
                    )
                    st.write(
                        action.suggested_method
                    )

                if action.expected_decision_impact:
                    st.markdown(
                        "**Expected decision impact**"
                    )
                    st.write(
                        action.expected_decision_impact
                    )

    if assessment.data_gaps:
        st.subheader("Data gaps")

        for gap in assessment.data_gaps:
            st.markdown(f"- {gap}")

    if assessment.assumptions:
        with st.expander("Assessment assumptions"):
            for assumption in assessment.assumptions:
                st.markdown(
                    f"- {assumption}"
                )


def render_evidence(
    llm_context,
    *,
    trade_availability=None,
) -> None:
    """Render compact evidence supplied to the LLM."""

    st.header("Evidence & sources")
    if llm_context.domestic_production:
        st.subheader("Country-specific domestic production context")
        render_domestic_production(llm_context.domestic_production)

    trade_results = (
        llm_context.trade_availability if trade_availability is None else trade_availability
    )
    if trade_results:
        st.subheader("Country-specific historical trade")
        render_trade_results(trade_results)

    if llm_context.safety:
        st.subheader("Chemical safety")

        for safety in llm_context.safety:
            with st.expander(
                safety.chemical
            ):
                if safety.formula:
                    st.markdown(
                        f"**Formula:** {safety.formula}"
                    )

                if safety.signal_words:
                    st.markdown(
                        "**Signal words:** "
                        + ", ".join(
                            safety.signal_words
                        )
                    )

                if safety.pictograms:
                    st.markdown(
                        "**GHS pictograms:** "
                        + ", ".join(
                            safety.pictograms
                        )
                    )

                if safety.hazard_statements:
                    st.markdown(
                        "**Hazard statements**"
                    )

                    for hazard in safety.hazard_statements:
                        st.markdown(f"- {hazard}")

                for source in safety.sources:
                    if source.url:
                        st.markdown(
                            f"[{source.name}]"
                            f"({source.url})"
                        )
                    else:
                        st.write(source.name)

    if llm_context.markets:
        st.subheader("Commodity markets")

        for market in llm_context.markets:
            with st.container(border=True):
                st.markdown(
                    f"### {market.commodity}"
                )

                columns = st.columns(3)

                if market.latest_price is not None:
                    columns[0].metric(
                        "Reference price",
                        (
                            f"{market.latest_price:,.2f} "
                            f"{market.latest_price_units or ''}"
                        ),
                    )

                if (
                    market.price_change_percent
                    is not None
                ):
                    columns[1].metric(
                        "Price change",
                        (
                            f"{market.price_change_percent:+.1f}%"
                        ),
                    )

                if (
                    market.annualized_volatility_percent
                    is not None
                ):
                    columns[2].metric(
                        "Annualized volatility",
                        (
                            f"{market.annualized_volatility_percent:.1f}%"
                        ),
                    )

                st.caption(
                    "Commodity-market reference data are "
                    "upstream indicators, not direct "
                    "precursor purchase prices."
                )

                for source in market.sources:
                    if source.url:
                        st.markdown(
                            f"[{source.name}]"
                            f"({source.url})"
                        )

    if llm_context.supply:
        st.subheader("Supply-chain indicators")

        for supply in llm_context.supply:
            with st.container(border=True):
                st.markdown(
                    f"### {supply.commodity}"
                )

                if supply.leading_producer:
                    st.write(
                        "**Largest reported producer:** "
                        f"{supply.leading_producer}"
                    )

                    if (
                        supply.leading_producer_share_percent
                        is not None
                    ):
                        st.write(
                            "**Share of reported global "
                            "production:** "
                            f"{supply.leading_producer_share_percent:.1f}%"
                        )

                if supply.world_production is not None:
                    st.write(
                        "**World production:** "
                        f"{supply.world_production:,.0f} "
                        f"{supply.world_production_units or ''}"
                    )

                if supply.import_reliance:
                    st.markdown(
                        "**U.S. net import reliance:**"
                    )

                    for reliance in supply.import_reliance:
                        if reliance.raw_value:
                            value = reliance.raw_value
                        elif reliance.value is not None:
                            value = str(reliance.value)
                        else:
                            value = "Not reported"

                        detail = (
                            f" ({reliance.detail})"
                            if reliance.detail
                            else ""
                        )

                        units = (
                            f" {reliance.units}"
                            if reliance.units
                            else ""
                        )

                        st.markdown(
                            f"- {value}{units}{detail}"
                        )

                if supply.is_us_critical_mineral:
                    st.write(
                        "**U.S. critical mineral:** Yes"
                    )

                for source in supply.sources:
                    if source.url:
                        st.markdown(
                            f"[{source.name}]"
                            f"({source.url})"
                        )


def main() -> None:
    """Run the SyntheScale Streamlit application."""

    configure_page()

    st.title("⚗️ SyntheScale")

    st.write(
        "Evidence-grounded AI assessment for early-stage "
        "materials scale-up."
    )

    st.caption(
        "SyntheScale combines chemical safety, commodity-market, "
        "and mineral supply-chain evidence with structured AI "
        "reasoning."
    )

    include_trade = st.toggle(
        "Enable UN Comtrade",
        value=False,
        key="enable_un_comtrade",
        help=(
            "Enable on a network that can reach the Comtrade API, such as your hotspot. "
            "Turn off on restricted networks to skip all Comtrade requests."
        ),
    )
    if not include_trade:
        for state_key in ("lookup_trade_results", "assessment_trade_results"):
            st.session_state.pop(state_key, None)
        st.info(
            "UN Comtrade is disabled. No Comtrade requests will be made, and trade "
            "evidence will not be included in assessments. Other evidence sources remain available."
        )

    workflow = st.radio(
        "Workflow",
        ["Scale-up assessment", "Country/material availability"],
        horizontal=True,
    )
    if workflow == "Country/material availability":
        if include_trade:
            render_availability_lookup()
        else:
            st.info("Turn on Enable UN Comtrade to use country/material availability lookup.")
        return

    if not WORLD_BANK_PATH.exists() or not USGS_PATH.exists():
        st.error(
            "Required external datasets are missing. Run "
            "`python scripts/download_data.py` first."
        )
        st.stop()

    st.header("Assess a material")

    countries, products = [], []
    if include_trade:
        try:
            countries, products = trade_catalogs()
        except ComtradeError as error:
            st.error(str(error))
            st.info(
                "Follow the diagnostic above, or turn off Enable UN Comtrade to continue "
                "with the existing assessment sources."
            )
            st.stop()

    left, right = st.columns(2)

    with left:
        material_name = st.text_input(
            "Material",
            value="Zeolite 13X",
        )

        selected_country = None
        if include_trade:
            selected_country = select_country(countries, key="assessment_country")
            country = selected_country.name
        else:
            country = st.text_input(
                "Production country",
                value="United States",
            )

        target_amount = st.number_input(
            "Target production amount",
            min_value=0.001,
            value=1.0,
        )

    with right:
        material_description = st.text_area(
            "Material description",
            value=(
                "Example aluminosilicate material."
            ),
            height=68,
        )

        region = st.text_input(
            "Region",
            value="Illinois",
        )

        target_units = st.selectbox(
            "Target units",
            options=[
                "g",
                "kg",
                "metric tons",
            ],
            index=1,
        )

    st.subheader("Synthesis route")

    route_name = st.text_input(
        "Route name",
        value="Example hydrothermal synthesis",
    )

    route_description = st.text_area(
        "Additional process information (optional)",
        placeholder=(
            "Paste known synthesis conditions, demonstrated "
            "scale, yield information, or other process details..."
        ),
    )

    st.markdown("**Raw materials**")

    edited_inputs = st.data_editor(
        DEFAULT_INPUTS,
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Chemical": st.column_config.TextColumn(
                "Chemical",
                required=True,
            ),
            "Role": st.column_config.TextColumn(
                "Role",
            ),
        },
        key="chemical_inputs",
    )

    trade_results = []
    if selected_country is not None:
        st.subheader("Confirm trade classifications")
        trade_results = render_trade_selection(
            selected_country,
            [
                str(value).strip()
                for value in edited_inputs["Chemical"].dropna()
                if str(value).strip().casefold() != "water"
            ],
            products,
            key="assessment",
        )

    assess = st.button(
        "Assess scale-up",
        type="primary",
        width="stretch",
    )

    if not assess:
        st.stop()

    if not material_name.strip():
        st.error("Material name is required.")
        st.stop()

    try:
        with st.status(
            "Building SyntheScale assessment...",
            expanded=True,
        ) as status:
            st.write(
                "Resolving chemical identities with PubChem..."
            )

            scenario = build_scenario(
                material_name=material_name,
                material_description=material_description,
                country=country,
                region=region,
                target_amount=target_amount,
                target_units=target_units,
                route_name=route_name,
                route_description=route_description,
                inputs=edited_inputs,
            )

            st.write(
                "Gathering safety, market, and "
                "supply-chain evidence..."
            )

            full_context = (
                get_context_builder().build(
                    scenario,
                    trade_availability=trade_results,
                )
            )
            if include_trade:
                covered = {result.match.requested_material for result in trade_results}
                for value in edited_inputs["Chemical"].dropna():
                    name = str(value).strip()
                    if name and name.casefold() != "water" and name not in covered:
                        full_context.data_gaps.append(
                            "No confirmed country-specific trade evidence "
                            f"was retrieved for {name}."
                        )
            else:
                full_context.data_gaps.append(
                    "UN Comtrade was disabled by the user. Country-specific trade evidence "
                    "was not retrieved; this does not establish low availability "
                    "or supply-chain risk."
                )

            st.write(
                f"Collected {len(full_context.evidence)} "
                "source-grounded evidence records."
            )

            llm_context = build_llm_context(
                full_context
            )

            st.write(
                "Generating structured AI assessment..."
            )

            assessment = (
                get_assessment_generator().generate(
                    llm_context
                )
            )

            status.update(
                label="Assessment complete",
                state="complete",
                expanded=False,
            )

        assessment_tab, evidence_tab = st.tabs(
            [
                "Assessment",
                "Evidence & sources",
            ]
        )

        with assessment_tab:
            render_assessment(assessment)

        with evidence_tab:
            render_evidence(
                llm_context,
                trade_availability=full_context.trade_availability,
            )

            if llm_context.data_gaps:
                st.subheader("Evidence gaps")

                for gap in llm_context.data_gaps:
                    st.markdown(f"- {gap}")

            with st.expander(
                "Compact AI context"
            ):
                st.json(
                    llm_context.model_dump(
                        exclude_none=True,
                    )
                )

    except ChemicalNotFoundError as error:
        st.error(str(error))

    except Exception as error:
        st.error(
            f"Assessment failed: {error}"
        )

        with st.expander("Technical details"):
            st.exception(error)


if __name__ == "__main__":
    main()
    