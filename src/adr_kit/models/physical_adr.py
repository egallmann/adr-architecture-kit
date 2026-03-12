"""Pydantic models for Physical ADRs."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common import ADRFrontmatter, ADRType, Alternative, Gap


class TechnologyChoice(BaseModel):
    """Technology stack choice with rationale."""
    category: str = Field(..., pattern=r"^(language|framework|library|database|messaging|infrastructure|tooling)$")
    name: str
    version: str
    rationale: str


class ArchitecturePattern(BaseModel):
    """Architecture pattern application."""
    pattern_name: str
    application: str
    components_affected: List[str] = Field(default_factory=list)


class Interface(BaseModel):
    """Component interface specification."""
    id: str = Field(..., pattern=r"^IFACE-\d{4}$")
    type: str = Field(..., pattern=r"^(REST|gRPC|GraphQL|message|event|stream|batch)$")
    specification: str
    contract_reference: Optional[str] = None


class ImplementationIdentifiers(BaseModel):
    """Identifiers for EDR matching and correction agent location."""
    service_name: Optional[str] = Field(None, description="Runtime service name")
    repository: Optional[str] = Field(None, description="Source control repository")
    module_path: Optional[str] = Field(None, description="Code location")
    deployment_name: Optional[str] = Field(None, description="Deployment identifier")


class ComponentSpecification(BaseModel):
    """Component specification with implementation details."""
    id: str = Field(..., pattern=r"^COMP-\d{4}$")
    name: str
    type: str = Field(..., pattern=r"^(service|library|database|queue|cache|gateway|proxy|worker|scheduler)$")
    responsibilities: str
    
    interfaces: List[Interface] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    upstream_services: List[str] = Field(default_factory=list, description="For blast radius analysis")
    downstream_services: List[str] = Field(default_factory=list, description="For blast radius analysis")
    
    implements_capabilities: List[str] = Field(
        default_factory=list,
        description="Capabilities (CAP-XXXX) this component implements"
    )
    realizes_entities: List[str] = Field(
        default_factory=list,
        description="Other entities (BOUND, CONTRACT, etc.) this component realizes"
    )
    
    implementation_identifiers: Optional[ImplementationIdentifiers] = None


class DeploymentModel(BaseModel):
    """Deployment and orchestration model."""
    hosting: Optional[str] = Field(None, pattern=r"^(cloud|on-premise|hybrid|edge)$")
    orchestration: Optional[str] = None
    scaling_strategy: Optional[str] = None


class DataArchitecture(BaseModel):
    """Data architecture specification."""
    entity: str
    storage: str
    schema_definition: Optional[str] = Field(None, alias="schema")
    access_patterns: Optional[str] = None
    
    model_config = ConfigDict(populate_by_name=True)


class ImplementationDecision(BaseModel):
    """Implementation-level decision."""
    id: str = Field(..., pattern=r"^IMPL-\d{4}$")
    summary: str
    rationale: str
    implements_invariants: List[str] = Field(default_factory=list)
    alternatives_considered: List[Alternative] = Field(default_factory=list)


class IntegrationPoint(BaseModel):
    """Integration point between systems."""
    id: str = Field(..., pattern=r"^INTEG-\d{4}$")
    systems: List[str] = Field(..., min_length=2)
    protocol: str
    specification: str
    contract_adr: Optional[str] = Field(None, pattern=r"^ADR-(L|P|PS|PC|D)-\d{4}$")


class OperationalRequirements(BaseModel):
    """Operational requirements."""
    monitoring: Optional[str] = None
    logging: Optional[str] = None
    backup_recovery: Optional[str] = None
    security: Optional[str] = None


class PhysicalADR(ADRFrontmatter):
    """Physical ADR - implementation specifications."""
    
    adr_type: ADRType = Field(ADRType.PHYSICAL, frozen=True)
    id: str = Field(..., pattern=r"^ADR-P-\d{4}$")
    
    implements_logical: List[str] = Field(..., min_length=1)
    technologies: List[str] = Field(default_factory=list)
    
    @field_validator('implements_logical')
    @classmethod
    def validate_logical_ids(cls, v: List[str]) -> List[str]:
        """Validate that all IDs are logical ADR IDs."""
        import re
        pattern = re.compile(r"^ADR-L-\d{4}$")
        for id_val in v:
            if not pattern.match(id_val):
                raise ValueError(f"implements_logical must contain logical ADR IDs (ADR-L-XXXX), got {id_val}")
        return v
    
    context: str = Field(..., description="Implementation context and technology choices")
    
    technology_stack: List[TechnologyChoice] = Field(..., min_length=1)
    architecture_patterns: List[ArchitecturePattern] = Field(default_factory=list)
    component_specifications: List[ComponentSpecification] = Field(..., min_length=1)
    deployment_model: Optional[DeploymentModel] = None
    data_architecture: List[DataArchitecture] = Field(default_factory=list)
    implementation_decisions: List[ImplementationDecision] = Field(default_factory=list)
    integration_points: List[IntegrationPoint] = Field(default_factory=list)
    operational_requirements: Optional[OperationalRequirements] = None
    gaps: List[Gap] = Field(default_factory=list)
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "schema_version": "1.0",
                "adr_type": "physical",
                "id": "ADR-P-0001",
                "title": "Python Toolkit Implementation",
                "status": "accepted",
                "created_date": "2026-03-07",
                "authors": ["erik.gallmann"],
                "domains": ["implementation", "tooling"],
                "implements_logical": ["ADR-L-0001"],
                "technologies": ["python", "pydantic", "yaml"],
                "context": "Implement ADR Kit using Python ecosystem...",
                "technology_stack": [{
                    "category": "language",
                    "name": "Python",
                    "version": "3.10+",
                    "rationale": "Strong typing, excellent libraries, wide adoption"
                }],
                "component_specifications": [{
                    "id": "COMP-0001",
                    "name": "Schema Validator",
                    "type": "library",
                    "responsibilities": "Validate ADRs against JSON Schema"
                }]
            }]
        }
    )
