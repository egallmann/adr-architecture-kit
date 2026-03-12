"""Pydantic models for generated manifest."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import ImpactLevel, Status


class ManifestADREntry(BaseModel):
    """ADR entry in manifest (aggregated metadata)."""
    id: str = Field(..., pattern=r"^ADR-(L|P|PS|PC|D)-\d{4}$")
    type: str = Field(..., pattern=r"^(logical|physical|physical-system|physical-component|decision)$")
    title: str
    status: Status
    file_path: str
    
    domains: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    implements_logical: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    
    decision_count: int = Field(0, ge=0)
    invariant_count: int = Field(0, ge=0)
    gap_count: int = Field(0, ge=0)
    blocking_gaps: int = Field(0, ge=0)
    component_count: int = Field(0, ge=0)


class ManifestInvariant(BaseModel):
    """Invariant entry in manifest."""
    id: str = Field(..., pattern=r"^INV-\d{4}$")
    statement: str
    defined_in: str = Field(..., pattern=r"^ADR-(L|P|PS|PC|D)-\d{4}$")
    enforced_by: List[str] = Field(default_factory=list)
    enforcement_level: str = Field(..., pattern=r"^(must|should|may)$")


class GapSummaryByADR(BaseModel):
    """Gap summary for a single ADR."""
    total: int = Field(..., ge=0)
    blocking: int = Field(..., ge=0)


class GapsSummary(BaseModel):
    """Summary of gaps across all ADRs."""
    total: int = Field(..., ge=0)
    blocking: int = Field(..., ge=0)
    by_adr: Dict[str, GapSummaryByADR] = Field(default_factory=dict)


class ManifestStatistics(BaseModel):
    """Aggregate statistics."""
    total_adrs: int = Field(..., ge=0)
    logical_adrs: int = Field(..., ge=0)
    physical_adrs: int = Field(..., ge=0)
    physical_system_adrs: int = Field(0, ge=0)
    physical_component_adrs: int = Field(0, ge=0)
    decision_adrs: int = Field(0, ge=0)
    total_decisions: int = Field(0, ge=0)
    total_invariants: int = Field(0, ge=0)
    total_components: int = Field(0, ge=0)
    total_gaps: int = Field(0, ge=0)
    blocking_gaps: int = Field(0, ge=0)
    total_entities: int = Field(0, ge=0)
    total_requirements_snapshots: int = Field(0, ge=0)
    total_decision_ledgers: int = Field(0, ge=0)


class ManifestEntity(BaseModel):
    """Entity entry in manifest."""
    entity_id: str = Field(..., pattern=r"^[A-Z]+-\d{4}$")
    entity_type: str
    name: str
    introduced_by: str = Field(..., pattern=r"^ADR-(L|P|PS|PC|D)-\d{4}$")
    lifecycle_stage: str


class ManifestRequirementsSnapshot(BaseModel):
    """Requirements snapshot entry in manifest."""
    snapshot_id: str = Field(..., pattern=r"^REQ-\d{4}$")
    domains: List[str]
    capability_count: int = Field(0, ge=0)


class ManifestDecisionLedger(BaseModel):
    """Decision ledger entry in manifest."""
    ledger_id: str = Field(..., pattern=r"^LEDGER-\d{4}$")
    target_logical_adr: str = Field(..., pattern=r"^ADR-L-\d{4}$")
    decision_count: int = Field(0, ge=0)


class Manifest(BaseModel):
    """Generated manifest for ADR discovery (SYS-14: Index Currency)."""
    
    schema_version: str = Field("1.0", pattern=r"^1\.0$")
    type: str = Field("manifest", pattern=r"^manifest$")
    generated_date: datetime
    generated_from: str = Field(..., description="Glob pattern of source ADRs")
    
    adrs: List[ManifestADREntry]
    
    by_domain: Dict[str, List[str]] = Field(default_factory=dict)
    by_status: Dict[str, List[str]] = Field(default_factory=dict)
    by_technology: Dict[str, List[str]] = Field(default_factory=dict)

    logical_to_physical_map: Dict[str, List[str]] = Field(default_factory=dict)
    system_to_components_map: Dict[str, List[str]] = Field(default_factory=dict, description="Physical-System to Physical-Component mapping")
    
    invariants: List[ManifestInvariant] = Field(default_factory=list)
    entities: List[ManifestEntity] = Field(default_factory=list, description="All entities across all ADRs")
    requirements_snapshots: List[ManifestRequirementsSnapshot] = Field(default_factory=list, description="Requirements snapshots summary")
    decision_ledgers: List[ManifestDecisionLedger] = Field(default_factory=list, description="Decision ledgers summary")
    gaps_summary: GapsSummary
    statistics: ManifestStatistics
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "schema_version": "1.0",
                "type": "manifest",
                "generated_date": "2026-03-07T19:45:00Z",
                "generated_from": "adrs/**/*.yaml",
                "adrs": [{
                    "id": "ADR-L-0001",
                    "type": "logical",
                    "title": "Two-Layer Architecture Model",
                    "status": "accepted",
                    "file_path": "adrs/logical/ADR-L-0001.yaml",
                    "domains": ["architecture"],
                    "decision_count": 3
                }],
                "statistics": {
                    "total_adrs": 1,
                    "logical_adrs": 1,
                    "physical_adrs": 0
                },
                "gaps_summary": {
                    "total": 0,
                    "blocking": 0,
                    "by_adr": {}
                }
            }]
        }
    )
