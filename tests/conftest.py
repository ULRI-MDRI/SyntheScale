from pathlib import Path

import pandas as pd
import pytest

from material_scaleup.providers.usgs import USGSCommodityProvider
from material_scaleup.providers.world_bank import WorldBankCommodityProvider


@pytest.fixture
def local_world_bank_provider(tmp_path: Path) -> WorldBankCommodityProvider:
    path = tmp_path / "world_bank.xlsx"
    frame = pd.DataFrame(
        [
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, "Aluminum", "Phosphate rock", "Gold"],
            [None, "($/mt)", "($/mt)", "($/troy oz)"],
            ["2026M01", 100, 200, 300],
            ["2026M02", 110, 220, 330],
            ["2026M03", 105, 210, 315],
        ]
    )
    frame.to_excel(path, sheet_name="Monthly Prices", index=False, header=False)
    return WorldBankCommodityProvider(path)


@pytest.fixture
def local_usgs_provider(tmp_path: Path) -> USGSCommodityProvider:
    path = tmp_path / "usgs.csv"
    records = [
        {
            **dict.fromkeys(USGSCommodityProvider.REQUIRED_COLUMNS, ""),
            "Section": "World Mine Production and Reserves",
            "Commodity": commodity,
            "Country": "World total",
            "Statistics": "Production",
            "Unit": "metric tons",
            "Year": "2025",
            "Value": "1,000",
            "Is critical mineral 2025": "Yes",
        }
        for commodity in ["Aluminum", "Phosphate Rock", "Gold", "Silicon"]
    ]
    pd.DataFrame.from_records(records).to_csv(path, index=False)
    return USGSCommodityProvider(path)
