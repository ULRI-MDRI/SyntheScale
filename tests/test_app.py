from pathlib import Path
from unittest.mock import Mock, patch

import pytest

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_app_reports_unrecognized_chemical_without_traceback():
    app_test = pytest.importorskip("streamlit.testing.v1").AppTest
    pytest.importorskip("openai")
    script = f"""
import runpy
from pathlib import Path

namespace = runpy.run_path({str(APP_PATH)!r})
main = namespace["main"]
# This test stops during identity resolution, before loading any datasets.
main.__globals__["WORLD_BANK_PATH"] = Path({str(APP_PATH)!r})
main.__globals__["USGS_PATH"] = Path({str(APP_PATH)!r})
main.__globals__["DEFAULT_INPUTS"].loc[0, "Chemical"] = "sodium fumerate"
main()
"""
    response = Mock(status_code=404)
    with (
        patch("material_scaleup.providers.pubchem.requests.get", return_value=response) as get,
        patch(
            "material_scaleup.services.context_builder.AssessmentContextBuilder.build"
        ) as build_context,
    ):
        app = app_test.from_string(script).run()
        assert not app.exception
        assert not app.error
        app.button[0].click().run()

    assert not app.exception
    assert len(app.error) == 1
    assert "sodium fumerate" in app.error[0].value
    assert "Check the spelling" in app.error[0].value
    assert "No chemical has been substituted" in app.error[0].value
    assert not any(expander.label == "Technical details" for expander in app.expander)
    get.assert_called_once()
    build_context.assert_not_called()
