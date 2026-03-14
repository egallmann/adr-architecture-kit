"""Pydantic models for derived architecture discovery artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DiscoveryProvenance(BaseModel):
    """Extraction provenance for a derived record."""

    source_type: str
    source_ref: str
    extraction_phase: str
    classification: str = Field(pattern=r"^(explicit|derived|heuristic)$")
    generator: str


class CanonicalSource(BaseModel):
    """Canonical source anchor for a normalized entity."""

    source_type: str
    source_ref: str
    artifact_path: str


class SourceRef(BaseModel):
    """Non-canonical mention of an entity."""

    source_type: str
    source_ref: str
    artifact_path: str
    mention_role: str


class Completeness(BaseModel):
    """Completeness state for a normalized entity."""

    status: str = Field(pattern=r"^(complete|partial|reference_only|conflicted)$")
    missing_fields: List[str] = Field(default_factory=list)


class EntityRelationshipSummary(BaseModel):
    """Local relationship summary attached to an entity."""

    declared_in: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    related_to: List[str] = Field(default_factory=list)
    enforces: List[str] = Field(default_factory=list)
    enabled_by: List[str] = Field(default_factory=list)
    enables: List[str] = Field(default_factory=list)
    governs: List[str] = Field(default_factory=list)
    implemented_by: List[str] = Field(default_factory=list)
    embodied_in: List[str] = Field(default_factory=list)
    supersedes: List[str] = Field(default_factory=list)
    superseded_by: List[str] = Field(default_factory=list)
    refines: List[str] = Field(default_factory=list)


class NormalizedEntity(BaseModel):
    """Normalized architecture discovery entity."""

    id: str
    entity_type: Literal["adr", "system", "component", "decision", "capability", "invariant"]
    name: str
    summary: str
    canonical_source: CanonicalSource
    source_refs: List[SourceRef] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    relationships: EntityRelationshipSummary = Field(default_factory=EntityRelationshipSummary)
    completeness: Completeness
    provenance: DiscoveryProvenance


class NormalizedEntityRegistry(BaseModel):
    """Registry of normalized architecture entities."""

    schema_version: str = "1.1"
    type: Literal["normalized_entity_registry"] = "normalized_entity_registry"
    entities: List[NormalizedEntity] = Field(default_factory=list)


class RelationshipRecord(BaseModel):
    """First-class relationship record."""

    relationship_id: str
    relationship_type: Literal[
        "declared_in",
        "references",
        "related_to",
        "enforces",
        "enabled_by",
        "enables",
        "governs",
        "implemented_by",
        "embodied_in",
        "supersedes",
        "superseded_by",
        "refines",
    ]
    from_entity_id: str
    to_entity_id: str
    provenance_classification: Literal["explicit", "derived", "heuristic"]
    evidence: List[str] = Field(default_factory=list)
    canonical_source_ref: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RelationshipRegistry(BaseModel):
    """Registry of normalized relationships."""

    schema_version: str = "1.1"
    type: Literal["relationship_registry"] = "relationship_registry"
    relationships: List[RelationshipRecord] = Field(default_factory=list)


class ArchitectureGraphNode(BaseModel):
    """Node record for the additive architecture graph artifact."""

    id: str
    entity_type: Literal["adr", "system", "component", "decision", "capability", "invariant"]
    name: str
    canonical_source: CanonicalSource


class ArchitectureGraphEdge(BaseModel):
    """Edge record for the additive architecture graph artifact."""

    relationship_id: str
    relationship_type: Literal[
        "declared_in",
        "references",
        "related_to",
        "enforces",
        "enabled_by",
        "enables",
        "governs",
        "implemented_by",
        "embodied_in",
        "supersedes",
        "superseded_by",
        "refines",
    ]
    source_entity_id: str
    target_entity_id: str
    provenance_classification: Literal["explicit", "derived", "heuristic"]
    evidence: List[str] = Field(default_factory=list)
    canonical_source_ref: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ArchitectureGraph(BaseModel):
    """Additive graph navigation artifact projected from compiler IR."""

    schema_version: str = "1.0"
    type: Literal["architecture_graph"] = "architecture_graph"
    architecture_namespace: str
    generated_at: datetime
    nodes: List[ArchitectureGraphNode] = Field(default_factory=list)
    edges: List[ArchitectureGraphEdge] = Field(default_factory=list)


class UnresolvedRecord(BaseModel):
    """Unresolved architecture signal."""

    id: str
    gap_class: Literal["author_declared", "generator_derived"]
    gap_type: str
    source_entity_id: str
    related_entity_id: Optional[str] = None
    expected_relationship: Optional[str] = None
    severity: Literal["critical", "important", "advisory"]
    provenance: DiscoveryProvenance
    evidence: List[str] = Field(default_factory=list)
    suggested_resolution: Optional[str] = None


class UnresolvedRegistry(BaseModel):
    """Registry of unresolved architecture signals."""

    schema_version: str = "1.1"
    type: Literal["unresolved_registry"] = "unresolved_registry"
    unresolved: List[UnresolvedRecord] = Field(default_factory=list)


class ValidationSummary(BaseModel):
    """Generation validation summary."""

    hard_failures: int = 0
    warnings: int = 0
    unresolved_entries: int = 0


class SourceCoverageSummary(BaseModel):
    """Coverage summary of discovered sources."""

    logical_adrs: int = 0
    physical_adrs: int = 0
    physical_system_adrs: int = 0
    physical_component_adrs: int = 0
    standalone_invariants: int = 0


class ArchitectureIndex(BaseModel):
    """Bootstrap index for architecture discovery."""

    schema_version: str = "1.1"
    type: Literal["architecture_index"] = "architecture_index"
    architecture_namespace: str
    generated_at: datetime
    generator: str
    entity_registry_path: str
    relationship_registry_path: str
    unresolved_registry_path: str
    decision_registry_path: str
    capability_registry_path: str
    invariant_registry_path: str
    component_registry_path: str
    system_registry_path: str
    validation_summary: ValidationSummary
    source_coverage: SourceCoverageSummary
