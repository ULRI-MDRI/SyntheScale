# src/material_scaleup/calculations/volatility.py

from math import log
from statistics import stdev

from material_scaleup.models.cost import CommodityPriceObservation

__all__ = [
    "annualized_price_volatility",
    "price_change",
]


def price_change(observations: list[CommodityPriceObservation]) -> float | None:
    """
    Calculate total fractional price change over a series.

    Args:
        observations: list[CommodityPriceObservation]
            A list of commodity price observations ordered by date.

    Returns:
        float | None:
            Fractional change. For example, 0.25 represents a 25% increase.
    """
    if len(observations) < 2:
        return None

    ordered = sorted(observations, key=lambda observation: observation.date)

    first = ordered[0].price
    last = ordered[-1].price

    if first <= 0:
        return None

    return (last - first) / first


def annualized_price_volatility(
    observations: list[CommodityPriceObservation],
) -> float | None:
    """
    Calculate annualized volatility from monthly logarithmic returns.

    Logic:
        1. Sort the observations by date.
        2. Calculate the logarithmic returns for each consecutive month.
        3. Compute the standard deviation of the monthly returns.
        4. Annualize the volatility by multiplying the monthly standard
           deviation by the square root of 12.

    The result is expressed as a fraction. For example, 0.30
    represents approximately 30% annualized volatility.

    Args:
        observations: list[CommodityPriceObservation]
            A list of commodity price observations ordered by date.

    Returns:
        float | None:
            Annualized price volatility as a fraction. For example, 0.30
            represents approximately 30% annualized volatility.
    """
    if len(observations) < 3:
        return None

    ordered = sorted(observations, key=lambda observation: observation.date)

    monthly_returns = [
        log(current.price / previous.price)
        for previous, current in zip(
            ordered,
            ordered[1:],
            strict=False,
        )
        if previous.price > 0 and current.price > 0
    ]

    if len(monthly_returns) < 2:
        return None

    monthly_volatility = stdev(monthly_returns)

    return monthly_volatility * (12**0.5)
