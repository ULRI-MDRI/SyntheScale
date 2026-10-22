# src/material_scaleup/providers/world_bank.py

from datetime import date
from pathlib import Path
from typing import cast

import pandas as pd

from material_scaleup.models.cost import CommodityPriceObservation
from material_scaleup.models.source import Source
from material_scaleup.resolvers.commodity_name import resolve_commodity_name

__all__ = [
    "WorldBankCommodityProvider",
]


class WorldBankCommodityProvider:
    """Read commodity price histories from the World Bank Pink Sheet."""

    SHEET_NAME = "Monthly Prices"
    COMMODITY_ROW = 4
    UNITS_ROW = 5
    FIRST_DATA_ROW = 6

    SOURCE_URL = "https://www.worldbank.org/en/research/commodity-markets"

    COLUMNS = [
        "commodity",
        "date",
        "price",
        "units",
    ]

    COMMODITY_ALIASES = {
        "aluminum": "Aluminum",
        "copper": "Copper",
        "nickel": "Nickel",
        "zinc": "Zinc",
        "phosphate rock": "Phosphate rock",
        "urea": "Urea",
    }

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

        if not self.path.exists():
            raise FileNotFoundError(f"World Bank commodity workbook not found: {self.path}")

        self._prices = self._load_prices()

    def commodities(self) -> list[str]:
        """
        Return commodities available in the workbook.

        Returns:
            list[str]:
                List of commodity names available in the workbook.
        """

        return sorted(cast(list[str], self._prices["commodity"].unique().tolist()))

    def get_price_history(
        self,
        commodity: str,
        months: int | None = None,
    ) -> list[CommodityPriceObservation]:
        """
        Return monthly price observations for a commodity.

        Args:
            commodity (str):
                The name of the commodity to retrieve price history for.

            months (int | None, optional):
                The number of most recent months to include. If None, include
                all available data.

        Returns:
            list[CommodityPriceObservation]:
                A list of monthly price observations for the specified commodity.

        Raises:
            LookupError:
                If the specified commodity is not found in the workbook.

            ValueError:
                If the months parameter is less than or equal to zero.
        """
        normalized = commodity.casefold().strip()

        commodity_names = self._prices["commodity"].astype(str)

        matches = self._prices[commodity_names.str.casefold() == normalized].copy()

        if matches.empty:
            raise LookupError(f"World Bank commodity not found: {commodity!r}")

        matches = matches.sort_values("date")

        if months is not None:
            if months <= 0:
                raise ValueError("months must be greater than zero.")

            matches = matches.tail(months)

        source = Source(
            name="World Bank Commodity Price Data (Pink Sheet)",
            publisher="World Bank",
            url=self.SOURCE_URL,
        )

        observations: list[CommodityPriceObservation] = []

        for _, row in matches.iterrows():
            observations.append(
                CommodityPriceObservation(
                    commodity=cast(str, row["commodity"]),
                    date=cast(date, row["date"]),
                    price=float(cast(float, row["price"])),
                    currency="USD",
                    units=cast(str, row["units"]),
                    source=source,
                )
            )

        return observations

    def get_latest_price(self, commodity: str) -> CommodityPriceObservation:
        """
        Return the latest available price for a commodity.

        Args:
            commodity (str):
                The name of the commodity for which to retrieve the latest price.

        Returns:
            CommodityPriceObservation:
                The latest available price observation for the specified commodity.
        """

        history = self.get_price_history(commodity=commodity, months=1)

        return history[0]

    def _load_prices(self) -> pd.DataFrame:
        """Load and normalize the World Bank monthly price sheet."""

        raw = pd.read_excel(
            self.path,
            sheet_name=self.SHEET_NAME,
            header=None,
            engine="openpyxl",
        )

        if len(raw) <= self.FIRST_DATA_ROW:
            raise ValueError("World Bank monthly price sheet contains too few rows.")

        commodity_names = raw.iloc[self.COMMODITY_ROW]
        commodity_units = raw.iloc[self.UNITS_ROW]

        records: list[dict[str, object]] = []

        for row_index in range(self.FIRST_DATA_ROW, len(raw)):
            period = raw.iloc[row_index, 0]

            if not isinstance(period, str):
                continue

            observation_date = self._parse_period(period)

            if observation_date is None:
                continue

            for column_index in range(1, len(raw.columns)):
                commodity = commodity_names.iloc[column_index]
                units = commodity_units.iloc[column_index]
                value = raw.iloc[row_index, column_index]

                if not isinstance(commodity, str):
                    continue

                numeric_value = pd.to_numeric(value, errors="coerce")

                if pd.isna(numeric_value):
                    continue

                records.append(
                    {
                        "commodity": commodity.strip(),
                        "date": observation_date,
                        "price": float(numeric_value),
                        "units": self._normalize_units(units),
                    }
                )

        if not records:
            raise ValueError(
                f"No commodity-price records could be parsed from {self.path}"
                "The World Bank workbook layout may have changed."
            )

        return pd.DataFrame.from_records(records, columns=self.COLUMNS)

    @staticmethod
    def _parse_period(period: str) -> date | None:
        """Convert a Pink Sheet period such as 2026M09 to a date."""

        value = period.strip()

        if len(value) != 7 or value[4] != "M":
            return None

        try:
            year = int(value[:4])
            month = int(value[5:7])

            return date(year=year, month=month, day=1)

        except ValueError:
            return None

    @staticmethod
    def _normalize_units(value: object) -> str:
        """Normalize the display units used by the workbook."""

        if not isinstance(value, str):
            return "unknown"

        units = value.strip()

        if units.startswith("(") and units.endswith(")"):
            units = units[1:-1]

        return units

    def resolve_commodity_name(self, commodity: str) -> str | None:
        """
        Resolve a SyntheScale commodity to a World Bank series.

        Args:
            commodity (str):
                The SyntheScale commodity name to resolve.

        Returns:
            str | None:
                The catalog series name found by alias, exact lookup, or conservative
                fuzzy matching; None for missing, weak, or ambiguous matches.
        """
        return resolve_commodity_name(
            commodity,
            commodities=self.commodities(),
            aliases=self.COMMODITY_ALIASES,
        )
