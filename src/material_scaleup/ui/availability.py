import hashlib
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from material_scaleup.models.domestic import DomesticProductionResult
from material_scaleup.models.trade import (
    AvailabilityResult,
    TradeCountry,
    TradeMatch,
    TradeProduct,
)
from material_scaleup.providers.comtrade import ComtradeError, ComtradeProvider
from material_scaleup.providers.usgs import USGSCommodityProvider
from material_scaleup.resolvers.trade import find_trade_matches
from material_scaleup.services.availability import TRADE_LIMITATIONS, AvailabilityService
from material_scaleup.services.domestic import DomesticProductionService


def get_domestic_service() -> DomesticProductionService:
    path = (
        Path(__file__).resolve().parents[3]
        / "data/raw/usgs/mcs2026/MCS2026_Commodities_Data.csv"
    )
    if not path.exists():
        return DomesticProductionService(None)
    try:
        return DomesticProductionService(USGSCommodityProvider(path))
    except (OSError, ValueError) as error:
        return DomesticProductionService(
            None, source_error=f"USGS domestic-production dataset could not be loaded: {error}"
        )


def render_domestic_production(results: list[DomesticProductionResult]) -> None:
    for result in results:
        with st.container(border=True):
            st.markdown(f"**Domestic upstream context: {result.material}**")
            st.write(
                f"Country: {result.requested_country}; source country: "
                f"{result.source_country or 'unresolved/not checked'}. "
                f"Upstream evidence: {result.status}. "
                f"Direct material production: {result.direct_material_status}."
            )
            st.caption(f"Checked {result.checked_at.isoformat()}")
            if result.observations:
                st.dataframe(
                    [
                        {
                            "Commodity": row.commodity,
                            "Country": row.country,
                            "Year": row.raw_year,
                            "Published value": row.raw_value,
                            "Units": row.units,
                            "Production detail": row.statistic_detail,
                            "Section": row.section,
                            "Notes": row.notes,
                            "Other notes": row.other_notes,
                            "Qualifier": row.value_qualifier,
                        }
                        for row in result.observations
                    ],
                    hide_index=True,
                )
                for url in sorted({
                    row.source.url for row in result.observations if row.source.url
                }):
                    st.markdown(f"[USGS production source]({url})")
            for limitation in result.limitations:
                st.info(limitation)


@st.cache_resource
def get_trade_provider() -> ComtradeProvider:
    return ComtradeProvider.from_environment()


def trade_catalogs() -> tuple[list[TradeCountry], list[TradeProduct]]:
    provider = get_trade_provider()
    return provider.countries(), provider.products()


def select_country(countries: list[TradeCountry], *, key: str) -> TradeCountry:
    by_code = {country.code: country for country in countries}
    default = next((index for index, item in enumerate(countries) if item.code == 842), 0)
    code = st.selectbox(
        "Destination country / area",
        options=list(by_code),
        format_func=lambda value: by_code[value].name,
        index=default,
        key=key,
    )
    return by_code[code]


def render_trade_results(results: list[AvailabilityResult]) -> None:
    st.caption(TRADE_LIMITATIONS)
    for result in results:
        with st.container(border=True):
            st.subheader(f"{result.match.requested_material} — {result.country.name}")
            st.write(
                f"Selected catalog category (HS2022): {result.match.product.code}: "
                f"{result.match.product.description}"
            )
            st.caption("Data queried using HS; reported revisions are shown per year, not assumed.")
            st.warning(f"{result.match.relationship} match: {result.match.reason}")
            st.write(f"Data status: {result.status}. Risk score: not scored (pilot).")
            st.caption(
                f"Lookup at {result.retrieved_at.isoformat()}; "
                "API responses may be cached for up to one hour."
            )
            if result.years:
                st.caption("Weight coverage: partner value with usable non-estimated weight.")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Year": year.year,
                                "Status": year.status,
                                "Reported HS revision": ", ".join(year.reported_classifications)
                                or "unverified",
                                "Matches selected catalog": year.classification_matches_catalog,
                                "Imports (USD)": year.import_value_usd,
                                "Reported net weight (kg)": year.reported_net_weight_kg,
                                "Largest partner (%)": year.largest_partner_share_percent,
                                "Top three partners (%)": year.top_three_share_percent,
                                "HHI (0–10000)": year.hhi,
                                "Historical unit value (USD/kg)": year.unit_value_usd_per_kg,
                                "Weight coverage (%)": year.usable_weight_value_coverage_percent,
                            }
                            for year in result.years
                        ]
                    ),
                    hide_index=True,
                )
                for year in result.years:
                    with st.expander(f"{year.year}: partners, basis and warnings"):
                        if year.unit_value_basis:
                            st.write(year.unit_value_basis)
                        for warning in year.warnings:
                            st.warning(warning)
                        if year.partners:
                            st.dataframe(
                                [partner.model_dump() for partner in year.partners],
                                hide_index=True,
                            )
            if result.value_change_percent is not None:
                st.write(
                    f"Import value change: {result.value_change_percent:+.1f}% "
                    f"over {result.trend_period}."
                )
            for gap in result.data_gaps:
                st.info(gap)
            if result.domestic_production is not None:
                render_domestic_production([result.domestic_production])
            st.markdown(f"[UN Comtrade source]({result.source.url})")


