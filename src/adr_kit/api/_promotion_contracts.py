"""Immutable public contracts for Design Journal promotion operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ._contracts import (
    API_CONTRACT_VERSION,
    Diagnostic,
    _normalize_project_root,
    _normalize_timestamp,
)
from ._errors import InvalidRequestError

GOVERNED_AUTHORITY_DIR = "adrs"
GOVERNED_ROADMAP_NAME = "ROADMAP.md"


def _normalize_existing_file(value: str | Path, *, field_name: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise InvalidRequestError(f"{field_name} is not a file: {path}")
    return path


def _is_governed_authority_path(project_root: Path, candidate: Path) -> bool:
    resolved = candidate.expanduser().resolve()
    root = project_root.expanduser().resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        return False
    parts = relative.parts
    if not parts:
        return False
    if parts[0] == GOVERNED_AUTHORITY_DIR:
        return True
    return relative.as_posix() == GOVERNED_ROADMAP_NAME


def _normalize_prepared_output_path(
    project_root: Path,
    value: str | Path | None,
) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser().resolve()
    if _is_governed_authority_path(project_root, path):
        raise InvalidRequestError(
            "prepared_contract_output_path must not resolve into governed authority "
            f"(adrs/** or ROADMAP.md): {path}"
        )
    if path.exists() and path.is_dir():
        raise InvalidRequestError(f"prepared_contract_output_path must be a file path: {path}")
    return path


@dataclass(frozen=True, slots=True)
class PromotionBindingDescriptor:
    """Immutable public view of a payload or schema/rule binding."""

    kind: Literal["payload", "schema_rule"]
    mutation_id: str
    ref: str
    fingerprint: str
    relative_path: str | None = None


@dataclass(frozen=True, slots=True)
class PromotionValidationEvidenceDescriptor:
    """Immutable public view of exact-pair validation evidence."""

    mutation_id: str
    payload_fingerprint: str
    schema_binding_fingerprint: str
    result: str
    evidence_ref: str | None = None


@dataclass(frozen=True, slots=True)
class PromotionBlockerDescriptor:
    """Immutable public view of one promotion blocker."""

    id: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class PromotionBaselineDescriptor:
    """Path-scoped authority baseline status."""

    kind: str
    value: str
    provider: str
    equivalent: bool
    coverage: tuple[str, ...] = ("adrs/**", "ROADMAP.md")


@dataclass(frozen=True, slots=True)
class PromotionMutationDescriptor:
    """Immutable public view of one prepared or applied mutation."""

    mutation_id: str
    operation: Literal["create", "amend", "supersede"]
    provider_target_ref: str
    relative_path: str
    outcome_refs: tuple[str, ...]
    payload: PromotionBindingDescriptor | None = None
    schema_rule: PromotionBindingDescriptor | None = None
    validation_evidence: PromotionValidationEvidenceDescriptor | None = None


@dataclass(frozen=True, slots=True)
class PromotionExecutionEvidenceDescriptor:
    """Immutable public view of one append-only execution evidence entry."""

    attempt_id: str
    classification: str
    message: str
    at: str | None = None


@dataclass(frozen=True, slots=True)
class PromotionPrepareRequest:
    """Inputs for preparing one Promotion Contract against a repository."""

    project_root: Path
    promotion_contract_path: Path
    design_journal_path: Path | None = None
    prepared_contract_output_path: Path | None = None

    def __post_init__(self) -> None:
        root = _normalize_project_root(self.project_root)
        object.__setattr__(self, "project_root", root)
        object.__setattr__(
            self,
            "promotion_contract_path",
            _normalize_existing_file(
                self.promotion_contract_path, field_name="promotion_contract_path"
            ),
        )
        if self.design_journal_path is not None:
            object.__setattr__(
                self,
                "design_journal_path",
                _normalize_existing_file(
                    self.design_journal_path, field_name="design_journal_path"
                ),
            )
        object.__setattr__(
            self,
            "prepared_contract_output_path",
            _normalize_prepared_output_path(root, self.prepared_contract_output_path),
        )


@dataclass(frozen=True, slots=True)
class PromotionPrepareResult:
    """Completed preparation outcome without mutating canonical authority."""

    request: PromotionPrepareRequest
    success: bool
    design_lock_ready: bool
    mechanical_promotion_ready: bool
    locked_intent_fingerprint: str
    baseline: PromotionBaselineDescriptor
    blockers: tuple[PromotionBlockerDescriptor, ...]
    mutations: tuple[PromotionMutationDescriptor, ...]
    prepared_contract: dict[str, Any]
    prepared_contract_path: Path | None
    diagnostics: tuple[Diagnostic, ...]
    package_version: str
    api_contract_version: str = API_CONTRACT_VERSION
    authority_mutated: bool = False


@dataclass(frozen=True, slots=True)
class PromotionCheckRequest:
    """Inputs for re-evaluating a prepared or locked Promotion Contract."""

    project_root: Path
    promotion_contract_path: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", _normalize_project_root(self.project_root))
        object.__setattr__(
            self,
            "promotion_contract_path",
            _normalize_existing_file(
                self.promotion_contract_path, field_name="promotion_contract_path"
            ),
        )


@dataclass(frozen=True, slots=True)
class PromotionCheckResult:
    """Readiness/blocker inspection without authority writes."""

    request: PromotionCheckRequest
    success: bool
    design_lock_ready: bool
    mechanical_promotion_ready: bool
    locked_intent_fingerprint: str
    baseline: PromotionBaselineDescriptor
    blockers: tuple[PromotionBlockerDescriptor, ...]
    mutations: tuple[PromotionMutationDescriptor, ...]
    human_lock_present: bool
    diagnostics: tuple[Diagnostic, ...]
    package_version: str
    api_contract_version: str = API_CONTRACT_VERSION
    authority_mutated: bool = False


@dataclass(frozen=True, slots=True)
class PromotionApplyRequest:
    """Inputs for dry-run or committing a locked prepared Promotion Contract."""

    project_root: Path
    promotion_contract_path: Path
    commit: bool = False
    timestamp: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", _normalize_project_root(self.project_root))
        object.__setattr__(
            self,
            "promotion_contract_path",
            _normalize_existing_file(
                self.promotion_contract_path, field_name="promotion_contract_path"
            ),
        )
        if not isinstance(self.commit, bool):
            raise InvalidRequestError("commit must be a bool")
        object.__setattr__(self, "timestamp", _normalize_timestamp(self.timestamp))


@dataclass(frozen=True, slots=True)
class PromotionApplyResult:
    """Apply outcome including post-commit recovery state flags."""

    request: PromotionApplyRequest
    success: bool
    semantic_state: str
    authority_committed: bool
    apply_execution_evidence_appended: bool
    regeneration_completed: bool
    validation_success: bool
    locked_intent_fingerprint: str
    baseline: PromotionBaselineDescriptor
    mutations: tuple[PromotionMutationDescriptor, ...]
    execution_evidence: tuple[PromotionExecutionEvidenceDescriptor, ...]
    corpus_fingerprint: str | None
    diagnostics: tuple[Diagnostic, ...]
    package_version: str
    api_contract_version: str = API_CONTRACT_VERSION
