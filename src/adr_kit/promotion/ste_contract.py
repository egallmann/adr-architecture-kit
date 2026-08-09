"""STE Promotion Contract v0.1 conformance helpers (provider-local)."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

CONTRACT_VERSION = "ste.design_journal.promotion_contract/v0.1"
DESIGN_JOURNAL_VERSION = "ste.design_journal/v0.1"
PROVIDER_ID = "adr-architecture-kit"

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_CANDIDATES = (
    _REPO_ROOT / "contracts" / "design-journal-promotion-contract" / "v0.1" / "schema.json",
    Path(__file__).resolve().parent / "schemas" / "promotion_contract_v0_1.json",
)


def jcs_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_prefixed(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_promotion_contract_schema() -> dict[str, Any]:
    for candidate in _SCHEMA_CANDIDATES:
        if candidate.is_file():
            loaded = load_json(candidate)
            if isinstance(loaded, dict):
                return loaded
    raise FileNotFoundError("STE promotion contract schema mirror not found")


def _scope_outcome_ids(contract: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for mutation in contract.get("mutations", []):
        ids.update(mutation.get("outcome_refs", []))
    for outcome in contract.get("outcomes", []):
        if outcome.get("promotion_required"):
            ids.add(outcome["id"])
    return ids


def locked_intent_fingerprint(contract: dict[str, Any]) -> str:
    outcomes: list[dict[str, Any]] = []
    scoped = _scope_outcome_ids(contract)
    for outcome in contract.get("outcomes", []):
        if not outcome.get("promotion_required") and outcome.get("id") not in scoped:
            continue
        item: dict[str, Any] = {
            "id": outcome["id"],
            "category": outcome["category"],
            "promotion_required": outcome["promotion_required"],
        }
        if "disposition" in outcome:
            item["disposition"] = outcome["disposition"]
        if "statement" in outcome:
            item["statement"] = outcome["statement"]
        if "semantic_binding" in outcome:
            item["semantic_binding"] = outcome["semantic_binding"]
        outcomes.append(item)
    outcomes.sort(key=lambda item: item["id"])
    mutations: list[dict[str, Any]] = []
    for mutation in contract.get("mutations", []):
        mutations.append(
            {
                "id": mutation["id"],
                "operation": mutation["operation"],
                "provider": mutation["provider"],
                "provider_target_ref": mutation["provider_target_ref"],
                "outcome_refs": list(mutation["outcome_refs"]),
                "payload_binding": mutation.get("payload_binding"),
                "schema_binding": mutation.get("schema_binding"),
                "validation_evidence": mutation.get("validation_evidence"),
            }
        )
    mutations.sort(key=lambda item: item["id"])
    locked = {
        "contract_version": contract["contract_version"],
        "design_journal_version": contract["design_journal_version"],
        "journal_id": contract["journal_id"],
        "provider": contract.get("provider"),
        "authority_baseline": contract.get("authority_baseline"),
        "promotion_scope": {
            "outcome_ids": sorted(scoped),
            "mutation_ids": sorted(item["id"] for item in contract.get("mutations", [])),
        },
        "outcomes": outcomes,
        "mutations": mutations,
    }
    return sha256_prefixed(jcs_dumps(locked))


def mechanical_ready(contract: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if contract.get("blockers"):
        errors.append("non-empty blockers")
    provider = contract.get("provider")
    if not provider:
        errors.append("provider required")
    baseline = contract.get("authority_baseline")
    if not baseline:
        errors.append("authority_baseline required")
    elif baseline.get("provider") != provider:
        errors.append("authority_baseline.provider mismatch")
    outcome_ids = [item["id"] for item in contract.get("outcomes", [])]
    if len(outcome_ids) != len(set(outcome_ids)):
        errors.append("duplicate outcome id")
    mutation_ids = [item["id"] for item in contract.get("mutations", [])]
    if len(mutation_ids) != len(set(mutation_ids)):
        errors.append("duplicate mutation id")
    providers = {item["provider"] for item in contract.get("mutations", [])}
    if len(providers) > 1:
        errors.append("multi-provider unsupported in v0.1")
    if providers and provider and providers != {provider}:
        errors.append("mutation provider != contract provider")
    id_set = set(outcome_ids)
    mapped: set[str] = set()
    for mutation in contract.get("mutations", []):
        for ref in mutation.get("outcome_refs", []):
            if ref not in id_set:
                errors.append(f"unresolved outcome_ref {ref}")
            mapped.add(ref)
        payload = mutation.get("payload_binding") or {}
        schema = mutation.get("schema_binding") or {}
        if not (payload.get("fingerprint") or payload.get("immutable_revision")):
            errors.append(f"mutation {mutation['id']} missing immutable payload_binding")
        if not (schema.get("fingerprint") or schema.get("immutable_revision")):
            errors.append(f"mutation {mutation['id']} missing immutable schema_binding")
        evidence = mutation.get("validation_evidence")
        if not evidence:
            errors.append(f"mutation {mutation['id']} missing validation_evidence")
        else:
            payload_fp = payload.get("fingerprint")
            schema_fp = schema.get("fingerprint")
            if payload_fp and evidence.get("payload_fingerprint") != payload_fp:
                errors.append(f"mutation {mutation['id']} validation payload fingerprint mismatch")
            if schema_fp and evidence.get("schema_binding_fingerprint") != schema_fp:
                errors.append(f"mutation {mutation['id']} validation schema fingerprint mismatch")
    for outcome in contract.get("outcomes", []):
        if outcome.get("promotion_required") and outcome["id"] not in mapped:
            errors.append(f"unmapped promotion_required outcome {outcome['id']}")
        if outcome.get("promotion_required") and not (
            outcome.get("statement") or outcome.get("semantic_binding")
        ):
            errors.append(f"promotion_required outcome {outcome['id']} missing semantic binding")
    return (len(errors) == 0, errors)


def validate_contract_schema(contract: dict[str, Any]) -> list[str]:
    schema = load_promotion_contract_schema()
    validator = Draft202012Validator(schema)
    return [
        f"schema: {error.message}"
        for error in sorted(validator.iter_errors(contract), key=lambda item: list(item.path))
    ]


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors = validate_contract_schema(contract)
    ready, ready_errors = mechanical_ready(contract)
    stored = (contract.get("readiness") or {}).get("mechanical_promotion")
    if stored is True and not ready:
        errors.append(
            "behavioral: readiness.mechanical_promotion true but predicate false: "
            + "; ".join(ready_errors)
        )
    if contract.get("blockers") and stored is True:
        errors.append("behavioral: blockers non-empty but mechanical_promotion true")
    providers = {
        mutation.get("provider")
        for mutation in contract.get("mutations", [])
        if mutation.get("provider")
    }
    if len(providers) > 1:
        errors.append("behavioral: multi-provider unsupported in v0.1")
    return errors


def human_lock_valid(contract: dict[str, Any]) -> tuple[bool, list[str]]:
    lock = contract.get("human_lock")
    if not lock:
        return False, ["human_lock missing"]
    errors: list[str] = []
    if lock.get("approved") is not True:
        errors.append("human_lock.approved must be true")
    for field in ("approver", "approved_at", "journal_id", "locked_intent_fingerprint"):
        if not lock.get(field):
            errors.append(f"human_lock.{field} required")
    if lock.get("journal_id") and lock.get("journal_id") != contract.get("journal_id"):
        errors.append("human_lock.journal_id mismatch")
    expected = locked_intent_fingerprint(contract)
    if lock.get("locked_intent_fingerprint") and lock["locked_intent_fingerprint"] != expected:
        errors.append("human_lock.locked_intent_fingerprint mismatch")
    ready, ready_errors = mechanical_ready(contract)
    if not ready:
        errors.extend(ready_errors)
    return len(errors) == 0, errors


def immutable_fields_tampered(before: dict[str, Any], after: dict[str, Any]) -> bool:
    left = dict(before)
    right = dict(after)
    left.pop("execution_evidence", None)
    right.pop("execution_evidence", None)
    return locked_intent_fingerprint(left) != locked_intent_fingerprint(right)