def render_trade_selection(
    country: TradeCountry,
    materials: list[str],
    products: list[TradeProduct],
    *,
    key: str,
) -> list[AvailabilityResult]:
    state_key = f"{key}_trade_results"
    names = list(dict.fromkeys(name.strip() for name in materials if name.strip()))
    if not names:
        st.session_state.pop(state_key, None)
        st.info("Enter at least one material.")
        return []
    if len(names) > 10:
        st.session_state.pop(state_key, None)
        st.error("Look up at most 10 materials at a time to keep API requests bounded.")
        return []
    fingerprint = hashlib.sha256(
        json.dumps([country.code, names], ensure_ascii=True).encode()
    ).hexdigest()[:16]
    selected: list[TradeMatch] = []
    confirmations: list[bool] = []
    for index, material in enumerate(names):
        candidates = find_trade_matches(material, products)
        if not candidates:
            st.warning(
                f"{material}: no defensible trade candidate found; no material was substituted."
            )
            continue
        prefix = f"{key}_{fingerprint}_{index}"
        selected_code = st.selectbox(
            f"Trade category for {material}",
            options=[None, *[candidate.product.code for candidate in candidates]],
            format_func=lambda code, choices=candidates: (
                "Choose a trade category"
                if code is None
                else next(
                    f"HS2022 {item.product.code} — {item.product.description}"
                    for item in choices
                    if item.product.code == code
                )
            ),
            key=f"{prefix}_category",
        )
        if selected_code is None:
            continue
        match = next(item for item in candidates if item.product.code == selected_code)
        st.warning(match.reason)
        confirmed = st.checkbox(
            f"I confirm the scope of this category for {material}; it may be a broader proxy.",
            key=f"{prefix}_{selected_code}_confirmed",
        )
        selected.append(match)
        confirmations.append(confirmed)
    signature = json.dumps(
        [fingerprint, [item.model_dump() for item in selected], confirmations],
        sort_keys=True,
    )
    if state_key in st.session_state and st.session_state[state_key]["signature"] != signature:
        del st.session_state[state_key]
    if st.button(
        "Retrieve trade evidence",
        key=f"{key}_retrieve",
        disabled=not selected or not all(confirmations),
    ):
        service = AvailabilityService(
            get_trade_provider(), domestic_service=get_domestic_service()
        )
        results = []
        for index, match in enumerate(selected):
            with st.spinner(f"Retrieving {index + 1}/{len(selected)}: {match.requested_material}"):
                results.append(service.lookup(country, match, confirmed=True))
        st.session_state[state_key] = {"signature": signature, "results": results}
    results = st.session_state[state_key]["results"] if state_key in st.session_state else []
    uncovered = set(names) - {result.match.requested_material for result in results}
    if uncovered:
        st.info("Trade evidence has not been retrieved for: " + ", ".join(sorted(uncovered)))
    if results:
        render_trade_results(results)
        st.download_button(
            "Download trade evidence (JSON)",
            data=json.dumps([item.model_dump(mode="json") for item in results], indent=2),
            file_name="trade_availability.json",
            mime="application/json",
            key=f"{key}_download",
        )
    return results


def render_availability_lookup() -> None:
    st.header("Country/material availability")
    st.write(
        "Choose a destination and enter materials (one per line). "
        "Catalog matches require confirmation; similar names do not establish chemical equivalence."
    )
    try:
        countries, products = trade_catalogs()
    except ComtradeError as error:
        st.error(str(error))
        st.info(
            "Missing/rejected key: check UN_COMTRADE_API_KEY and restart Streamlit "
            "from the terminal where it was exported. "
            "DNS/connection failure: restore network access to the API before retrying."
        )
        return
    country = select_country(countries, key="lookup_country")
    materials = st.text_area(
        "Materials (one per line; up to 10)",
        value="sodium aluminate\nsodium silicate\nsodium hydroxide",
        key="lookup_materials",
    )
    render_trade_selection(country, materials.splitlines(), products, key="lookup")
