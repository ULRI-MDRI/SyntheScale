
# src/material_scaleup/providers.py/base.py

from abc import ABC, abstractmethod

from material_scaleup.models.chemical import ChemicalIdentity
from material_scaleup.models.evidence import Evidence

__all__ = [
    "ChemicalIdentityProvider",
    "EvidenceProvider",
]

class ChemicalIdentityProvider(ABC):
    """Provider capable of resolving chemical identity information."""

    @abstractmethod
    def get_by_cas_rn(self, cas_rn: str) -> ChemicalIdentity:
        ...

class EvidenceProvider(ABC):
    """Provider capable of retrieving scale-up evidence."""

    @abstractmethod
    def get_evidence(
        self,
        chemical: ChemicalIdentity,
    ) -> list[Evidence]:
        ...
