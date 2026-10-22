#!/usr/bin/env python3

# scripts/download_data.py

import argparse
import csv
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from zipfile import BadZipFile, ZipFile

import requests
from openpyxl import load_workbook


SCRIPT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_DIR.parent
DATA_ROOT = REPOSITORY_ROOT / "data" / "raw"


WORLD_BANK_MONTHLY_PRICES_URL = (
    "https://thedocs.worldbank.org/en/doc/"
    "74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/"
    "related/CMO-Historical-Data-Monthly.xlsx"
)

WORLD_BANK_OUTPUT_PATH = (
    DATA_ROOT
    / "world_bank"
    / "CMO-Historical-Data-Monthly.xlsx"
)

REQUIRED_WORLD_BANK_SHEETS = {
    "Monthly Prices",
    "Monthly Indices",
    "Description",
}


USGS_RELEASE_ITEM_ID = "696a75d5d4be0228872d3bf8"

USGS_SALIENT_ITEM_ID = "69837e43b66b01367d7ec7c7"

SCIENCEBASE_ITEM_URL = (
    "https://www.sciencebase.gov/catalog/item/{item_id}"
    "?format=json"
)

USGS_OUTPUT_DIRECTORY = (
    DATA_ROOT
    / "usgs"
    / "mcs2026"
)

USGS_REQUIRED_FILE = "MCS2026_Commodities_Data.csv"

USGS_SELECTED_FILES = {
    "MCS2026_Commodities_Data.csv",
}

XLSX_SIGNATURE = b"PK"


def download_file(
    url: str,
    destination: Path,
    *,
    force: bool = False,
    timeout: float = 60.0,
) -> Path:
    """
    Download a file atomically.

    The file is first written to a temporary location and moved into
    place only after the download succeeds.
    """

    if destination.exists() and not force:
        print(f"Already present: {destination}")
        return destination

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"Downloading: {url}")
    print(f"Destination: {destination.resolve()}")

    temporary_path: Path | None = None

    try:
        with requests.get(
            url,
            stream=True,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "SyntheScale/0.1 "
                    "(materials scale-up feasibility prototype)"
                )
            },
        ) as response:
            response.raise_for_status()

            with NamedTemporaryFile(
                mode="wb",
                prefix=f".{destination.name}.",
                suffix=".tmp",
                dir=destination.parent,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)

                for chunk in response.iter_content(
                    chunk_size=1024 * 1024,
                ):
                    if chunk:
                        temporary_file.write(chunk)

                temporary_file.flush()
                os.fsync(temporary_file.fileno())

        if temporary_path is None:
            raise RuntimeError(
                "Temporary download path was not created."
            )

        temporary_path.replace(destination)

    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

        raise

    print(
        f"Downloaded {destination.stat().st_size:,} bytes."
    )

    return destination


