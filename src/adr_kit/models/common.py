"""Common Pydantic models and types for ADR artifacts."""

from datetime import date, datetime
from enum import Enum
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Fingerprint = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
LocalEntityReference = Annotated[
    str,
    Field(pattern=r"^(ADR-(L|V|P|PS|PC|D)-\d{4}|[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)$"),
]


class ADRType(str, Enum):
    """ADR type enumeration."""
    LOGICAL = "logical"
    PHYSICAL = "physical"  # Legacy, use PHYSICAL_SYSTEM or PHYSICAL_COMPONENT
    PHYSICAL_SYSTEM = "physical-system"
    PHYSICAL_COMPONENT = "physical-component"
    DECISION = "decision"


class Status(str, Enum):
    """ADR lifecycle status."""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class EnforcementLevel(str, Enum):
    """RFC 2119 enforcement levels for invariants."""
    MUST = "must"
    SHOULD = "should"
    MAY = "may"


class ImpactLevel(str, Enum):
    """Impact assessment levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ImplementationAuthority(str, Enum):
    """Implementation authority level for one ADR."""
    NONE = "none"
    ADVISORY = "advisory"
    IMPLEMENTATION_AUTHORITATIVE = "implementation_authoritative"


class Alternative(BaseModel):
    """Alternative approach that was considered and rejected."""
    name: str
    rejected_because: str = Field(..., description="Why this alternative was not chosen")


class Consequences(BaseModel):
    """Positive and negative consequences of a decision."""
    positive: List[str] = Field(default_factory=list)
    negative: List[str] = Field(default_factory=list)


class Gap(BaseModel):
    """Explicit gap or unresolved question."""
    id: str = Field(..., pattern=r"^GAP-\d{4}$")
    question: str = Field(..., description="Unresolved design question")
    context: Optional[str] = None
    impact: ImpactLevel
    blocking: bool = Field(..., description="Does this gap block implementation?")
    affects: List[str] = Field(default_factory=list)
    options: List[dict] = Field(default_factory=list)
    decision_required_from: Optional[str] = None


class Ownership(BaseModel):
    """Ownership metadata for governance."""
    architecture_authority: Optional[str] = Field(None, description="Team responsible for architectural decisions")
    implementation_owners: List[str] = Field(default_factory=list, description="Teams implementing this ADR")


class Governance(BaseModel):
    """Compact governance metadata for approval and implementation gating."""

    steelman_review_required: Optional[bool] = None
    steelman_review_completed: Optional[bool] = None
    implementation_authority: Optional[ImplementationAuthority] = None
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None
    related_reviews: List[str] = Field(default_factory=list)
    related_overrides: List[str] = Field(default_factory=list)
    related_ledgers: List[str] = Field(default_factory=list)


class ExternalReference(BaseModel):
    """Qualified reference to authority owned by another namespace."""

    namespace: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    id: str = Field(min_length=1)
    kind: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    fingerprint: Fingerprint

    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    def qualified_id(self) -> str:
        """Return the deterministic display qualification without claiming ownership."""

        return f"{self.namespace}:{self.id}"


EntityReference = Union[LocalEntityReference, ExternalReference]


class SubstrateBinding(BaseModel):
    """Authored selection of externally owned substrate."""

    external_namespace: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    artifact_id: str = Field(min_length=1)
    kind: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._+:-]*$")
    fingerprint: Fingerprint
    source_pack: Optional[str] = None
    role: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    selected_by: LocalEntityReference
    local_config_ref: Optional[str] = None
    supersedes: List[ExternalReference] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @property
    def binding_identity(self) -> tuple[str, str, str]:
        """Return the ADR-local deterministic binding identity."""

        return (self.external_namespace, self.artifact_id, self.role)


class RuleBinding(BaseModel):
    """Authored disposition toward an externally owned rule."""

    rule_id: str = Field(min_length=1)
    namespace: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._+:-]*$")
    fingerprint: Fingerprint
    disposition: Literal["adopted", "refined", "overridden", "exempted", "not_applicable"]
    rationale: Optional[str] = Field(default=None, min_length=1)
    exception_ref: Optional[str] = Field(default=None, min_length=1)
    owner: Optional[str] = None
    affected_entities: List[EntityReference] = Field(min_length=1)
    expected_evidence_ref: Optional[str] = Field(default=None, pattern=r"^EVID-[A-Z0-9-]+$")

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_disposition_requirements(self) -> "RuleBinding":
        """Enforce rationale and exception requirements from ADR-L-0018."""

        if self.disposition in {"refined", "overridden", "exempted", "not_applicable"}:
            if self.rationale is None:
                raise ValueError(f"{self.disposition} rule bindings require rationale")
        if self.disposition == "exempted" and self.exception_ref is None:
            raise ValueError("exempted rule bindings require exception_ref")
        return self

    @property
    def binding_identity(self) -> tuple[str, str]:
        """Return the ADR-local deterministic binding identity."""

        return (self.namespace, self.rule_id)


class EvidenceExpectation(BaseModel):
    """Authored expectation for evidence, never an observed evidence record."""

    expectation_id: str = Field(pattern=r"^EVID-[A-Z0-9-]+$")
    kind: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    related_entities: List[EntityReference] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ADRFrontmatter(BaseModel):
    """Common frontmatter for all ADR types (STE-compliant, PRIME-1, PRIME-2)."""
    
    schema_version: str = Field("1.0", pattern=r"^(1\.0|1\.2)$")
    adr_type: ADRType
    id: str = Field(..., pattern=r"^ADR-(L|V|P|PS|PC|D)-\d{4}$")
    title: str = Field(..., min_length=5, max_length=200)
    status: Status
    created_date: date
    modified_date: Optional[date] = None
    authors: List[str] = Field(..., min_length=1)
    
    domains: List[str] = Field(default_factory=list, min_length=1)
    tags: List[str] = Field(default_factory=list)
    
    related_adrs: List[str] = Field(default_factory=list)
    supersedes: List[str] = Field(default_factory=list)
    superseded_by: Optional[str] = None

    projection_signals: List[str] = Field(
        default_factory=list,
        description="Context signals for rule projection (ste-rules-library)"
    )
    ai_projectable: Optional[dict] = Field(
        None,
        description="AI-first projection hints (minimal_sections, primary_domains)"
    )
    
    ownership: Optional[Ownership] = None
    governance: Optional[Governance] = None
    
    introduces_entities: List[str] = Field(
        default_factory=list,
        description="Entities introduced by this ADR (CAP-XXXX, COMP-XXXX, etc.)"
    )
    modifies_entities: List[str] = Field(
        default_factory=list,
        description="Entities modified (lifecycle, relationships, or properties)"
    )
    realizes_entities: List[str] = Field(
        default_factory=list,
        description="Entities realized by this Physical ADR (COMP implements CAP)"
    )
    related_ledgers: List[str] = Field(
        default_factory=list,
        description="Deprecated in favor of governance.related_ledgers"
    )
    substrate_bindings: List[SubstrateBinding] = Field(default_factory=list)
    rule_bindings: List[RuleBinding] = Field(default_factory=list)
    evidence_expectations: List[EvidenceExpectation] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_governance_references(self) -> "ADRFrontmatter":
        """Preserve compatibility while treating governance as canonical."""
        if self.related_ledgers:
            if self.governance is None:
                self.governance = Governance(related_ledgers=list(self.related_ledgers))
            elif not self.governance.related_ledgers:
                self.governance.related_ledgers = list(self.related_ledgers)
        if self.schema_version == "1.0" and (
            self.substrate_bindings or self.rule_bindings or self.evidence_expectations
        ):
            raise ValueError("Phase 2 binding fields require ADR schema_version 1.2")

        substrate_identities = [binding.binding_identity for binding in self.substrate_bindings]
        if len(substrate_identities) != len(set(substrate_identities)):
            raise ValueError("duplicate substrate binding identity")

        rule_identities = [binding.binding_identity for binding in self.rule_bindings]
        if len(rule_identities) != len(set(rule_identities)):
            raise ValueError("duplicate rule binding identity")

        expectation_ids = [item.expectation_id for item in self.evidence_expectations]
        if len(expectation_ids) != len(set(expectation_ids)):
            raise ValueError("duplicate evidence expectation identity")
        expectation_id_set = set(expectation_ids)
        for binding in self.rule_bindings:
            if (
                binding.expected_evidence_ref is not None
                and binding.expected_evidence_ref not in expectation_id_set
            ):
                raise ValueError(
                    "rule binding expected_evidence_ref must identify an evidence expectation "
                    "in the same ADR"
                )
        return self
    
    @field_validator('id')
    @classmethod
    def validate_id_matches_type(cls, v: str, info) -> str:
        """Validate that ID prefix matches adr_type."""
        adr_type = info.data.get('adr_type')
        if adr_type == ADRType.LOGICAL and not (v.startswith('ADR-L-') or v.startswith('ADR-V-')):
            raise ValueError(f"Logical ADR must have ID starting with ADR-L- or ADR-V-, got {v}")
        elif adr_type == ADRType.PHYSICAL and not v.startswith('ADR-P-'):
            raise ValueError(f"Physical ADR must have ID starting with ADR-P-, got {v}")
        elif adr_type == ADRType.PHYSICAL_SYSTEM and not v.startswith('ADR-PS-'):
            raise ValueError(f"Physical-System ADR must have ID starting with ADR-PS-, got {v}")
        elif adr_type == ADRType.PHYSICAL_COMPONENT and not v.startswith('ADR-PC-'):
            raise ValueError(f"Physical-Component ADR must have ID starting with ADR-PC-, got {v}")
        elif adr_type == ADRType.DECISION and not v.startswith('ADR-D-'):
            raise ValueError(f"Decision ADR must have ID starting with ADR-D-, got {v}")
        return v
