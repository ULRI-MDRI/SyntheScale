import runpy
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from material_scaleup.models.chemical import MaterialSpec
from material_scaleup.models.context import AssessmentContext
from material_scaleup.models.generated_assessment import GeneratedAssessment
from material_scaleup.models.scenario import ScaleUpScenario
from material_scaleup.models.source import Source
from material_scaleup.models.trade import AvailabilityResult, TradeCountry, TradeMatch, TradeProduct

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
COUNTRY = TradeCountry(code=842, name="USA")
PRODUCTS = [
    TradeProduct(code="284190", description="Oxometallic salts; other"),
    TradeProduct(code="283919", description="Sodium silicates; other"),
    TradeProduct(code="281511", description="Sodium hydroxide; solid"),
    TradeProduct(code="281512", description="Sodium hydroxide; aqueous solution"),
]


def app_test(*, missing_datasets=False):
    runner = pytest.importorskip("streamlit.testing.v1").AppTest
    return runner.from_string(f"""
import runpy
namespace = runpy.run_path({str(APP_PATH)!r})
if {missing_datasets!r}:
    from pathlib import Path
    namespace["main"].__globals__["WORLD_BANK_PATH"] = Path("/nonexistent/synthescale/world_bank")
    namespace["main"].__globals__["USGS_PATH"] = Path("/nonexistent/synthescale/usgs")
namespace["main"]()
""")


def result_for(country, match, *, confirmed):
    return AvailabilityResult(
        country=country,
        match=match,
        confirmed=confirmed,
        retrieved_at=datetime.now(UTC),
        source=Source(name="Test source", url="https://comtradeplus.un.org/"),
        status="insufficient_data",
        data_gaps=["No complete periods in test response"],
    )


def test_standalone_does_not_require_llm_or_local_datasets(monkeypatch):
    monkeypatch.delenv("UN_COMTRADE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with (
        patch(
            "material_scaleup.ui.availability.trade_catalogs",
            return_value=([COUNTRY], PRODUCTS),
        ),
        patch("material_scaleup.services.context_builder.AssessmentContextBuilder.build") as build,
    ):
        app = app_test(missing_datasets=True).run()
        app.radio[0].set_value("Country/material availability").run()
        app.toggle[0].set_value(True).run()
    assert not app.exception
    assert not app.error
    assert app.selectbox[0].value == 842
    assert len(app.selectbox) == 4
    build.assert_not_called()


def test_missing_key_is_explicit(monkeypatch):
    monkeypatch.delenv("UN_COMTRADE_API_KEY", raising=False)
    from material_scaleup.ui.availability import get_trade_provider

    get_trade_provider.clear()
    app = app_test().run()
    app.radio[0].set_value("Country/material availability").run()
    app.toggle[0].set_value(True).run()
    assert not app.exception
    assert any("UN_COMTRADE_API_KEY" in item.value for item in app.error)


def test_confirmation_persistence_and_changed_category_invalidate_results(monkeypatch):
    monkeypatch.delenv("UN_COMTRADE_API_KEY", raising=False)
    with (
        patch(
            "material_scaleup.ui.availability.trade_catalogs",
            return_value=([COUNTRY], PRODUCTS),
        ),
        patch("material_scaleup.ui.availability.get_trade_provider"),
        patch(
            "material_scaleup.ui.availability.AvailabilityService.lookup",
            side_effect=result_for,
        ) as lookup,
    ):
        app = app_test().run()
        app.radio[0].set_value("Country/material availability").run()
        app.toggle[0].set_value(True).run()
        app.text_area[0].set_value("sodium hydroxide").run()
        app.selectbox[1].set_value("281511").run()
        assert app.button[0].disabled
        app.checkbox[0].check().run()
        assert not app.button[0].disabled
        app.button[0].click().run()
        assert not app.exception
        assert any("Data status:" in item.value for item in app.markdown)
        app.run()
        assert any("Data status:" in item.value for item in app.markdown)
        app.selectbox[1].set_value("281512").run()
        assert not any("Data status:" in item.value for item in app.markdown)
        assert not app.checkbox[0].value
        assert app.button[0].disabled
        lookup.assert_called_once()


def test_global_toggle_defaults_off_even_with_key_and_skips_comtrade(monkeypatch):
    monkeypatch.setenv("UN_COMTRADE_API_KEY", "test-key-not-a-secret")
    with (
        patch("material_scaleup.ui.availability.trade_catalogs") as catalogs,
        patch("material_scaleup.ui.availability.get_trade_provider") as provider,
    ):
        app = app_test().run()
        assert not app.toggle[0].value
        assert not app.exception
        assert any(button.label == "Assess scale-up" for button in app.button)
        app.radio[0].set_value("Country/material availability").run()
        app.run()
        assert not app.toggle[0].value
        assert not app.selectbox
        assert any("UN Comtrade is disabled" in info.value for info in app.info)
        catalogs.assert_not_called()
        provider.assert_not_called()


