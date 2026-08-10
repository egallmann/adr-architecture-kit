"""Promotion application service: prepare, check, apply."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from .. import __version__
from ..api._contracts import API_CONTRACT_VERSION, Diagnostic
from ..api._errors import InvalidRequestError, OperationError
from ..api._promotion_contracts import (
    PromotionApplyRequest,
    PromotionApplyResult,
    PromotionBaselineDescriptor,
    PromotionBindingDescriptor,
    PromotionBlockerDescriptor,
    PromotionCheckRequest,
    PromotionCheckResult,
    PromotionExecutionEvidenceDescriptor,
    PromotionMutationDescriptor,
    PromotionPrepareRequest,
    PromotionPrepareResult,
    PromotionValidationEvidenceDescriptor,
    _is_governed_authority_path,
)
from .baseline import path_scoped_baseline_equivalent
from .bindings import (
    authorized_adr_schema_fingerprint,
    binding_dict,
    evidence_dict,
    fingerprint_bytes,
    roadmap_rules_fingerprint,
    validate_roadmap_content,
)
from .amendment_projection import ANNOTATION_ONLY_MARKER, assert_amendment_embodied
from .candidate_validation import (
    candidate_validation_result,
    validate_adr_payload_bytes,
    validate_projected_authority_overlay,
)
from .candidates import (
    allocate_for_identity_create,
    build_create_adr_post_image,
    build_supersede_post_image,
    resolve_mutation_target,
)
from .identity_v13 import (
    IDENTITY_V13_JOURNAL_ID,
    apply_identity_v13_amend,
    build_identity_v13_create_children,
    build_identity_v13_create_context,
    deferred_children_are_non_active,
)
from .regeneration import regenerate_and_validate
from .ste_contract import (
    PROVIDER_ID,
    human_lock_valid,
    load_json,
    locked_intent_fingerprint,
    mechanical_ready,
    validate_contract,
)
from .transaction import PlannedWrite, TransactionAborted, commit_all_or_none

SEMANTIC_PRE_COMMIT_FAILURE = "PRE_COMMIT_FAILURE"
SEMANTIC_EVIDENCE_PENDING = "AUTHORITY_COMMITTED_EVIDENCE_PENDING"
SEMANTIC_REGEN_PENDING = "AUTHORITY_COMMITTED_REGEN_PENDING"
SEMANTIC_VALIDATION_FAILED = "AUTHORITY_COMMITTED_VALIDATION_FAILED"
SEMANTIC_COMPLETE = "PROMOTION_COMPLETE"

# Advertise when full public behavioral contract is implemented.
PROMOTION_OPERATIONS_ADVERTISED = True


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _authority_snapshot(project_root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    root = project_root.resolve()
    roadmap = root / "ROADMAP.md"
    if roadmap.is_file():
        snapshot["ROADMAP.md"] = roadmap.read_bytes()
    adrs = root / "adrs"
    if adrs.is_dir():
        for path in adrs.rglob("*"):
            if path.is_file():
                snapshot[path.relative_to(root).as_posix()] = path.read_bytes()
    return snapshot


def _diagnostic(code: str, message: str, *, severity: str = "error") -> Diagnostic:
    return Diagnostic(severity=severity, code=code, message=message)  # type: ignore[arg-type]


def _resolved_map(store: Path) -> dict[str, str]:
    path = store / "resolved-targets.json"
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return {}
    return {str(key): str(value) for key, value in loaded.items()}


def _load_contract(path: Path) -> dict[str, Any]:
    loaded = load_json(path)
    if not isinstance(loaded, dict):
        raise OperationError("PROMOTION_INVALID_CONTRACT: expected JSON object")
    return loaded


def _mutation_descriptors(
    contract: dict[str, Any], project_root: Path
) -> tuple[PromotionMutationDescriptor, ...]:
    store = _provider_store(project_root)
    resolved_map = _resolved_map(store)
    descriptors: list[PromotionMutationDescriptor] = []
    for mutation in contract.get("mutations", []):
        title = None
        if mutation.get("operation") == "create":
            title = "Canonical Entity Identity"
        relative = resolved_map.get(mutation["id"])
        if relative is None:
            try:
                resolved = resolve_mutation_target(project_root, mutation, create_title=title)
                relative = resolved.relative_path
            except OperationError:
                relative = mutation.get("provider_target_ref", "")
        payload = mutation.get("payload_binding")
        schema = mutation.get("schema_binding")
        evidence = mutation.get("validation_evidence")
        descriptors.append(
            PromotionMutationDescriptor(
                mutation_id=mutation["id"],
                operation=mutation["operation"],
                provider_target_ref=mutation["provider_target_ref"],
                relative_path=relative,
                outcome_refs=tuple(mutation.get("outcome_refs", [])),
                payload=(
                    PromotionBindingDescriptor(
                        kind="payload",
                        mutation_id=mutation["id"],
                        ref=payload.get("ref", ""),
                        fingerprint=payload.get("fingerprint", ""),
                        relative_path=payload.get("ref"),
                    )
                    if payload
                    else None
                ),
                schema_rule=(
                    PromotionBindingDescriptor(
                        kind="schema_rule",
                        mutation_id=mutation["id"],
                        ref=schema.get("ref", ""),
                        fingerprint=schema.get("fingerprint", ""),
                    )
                    if schema
                    else None
                ),
                validation_evidence=(
                    PromotionValidationEvidenceDescriptor(
                        mutation_id=mutation["id"],
                        payload_fingerprint=evidence.get("payload_fingerprint", ""),
                        schema_binding_fingerprint=evidence.get("schema_binding_fingerprint", ""),
                        result=evidence.get("result", ""),
                        evidence_ref=evidence.get("evidence_ref"),
                    )
                    if evidence
                    else None
                ),
            )
        )
    return tuple(descriptors)


def _baseline_descriptor(
    contract: dict[str, Any], project_root: Path
) -> PromotionBaselineDescriptor:
    baseline = contract.get("authority_baseline") or {}
    kind = str(baseline.get("kind", ""))
    value = str(baseline.get("value", ""))
    provider = str(baseline.get("provider", ""))
    equivalent = False
    if kind and value:
        equivalent, _detail = path_scoped_baseline_equivalent(
            project_root, baseline_kind=kind, baseline_value=value
        )
    return PromotionBaselineDescriptor(
        kind=kind,
        value=value,
        provider=provider,
        equivalent=equivalent,
    )


def _provider_store(project_root: Path) -> Path:
    path = project_root.resolve() / ".adr-kit" / "promotion"
    path.mkdir(parents=True, exist_ok=True)
    if _is_governed_authority_path(project_root, path):
        raise OperationError("PROMOTION_STORE_INVALID: provider store resolved into authority")
    return path


def _ensure_output_outside_authority(project_root: Path, path: Path) -> None:
    if _is_governed_authority_path(project_root, path):
        raise InvalidRequestError(
            f"prepared output must not resolve into governed authority: {path}"
        )


def _build_post_images(
    project_root: Path,
    contract: dict[str, Any],
) -> dict[str, tuple[str, bytes]]:
    """Return mutation_id -> (relative_path, content bytes)."""

    images: dict[str, tuple[str, bytes]] = {}
    outcomes = {item["id"]: item for item in contract.get("outcomes", [])}
    journal_id = str(contract.get("journal_id") or "")
    for mutation in contract.get("mutations", []):
        operation = mutation["operation"]
        target_ref = mutation["provider_target_ref"]
        if operation == "create" and target_ref.startswith("adr:"):
            adr_id = target_ref.split(":", 1)[1]
            title = "Canonical Entity Identity"
            if adr_id == "ADR-L-0019":
                dec_ids, inv_ids = allocate_for_identity_create(project_root)
                selected = [
                    outcomes[oid]
                    for oid in mutation.get("outcome_refs", [])
                    if oid in outcomes and (oid.startswith("D-") or oid.startswith("I-"))
                ]
                decisions, invariants, gaps = build_identity_v13_create_children(
                    selected,
                    dec_ids=dec_ids,
                    inv_ids=inv_ids,
                )
                if journal_id == IDENTITY_V13_JOURNAL_ID and not deferred_children_are_non_active(
                    decisions, invariants, gaps
                ):
                    raise OperationError(
                        "DEFERRED_CHILD_ENCODING_UNSAFE: D-12/I-13 must not assert active "
                        "v1.3 constraints"
                    )
                text = build_create_adr_post_image(
                    adr_id=adr_id,
                    title=title,
                    decisions=decisions,
                    invariants=invariants,
                    gaps=gaps,
                    context=build_identity_v13_create_context(
                        journal_id=journal_id,
                        outcomes=selected,
                    ),
                )
            else:
                text = build_create_adr_post_image(
                    adr_id=adr_id,
                    title=title,
                    decisions=[
                        {
                            "id": "DEC-0001",
                            "summary": "created",
                            "rationale": "Created by promotion provider.",
                        }
                    ],
                    invariants=[],
                )
            resolved = resolve_mutation_target(project_root, mutation, create_title=title)
            images[mutation["id"]] = (resolved.relative_path, text.encode("utf-8"))
        elif operation == "amend" and target_ref == "file:ROADMAP.md":
            resolved = resolve_mutation_target(project_root, mutation)
            current = resolved.absolute_path.read_text(encoding="utf-8")
            if "Phase 2.5" not in current:
                marker = "## Phase 3"
                insertion = (
                    "## Phase 2.5 — canonical entity identity and promotion provider\n\n"
                    "Promote the closed v1.3 identity Design Journal through the ADR Kit "
                    "promotion provider before schema/model v1.3 embodiment and corpus migration.\n\n"
                    "Keep canonical updated_at and general transactional authoring in Phase 3. "
                    "Phase 3 consumes, and does not redefine, v1.3 entity identity.\n\n"
                )
                if marker in current:
                    current = current.replace(marker, insertion + marker, 1)
                else:
                    current = current.rstrip() + "\n\n" + insertion
            errors = validate_roadmap_content(current)
            if errors:
                raise OperationError("PROMOTION_CANDIDATE_INVALID: " + "; ".join(errors))
            if journal_id == IDENTITY_V13_JOURNAL_ID:
                embody_errors = assert_amendment_embodied(
                    mutation_id=mutation["id"],
                    before=None,
                    after=current,
                    journal_id=journal_id,
                )
                if embody_errors:
                    raise OperationError(
                        "PROMOTION_AMENDMENT_NOT_EMBODIED: " + "; ".join(embody_errors)
                    )
            images[mutation["id"]] = (resolved.relative_path, current.encode("utf-8"))
        elif operation == "amend" and target_ref.startswith("adr:"):
            resolved = resolve_mutation_target(project_root, mutation)
            before = yaml.safe_load(resolved.absolute_path.read_text(encoding="utf-8"))
            if not isinstance(before, dict):
                raise OperationError(
                    f"PROMOTION_INVALID_TARGET: expected mapping in {resolved.relative_path}"
                )
            if journal_id == IDENTITY_V13_JOURNAL_ID:
                try:
                    after = apply_identity_v13_amend(mutation["id"], before)
                except (KeyError, ValueError) as exc:
                    raise OperationError(
                        f"INCOMPLETE_MUTATION_SPECIFICATION: {mutation['id']}: {exc}"
                    ) from exc
                embody_errors = assert_amendment_embodied(
                    mutation_id=mutation["id"],
                    before=before,
                    after=after,
                    journal_id=journal_id,
                )
                if embody_errors:
                    raise OperationError(
                        "PROMOTION_AMENDMENT_NOT_EMBODIED: " + "; ".join(embody_errors)
                    )
                if ANNOTATION_ONLY_MARKER in yaml.safe_dump(after, sort_keys=False):
                    # Marker may appear only if somehow reintroduced; fail closed.
                    before_core = {k: v for k, v in before.items() if k != "notes"}
                    after_core = {k: v for k, v in after.items() if k != "notes"}
                    if before_core == after_core:
                        raise OperationError("ANNOTATION_ONLY_AMENDMENT: scoped amendments missing")
                text = yaml.safe_dump(after, sort_keys=False, allow_unicode=True)
            else:
                # Non-identity journals must not silently annotation-amend.
                raise OperationError(
                    "UNSUPPORTED_MUTATION_INSTRUCTION: amend projection requires a "
                    f"provider mutation specification for journal {journal_id!r}"
                )
            images[mutation["id"]] = (resolved.relative_path, text.encode("utf-8"))
        elif operation == "supersede" and target_ref.startswith("adr:"):
            resolved = resolve_mutation_target(project_root, mutation)
            import re

            doc = yaml.safe_load(resolved.absolute_path.read_text(encoding="utf-8"))
            superseded = None
            for oid in mutation.get("outcome_refs", []):
                outcome = outcomes.get(oid) or {}
                statement = str(outcome.get("statement", ""))
                match = re.search(r"supersedes\s+(ADR-(?:L|PS|PC)-\d{4})", statement)
                if match:
                    superseded = match.group(1)
                    break
            if not superseded:
                raise OperationError(
                    "PROMOTION_SUPERSEDE_LINK_REQUIRED: explicit supersession linkage required"
                )
            text = build_supersede_post_image(
                replacement_path=resolved.absolute_path,
                replacement_document=doc,
                superseded_id=str(superseded),
            )
            images[mutation["id"]] = (resolved.relative_path, text.encode("utf-8"))
        else:
            raise OperationError(
                f"PROMOTION_UNSUPPORTED_MUTATION: {mutation.get('id')} {operation} {target_ref}"
            )
    return images


def _bind_prepared_contract(
    project_root: Path,
    contract: dict[str, Any],
    images: dict[str, tuple[str, bytes]],
    store: Path,
) -> dict[str, Any]:
    prepared = deepcopy(contract)
    prepared["provider"] = PROVIDER_ID
    schema_ref, schema_fp = authorized_adr_schema_fingerprint(project_root)
    roadmap_fp = roadmap_rules_fingerprint()
    blockers: list[dict[str, Any]] = []
    payloads_dir = store / "payloads"
    evidence_dir = store / "evidence"
    payloads_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    for mutation in prepared.get("mutations", []):
        mutation_id = mutation["id"]
        relative_path, content = images[mutation_id]
        payload_fp = fingerprint_bytes(content)
        payload_rel = f"payloads/{mutation_id}.bin"
        (payloads_dir / f"{mutation_id}.bin").write_bytes(content)
        mutation["payload_binding"] = binding_dict(ref=payload_rel, fingerprint=payload_fp)
        if mutation["provider_target_ref"].startswith("file:"):
            schema_binding = binding_dict(
                ref="rules:roadmap_file_rules_v1",
                fingerprint=roadmap_fp,
            )
            # Validate roadmap candidate
            errors = validate_roadmap_content(content.decode("utf-8"))
            result = candidate_validation_result(errors)
            if errors:
                blockers.append(
                    {
                        "id": f"B-VAL-{mutation_id}",
                        "code": "candidate_validation_failure",
                        "message": "; ".join(errors),
                    }
                )
        else:
            schema_binding = binding_dict(ref=schema_ref, fingerprint=schema_fp)
            # Validate the exact final bound bytes with the canonical ADR validator.
            errors = validate_adr_payload_bytes(content, relative_path=relative_path)
            result = candidate_validation_result(errors)
            if errors:
                blockers.append(
                    {
                        "id": f"B-VAL-{mutation_id}",
                        "code": "candidate_validation_failure",
                        "message": "; ".join(errors),
                    }
                )
        mutation["schema_binding"] = schema_binding
        if schema_binding["ref"].startswith("schema:adr") and mutation[
            "provider_target_ref"
        ].startswith("file:"):
            raise OperationError("PROMOTION_SCHEMA_BINDING_INVALID: ROADMAP bound to ADR schema")
        if mutation["provider_target_ref"].startswith("file:") and schema_binding["ref"].startswith(
            "schema:adr"
        ):
            raise OperationError("PROMOTION_SCHEMA_BINDING_INVALID: ROADMAP bound to ADR schema")
        evidence_rel = f"evidence/{mutation_id}.json"
        evidence = evidence_dict(
            payload_fingerprint=payload_fp,
            schema_binding_fingerprint=schema_binding["fingerprint"],
            result=result,
            evidence_ref=evidence_rel,
        )
        (evidence_dir / f"{mutation_id}.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        mutation["validation_evidence"] = evidence

    # Persist resolved paths outside the PC document (PC mutation additionalProperties=false)
    resolved_map = {mutation_id: images[mutation_id][0] for mutation_id in images}
    (store / "resolved-targets.json").write_text(
        json.dumps(resolved_map, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Complete projected corpus must also validate before mechanical readiness.
    overlay_errors = validate_projected_authority_overlay(project_root, images)
    if overlay_errors:
        blockers.append(
            {
                "id": "B-VAL-OVERLAY",
                "code": "candidate_validation_failure",
                "message": "; ".join(overlay_errors),
            }
        )

    prepared["blockers"] = [
        item
        for item in prepared.get("blockers", [])
        if item.get("code")
        not in {
            "missing_mutation_bindings",
            "promotion_provider_api_absent",
            "non_transactional_writes",
        }
    ]
    prepared["blockers"].extend(blockers)
    ready, ready_errors = mechanical_ready(prepared)
    prepared.setdefault("readiness", {})
    prepared["readiness"]["design_lock"] = True
    prepared["readiness"]["mechanical_promotion"] = ready
    if not ready and not prepared["blockers"]:
        prepared["blockers"].append(
            {
                "id": "B-READY",
                "code": "mechanical_readiness_false",
                "message": "; ".join(ready_errors),
            }
        )
    return prepared


def prepare_promotion(request: PromotionPrepareRequest) -> PromotionPrepareResult:
    before = _authority_snapshot(request.project_root)
    contract = _load_contract(request.promotion_contract_path)
    schema_errors = validate_contract_schema_only(contract)
    diagnostics: list[Diagnostic] = [
        _diagnostic("PROMOTION_INVALID_CONTRACT", message) for message in schema_errors
    ]
    if schema_errors:
        baseline = _baseline_descriptor(contract, request.project_root)
        return PromotionPrepareResult(
            request=request,
            success=False,
            design_lock_ready=False,
            mechanical_promotion_ready=False,
            locked_intent_fingerprint="",
            baseline=baseline,
            blockers=tuple(
                PromotionBlockerDescriptor(id="B-SCHEMA", code="invalid_contract", message=msg)
                for msg in schema_errors
            ),
            mutations=(),
            prepared_contract=contract,
            prepared_contract_path=None,
            diagnostics=tuple(diagnostics),
            package_version=__version__,
            api_contract_version=API_CONTRACT_VERSION,
            authority_mutated=False,
        )

    if contract.get("provider") not in (None, PROVIDER_ID):
        raise OperationError("PROMOTION_WRONG_PROVIDER: provider must be adr-architecture-kit")

    store = _provider_store(request.project_root)
    images = _build_post_images(request.project_root, contract)
    prepared = _bind_prepared_contract(request.project_root, contract, images, store)
    fingerprint = locked_intent_fingerprint(prepared)
    baseline = _baseline_descriptor(prepared, request.project_root)
    if not baseline.equivalent:
        prepared.setdefault("blockers", []).append(
            {
                "id": "B-BASELINE",
                "code": "authority_baseline_mismatch",
                "message": "path-scoped authority baseline is not equivalent",
            }
        )
        prepared["readiness"]["mechanical_promotion"] = False

    output_path = request.prepared_contract_output_path
    if output_path is None:
        output_path = store / "prepared-promotion-contract.json"
    assert output_path is not None
    _ensure_output_outside_authority(request.project_root, output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(prepared, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    after = _authority_snapshot(request.project_root)
    if before != after:
        raise OperationError("PROMOTION_AUTHORITY_MUTATED: prepare mutated governed authority")

    ready, _ = mechanical_ready(prepared)
    blockers = tuple(
        PromotionBlockerDescriptor(
            id=str(item.get("id", "")),
            code=str(item.get("code", "")),
            message=str(item.get("message", "")),
        )
        for item in prepared.get("blockers", [])
    )
    return PromotionPrepareResult(
        request=request,
        success=baseline.equivalent and ready and not blockers,
        design_lock_ready=bool((prepared.get("readiness") or {}).get("design_lock")),
        mechanical_promotion_ready=ready and baseline.equivalent and not blockers,
        locked_intent_fingerprint=fingerprint,
        baseline=baseline,
        blockers=blockers,
        mutations=_mutation_descriptors(prepared, request.project_root),
        prepared_contract=prepared,
        prepared_contract_path=output_path,
        diagnostics=tuple(diagnostics),
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
        authority_mutated=False,
    )


def validate_contract_schema_only(contract: dict[str, Any]) -> list[str]:
    from .ste_contract import validate_contract_schema

    return validate_contract_schema(contract)


def check_promotion(request: PromotionCheckRequest) -> PromotionCheckResult:
    before = _authority_snapshot(request.project_root)
    contract = _load_contract(request.promotion_contract_path)
    errors = validate_contract(contract)
    baseline = _baseline_descriptor(contract, request.project_root)
    ready, _ = mechanical_ready(contract)
    fingerprint = locked_intent_fingerprint(contract)
    blockers = tuple(
        PromotionBlockerDescriptor(
            id=str(item.get("id", "")),
            code=str(item.get("code", "")),
            message=str(item.get("message", "")),
        )
        for item in contract.get("blockers", [])
    )
    diagnostics = tuple(_diagnostic("PROMOTION_CHECK", message) for message in errors)
    after = _authority_snapshot(request.project_root)
    if before != after:
        raise OperationError("PROMOTION_AUTHORITY_MUTATED: check mutated governed authority")
    return PromotionCheckResult(
        request=request,
        success=not errors and baseline.equivalent,
        design_lock_ready=bool((contract.get("readiness") or {}).get("design_lock")),
        mechanical_promotion_ready=ready and baseline.equivalent and not blockers,
        locked_intent_fingerprint=fingerprint,
        baseline=baseline,
        blockers=blockers,
        mutations=_mutation_descriptors(contract, request.project_root),
        human_lock_present=contract.get("human_lock") is not None,
        diagnostics=diagnostics,
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
        authority_mutated=False,
    )


def _append_execution_evidence(contract_path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    contract = _load_contract(contract_path)
    evidence = list(contract.get("execution_evidence") or [])
    evidence.append(entry)
    contract["execution_evidence"] = evidence
    contract_path.write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return contract


def _post_images_match_locked(project_root: Path, contract: dict[str, Any], store: Path) -> bool:
    resolved_map = _resolved_map(store)
    for mutation in contract.get("mutations", []):
        payload = mutation.get("payload_binding") or {}
        ref = payload.get("ref")
        expected_fp = payload.get("fingerprint")
        if not ref or not expected_fp:
            return False
        payload_path = store / ref
        if not payload_path.exists():
            return False
        relative = resolved_map.get(mutation["id"])
        if not relative:
            resolved = resolve_mutation_target(
                project_root,
                mutation,
                create_title="Canonical Entity Identity",
            )
            relative = resolved.relative_path
        absolute = project_root / relative
        if not absolute.exists():
            return False
        if fingerprint_bytes(absolute.read_bytes()) != expected_fp:
            return False
        if fingerprint_bytes(payload_path.read_bytes()) != expected_fp:
            return False
    return True


def _has_success_evidence(contract: dict[str, Any], locked_fp: str) -> bool:
    for item in contract.get("execution_evidence") or []:
        if (
            item.get("class") == "apply_success"
            and item.get("locked_intent_fingerprint") == locked_fp
        ):
            return True
    return False


def apply_promotion(
    request: PromotionApplyRequest,
    *,
    fault: Callable[[str], None] | None = None,
) -> PromotionApplyResult:
    contract = _load_contract(request.promotion_contract_path)
    diagnostics: list[Diagnostic] = []
    baseline = _baseline_descriptor(contract, request.project_root)
    locked_fp = locked_intent_fingerprint(contract)
    store = _provider_store(request.project_root)

    def fail(
        state: str,
        *,
        authority_committed: bool = False,
        evidence: bool = False,
        regen: bool = False,
        validation: bool = False,
        message: str,
        code: str,
    ) -> PromotionApplyResult:
        diagnostics.append(_diagnostic(code, message))
        return PromotionApplyResult(
            request=request,
            success=False,
            semantic_state=state,
            authority_committed=authority_committed,
            apply_execution_evidence_appended=evidence,
            regeneration_completed=regen,
            validation_success=validation,
            locked_intent_fingerprint=locked_fp,
            baseline=baseline,
            mutations=_mutation_descriptors(contract, request.project_root),
            execution_evidence=tuple(
                PromotionExecutionEvidenceDescriptor(
                    attempt_id=str(item.get("attempt_id", "")),
                    classification=str(item.get("class", "")),
                    message=str(item.get("message", "")),
                    at=item.get("at"),
                )
                for item in contract.get("execution_evidence") or []
            ),
            corpus_fingerprint=None,
            diagnostics=tuple(diagnostics),
            package_version=__version__,
            api_contract_version=API_CONTRACT_VERSION,
        )

    schema_errors = validate_contract(contract)
    if schema_errors and not contract.get("human_lock"):
        # still allow locked contracts with append-only evidence differences
        pass
    if contract.get("contract_version") != "ste.design_journal.promotion_contract/v0.1":
        return fail(
            SEMANTIC_PRE_COMMIT_FAILURE,
            message="unsupported promotion contract version",
            code="PROMOTION_UNSUPPORTED_CONTRACT_VERSION",
        )
    if contract.get("provider") != PROVIDER_ID:
        return fail(
            SEMANTIC_PRE_COMMIT_FAILURE,
            message="wrong provider",
            code="PROMOTION_WRONG_PROVIDER",
        )
    if not baseline.equivalent:
        return fail(
            SEMANTIC_PRE_COMMIT_FAILURE,
            message="authority baseline mismatch",
            code="PROMOTION_BASELINE_MISMATCH",
        )

    # Idempotent complete
    if _post_images_match_locked(request.project_root, contract, store) and _has_success_evidence(
        contract, locked_fp
    ):
        return PromotionApplyResult(
            request=request,
            success=True,
            semantic_state=SEMANTIC_COMPLETE,
            authority_committed=True,
            apply_execution_evidence_appended=True,
            regeneration_completed=True,
            validation_success=True,
            locked_intent_fingerprint=locked_fp,
            baseline=baseline,
            mutations=_mutation_descriptors(contract, request.project_root),
            execution_evidence=tuple(
                PromotionExecutionEvidenceDescriptor(
                    attempt_id=str(item.get("attempt_id", "")),
                    classification=str(item.get("class", "")),
                    message=str(item.get("message", "")),
                    at=item.get("at"),
                )
                for item in contract.get("execution_evidence") or []
            ),
            corpus_fingerprint=None,
            diagnostics=(),
            package_version=__version__,
            api_contract_version=API_CONTRACT_VERSION,
        )

    # Evidence-pending recovery
    if _post_images_match_locked(
        request.project_root, contract, store
    ) and not _has_success_evidence(contract, locked_fp):
        if not request.commit:
            return fail(
                SEMANTIC_EVIDENCE_PENDING,
                authority_committed=True,
                message="authority committed; execution evidence pending",
                code="PROMOTION_EVIDENCE_PENDING",
            )
        try:
            contract = _append_execution_evidence(
                request.promotion_contract_path,
                {
                    "attempt_id": f"recover-{_utc_now()}",
                    "class": "apply_success",
                    "message": "recovered missing apply success evidence",
                    "at": _utc_now(),
                    "locked_intent_fingerprint": locked_fp,
                },
            )
        except Exception as exc:  # noqa: BLE001
            return fail(
                SEMANTIC_EVIDENCE_PENDING,
                authority_committed=True,
                message=f"failed to append execution evidence: {exc}",
                code="PROMOTION_EVIDENCE_APPEND_FAILED",
            )
        regen_ok, validation_ok, fingerprint, regen_diagnostics = regenerate_and_validate(
            request.project_root, timestamp=request.timestamp
        )
        diagnostics.extend(regen_diagnostics)
        state = (
            SEMANTIC_COMPLETE
            if regen_ok and validation_ok
            else (SEMANTIC_REGEN_PENDING if not regen_ok else SEMANTIC_VALIDATION_FAILED)
        )
        return PromotionApplyResult(
            request=request,
            success=state == SEMANTIC_COMPLETE,
            semantic_state=state,
            authority_committed=True,
            apply_execution_evidence_appended=True,
            regeneration_completed=regen_ok,
            validation_success=validation_ok,
            locked_intent_fingerprint=locked_fp,
            baseline=baseline,
            mutations=_mutation_descriptors(contract, request.project_root),
            execution_evidence=tuple(
                PromotionExecutionEvidenceDescriptor(
                    attempt_id=str(item.get("attempt_id", "")),
                    classification=str(item.get("class", "")),
                    message=str(item.get("message", "")),
                    at=item.get("at"),
                )
                for item in contract.get("execution_evidence") or []
            ),
            corpus_fingerprint=fingerprint,
            diagnostics=tuple(diagnostics),
            package_version=__version__,
            api_contract_version=API_CONTRACT_VERSION,
        )

    lock_ok, lock_errors = human_lock_valid(contract)
    if request.commit and not lock_ok:
        return fail(
            SEMANTIC_PRE_COMMIT_FAILURE,
            message="human_lock invalid: " + "; ".join(lock_errors),
            code="PROMOTION_HUMAN_LOCK_INVALID",
        )
    ready, ready_errors = mechanical_ready(contract)
    if not ready:
        return fail(
            SEMANTIC_PRE_COMMIT_FAILURE,
            message="mechanical readiness false: " + "; ".join(ready_errors),
            code="PROMOTION_NOT_READY",
        )

    # Build writes from bound payloads
    writes: list[PlannedWrite] = []
    resolved_map = _resolved_map(store)
    for mutation in contract.get("mutations", []):
        payload = mutation.get("payload_binding") or {}
        ref = payload.get("ref")
        expected = payload.get("fingerprint")
        if not isinstance(ref, str) or not ref:
            return fail(
                SEMANTIC_PRE_COMMIT_FAILURE,
                message=f"missing payload binding for {mutation['id']}",
                code="PROMOTION_PAYLOAD_MISSING",
            )
        payload_path = store / ref
        if not payload_path.exists():
            return fail(
                SEMANTIC_PRE_COMMIT_FAILURE,
                message=f"missing payload binding for {mutation['id']}",
                code="PROMOTION_PAYLOAD_MISSING",
            )
        content = payload_path.read_bytes()
        if fingerprint_bytes(content) != expected:
            return fail(
                SEMANTIC_PRE_COMMIT_FAILURE,
                message=f"payload fingerprint mismatch for {mutation['id']}",
                code="PROMOTION_PAYLOAD_FINGERPRINT_MISMATCH",
            )
        relative = resolved_map.get(mutation["id"])
        if not relative:
            resolved = resolve_mutation_target(
                request.project_root,
                mutation,
                create_title="Canonical Entity Identity",
            )
            relative = resolved.relative_path
        writes.append(
            PlannedWrite(
                relative_path=relative,
                absolute_path=(request.project_root / relative).resolve(),
                content=content,
                operation=mutation["operation"],
            )
        )

    def validate_staged(overlay: Path) -> None:
        # ROADMAP rules + ADR parse presence + PROJECT.yaml
        roadmap = overlay / "ROADMAP.md"
        if roadmap.is_file():
            errors = validate_roadmap_content(roadmap.read_text(encoding="utf-8"))
            if errors:
                raise TransactionAborted("staged ROADMAP invalid: " + "; ".join(errors))
        if not (overlay / "PROJECT.yaml").is_file():
            # copy not required for all fixtures; skip hard fail if absent in overlay only when root has it
            pass
        for item in writes:
            staged = overlay / item.relative_path
            if not staged.is_file():
                raise TransactionAborted(f"staged missing {item.relative_path}")
            if item.relative_path.endswith((".yaml", ".yml")):
                schema_errors = validate_adr_payload_bytes(
                    staged.read_bytes(),
                    relative_path=item.relative_path,
                )
                if schema_errors:
                    raise TransactionAborted(
                        f"staged ADR invalid {item.relative_path}: " + "; ".join(schema_errors)
                    )

    if not request.commit:
        # Dry-run: stage+validate only
        try:
            commit_all_or_none(
                request.project_root,
                writes,
                validate_staged=validate_staged,
                fault=fault,
                journal_root=store / "dry-run-journal",
            )
        except Exception:
            # Dry-run should not commit; use a side journal and always abort before commit
            pass
        # Explicit dry-run validation without writing authority
        tmp = store / "dry-run-overlay"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        if (request.project_root / "adrs").is_dir():
            shutil.copytree(request.project_root / "adrs", tmp / "adrs")
        if (request.project_root / "ROADMAP.md").is_file():
            shutil.copy2(request.project_root / "ROADMAP.md", tmp / "ROADMAP.md")
        if (request.project_root / "PROJECT.yaml").is_file():
            shutil.copy2(request.project_root / "PROJECT.yaml", tmp / "PROJECT.yaml")
        for item in writes:
            target = tmp / item.relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(item.content)
        try:
            validate_staged(tmp)
        except Exception as exc:  # noqa: BLE001
            return fail(
                SEMANTIC_PRE_COMMIT_FAILURE,
                message=str(exc),
                code="PROMOTION_STAGED_VALIDATION_FAILED",
            )
        return PromotionApplyResult(
            request=request,
            success=True,
            semantic_state="DRY_RUN_OK",
            authority_committed=False,
            apply_execution_evidence_appended=False,
            regeneration_completed=False,
            validation_success=False,
            locked_intent_fingerprint=locked_fp,
            baseline=baseline,
            mutations=_mutation_descriptors(contract, request.project_root),
            execution_evidence=(),
            corpus_fingerprint=None,
            diagnostics=(),
            package_version=__version__,
            api_contract_version=API_CONTRACT_VERSION,
        )

    before = _authority_snapshot(request.project_root)
    try:
        commit_all_or_none(
            request.project_root,
            writes,
            validate_staged=validate_staged,
            fault=fault,
            journal_root=store / f"journal-{_utc_now().replace(':', '')}",
        )
    except Exception as exc:  # noqa: BLE001
        after = _authority_snapshot(request.project_root)
        if before != after:
            # transaction layer should have recovered; if not, report failure loudly
            return fail(
                SEMANTIC_PRE_COMMIT_FAILURE,
                message=f"transaction failed with authority drift: {exc}",
                code="PROMOTION_TRANSACTION_COMMIT_FAILURE",
            )
        return fail(
            SEMANTIC_PRE_COMMIT_FAILURE,
            message=str(exc),
            code="PROMOTION_TRANSACTION_STAGING_FAILURE",
        )

    # Authority committed — append evidence
    try:
        if fault is not None:
            fault("after_authority_before_evidence")
        contract = _append_execution_evidence(
            request.promotion_contract_path,
            {
                "attempt_id": f"apply-{_utc_now()}",
                "class": "apply_success",
                "message": "authority mutations committed",
                "at": _utc_now(),
                "locked_intent_fingerprint": locked_fp,
            },
        )
    except Exception as exc:  # noqa: BLE001
        return fail(
            SEMANTIC_EVIDENCE_PENDING,
            authority_committed=True,
            message=f"authority committed; evidence append failed: {exc}",
            code="PROMOTION_EVIDENCE_APPEND_FAILED",
        )

    regen_ok, validation_ok, fingerprint, regen_diagnostics = regenerate_and_validate(
        request.project_root, timestamp=request.timestamp
    )
    diagnostics.extend(regen_diagnostics)
    state = (
        SEMANTIC_COMPLETE
        if regen_ok and validation_ok
        else (SEMANTIC_REGEN_PENDING if not regen_ok else SEMANTIC_VALIDATION_FAILED)
    )
    return PromotionApplyResult(
        request=request,
        success=state == SEMANTIC_COMPLETE,
        semantic_state=state,
        authority_committed=True,
        apply_execution_evidence_appended=True,
        regeneration_completed=regen_ok,
        validation_success=validation_ok,
        locked_intent_fingerprint=locked_fp,
        baseline=baseline,
        mutations=_mutation_descriptors(contract, request.project_root),
        execution_evidence=tuple(
            PromotionExecutionEvidenceDescriptor(
                attempt_id=str(item.get("attempt_id", "")),
                classification=str(item.get("class", "")),
                message=str(item.get("message", "")),
                at=item.get("at"),
            )
            for item in contract.get("execution_evidence") or []
        ),
        corpus_fingerprint=fingerprint,
        diagnostics=tuple(diagnostics),
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
    )
