"""Pydantic models for Entity Registry (v1.1)."""

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SourceArtifactType(str, Enum):
    """Source artifact type for derived registry entities."""

    LOGICAL_ADR = "logical_adr"
    PHYSICAL_ADR = "physical_adr"
    PHYSICAL_SYSTEM_ADR = "physical_system_adr"
    PHYSICAL_COMPONENT_ADR = "physical_component_adr"
    STANDALONE_INVARIANT = "standalone_invariant"


class EntityType(str, Enum):
    """Entity type enumeration."""
    CAPABILITY = "capability"
    BOUNDARY = "boundary"
    CONTRACT = "contract"
    CONSTRAINT = "constraint"
    NFR = "nfr"
    DECISION = "decision"
    GAP = "gap"
    COMPONENT = "component"
    INTERFACE = "interface"
    INTEGRATION = "integration"
    IMPLEMENTATION_DECISION = "implementation_decision"
    INVARIANT = "invariant"


class LifecycleStage(str, Enum):
    """Entity lifecycle stage."""
    PROPOSED = "proposed"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class EntityRelationships(BaseModel):
    """Forward-only entity relationships (inverse edges automatically derived)."""
    depends_on: Optional[List[str]] = Field(default_factory=list, description="Entity dependencies")
    implements: Optional[List[str]] = Field(default_factory=list, description="Entities this implements")
    consumes: Optional[List[str]] = Field(default_factory=list, description="Entities this consumes")
    realizes: Optional[List[str]] = Field(default_factory=list, description="Entities this realizes")


class EntityOwnership(BaseModel):
    """Ownership metadata derived from source artifacts."""

    architecture_authority: Optional[str] = None
    implementation_owners: Optional[List[str]] = Field(default_factory=list)


class Entity(BaseModel):
    """Architecture entity with lifecycle and relationships."""
    entity_id: str = Field(..., pattern=r"^[A-Z]+-\d{4}$", description="Entity ID (CAP-XXXX, COMP-XXXX, etc.)")
    entity_type: EntityType
    name: str = Field(..., description="Human-readable name")
    introduced_by: str = Field(..., pattern=r"^ADR-(L|V|P|PS|PC|D)-\d{4}$", description="ADR that introduced this entity")
    lifecycle_stage: LifecycleStage
    source_path: str = Field(..., description="Scope-relative canonical source artifact path")
    source_artifact_type: SourceArtifactType
    domains: Optional[List[str]] = Field(default_factory=list, description="Business/technical domains")
    related_adrs: Optional[List[str]] = Field(default_factory=list, description="Related ADR references for discovery")
    realized_by: Optional[List[str]] = Field(default_factory=list, description="ADRs or entities that operationalize this entity")
    ownership: Optional[EntityOwnership] = Field(default=None, description="Derived ownership metadata")
    relationships: Optional[EntityRelationships] = Field(default=None, description="Forward relationships only")


class EntityRegistry(BaseModel):
    """Canonical registry of all architecture entities across ADRs."""
    schema_version: Literal["1.1"] = "1.1"
    type: Literal["entity_registry"] = "entity_registry"
    entities: List[Entity] = Field(default_factory=list, description="All entities across all ADRs")
