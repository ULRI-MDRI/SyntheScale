# tests/providers/test_download_data.py

from scripts.download_data import (
    REPOSITORY_ROOT,
    WORLD_BANK_OUTPUT_PATH,
)


def test_world_bank_download_path_is_inside_repository():
    expected = REPOSITORY_ROOT / "data" / "raw" / "world_bank" / "CMO-Historical-Data-Monthly.xlsx"

    assert WORLD_BANK_OUTPUT_PATH == expected


def test_repository_root_contains_pyproject():
    assert (REPOSITORY_ROOT / "pyproject.toml").exists()


def test_download_path_is_absolute():
    assert WORLD_BANK_OUTPUT_PATH.is_absolute()
