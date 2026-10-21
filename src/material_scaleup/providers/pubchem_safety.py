# src/material_scaleup/providers/pubchem_safety.py

from collections.abc import Iterable
from typing import Any

import requests

from material_scaleup.models.categories import AssessmentCategory, EvidenceStatus
from material_scaleup.models.chemical import ChemicalIdentity
from material_scaleup.models.evidence import Evidence, EvidenceValue
from material_scaleup.models.scenario import ScaleUpScenario
from material_scaleup.models.source import Source, SourceLocation
from material_scaleup.providers.base import EvidenceProvider

__all__ = [
    "PubChemSafetyProvider",
]


class PubChemSafetyProvider(EvidenceProvider):
    """Retrieve GHS safety evidence using PubChem PUG-View."""

    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def get_evidence(self, scenario: ScaleUpScenario) -> list[Evidence]:
        """
        Retrieve safety evidence for chemicals in a scenario.

        For the initial implementation, synthesis-route inputs are assessed.

        Args:
            scenario (ScaleUpScenario):
                The scale-up scenario for which to retrieve safety evidence.

        Returns:
            list[Evidence]:
                A list of evidence records related to the safety of chemicals in the scenario.
        """
        route = scenario.synthesis_route

        if route is None:
            return []

        evidence: list[Evidence] = []

        for process_input in route.inputs:
            evidence.extend(self.get_chemical_evidence(process_input.chemical))

        return evidence

    def get_chemical_evidence(self, chemical: ChemicalIdentity) -> list[Evidence]:
        """
        Retrieve GHS safety evidence for one chemical.

        Args:
            chemical (ChemicalIdentity):
                The chemical for which to retrieve GHS safety evidence.

        Returns:
            list[Evidence]:
                A list of evidence records related to the GHS safety of the
                chemical.
        """
        if chemical.pubchem_cid is None:
            return [self._missing_cid_evidence(chemical)]

        cid = chemical.pubchem_cid

        url = f"{self.BASE_URL}/data/compound/{cid}/JSON"

        response = requests.get(
            url,
            params={"heading": "GHS Classification"},
            timeout=self.timeout,
        )

        if response.status_code == 404:
            return [self._not_found_evidence(chemical)]

        response.raise_for_status()

        payload = response.json()

        return self._parse_ghs_evidence(
            chemical=chemical,
            payload=payload,
            source_url=response.url,
        )

    def _parse_ghs_evidence(
        self,
        chemical: ChemicalIdentity,
        payload: dict[str, Any],
        source_url: str,
    ) -> list[Evidence]:
        """
        Convert a PubChem GHS response into Evidence records.

        Args:
            chemical (ChemicalIdentity):
                The chemical for which to retrieve GHS safety evidence.

            payload (dict[str, Any]):
                The JSON payload returned by the PubChem API.

            source_url (str):
                The URL from which the payload was retrieved.

        Returns:
            list[Evidence]:
                A list of evidence records related to the GHS safety of the
                chemical.
        """
        information_nodes = self._find_ghs_information(payload)

        if not information_nodes:
            return [self._not_found_evidence(chemical)]

        evidence: list[Evidence] = []

        for node in information_nodes:
            name = node.get("Name")

            if name == "Signal":
                evidence.extend(
                    self._make_text_evidence(
                        chemical=chemical,
                        claim="GHS signal word",
                        values=self._extract_strings(node),
                        source_url=source_url,
                    )
                )

            elif name == "GHS Hazard Statements":
                evidence.extend(
                    self._make_text_evidence(
                        chemical=chemical,
                        claim="GHS hazard statement",
                        values=self._extract_strings(node),
                        source_url=source_url,
                    )
                )

            elif name == "Pictogram(s)":
                evidence.extend(
                    self._make_text_evidence(
                        chemical=chemical,
                        claim="GHS pictogram",
                        values=self._extract_pictograms(node),
                        source_url=source_url,
                    )
                )

        if not evidence:
            return [self._not_found_evidence(chemical)]

        return evidence

    @classmethod
    def _find_ghs_information(
        cls,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Find Information records beneath GHS Classification sections.

        Args:
            payload (dict[str, Any]):
                The JSON payload returned by the PubChem API.

        Returns:
            list[dict[str, Any]]:
                A list of information records found under GHS Classification
                sections.
        """
        record = payload.get("Record")

        if not isinstance(record, dict):
            return []

        sections = record.get("Section", [])

        if not isinstance(sections, list):
            return []

        return cls._find_information_in_sections(sections)

    @classmethod
    def _find_information_in_sections(
        cls,
        sections: Iterable[object],
    ) -> list[dict[str, Any]]:
        """
        Recursively search PubChem sections for GHS information.

        Args:
            sections (Iterable[object]):
                The sections to search.

        Returns:
            list[dict[str, Any]]:
                A list of information records found under GHS Classification
                sections.
        """
        results: list[dict[str, Any]] = []

        for section in sections:
            if not isinstance(section, dict):
                continue

            if section.get("TOCHeading") == "GHS Classification":
                information = section.get("Information", [])

                if isinstance(information, list):
                    results.extend(item for item in information if isinstance(item, dict))

            child_sections = section.get("Section", [])

            if isinstance(child_sections, list):
                results.extend(cls._find_information_in_sections(child_sections))

        return results

    @staticmethod
    def _extract_strings(node: dict[str, Any]) -> list[str]:
        """
        Extract plain strings from a PubChem Information node.

        Args:
            node (dict[str, Any]):
                The PubChem Information node to extract strings from.

        Returns:
            list[str]:
                A list of extracted plain strings.
        """
        value = node.get("Value")

        if not isinstance(value, dict):
            return []

        strings = value.get("StringWithMarkup", [])

        if not isinstance(strings, list):
            return []

        results: list[str] = []

        for item in strings:
            if not isinstance(item, dict):
                continue

            text = item.get("String")

            if isinstance(text, str) and text.strip():
                results.append(text.strip())

        return results

    @staticmethod
    def _extract_pictograms(node: dict[str, Any]) -> list[str]:
        """
        Extract human-readable GHS pictogram names.

        Args:
            node (dict[str, Any]):
                The PubChem Information node to extract pictogram names from.

        Returns:
            list[str]:
                A list of extracted human-readable GHS pictogram names.
        """
        value = node.get("Value")

        if not isinstance(value, dict):
            return []

        strings = value.get("StringWithMarkup", [])

        if not isinstance(strings, list):
            return []

        results: list[str] = []

        for item in strings:
            if not isinstance(item, dict):
                continue

            markup = item.get("Markup", [])

            if not isinstance(markup, list):
                continue

            for entry in markup:
                if not isinstance(entry, dict):
                    continue

                extra = entry.get("Extra")

                if isinstance(extra, str) and extra.strip():
                    results.append(extra.strip())

        return list(dict.fromkeys(results))

    @staticmethod
    def _chemical_label(chemical: ChemicalIdentity) -> str:
        """
        Return the most useful available chemical label.

        Args:
            chemical (ChemicalIdentity):
                The chemical identity to generate a label for.

        Returns:
            str:
                The most useful available chemical label.
        """
        return (
            chemical.name
            or chemical.formula
            or chemical.cas_rn
            or chemical.inchikey
            or f"PubChem CID {chemical.pubchem_cid}"
        )

    def _make_text_evidence(
        self,
        chemical: ChemicalIdentity,
        claim: str,
        values: list[str],
        source_url: str,
    ) -> list[Evidence]:
        """
        Create Evidence records from extracted PubChem values.

        Args:
            chemical (ChemicalIdentity):
                The chemical identity the evidence pertains to.

            claim (str):
                The claim being made about the chemical.

            values (list[str]):
                The extracted PubChem values supporting the claim.

            source_url (str):
                The URL of the PubChem source page.

        Returns:
            list[Evidence]:
                A list of Evidence records created from the extracted values.
        """
        chemical_label = self._chemical_label(chemical)

        source = Source(
            name="PubChem",
            publisher="National Library of Medicine",
            url=source_url,
            location=SourceLocation(section="GHS Classification"),
        )

        return [
            Evidence(
                category=AssessmentCategory.SAFETY,
                claim=f"{claim} for {chemical_label}",
                reported_value=EvidenceValue(value=value),
                source=source,
                metadata={
                    "pubchem_cid": chemical.pubchem_cid,
                    "chemical": chemical_label,
                },
            )
            for value in values
        ]

    def _missing_cid_evidence(
        self,
        chemical: ChemicalIdentity,
    ) -> Evidence:
        """
        Report that PubChem safety lookup cannot run without a CID.

        Args:
            chemical (ChemicalIdentity):
                The chemical identity for which the lookup cannot be performed.

        Returns:
            Evidence:
                An Evidence record indicating the lookup could not be performed
                due to missing CID.
        """
        chemical_label = self._chemical_label(chemical)

        return Evidence(
            category=AssessmentCategory.SAFETY,
            claim=f"PubChem safety lookup unavailable for {chemical_label}",
            status=EvidenceStatus.NOT_FOUND,
            notes="Chemical identity does not contain a PubChem CID.",
            metadata={"chemical": chemical_label},
        )

    def _not_found_evidence(self, chemical: ChemicalIdentity) -> Evidence:
        """
        Report absence of GHS classification data.

        Args:
            chemical (ChemicalIdentity):
                The chemical identity for which GHS classification data is absent.

        Returns:
            Evidence:
                An Evidence record indicating the absence of GHS classification
                data.
        """
        chemical_label = self._chemical_label(chemical)

        return Evidence(
            category=AssessmentCategory.SAFETY,
            claim=f"No PubChem GHS classification was found for {chemical_label}",
            status=EvidenceStatus.NOT_FOUND,
            notes=(
                "Absence of PubChem GHS data must not be interpreted "
                "as evidence that the chemical is safe."
            ),
            metadata={
                "pubchem_cid": chemical.pubchem_cid,
                "chemical": chemical_label,
            },
        )