def test_toggle_persists_across_workflows_and_can_recover_from_network_error(monkeypatch):
    from material_scaleup.providers.comtrade import ComtradeError

    monkeypatch.setenv("UN_COMTRADE_API_KEY", "test-key-not-a-secret")
    with patch(
        "material_scaleup.ui.availability.trade_catalogs",
        side_effect=ComtradeError("DNS lookup failed"),
    ) as catalogs:
        app = app_test().run()
        app.toggle[0].set_value(True).run()
        assert app.toggle[0].value
        assert any("DNS lookup failed" in error.value for error in app.error)
        app.radio[0].set_value("Country/material availability").run()
        assert app.toggle[0].value
        assert any("DNS lookup failed" in error.value for error in app.error)
        calls = catalogs.call_count
        app.toggle[0].set_value(False).run()
        app.radio[0].set_value("Scale-up assessment").run()
        assert not app.exception
        assert not app.error
        assert not app.toggle[0].value
        assert any(button.label == "Assess scale-up" for button in app.button)
        assert catalogs.call_count == calls


def test_disabling_clears_lookup_results_and_requires_fresh_retrieval(monkeypatch):
    monkeypatch.delenv("UN_COMTRADE_API_KEY", raising=False)
    with (
        patch(
            "material_scaleup.ui.availability.trade_catalogs",
            return_value=([COUNTRY], PRODUCTS),
        ),
        patch("material_scaleup.ui.availability.get_trade_provider"),
        patch(
            "material_scaleup.ui.availability.AvailabilityService.lookup",
            side_effect=result_for,
        ) as lookup,
    ):
        app = app_test().run()
        app.radio[0].set_value("Country/material availability").run()
        app.toggle[0].set_value(True).run()
        app.text_area[0].set_value("sodium hydroxide").run()
        app.selectbox[1].set_value("281511").run()
        app.checkbox[0].check().run()
        app.button[0].click().run()
        assert any("Data status:" in item.value for item in app.markdown)
        app.toggle[0].set_value(False).run()
        assert not any("Data status:" in item.value for item in app.markdown)
        assert "lookup_trade_results" not in app.session_state
        app.toggle[0].set_value(True).run()
        assert not any("Data status:" in item.value for item in app.markdown)
        lookup.assert_called_once()


def test_disabled_assessment_excludes_stale_trade_and_records_gap(monkeypatch):
    monkeypatch.setenv("UN_COMTRADE_API_KEY", "test-key-not-a-secret")
    runner = pytest.importorskip("streamlit.testing.v1").AppTest
    scenario = ScaleUpScenario(material=MaterialSpec(name="Example"))
    full_context = AssessmentContext(scenario=scenario)
    generator = Mock()
    generator.generate.return_value = GeneratedAssessment(executive_summary="Test assessment")
    script = f"""
import runpy
from unittest.mock import Mock
import streamlit as st
from material_scaleup.models.chemical import MaterialSpec
from material_scaleup.models.scenario import ScaleUpScenario
namespace = runpy.run_path({str(APP_PATH)!r})
main = namespace["main"]
main.__globals__["build_scenario"] = Mock(
    return_value=ScaleUpScenario(material=MaterialSpec(name="Example"))
)
if "assessment_trade_results" not in st.session_state:
    st.session_state["assessment_trade_results"] = {{"results": ["stale trade"]}}
main()
"""
    with (
        patch("material_scaleup.ui.availability.trade_catalogs") as catalogs,
        patch(
            "material_scaleup.services.context_builder.AssessmentContextBuilder.build",
            return_value=full_context,
        ) as build,
        patch(
            "material_scaleup.services.openai_client.create_assessment_generator_from_environment",
            return_value=generator,
        ),
    ):
        app = runner.from_string(script).run()
        app.button[0].click().run()
    assert not app.exception
    assert not app.error
    assert "assessment_trade_results" not in app.session_state
    build.assert_called_once_with(scenario, trade_availability=[])
    catalogs.assert_not_called()
    llm_context = generator.generate.call_args.args[0]
    assert not llm_context.trade_availability
    assert any("disabled by the user" in gap for gap in llm_context.data_gaps)


def test_export_contract_has_no_secret_fields():
    result = result_for(
        COUNTRY,
        TradeMatch(
            requested_material="sodium hydroxide",
            product=PRODUCTS[2],
            relationship="broader",
            reason="Verify solid form",
        ),
        confirmed=True,
    )
    assert "api_key" not in result.model_dump_json()
    assert "confirmed" in result.model_dump_json()


def test_app_module_can_load_without_openai_client_import():
    with patch.dict("sys.modules", {"material_scaleup.services.openai_client": None}):
        namespace = runpy.run_path(str(APP_PATH))
    assert callable(namespace["main"])
