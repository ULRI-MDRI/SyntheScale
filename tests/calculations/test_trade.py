import pytest

from material_scaleup.calculations.trade import summarize_trade_year
from material_scaleup.models.trade import TradeObservation


def observation(partner, value, weight, estimated=False):
    return TradeObservation(
        year=2024,
        partner_code=partner,
        partner_name=str(partner),
        value_usd=value,
        net_weight_kg=weight,
        weight_estimated=estimated,
    )


def test_exact_concentration_and_ratio_of_totals_not_average():
    result = summarize_trade_year(
        2024,
        [
            observation(0, 1000, 250),
            observation(156, 800, 200),
            observation(276, 200, 100),
        ],
    )
    assert result.import_value_usd == 1000
    assert result.largest_partner_share_percent == 80
    assert result.top_three_share_percent == 100
    assert result.hhi == pytest.approx(6800)
    assert result.unit_value_usd_per_kg == pytest.approx(1000 / 300)
    assert result.usable_weight_value_coverage_percent == 100
    assert len(result.partners) == 2


def test_cost_uses_same_eligible_records_for_numerator_and_denominator():
    result = summarize_trade_year(
        2024,
        [
            observation(0, 1000, None),
            observation(156, 800, 200),
            observation(276, 200, None),
        ],
    )
    assert result.unit_value_usd_per_kg == 4
    assert result.usable_weight_value_coverage_percent == 80


@pytest.mark.parametrize("weight", [None, 0, 100])
def test_cost_withheld_when_usable_coverage_below_threshold(weight):
    result = summarize_trade_year(
        2024,
        [
            observation(0, 1000, None),
            observation(156, 700, 200),
            observation(276, 300, weight, estimated=weight == 100),
        ],
    )
    assert result.usable_weight_value_coverage_percent == 70
    assert result.unit_value_usd_per_kg is None
    assert result.hhi is not None


def test_incomplete_partner_totals_withhold_concentration_and_cost():
    result = summarize_trade_year(
        2024,
        [
            observation(0, 1000, 100),
            observation(156, 500, 50),
        ],
    )
    assert result.import_value_usd == 1000
    assert result.hhi is None
    assert result.unit_value_usd_per_kg is None


@pytest.mark.parametrize(("total", "accepted"), [(995, True), (994.99, False)])
def test_reconciliation_threshold_is_enforced(total, accepted):
    result = summarize_trade_year(
        2024, [observation(0, 1000, 100), observation(156, total, 100)]
    )
    assert (result.hhi is not None) is accepted
    assert (result.unit_value_usd_per_kg is not None) is accepted


@pytest.mark.parametrize(
    ("rows", "status"),
    [
        ([], "no_reported_trade"),
        ([observation(156, 10, 1)], "insufficient_data"),
        ([observation(0, 0, 0)], "no_reported_trade"),
        ([observation(0, 0, 0), observation(156, 10, 1)], "insufficient_data"),
    ],
)
def test_missing_and_zero_trade_are_not_scarcity(rows, status):
    result = summarize_trade_year(2024, rows)
    assert result.status == status
    assert result.hhi is None
    assert result.unit_value_usd_per_kg is None
