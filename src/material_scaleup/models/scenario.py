
# src/material_scaleup/models/scenario.py

from pydantic import BaseModel, Field, model_validator

from material_scaleup.models.categories import RouteOrigin
from material_scaleup.models.chemical import ChemicalIdentity, MaterialSpec

__all__ = [
    "ApplicationSpec",
    "LocationSpec",
    "ProcessInput",
    "ProcessStep",
    "ProductionTarget",
    "ScaleUpScenario",
    "SynthesisRoute",
]

class LocationSpec(BaseModel):
    """
    Location in which production is being considered.
    
    At least one of country, region, or locality must be specified.

    Attributes:
        country (str | None):
            Country in which production is being considered.

        region (str | None):
            Region in which production is being considered.

        locality (str | None):
            Locality in which production is being considered.
    """
    country: str | None = None
    region: str | None = None
    locality: str | None = None

    @model_validator(mode="after")
    def require_location_value(self) -> "LocationSpec":
        if not any((self.country, self.region, self.locality)):
            raise ValueError("At least one location field must be provided.")

        return self

class ApplicationSpec(BaseModel):
    """
    Intended application and its relevant requirements.
    
    Attributes:
        name (str):
            Name of the intended application.

        description (str | None):
            Description of the intended application.

        requirements (list[str]):
            List of specific requirements for the application.
    """
    name: str
    description: str | None = None
    requirements: list[str] = Field(default_factory=list)

class ProductionTarget(BaseModel):
    """
    Target production quantity and time basis.
    
    Attributes:
        amount (float):
            Target production amount. Must be greater than 0.

        units (str):
            Units for the target production amount.

        period (str | None):
            Time period for the target production amount.

        batches_per_period (int | None):
            Number of batches per period. Must be at least 1 if specified.
    """
    amount: float = Field(gt=0)
    units: str
    period: str | None = None
    batches_per_period: int | None = Field(default=None, ge=1)

class ProcessInput(BaseModel):
    """
    Chemical, solvent, reagent, utility, or other process input.
    
    Attributes:
        chemical (ChemicalIdentity):
            Identity of the chemical input.

        role (str | None):
            Role of the input in the process.

        amount (float | None):
            Amount of the input. Must be non-negative if specified.

        units (str | None):
            Units for the input amount.

        stoichiometric_coefficient (float | None):
            Stoichiometric coefficient for the input. Must be greater than 0 if
            specified.

        purity (float | None):
            Purity of the input. Must be between 0 and 1 if specified.

        recoverable (bool | None):
            Indicates if the input is recoverable.
    """
    chemical: ChemicalIdentity
    role: str | None = None
    amount: float | None = Field(default=None, ge=0)
    units: str | None = None
    stoichiometric_coefficient: float | None = Field(default=None, gt=0)
    purity: float | None = Field(default=None, gt=0, le=1)
    recoverable: bool | None = None

class ProcessStep(BaseModel):
    """
    An individual operation in a synthesis or production route.
    
    Attributes:
        name (str):
            Name of the process step.

        description (str | None):
            Description of the process step.

        operation (str | None):
            Operation performed in the process step.

        temperature (float | None):
            Temperature at which the process step is carried out.

        temperature_units (str | None):
            Units for the temperature.

        pressure (float | None):
            Pressure at which the process step is carried out.

        pressure_units (str | None):
            Units for the pressure.

        duration (float | None):
            Duration of the process step. Must be non-negative if specified.

        duration_units (str | None):
            Units for the duration.

        atmosphere (str | None):
            Atmosphere under which the process step is carried out.

        equipment (list[str]):
            List of equipment used in the process step.

        inputs (list[ProcessInput]):
            List of inputs for the process step.

        expected_yield (float | None):
            Expected yield of the process step. Must be between 0 and 1 if
            specified.
    """
    name: str
    description: str | None = None
    operation: str | None = None
    temperature: float | None = None
    temperature_units: str | None = None
    pressure: float | None = None
    pressure_units: str | None = None
    duration: float | None = Field(default=None, ge=0)
    duration_units: str | None = None
    atmosphere: str | None = None
    equipment: list[str] = Field(default_factory=list)
    inputs: list[ProcessInput] = Field(default_factory=list)
    expected_yield: float | None = Field(default=None, ge=0, le=1)

class SynthesisRoute(BaseModel):
    """
    Known, proposed, or predicted route for producing a material.
    
    Attributes:
        name (str):
            Name of the synthesis route.

        origin (RouteOrigin):
            Origin of the synthesis route.

        description (str | None):
            Description of the synthesis route.

        inputs (list[ProcessInput]):
            List of inputs for the synthesis route.

        steps (list[ProcessStep]):
            List of process steps in the synthesis route.

        wastes (list[str]):
            List of wastes generated in the synthesis route.

        assumptions (list[str]):
            List of assumptions made in the synthesis route.

        demonstrated_scale (float | None):
            Demonstrated scale of the synthesis route. Must be non-negative if
            specified.

        demonstrated_scale_units (str | None):
            Units for the demonstrated scale.
    """
    name: str
    origin: RouteOrigin = RouteOrigin.UNKNOWN
    description: str | None = None
    inputs: list[ProcessInput] = Field(default_factory=list)
    steps: list[ProcessStep] = Field(default_factory=list)
    wastes: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    demonstrated_scale: float | None = Field(default=None, ge=0)
    demonstrated_scale_units: str | None = None

class ScaleUpScenario(BaseModel):
    """
    Material and production scenario submitted for assessment.
    
    Attributes:
        material (MaterialSpec):
            Specification of the material being assessed.

        application (ApplicationSpec | None):
            Specification of the application for which the material is intended.

        production_location (LocationSpec | None):
            Location where the material is intended to be produced.

        production_target (ProductionTarget | None):
            Target production parameters for the material.

        synthesis_route (SynthesisRoute | None):
            Synthesis route for producing the material.
    """
    material: MaterialSpec
    application: ApplicationSpec | None = None
    production_location: LocationSpec | None = None
    production_target: ProductionTarget | None = None
    synthesis_route: SynthesisRoute | None = None
