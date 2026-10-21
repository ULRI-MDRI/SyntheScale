
# src/material_scaleup/providers/base.py

from abc import ABC, abstractmethod

from material_scaleup.models.chemical import ChemicalIdentity
from material_scaleup.models.evidence import Evidence
from material_scaleup.models.scenario import ScaleUpScenario

__all__ = [
    "ChemicalIdentityProvider",
    "EvidenceProvider",
]

class ChemicalIdentityProvider(ABC):
    """Provider capable of resolving chemical identity information."""
    @abstractmethod
    def get_by_cas_rn(self, cas_rn: str) -> ChemicalIdentity:
        """
        Resolve a chemical using a CAS Registry Number.
        
        Args:
            cas_rn (str):
                The CAS Registry Number of the chemical to resolve.

        Returns:
            ChemicalIdentity:
                The resolved chemical identity.

        Raises:
            NotImplementedError:
                If the method is not implemented by the provider.
        """
        raise NotImplementedError

class EvidenceProvider(ABC):
    """Provider capable of retrieving scale-up evidence."""
    @abstractmethod
    def get_evidence(
        self,
        scenario: ScaleUpScenario,
    ) -> list[Evidence]:
        """
        Retrieve evidence relevant to a scale-up scenario.
        
        Args:
            scenario (ScaleUpScenario):
                The scale-up scenario for which to retrieve evidence.

        Returns:
            list[Evidence]:
                A list of evidence items relevant to the scale-up scenario.

        Raises:
            NotImplementedError:
                If the method is not implemented by the provider.
        """
        raise NotImplementedError
    