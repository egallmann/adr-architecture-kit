"""Pydantic models for Physical-System ADRs."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import ADRFrontmatter, ADRType, Gap, ImpactLevel


class TechnologyChoice(BaseModel):
    """Technology stack choice with rationale."""
    category: str = Field(..., pattern=r"^(language|framework|library|database|messaging|infrastructure|tooling)$")
    name: str
    version: str
    rationale: str
    inferred: Optional[bool] = Field(None, description="True if inferred by Watchdog Agent")


class DeploymentModel(BaseModel):
    """Deployment and orchestration model."""
    hosting: Optional[str] = Field(None, pattern=r"^(cloud|on-premise|hybrid|edge)$")
    orchestration: Optional[str] = None
    scaling_strategy: Optional[str] = None


class OperationalRequirements(BaseModel):
    """Operational requirements."""
    monitoring: Optional[str] = None
    logging: Optional[str] = None
    backup_recovery: Optional[str] = None
    security: Optional[str] = None


class HumanDecision(BaseModel):
    """Human decision captured during conversation."""
    question: str
    decision: str
    rationale: Optional[str] = None


class ConversationMetadata(BaseModel):
    """Metadata about how ADR was created through conversation."""
    creation_method: Optional[str] = Field(None, pattern=r"^(ai_interview|human_written|migrated|watchdog_inferred)$")
    interview_transcript_ref: Optional[str] = None
    gaps_resolved: List[str] = Field(default_factory=list)
    human_decisions: List[HumanDecision] = Field(default_factory=list)
    context_signals: List[str] = Field(default_factory=list)
    activated_rules: List[str] = Field(default_factory=list)


class SystemBoundary(BaseModel):
    """System boundary definition."""
    id: str = Field(..., pattern=r"^SYSBOUND-\d{4}$")
    name: str
    description: str
    external_dependencies: List[str] = Field(default_factory=list)
    exposed_interfaces: List[str] = Field(default_factory=list)


class ComponentTopologyComponent(BaseModel):
    """Component in topology."""
    id: Optional[str] = Field(None, pattern=r"^TOPO-[A-Z0-9][A-Z0-9-]*$")
    name: str
    type: str = Field(..., pattern=r"^(service|database|queue|cache|gateway|proxy|worker|scheduler)$")
    purpose: str
    implements_adr: Optional[str] = Field(None, pattern=r"^ADR-PC-\d{4}$")


class ComponentRelationship(BaseModel):
    """Relationship between components."""
    from_component: str = Field(..., alias="from")
    to_component: str = Field(..., alias="to")
    type: str = Field(..., pattern=r"^(calls|publishes_to|subscribes_to|reads_from|writes_to|depends_on)$")
    protocol: Optional[str] = None
    description: Optional[str] = None
    
    model_config = ConfigDict(populate_by_name=True)


class ComponentTopology(BaseModel):
    """High-level component topology."""
    components: List[ComponentTopologyComponent] = Field(default_factory=list)
    relationships: List[ComponentRelationship] = Field(default_factory=list)


class IntegrationPattern(BaseModel):
    """Integration pattern application."""
    pattern_name: str
    application: str
    components_affected: List[str] = Field(default_factory=list)
    rationale: Optional[str] = None


class DataFlow(BaseModel):
    """High-level data flow."""
    id: str = Field(..., pattern=r"^FLOW-\d{4}$")
    name: str
    description: str
    path: List[str] = Field(default_factory=list, description="Component names in flow order")
    data_type: Optional[str] = None
    volume: Optional[str] = None
    latency_requirements: Optional[str] = None


class ScalabilityStrategy(BaseModel):
    """System-level scalability strategy."""
    horizontal_scaling: Optional[str] = None
    vertical_scaling: Optional[str] = None
    bottlenecks: List[str] = Field(default_factory=list)
    capacity_planning: Optional[str] = None


class FailureMode(BaseModel):
    """System-level failure mode."""
    scenario: str
    impact: ImpactLevel
    mitigation: str
    detection: Optional[str] = None
    recovery: Optional[str] = None


class PhysicalSystemADR(ADRFrontmatter):
    """Physical-System ADR - high-level system architecture."""
    
    adr_type: ADRType = Field(ADRType.PHYSICAL_SYSTEM, frozen=True)
    id: str = Field(..., pattern=r"^ADR-PS-\d{4}$")
    
    implements_logical: List[str] = Field(..., min_length=1)
    technologies: List[str] = Field(default_factory=list)
    
    context: str = Field(..., description="Implementation context and technology choices")
    
    technology_stack: List[TechnologyChoice] = Field(..., min_length=1)
    system_boundaries: List[SystemBoundary] = Field(..., min_length=1)
    
    component_topology: Optional[ComponentTopology] = None
    integration_patterns: List[IntegrationPattern] = Field(default_factory=list)
    data_flows: List[DataFlow] = Field(default_factory=list)
    references_components: List[str] = Field(default_factory=list)
    
    deployment_model: Optional[DeploymentModel] = None
    scalability_strategy: Optional[ScalabilityStrategy] = None
    failure_modes: List[FailureMode] = Field(default_factory=list)
    operational_requirements: Optional[OperationalRequirements] = None
    
    conversation_metadata: Optional[ConversationMetadata] = None
    gaps: List[Gap] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_v12_topology_references(self) -> "PhysicalSystemADR":
        """Require every v1.2 topology reference to resolve exactly once."""
        if self.schema_version != "1.2" or self.component_topology is None:
            return self
        components = self.component_topology.components
        ids = [item.id for item in components if item.id is not None]
        duplicate_ids = sorted({item for item in ids if ids.count(item) > 1})
        if duplicate_ids:
            raise ValueError(f"Duplicate topology IDs: {', '.join(duplicate_ids)}")

        def resolve(reference: str) -> None:
            candidates = {
                index
                for index, component in enumerate(components)
                if component.id == reference or component.name == reference
            }
            if len(candidates) != 1:
                raise ValueError(
                    f"Topology reference {reference!r} must resolve exactly once; "
                    f"resolved {len(candidates)} times"
                )

        for relationship in self.component_topology.relationships:
            resolve(relationship.from_component)
            resolve(relationship.to_component)
        for flow in self.data_flows:
            for reference in flow.path:
                resolve(reference)
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "schema_version": "1.0",
                "adr_type": "physical-system",
                "id": "ADR-PS-0001",
                "title": "User Service System Architecture",
                "status": "accepted",
                "created_date": "2026-03-10",
                "authors": ["erik.gallmann"],
                "domains": ["user-management", "authentication"],
                "implements_logical": ["ADR-L-0042"],
                "technologies": ["nodejs", "postgresql", "redis"],
                "context": "Microservice architecture for user management...",
                "technology_stack": [{
                    "category": "language",
                    "name": "Node.js",
                    "version": "20.x",
                    "rationale": "Excellent REST framework ecosystem"
                }],
                "system_boundaries": [{
                    "id": "SYSBOUND-0001",
                    "name": "User Service Boundary",
                    "description": "Encapsulates user management functionality"
                }]
            }]
        }
    )
