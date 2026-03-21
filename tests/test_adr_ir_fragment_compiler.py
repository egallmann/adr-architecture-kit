from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml
from click.testing import CliRunner

from src.adr_kit.cli.main import cli
from src.adr_kit.compiler import (
    AdrIrFragmentCompileError,
    AdrIrSourceDescriptor,
    compile_logical_adr_ir_fragments,
)
from src.adr_kit.compiler.backend.adr_ir_fragment_rendering import (
    canonical_json_bytes,
    lower_ascii,
    norm,
    sha256_hex,
    sha256_prefixed_hex,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
KERNEL_SCHEMA_PATH = (
    REPO_ROOT.parent / "ste-kernel" / "architecture-ir" / "architecture-ir.schema.json"
)


def _load_kernel_schema() -> dict:
    return json.loads(KERNEL_SCHEMA_PATH.read_text(encoding="utf-8"))


def _write_logical_adr(tmp_path: Path, filename: str, payload: dict) -> Path:
    path = tmp_path / filename
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _logical_adr_payload(
    *,
    adr_id: str = "ADR-L-0001",
    status: str = "accepted",
    capability_ids: list[str] | None = None,
    decisions: list[dict] | None = None,
    constraints: list[dict] | None = None,
    invariants: list[dict] | None = None,
    tags: list[str] | None = None,
) -> dict:
    capability_ids = capability_ids or ["CAP-0001"]
    return {
        "schema_version": "1.0",
        "adr_type": "logical",
        "id": adr_id,
        "title": f"{adr_id} Logical ADR",
        "status": status,
        "created_date": "2026-03-20",
        "authors": ["erik.gallmann"],
        "domains": ["architecture"],
        "tags": tags or [],
        "context": "Profile-v1 logical ADR for IR compilation tests.",
        "capabilities": [
            {
                "id": capability_id,
                "name": f"Capability {capability_id}",
                "description": f"Description for {capability_id}.",
            }
            for capability_id in capability_ids
        ],
        "constraints": constraints if constraints is not None else [],
        "invariants": invariants if invariants is not None else [],
        "decisions": decisions
        if decisions is not None
        else [
            {
                "id": "DEC-0001",
                "summary": "Promote a deterministic logical architecture fragment.",
                "rationale": "Kernel IR ingestion requires stable ADR compilation.",
                "enables_capabilities": capability_ids,
            }
        ],
        "gaps": [],
    }


def _compile(tmp_path: Path, paths: list[Path]):
    return compile_logical_adr_ir_fragments(
        adr_file_paths=paths,
        namespace="repo:ste-kernel:test",
        artifact_kind="logical-adr",
        last_updated="2026-03-20T12:00:00.000Z",
        scope_root=tmp_path,
    )


def _build_compiled_document(result) -> dict:
    capabilities = [record for record in result.entities if record["kind"] == "capability"]
    decisions = [record for record in result.entities if record["kind"] == "decision"]
    return {
        "ir_version": "0.1.0",
        "schema_id": "https://ste-kernel.local/schema/architecture-ir/0.1.0/architecture-ir.schema.json",
        "document_id": "sha256:" + "a" * 64,
        "assembled_at": "2026-03-20T12:00:00.000Z",
        "namespace": "repo:ste-kernel:test",
        "entities": {
            "capabilities": capabilities,
            "decisions": decisions,
            "components": [],
            "invariants": [],
            "rules": [],
            "evidences": [],
        },
        "relationships": {
            "decision_supports_capability": result.relationships,
            "component_implements_decision": [],
            "invariant_constrains_component": [],
            "rule_evaluates_decision": [],
            "evidence_supports_component": [],
        },
    }


def test_norm_and_lower_ascii_helpers_follow_logical_adr_ir_profile_rules() -> None:
    assert norm("  CAP-0001  ") == "CAP-0001"
    assert lower_ascii("  CAP-0001  ") == "cap-0001"


def test_compile_logical_adr_ir_fragments_emits_schema_valid_records(tmp_path: Path) -> None:
    adr_path = _write_logical_adr(
        tmp_path,
        "ADR-L-0001.yaml",
        _logical_adr_payload(tags=["  Core  ", "core", "runtime"]),
    )

    result = _compile(tmp_path, [adr_path])

    assert {record["kind"] for record in result.entities} == {"decision", "capability"}
    assert {record["type"] for record in result.relationships} == {"decision_supports_capability"}
    assert result.canonical_fragment_bytes == canonical_json_bytes(result.records)
    assert all("document_id" not in record for record in result.records)
    assert all(record["id"].startswith(("decision:", "capability:", "rel:")) for record in result.records)
    assert result.entities[0].get("tags") == ["Core", "core", "runtime"]

    compiled_document = _build_compiled_document(result)
    jsonschema.validate(instance=compiled_document, schema=_load_kernel_schema())


def test_provenance_content_hash_matches_logical_adr_ir_profile_fragment_shape(tmp_path: Path) -> None:
    adr_path = _write_logical_adr(tmp_path, "ADR-L-0001.yaml", _logical_adr_payload())

    result = _compile(tmp_path, [adr_path])
    capability = next(record for record in result.entities if record["kind"] == "capability")
    decision = next(record for record in result.entities if record["kind"] == "decision")
    relationship = result.relationships[0]

    capability_fragment = {
        "schema_version": "1.0",
        "document_id": "ADR-L-0001",
        "decision_id": "",
        "record_kind": "capability",
        "record_id": capability["id"],
        "namespace": "repo:ste-kernel:test",
    }
    decision_fragment = {
        "schema_version": "1.0",
        "document_id": "ADR-L-0001",
        "decision_id": "DEC-0001",
        "record_kind": "decision",
        "record_id": decision["id"],
        "namespace": "repo:ste-kernel:test",
    }
    relationship_fragment = {
        "schema_version": "1.0",
        "document_id": "ADR-L-0001",
        "decision_id": "DEC-0001",
        "record_kind": "relationship",
        "record_id": relationship["id"],
        "namespace": "repo:ste-kernel:test",
    }

    assert capability["provenance"]["derivation_chain"] == [
        {
            "step": 0,
            "adapter": "adr",
            "operation": "compile_logical_adr_to_ir_fragment",
            "input_ref": "repo://ADR-L-0001.yaml",
            "adapter_schema_version": "logical_adr_ir_fragment.v1",
            "content_hash": sha256_prefixed_hex(capability_fragment),
        }
    ]
    assert decision["provenance"]["derivation_chain"][0]["content_hash"] == sha256_prefixed_hex(
        decision_fragment
    )
    assert relationship["provenance"]["derivation_chain"][0]["content_hash"] == sha256_prefixed_hex(
        relationship_fragment
    )


def test_compile_is_deterministic_across_reordered_source_arrays(tmp_path: Path) -> None:
    canonical_path = _write_logical_adr(
        tmp_path,
        "ADR-L-0100-a.yaml",
        _logical_adr_payload(
            adr_id="ADR-L-0100",
            capability_ids=["CAP-0001", "CAP-0002"],
            decisions=[
                {
                    "id": "DEC-0001",
                    "summary": "Decision one.",
                    "rationale": "Rationale one.",
                    "enables_capabilities": ["CAP-0001"],
                },
                {
                    "id": "DEC-0002",
                    "summary": "Decision two.",
                    "rationale": "Rationale two.",
                    "enables_capabilities": ["CAP-0002"],
                },
            ],
        ),
    )
    reordered_path = _write_logical_adr(
        tmp_path,
        "ADR-L-0100-b.yaml",
        _logical_adr_payload(
            adr_id="ADR-L-0100",
            capability_ids=["CAP-0002", "CAP-0001"],
            decisions=[
                {
                    "id": "DEC-0002",
                    "summary": "Decision two.",
                    "rationale": "Rationale two.",
                    "enables_capabilities": ["CAP-0002"],
                },
                {
                    "id": "DEC-0001",
                    "summary": "Decision one.",
                    "rationale": "Rationale one.",
                    "enables_capabilities": ["CAP-0001"],
                },
            ],
        ),
    )

    shared_sources = {
        canonical_path: AdrIrSourceDescriptor(
            artifact_uri="repo://logical/ADR-L-0100.yaml",
            input_ref="repo://logical/ADR-L-0100.yaml",
        ),
        reordered_path: AdrIrSourceDescriptor(
            artifact_uri="repo://logical/ADR-L-0100.yaml",
            input_ref="repo://logical/ADR-L-0100.yaml",
        ),
    }
    first = compile_logical_adr_ir_fragments(
        adr_file_paths=[canonical_path],
        namespace="repo:ste-kernel:test",
        artifact_kind="logical-adr",
        last_updated="2026-03-20T12:00:00.000Z",
        scope_root=tmp_path,
        source_overrides=shared_sources,
    )
    second = compile_logical_adr_ir_fragments(
        adr_file_paths=[reordered_path],
        namespace="repo:ste-kernel:test",
        artifact_kind="logical-adr",
        last_updated="2026-03-20T12:00:00.000Z",
        scope_root=tmp_path,
        source_overrides=shared_sources,
    )

    assert first.canonical_fragment_bytes == second.canonical_fragment_bytes


def test_compile_multiple_files_globally_sorts_fragment_records(tmp_path: Path) -> None:
    path_a = _write_logical_adr(
        tmp_path,
        "ADR-L-0002.yaml",
        _logical_adr_payload(
            adr_id="ADR-L-0002",
            capability_ids=["CAP-0200"],
            decisions=[
                {
                    "id": "DEC-0200",
                    "summary": "Decision 0200.",
                    "rationale": "Rationale 0200.",
                    "enables_capabilities": ["CAP-0200"],
                }
            ],
        ),
    )
    path_b = _write_logical_adr(
        tmp_path,
        "ADR-L-0001.yaml",
        _logical_adr_payload(
            adr_id="ADR-L-0001",
            capability_ids=["CAP-0100"],
            decisions=[
                {
                    "id": "DEC-0100",
                    "summary": "Decision 0100.",
                    "rationale": "Rationale 0100.",
                    "enables_capabilities": ["CAP-0100"],
                }
            ],
        ),
    )

    result = _compile(tmp_path, [path_a, path_b])

    assert [record["id"] for record in result.records] == sorted(
        (record["id"] for record in result.records),
        key=lambda item: item.encode("utf-8"),
    )


def test_compile_fails_fast_for_profile_v1_violations(tmp_path: Path) -> None:
    invalid_cases = {
        "adr-v": {
            **_logical_adr_payload(adr_id="ADR-V-0001"),
            "vision_category": True,
        },
        "nonempty-constraints": _logical_adr_payload(
            constraints=[
                {
                    "id": "CONST-0001",
                    "type": "technical",
                    "description": "Constraint.",
                    "rationale": "Rationale.",
                }
            ]
        ),
        "nonempty-invariants": _logical_adr_payload(
            invariants=[
                {
                    "id": "INV-0001",
                    "statement": "Must hold.",
                    "scope": "global",
                    "enforcement_level": "must",
                    "enforcement_mechanism": "design",
                    "verification_method": "automated",
                    "rationale": "Rationale.",
                }
            ]
        ),
        "governs-components": _logical_adr_payload(
            decisions=[
                {
                    "id": "DEC-0001",
                    "summary": "Decision one.",
                    "rationale": "Rationale one.",
                    "enables_capabilities": ["CAP-0001"],
                    "governs_components": ["component-a"],
                }
            ]
        ),
        "unknown-capability": _logical_adr_payload(
            decisions=[
                {
                    "id": "DEC-0001",
                    "summary": "Decision one.",
                    "rationale": "Rationale one.",
                    "enables_capabilities": ["CAP-9999"],
                }
            ]
        ),
        "unreferenced-capability": _logical_adr_payload(
            capability_ids=["CAP-0001", "CAP-0002"],
            decisions=[
                {
                    "id": "DEC-0001",
                    "summary": "Decision one.",
                    "rationale": "Rationale one.",
                    "enables_capabilities": ["CAP-0001"],
                }
            ],
        ),
        "duplicate-relationship-triple": _logical_adr_payload(
            decisions=[
                {
                    "id": "DEC-0001",
                    "summary": "Decision one.",
                    "rationale": "Rationale one.",
                    "enables_capabilities": ["CAP-0001", "CAP-0001"],
                }
            ]
        ),
    }

    for name, payload in invalid_cases.items():
        path = _write_logical_adr(tmp_path, f"{name}.yaml", payload)
        try:
            _compile(tmp_path, [path])
        except AdrIrFragmentCompileError:
            continue
        raise AssertionError(f"Expected logical ADR IR profile compile failure for case: {name}")


def test_compile_rejects_duplicate_emitted_entity_ids_across_documents(tmp_path: Path) -> None:
    first = _write_logical_adr(
        tmp_path,
        "ADR-L-0200-a.yaml",
        _logical_adr_payload(adr_id="ADR-L-0200"),
    )
    second = _write_logical_adr(
        tmp_path,
        "ADR-L-0200-b.yaml",
        _logical_adr_payload(adr_id="ADR-L-0200"),
    )

    try:
        _compile(tmp_path, [first, second])
    except AdrIrFragmentCompileError as exc:
        assert "Duplicate emitted capability id" in str(exc) or "Duplicate emitted decision id" in str(exc)
        return
    raise AssertionError("Expected duplicate entity ids to fail fast.")


def test_hashed_ids_follow_canonical_payloads(tmp_path: Path) -> None:
    adr_path = _write_logical_adr(tmp_path, "ADR-L-0001.yaml", _logical_adr_payload())

    result = _compile(tmp_path, [adr_path])
    capability = next(record for record in result.entities if record["kind"] == "capability")
    decision = next(record for record in result.entities if record["kind"] == "decision")
    relationship = result.relationships[0]

    adr_decision_key = "ADR-L-0001\u001fDEC-0001"
    assert decision["adr_id"] == adr_decision_key
    assert decision["id"] == f"decision:{sha256_hex({'namespace': 'repo:ste-kernel:test', 'adr_id': adr_decision_key})}"
    assert capability["id"] == f"capability:{sha256_hex({'namespace': 'repo:ste-kernel:test', 'slug': 'cap-0001'})}"
    assert relationship["id"] == (
        "rel:"
        + sha256_hex(
            {
                "namespace": "repo:ste-kernel:test",
                "type": "decision_supports_capability",
                "from_id": decision["id"],
                "to_id": capability["id"],
            }
        )
    )


def test_cli_compile_ir_fragments_writes_canonical_array(tmp_path: Path) -> None:
    adr_path = _write_logical_adr(tmp_path, "ADR-L-0001.yaml", _logical_adr_payload())
    output_path = tmp_path / "out" / "fragment.json"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "compile-ir-fragments",
            "--scope-root",
            str(tmp_path),
            "--adr-file",
            str(adr_path),
            "--namespace",
            "repo:ste-kernel:test",
            "--artifact-kind",
            "logical-adr",
            "--last-updated",
            "2026-03-20T12:00:00.000Z",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert output_path.exists()
    records = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(records) == 3
