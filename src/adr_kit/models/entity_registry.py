"""Pydantic models for Entity Registry (v1.1)."""

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


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


class Entity(BaseModel):
    """Architecture entity with lifecycle and relationships."""
    entity_id: str = Field(..., pattern=r"^[A-Z]+-\d{4}$", description="Entity ID (CAP-XXXX, COMP-XXXX, etc.)")
    entity_type: EntityType
    name: str = Field(..., description="Human-readable name")
    introduced_by: str = Field(..., pattern=r"^ADR-(L|P|PS|PC|D)-\d{4}$", description="ADR that introduced this entity")
    lifecycle_stage: LifecycleStage
    domains: Optional[List[str]] = Field(default_factory=list, description="Business/technical domains")
    relationships: Optional[EntityRelationships] = Field(default=None, description="Forward relationships only")


class EntityRegistry(BaseModel):
    """Canonical registry of all architecture entities across ADRs."""
    schema_version: Literal["1.1"] = "1.1"
    type: Literal["entity_registry"] = "entity_registry"
    entities: List[Entity] = Field(default_factory=list, description="All entities across all ADRs")
