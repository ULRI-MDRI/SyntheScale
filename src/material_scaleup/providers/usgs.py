# src/material_scaleup/providers/usgs.py

import re
from pathlib import Path
from typing import cast

import pandas as pd

from material_scaleup.models.source import Source
from material_scaleup.models.supply import USGSCommodityObservation

__all__ = [
    "USGSCommodityProvider",
]


class USGSCommodityProvider:
    """Read USGS Mineral Commodity Summaries structured data."""

    SOURCE_URL = "https://www.usgs.gov/data/mineral-commodity-summaries-2026-data-release"

    SOURCE_DOI = "10.5066/P1WKQ63T"

    REQUIRED_COLUMNS = {
        "Section",
        "Commodity",
        "Country",
        "Statistics",
        "Statistics_detail",
        "Unit",
        "Year",
        "Value",
        "Notes",
        "Is critical mineral 2025",
        "Other notes",
    }

    ENCODINGS = (
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin-1",
    )

    COMMODITY_ALIASES = {
        "aluminum": "Aluminum",
        "cobalt": "Cobalt",
        "nickel": "Nickel",
        "zinc": "Zinc",
        "phosphate rock": "Phosphate Rock",
        "silicon": "Silicon",
    }

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

        if not self.path.exists():
            raise FileNotFoundError(f"USGS commodity data not found: {self.path}")

        self._frame = self._load_data()

    def commodities(self) -> list[str]:
        """
        Return all commodities available in the dataset.

        Returns:
            list[str]:
                All unique commodity names available in the dataset.
        """
        values = self._frame["Commodity"].dropna().astype(str).str.strip().unique().tolist()

        return sorted(cast(list[str], values))

    def get_records(
        self,
        commodity: str,
        *,
        statistic: str | None = None,
        country: str | None = None,
        year: int | None = None,
    ) -> list[USGSCommodityObservation]:
        """
        Return records matching the requested commodity and filters.

        Args:
            commodity (str):
                The name of the commodity to filter records by.

            statistic (str | None):
                The name of the statistic to filter records by.

            country (str | None):
                The name of the country to filter records by.

            year (int | None):
                The year to filter records by.

        Returns:
            list[USGSCommodityObservation]:
                All records matching the requested commodity and filters.
        """
        frame = self._frame

        mask = (
            frame["Commodity"]
            .astype(str)
            .str.strip()
            .str.casefold()
            .eq(commodity.strip().casefold())
        )

        if statistic is not None:
            mask &= (
                frame["Statistics"]
                .astype(str)
                .str.strip()
                .str.casefold()
                .eq(statistic.strip().casefold())
            )

        if country is not None:
            mask &= (
                frame["Country"]
                .astype(str)
                .str.strip()
                .str.casefold()
                .eq(country.strip().casefold())
            )

        matches = frame.loc[mask].copy()

        if year is not None:
            matches = matches[matches["Year"].astype(str).str.strip().eq(str(year))]

        if matches.empty:
            return []

        return [self._row_to_observation(row) for _, row in matches.iterrows()]

    def get_latest_records(
        self,
        commodity: str,
        *,
        statistic: str,
        country: str | None = None,
    ) -> list[USGSCommodityObservation]:
        """
        Return records for the latest numeric year matching the filters.

        Multiple records may be returned because one commodity may have
        several statistic details for one year.

        Args:
            commodity (str):
                The name of the commodity to filter records by.

            statistic (str):
                The name of the statistic to filter records by.

            country (str | None):
                The name of the country to filter records by.

        Returns:
            list[USGSCommodityObservation]:
                All records matching the requested commodity and filters.
        """
        records = self.get_records(
            commodity,
            statistic=statistic,
            country=country,
        )

        numeric_years = [record.year for record in records if record.year is not None]

        if not numeric_years:
            return []

        latest_year = max(numeric_years)

        return [record for record in records if record.year == latest_year]

    def get_latest_world_production(
        self,
        commodity: str,
    ) -> USGSCommodityObservation | None:
        """
        Return the latest world-total production record.

        Args:
            commodity (str):
                The name of the commodity to filter records by.

        Returns:
            USGSCommodityObservation | None:
                The latest world-total production record, or None if no record
                is found.
        """
        records = self.get_latest_records(
            commodity,
            statistic="Production",
            country="World total",
        )

        return records[0] if records else None

    def get_latest_world_reserves(
        self,
        commodity: str,
    ) -> USGSCommodityObservation | None:
        """
        Return the latest world-total reserve record.

        Args:
            commodity (str):
                The name of the commodity to filter records by.

        Returns:
            USGSCommodityObservation | None:
                The latest world-total reserve record, or None if no record
                is found.
        """
        records = self.get_latest_records(
            commodity,
            statistic="Reserves",
            country="World total",
        )

        return records[0] if records else None

    def get_latest_country_production(
        self,
        commodity: str,
    ) -> list[USGSCommodityObservation]:
        """
        Return latest production records by producing country.

        Args:
            commodity (str):
                The name of the commodity to filter records by.

        Returns:
            list[USGSCommodityObservation]:
                The latest production records by producing country.
        """
        records = self.get_records(commodity, statistic="Production")

        numeric_years = [record.year for record in records if record.year is not None]

        if not numeric_years:
            return []

        latest_year = max(numeric_years)

        excluded_countries = {
            "world total",
            "other countries",
        }

        return [
            record
            for record in records
            if record.year == latest_year
            and record.country.casefold() not in excluded_countries
            and record.value is not None
        ]

    def get_latest_net_import_reliance(
        self,
        commodity: str,
    ) -> list[USGSCommodityObservation]:
        """
        Return the latest U.S. net-import-reliance records.

        Args:
            commodity (str):
                The name of the commodity to filter records by.

        Returns:
            list[USGSCommodityObservation]:
                The latest U.S. net-import-reliance records.
        """
        return self.get_latest_records(
            commodity,
            statistic="Net import reliance",
            country="United States",
        )

    def get_import_sources(
        self,
        commodity: str,
    ) -> list[USGSCommodityObservation]:
        """
        Return reported import-source shares.

        Args:
            commodity (str):
                The name of the commodity to filter records by.

        Returns:
            list[USGSCommodityObservation]:
                The reported import-source shares.
        """
        return self.get_records(commodity, statistic="Import sources 2021-2024")

    def is_critical_mineral(self, commodity: str) -> bool | None:
        """
        Return the USGS 2025 critical-mineral designation.

        Args:
            commodity (str):
                The name of the commodity to check for critical-mineral
                designation.

        Returns:
            bool | None:
                True if the commodity is designated as a critical mineral,
                False if not, or None if unknown.
        """
        records = self.get_records(commodity)

        values = {
            record.is_critical_mineral
            for record in records
            if record.is_critical_mineral is not None
        }

        if not values:
            return None

        if len(values) == 1:
            return values.pop()

        # Be conservative if inconsistent source rows exist.
        return True if True in values else False

    def _load_data(self) -> pd.DataFrame:
        """Load and validate the USGS commodity CSV."""

        encoding = self._detect_encoding()

        frame = pd.read_csv(
            self.path,
            encoding=encoding,
            dtype=str,
            keep_default_na=False,
        )

        missing = self.REQUIRED_COLUMNS - set(frame.columns)

        if missing:
            missing_text = ", ".join(sorted(missing))

            raise ValueError(f"USGS commodity CSV is missing required columns: {missing_text}")

        if frame.empty:
            raise ValueError(f"USGS commodity CSV contains no records: {self.path}")

        return frame

    def _detect_encoding(self) -> str:
        """
        Detect a supported encoding for the CSV.

        Returns:
            str:
                The detected encoding for the CSV file.

        Raises:
            ValueError:
                If no supported encoding could be detected for the CSV file.
        """
        sample = self.path.read_bytes()[:64_000]

        for encoding in self.ENCODINGS:
            try:
                sample.decode(encoding)
            except UnicodeDecodeError:
                continue

            return encoding

        raise ValueError(f"Could not determine CSV encoding: {self.path}")

    def _row_to_observation(self, row: pd.Series) -> USGSCommodityObservation:
        """Convert one pandas row into a typed observation."""
        raw_year = self._clean_text(row["Year"]) or ""
        raw_value = self._clean_text(row["Value"]) or ""

        return USGSCommodityObservation(
            commodity=self._required_text(row["Commodity"], "Commodity"),
            country=self._required_text(row["Country"], "Country"),
            section=self._required_text(row["Section"], "Section"),
            statistic=self._required_text(row["Statistics"], "Statistics"),
            statistic_detail=self._clean_text(row["Statistics_detail"]),
            year=self._parse_year(raw_year),
            raw_year=raw_year,
            value=self._parse_numeric_value(raw_value),
            value_qualifier=USGSCommodityObservation.parse_value_qualifier(raw_value),
            raw_value=raw_value,
            units=self._clean_text(row["Unit"]),
            notes=self._clean_text(row["Notes"]),
            other_notes=self._clean_text(row["Other notes"]),
            is_critical_mineral=self._parse_critical_status(row["Is critical mineral 2025"]),
            source=Source(
                name="USGS Mineral Commodity Summaries 2026 Data Release",
                publisher="U.S. Geological Survey",
                url=self.SOURCE_URL,
                doi=self.SOURCE_DOI,
            ),
        )

    @staticmethod
    def _parse_year(value: str) -> int | None:
        """Parse a four-digit year while preserving ranges separately."""
        if re.fullmatch(r"\d{4}", value):
            return int(value)

        return None

    @staticmethod
    def _parse_numeric_value(value: str) -> float | None:
        """
        Parse a numeric value while tolerating published qualifiers.

        Examples:
            "3,900,000" -> 3900000.0
            ">140,000,000" -> 140000000.0
            "<500" -> 500.0
            "W" -> None

        The exact published representation remains available in raw_value.
        """
        normalized = value.strip()

        if not normalized:
            return None

        normalized = normalized.replace(",", "")

        match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", normalized)

        if match is None:
            return None

        try:
            return float(match.group(0))
        except ValueError:
            return None

    @staticmethod
    def _parse_critical_status(value: object) -> bool | None:
        """Parse the USGS critical-mineral indicator."""
        text = USGSCommodityProvider._clean_text(value)

        if text is None:
            return None

        normalized = text.casefold()

        if normalized == "yes":
            return True

        if normalized == "no":
            return False

        # The observed "Yttrium" value appears source-specific/anomalous.
        return None

    @staticmethod
    def _clean_text(value: object) -> str | None:
        """Return stripped text or None for an empty value."""
        if value is None:
            return None

        text = str(value).strip()

        if not text or text.casefold() == "nan":
            return None

        return text

    @classmethod
    def _required_text(cls, value: object, field_name: str) -> str:
        """
        Return required text or raise a source-data error.

        Args:
            value (object):
                The value to clean and validate as required text.

            field_name (str):
                The name of the field being validated, used in the error message.

        Returns:
            str:
                The cleaned and validated text.

        Raises:
            ValueError:
                If the value is None or empty after cleaning, indicating missing
                required text.
        """
        text = cls._clean_text(value)

        if text is None:
            raise ValueError(f"USGS source row is missing {field_name}.")

        return text

    def resolve_commodity_name(self, commodity: str) -> str | None:
        """
        Resolve a SyntheScale commodity to a USGS commodity.

        Args:
            commodity (str):
                The SyntheScale commodity name to resolve.

        Returns:
            str | None:
                The corresponding USGS commodity name if found, otherwise None.
        """
        return self.COMMODITY_ALIASES.get(commodity.casefold().strip())
