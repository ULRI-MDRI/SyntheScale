# src/material_scaleup/resolvers/commodity.py

from abc import ABC, abstractmethod

from material_scaleup.models.chemical import ChemicalIdentity
from material_scaleup.models.commodity import CommodityExposure

__all__ = [
    "CommodityResolver",
    "CuratedCommodityResolver",
]


class CommodityResolver(ABC):
    """Resolve chemical feedstocks to commodity exposures."""

    @abstractmethod
    def resolve(self, chemical: ChemicalIdentity) -> list[CommodityExposure]:
        """
        Return relevant commodity exposures for a chemical.

        Args:
            chemical (ChemicalIdentity):
                The chemical for which to resolve commodity exposures.

        Returns:
            list[CommodityExposure]:
                A list of commodity exposures relevant to the chemical.

        Raises:
            NotImplementedError:
                If the method is not implemented by a subclass.
        """
        raise NotImplementedError


class CuratedCommodityResolver(CommodityResolver):
    """
    Resolve commodities using a small curated mapping.

    This resolver uses a predefined mapping of chemical names and synonyms
    to their corresponding commodity exposures. This is intended to be
    expanded upon in the future, or replaced with a more comprehensive resolver.

    A smarter future approach is to implement a resolver, e.g. one that includes
    some of the following steps:

    Chemical
    ↓
    1. Curated exact match
    │ no match
    ↓
    2. Chemical composition analysis
    │
    ├── contains Co → cobalt
    ├── contains Ni → nickel
    ├── contains Zn → zinc
    └── ...
    ↓
    3. Commodity ontology / external database
    │
    ↓
    4. LLM-assisted candidate mapping
    │
    ↓
    validate against known provider commodities

    For example, the resolver can do composition analysis like:
    LiNi0.8Mn0.1Co0.1O2
    ↓
    Nickel
    Manganese
    Cobalt
    Lithium
    """

    MAPPING: dict[str, list[str]] = {
        # Aluminum
        "sodium aluminate": ["aluminum"],
        "aluminum sulfate": ["aluminum"],
        "aluminium sulfate": ["aluminum"],
        "aluminum nitrate": ["aluminum"],
        "aluminium nitrate": ["aluminum"],
        "aluminum oxide": ["aluminum"],
        "alumina": ["aluminum"],
        # Silicon
        "sodium silicate": ["silicon"],
        "silica": ["silicon"],
        "silicon dioxide": ["silicon"],
        # Nickel
        "nickel sulfate": ["nickel"],
        "nickel nitrate": ["nickel"],
        "nickel oxide": ["nickel"],
        # Cobalt
        "cobalt sulfate": ["cobalt"],
        "cobalt nitrate": ["cobalt"],
        "cobalt oxide": ["cobalt"],
        # Zinc
        "zinc oxide": ["zinc"],
        "zinc sulfate": ["zinc"],
        "zinc nitrate": ["zinc"],
        # Phosphorus
        "phosphoric acid": ["phosphate rock"],
        # Directly represented commodities
        "urea": ["urea"],
    }

    def resolve(self, chemical: ChemicalIdentity) -> list[CommodityExposure]:
        """
        Resolve a chemical using curated names and synonyms.

        Args:
            chemical (ChemicalIdentity):
                The chemical for which to resolve commodity exposures.

        Returns:
            list[CommodityExposure]:
                A list of commodity exposures relevant to the chemical.
        """

        names = self._candidate_names(chemical)

        commodities: set[str] = set()

        matched_name: str | None = None

        for name in names:
            mapped = self.MAPPING.get(name.casefold())

            if mapped:
                commodities.update(mapped)
                matched_name = name

        if not commodities:
            return []

        return [
            CommodityExposure(
                chemical=chemical,
                commodity=commodity,
                reason=(
                    f"Curated mapping from "
                    f"{matched_name or chemical.name or 'chemical'} "
                    f"to upstream {commodity} commodity exposure."
                ),
                confidence=1.0,
            )
            for commodity in sorted(commodities)
        ]

    @staticmethod
    def _candidate_names(chemical: ChemicalIdentity) -> list[str]:
        """
        Return names that may identify the chemical.

        Args:
            chemical (ChemicalIdentity):
                The chemical for which to generate candidate names.

        Returns:
            list[str]:
                A list of candidate names that may identify the chemical.
        """

        candidates: list[str] = []

        if chemical.name:
            candidates.append(chemical.name)

        candidates.extend(chemical.synonyms)

        return [candidate.strip() for candidate in candidates if candidate.strip()]
