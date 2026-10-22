import math

from material_scaleup.models.trade import TradeObservation, TradeYear


def summarize_trade_year(year: int, observations: list[TradeObservation]) -> TradeYear:
    world = next((row for row in observations if row.partner_code == 0), None)
    partners = [row for row in observations if row.partner_code != 0]
    result = TradeYear(
        year=year,
        status="available" if observations else "no_reported_trade",
        partners=sorted(partners, key=lambda row: row.value_usd, reverse=True),
    )
    if world is None:
        result.status = "insufficient_data" if observations else "no_reported_trade"
        result.warnings.append(
            "No world-total observation: absent records do not establish zero trade."
        )
        return result
    result.import_value_usd = world.value_usd
    result.reported_net_weight_kg = world.net_weight_kg
    if world.weight_estimated:
        result.warnings.append("World-total net weight is estimated by the source.")
    total = sum(row.value_usd for row in partners)
    reconciled = math.isclose(total, world.value_usd, rel_tol=0.005, abs_tol=1)
    if world.value_usd > 0 and total > 0 and reconciled and partners:
        shares = sorted((row.value_usd / total for row in partners), reverse=True)
        result.largest_partner_share_percent = shares[0] * 100
        result.top_three_share_percent = sum(shares[:3]) * 100
        result.hhi = sum(share**2 for share in shares) * 10000
        result.warnings.append(
            "Concentration is by reported partner value; special/unspecified partners "
            "may be included. It is not a count of suppliers or verified origin countries."
        )
    elif world.value_usd > 0:
        result.warnings.append(
            "Partner values do not reconcile to the world total within 0.5% or USD 1; "
            "concentration and partner-based unit values are withheld."
        )
    if world.value_usd == 0:
        if total > 0:
            result.status = "insufficient_data"
            result.warnings.append("Zero world total conflicts with positive partner trade.")
        else:
            result.status = "no_reported_trade"
    usable = [
        row
        for row in partners
        if row.value_usd > 0
        and row.net_weight_kg is not None
        and row.net_weight_kg > 0
        and not row.weight_estimated
    ]
    if reconciled and total > 0 and usable:
        eligible_value = sum(row.value_usd for row in usable)
        eligible_weight = sum(row.net_weight_kg or 0 for row in usable)
        result.usable_weight_value_coverage_percent = eligible_value / total * 100
        if eligible_value / total >= 0.8:
            result.unit_value_usd_per_kg = eligible_value / eligible_weight
            result.unit_value_basis = (
                "Reported primary import value / reported non-estimated net weight; "
                "imports are generally CIF, but country valuation exceptions are not verified."
            )
        else:
            result.warnings.append(
                "Under 80% of partner value has usable non-estimated weight; "
                "cost benchmark withheld."
            )
    if result.unit_value_usd_per_kg is None:
        result.warnings.append("No defensible import unit-value benchmark for this period.")
    return result
