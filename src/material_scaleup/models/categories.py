
# src/material_scaleup/models/categories.py

from enum import StrEnum

__all__ = [
    "AssessmentCategory",
    "AssessmentStatus",
    "EvidenceStatus",
    "Priority",
    "RouteOrigin",
]

class AssessmentCategory(StrEnum):
    """
    Categories considered in a scale-up feasibility assessment.

    Categories:
        - AVAILABILITY
        - COST
        - MARKET_VOLATILITY
        - SUPPLY_CHAIN
        - SAFETY
        - REGULATORY
        - PROCESS_SCALABILITY
        - ENVIRONMENTAL
        - INFRASTRUCTURE
        - WASTE
        - ETHICAL
    """
    AVAILABILITY = "availability"
    COST = "cost"
    MARKET_VOLATILITY = "market_volatility"
    SUPPLY_CHAIN = "supply_chain"
    SAFETY = "safety"
    REGULATORY = "regulatory"
    PROCESS_SCALABILITY = "process_scalability"
    ENVIRONMENTAL = "environmental"
    INFRASTRUCTURE = "infrastructure"
    WASTE = "waste"
    ETHICAL = "ethical"

class AssessmentStatus(StrEnum):
    """
    Status describing whether an assessment could be completed.
    
    Categories:
        - ASSESSED
        - INSUFFICIENT_DATA
        - NOT_APPLICABLE
        - ERROR
    """
    ASSESSED = "assessed"
    INSUFFICIENT_DATA = "insufficient_data"
    NOT_APPLICABLE = "not_applicable"
    ERROR = "error"

class EvidenceStatus(StrEnum):
    """
    Status describing the outcome of an evidence lookup.
    
    Categories:
        - AVAILABLE
        - NOT_FOUND
        - NOT_APPLICABLE
        - ERROR
    """
    AVAILABLE = "available"
    NOT_FOUND = "not_found"
    NOT_APPLICABLE = "not_applicable"
    ERROR = "error"

class Priority(StrEnum):
    """
    Priority assigned to a recommended validation action.
    
    Categories:
        - LOW
        - MEDIUM
        - HIGH
        - CRITICAL
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RouteOrigin(StrEnum):
    """
    Origin of a synthesis route.
    
    Categories:
        - USER_PROVIDED
        - EXPERIMENTAL
        - LITERATURE
        - COMPUTATIONAL
        - AI_PROPOSED
        - UNKNOWN
    """
    USER_PROVIDED = "user_provided"
    EXPERIMENTAL = "experimental"
    LITERATURE = "literature"
    COMPUTATIONAL = "computational"
    AI_PROPOSED = "ai_proposed"
    UNKNOWN = "unknown"