def get_json(
    url: str,
    *,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Retrieve and validate a JSON response."""

    print(f"Reading metadata: {url}")

    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": (
                "SyntheScale/0.1 "
                "(materials scale-up feasibility prototype)"
            )
        },
    )

    response.raise_for_status()

    payload = response.json()

    if not isinstance(payload, dict):
        raise ValueError(
            f"Expected a JSON object from {url}."
        )

    return payload


def validate_world_bank_workbook(
    path: Path,
) -> None:
    """Validate that the download is an expected World Bank workbook."""

    if not path.exists():
        raise FileNotFoundError(
            f"Downloaded workbook does not exist: {path}"
        )

    if path.stat().st_size == 0:
        raise ValueError(
            f"Downloaded workbook is empty: {path}"
        )

    with path.open("rb") as handle:
        signature = handle.read(2)

    if signature != XLSX_SIGNATURE:
        raise ValueError(
            "Downloaded file is not an XLSX workbook. "
            "The server may have returned an HTML error page."
        )

    try:
        with ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError(
                    f"Downloaded XLSX archive is corrupt: {path}"
                )

    except BadZipFile as error:
        raise ValueError(
            f"Downloaded file is not a valid XLSX archive: {path}"
        ) from error

    workbook = load_workbook(
        path,
        read_only=True,
        data_only=True,
    )

    try:
        available_sheets = set(workbook.sheetnames)

    finally:
        workbook.close()

    missing_sheets = (
        REQUIRED_WORLD_BANK_SHEETS - available_sheets
    )

    if missing_sheets:
        missing = ", ".join(
            sorted(missing_sheets)
        )

        raise ValueError(
            "World Bank workbook is missing expected sheets: "
            f"{missing}"
        )

    print("World Bank workbook validation passed.")
    print(
        "Available sheets: "
        + ", ".join(sorted(available_sheets))
    )


def download_world_bank_data(
    *,
    force: bool = False,
) -> Path:
    """Download and validate World Bank monthly commodity prices."""

    path = download_file(
        WORLD_BANK_MONTHLY_PRICES_URL,
        WORLD_BANK_OUTPUT_PATH,
        force=force,
    )

    validate_world_bank_workbook(path)

    return path


def get_sciencebase_files(
    item_id: str,
) -> list[dict[str, Any]]:
    """Return downloadable file records from a ScienceBase item."""

    metadata_url = SCIENCEBASE_ITEM_URL.format(
        item_id=item_id,
    )

    payload = get_json(metadata_url)

    files = payload.get("files", [])

    if not isinstance(files, list):
        raise ValueError(
            f"ScienceBase item {item_id} has invalid file metadata."
        )

    return [
        file_record
        for file_record in files
        if isinstance(file_record, dict)
    ]


def sciencebase_download_url(
    file_record: dict[str, Any],
) -> str:
    """Extract the preferred download URL from a ScienceBase file."""

    for key in (
        "downloadUri",
        "url",
    ):
        value = file_record.get(key)

        if isinstance(value, str) and value:
            return value

    raise ValueError(
        "ScienceBase file record does not contain a download URL."
    )


def sciencebase_file_name(
    file_record: dict[str, Any],
) -> str:
    """Extract a file name from a ScienceBase file record."""

    name = file_record.get("name")

    if not isinstance(name, str) or not name:
        raise ValueError(
            "ScienceBase file record does not contain a file name."
        )

    return name


def detect_csv_encoding(
    path: Path,
) -> str:
    """Detect a supported text encoding for a CSV file."""

    encodings = (
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin-1",
    )

    sample = path.read_bytes()[:64_000]

    for encoding in encodings:
        try:
            sample.decode(encoding)
        except UnicodeDecodeError:
            continue

        return encoding

    raise ValueError(
        f"Could not determine text encoding for CSV: {path}"
    )


def validate_csv(
    path: Path,
) -> None:
    """Perform basic validation of a downloaded CSV file."""

    if not path.exists():
        raise FileNotFoundError(
            f"Downloaded CSV does not exist: {path}"
        )

    if path.stat().st_size == 0:
        raise ValueError(
            f"Downloaded CSV is empty: {path}"
        )

    encoding = detect_csv_encoding(path)

    with path.open(
        "r",
        encoding=encoding,
        newline="",
    ) as handle:
        reader = csv.reader(handle)

        try:
            header = next(reader)

        except StopIteration as error:
            raise ValueError(
                f"Downloaded CSV contains no rows: {path}"
            ) from error

    if not header:
        raise ValueError(
            f"Downloaded CSV has an empty header: {path}"
        )

    print(
        f"CSV validation passed: {path.name} "
        f"(encoding={encoding}, columns={len(header)})"
    )


def download_sciencebase_files(
    item_id: str,
    destination: Path,
    *,
    selected_names: set[str] | None = None,
    force: bool = False,
) -> list[Path]:
    """Download selected attached files from a ScienceBase item."""

    file_records = get_sciencebase_files(item_id)

    if not file_records:
        raise ValueError(
            f"ScienceBase item {item_id} contains no files."
        )

    available_names = {
        sciencebase_file_name(record)
        for record in file_records
    }

    if selected_names is not None:
        missing_names = selected_names - available_names

        if missing_names:
            print(
                "Warning: requested files not attached to this "
                "ScienceBase item: "
                + ", ".join(sorted(missing_names)),
                file=sys.stderr,
            )

    downloaded: list[Path] = []

    for file_record in file_records:
        name = sciencebase_file_name(file_record)

        if (
            selected_names is not None
            and name not in selected_names
        ):
            continue

        url = sciencebase_download_url(file_record)

        path = download_file(
            url,
            destination / name,
            force=force,
        )

        if path.suffix.casefold() == ".csv":
            validate_csv(path)

        downloaded.append(path)

    return downloaded


def download_usgs_data(
    *,
    force: bool = False,
) -> list[Path]:
    """Download selected USGS MCS 2026 commodity datasets."""

    USGS_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    downloaded = download_sciencebase_files(
        item_id=USGS_SALIENT_ITEM_ID,
        destination=USGS_OUTPUT_DIRECTORY,
        selected_names=USGS_SELECTED_FILES,
        force=force,
    )

    main_file = (
        USGS_OUTPUT_DIRECTORY
        / USGS_REQUIRED_FILE
    )

    if not main_file.exists():
        raise FileNotFoundError(
            "The expected USGS commodity data file was not "
            f"downloaded: {main_file}"
        )

    print("USGS MCS 2026 data validation passed.")
    print("Downloaded USGS files:")

    for path in downloaded:
        print(f"  - {path.resolve()}")

    return downloaded


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download external datasets required by SyntheScale."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace datasets that already exist.",
    )

    parser.add_argument(
        "--world-bank",
        action="store_true",
        help="Download World Bank commodity-price data.",
    )

    parser.add_argument(
        "--usgs",
        action="store_true",
        help="Download USGS MCS 2026 commodity data.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    selected_any = (
        args.world_bank
        or args.usgs
    )

    download_world_bank = (
        args.world_bank
        or not selected_any
    )

    download_usgs = (
        args.usgs
        or not selected_any
    )

    try:
        if download_world_bank:
            download_world_bank_data(
                force=args.force,
            )

        if download_usgs:
            download_usgs_data(
                force=args.force,
            )

    except (
        OSError,
        requests.RequestException,
        ValueError,
    ) as error:
        print(
            f"Data download failed: {error}",
            file=sys.stderr,
        )
        return 1

    print("SyntheScale data setup complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
