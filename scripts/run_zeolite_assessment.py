#!/usr/bin/env python3

# scripts/run_zeolite_assessment.py

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from material_scaleup.models.categories import RouteOrigin
from material_scaleup.models.chemical import MaterialSpec
from material_scaleup.models.scenario import (
    LocationSpec,
    ProcessInput,
    ProductionTarget,
    ScaleUpScenario,
    SynthesisRoute,
)
from material_scaleup.providers.pubchem import PubChemProvider
from material_scaleup.providers.pubchem_safety import PubChemSafetyProvider
from material_scaleup.providers.usgs import USGSCommodityProvider
from material_scaleup.providers.world_bank import WorldBankCommodityProvider
from material_scaleup.resolvers.commodity import CuratedCommodityResolver
from material_scaleup.services.context_builder import AssessmentContextBuilder
from material_scaleup.services.llm_context_builder import build_llm_context
from material_scaleup.services.openai_client import (
    create_assessment_generator_from_environment,
)


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_DIRECTORY.parent

WORLD_BANK_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "raw"
    / "world_bank"
    / "CMO-Historical-Data-Monthly.xlsx"
)

USGS_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "raw"
    / "usgs"
    / "mcs2026"
    / "MCS2026_Commodities_Data.csv"
)

OUTPUT_DIRECTORY = REPOSITORY_ROOT / "outputs"


def require_environment_variable(name: str) -> str:
    """Return a required environment variable."""

    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(
            f"Required environment variable {name!r} is not configured."
        )

    return value.strip()


def require_data_file(path: Path) -> None:
    """Raise a helpful error if an external dataset is missing."""

    if not path.exists():
        raise FileNotFoundError(
            f"Required dataset was not found: {path}\n"
            "Run `python scripts/download_data.py` first."
        )


def build_zeolite_scenario(
    identity_provider: PubChemProvider,
) -> ScaleUpScenario:
    """Build the Zeolite 13X prototype assessment scenario."""

    print("Resolving chemical identities through PubChem...")

    sodium_aluminate = identity_provider.get_by_name("sodium aluminate")
    sodium_silicate = identity_provider.get_by_name("sodium silicate")
    sodium_hydroxide = identity_provider.get_by_name("sodium hydroxide")
    water = identity_provider.get_by_name("water")

    return ScaleUpScenario(
        material=MaterialSpec(
            name="Zeolite 13X",
            description=(
                "Example aluminosilicate material used to demonstrate "
                "the SyntheScale evidence and assessment pipeline."
            ),
        ),
        production_location=LocationSpec(
            country="United States",
            region="Illinois",
        ),
        production_target=ProductionTarget(amount=1.0, units="kg"),
        synthesis_route=SynthesisRoute(
            name="Example hydrothermal synthesis",
            origin=RouteOrigin.USER_PROVIDED,
            description=(
                "Prototype route using sodium aluminate, sodium "
                "silicate, sodium hydroxide, and water. Exact "
                "stoichiometry, process conditions, and yield have "
                "not been supplied."
            ),
            inputs=[
                ProcessInput(
                    chemical=sodium_aluminate,
                    role="aluminum source",
                ),
                ProcessInput(
                    chemical=sodium_silicate,
                    role="silicon source",
                ),
                ProcessInput(
                    chemical=sodium_hydroxide,
                    role="mineralizer",
                ),
                ProcessInput(
                    chemical=water,
                    role="solvent",
                ),
            ],
            assumptions=[
                "The listed chemicals represent the principal "
                "prototype route inputs.",
                "Exact precursor quantities and synthesis yield "
                "remain unknown.",
            ],
        ),
    )


def write_json(path: Path, content: str) -> None:
    """Write JSON text to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n", encoding="utf-8")


def main() -> int:
    """Run the complete Zeolite 13X assessment pipeline."""

    try:
        model = require_environment_variable("SYNTHE_SCALE_MODEL")
        require_environment_variable("OPENAI_API_KEY")

        require_data_file(WORLD_BANK_PATH)
        require_data_file(USGS_PATH)

        identity_provider = PubChemProvider()

        scenario = build_zeolite_scenario(identity_provider)

        print("Building the full evidence context...")

        context_builder = AssessmentContextBuilder(
            commodity_resolver=CuratedCommodityResolver(),
            safety_provider=PubChemSafetyProvider(),
            world_bank_provider=WorldBankCommodityProvider(WORLD_BANK_PATH),
            usgs_provider=USGSCommodityProvider(USGS_PATH),
            market_history_months=60,
        )

        full_context = context_builder.build(scenario)

        print(f"Collected {len(full_context.evidence)} full evidence records.")

        llm_context = build_llm_context(full_context)

        llm_context_json = llm_context.model_dump_json(
            indent=2,
            exclude_none=True,
            exclude_defaults=True,
        )

        print(f"Compact LLM context size: {len(llm_context_json):,} characters.")
        print(f"Model: {model}")
        print("Generating structured assessment...")

        generator = create_assessment_generator_from_environment()

        llm_json = llm_context.model_dump_json(
            exclude_none=True,
            exclude_defaults=True,
        )

        print(f"LLM context characters: {len(llm_json):,}")
        print(f"Model: {generator.model}")
        print()

        assessment = generator.generate(llm_context)

        print(
            assessment.model_dump_json(
                indent=2,
                exclude_none=True,
            )
        )

        assessment_json = assessment.model_dump_json(
            indent=2,
            exclude_none=True,
        )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        run_directory = OUTPUT_DIRECTORY / f"zeolite_13x_{timestamp}"

        write_json(run_directory / "llm_context.json", llm_context_json)

        write_json(run_directory / "assessment.json", assessment_json)

        # Preserve the complete context separately for provenance.
        write_json(
            run_directory / "assessment_context.json",
            full_context.model_dump_json(indent=2, exclude_none=True),
        )

        print()
        print("Assessment complete.")
        print(f"Results directory: {run_directory.resolve()}")
        print()
        print(assessment_json)

        return 0

    except (
        FileNotFoundError,
        RuntimeError,
        ValueError,
    ) as error:
        print(f"SyntheScale assessment failed: {error}", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        print("\nAssessment interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
