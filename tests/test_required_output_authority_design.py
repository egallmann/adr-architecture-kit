"""ADR/schema audit only; publication is not evidence of runtime execution."""

from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft7Validator
from referencing import Registry, Resource

from adr_kit.semantic_contract import (
    get_semantic_contract,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)
from adr_kit.validators.adr_validator import ADRValidator

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "adrs/logical/ADR-L-0038-explicit-required-output-authority-across-the-ai-catalog.yaml"
AI = "architecture-interpretation/1.3/"


def document() -> dict[str, Any]:
    return yaml.safe_load(ADR.read_text(encoding="utf-8"))


def matrix() -> list[dict[str, str]]:
    text = next(d["rationale"] for d in document()["decisions"] if d["alias_id"] == "DEC-9011")
    return yaml.safe_load(text.split("```yaml\n", 1)[1].split("```", 1)[0])


def source_shape(selector: str) -> dict[str, Any]:
    filename, _, pointer = selector.partition("#")
    schema = load_semantic_resource("authoring/1.7/schema/" + filename.removesuffix(".json"))
    for token in pointer.strip("/").split("/") if pointer.strip("/") else []:
        schema = schema[token.replace("~1", "/").replace("~0", "~")]
    return schema


def registry() -> Registry:
    schemas = [
        load_semantic_resource("authoring/1.7/schema/" + name + ".schema")
        for name in (
            "types",
            "adr-common",
            "adr-logical",
            "adr-physical-base",
            "adr-physical-system",
            "adr-physical-component",
        )
    ]
    return Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in schemas)


def matrix_errors(rows: list[dict[str, str]]) -> list[str]:
    """Audit proposed selectors, not an output producer or interpreter."""
    catalog = load_semantic_resource(AI + "field-dispositions-1.7-to-2.5")
    types = {t["semantic_type"]: t for t in catalog["semantic_types"]}
    errors: list[str] = []
    counts = Counter(row["semantic_type"] for row in rows)
    if set(counts) != set(types) or any(n != 1 for n in counts.values()):
        errors.append("missing, duplicate or unknown semantic type")
    for row in rows:
        ty = row["semantic_type"]
        if ty not in types:
            continue
        if row["source_schema"] != types[ty]["source_schema"]:
            errors.append("wrong source selector")
            continue
        if row["category"] not in ("regular", "normative-proposition"):
            if row["name"] != "not-applicable" or row["summary"] != "not-applicable":
                errors.append("nonentity envelope invented")
            continue
        schema = source_shape(row["source_schema"])
        for destination in ("name", "summary"):
            mode, separator, field = row[destination].partition(":")
            if separator != ":" or mode not in ("A", "R"):
                errors.append("no actual qualified producer")
                continue
            if field not in schema.get("required", []) or field not in schema["properties"]:
                errors.append("input absent, optional or unknown")
                continue
            if mode == "A":
                matches = [
                    f
                    for f in types[ty]["field_dispositions"]
                    if f["semantic_field_key"] == ty + "#/" + field
                    and f["disposition"] == "canonical_field_placement"
                    and catalog["destination_catalog"][f["destination_ref"]].get("path")
                    == "/" + destination
                ]
                if len(matches) != 1:
                    errors.append("unqualified authored placement")
    return errors


def assert_governed_lifecycle(path: Path) -> None:
    """Check governed evidence shape, not whether a human actually granted approval."""
    adr = yaml.safe_load(path.read_text(encoding="utf-8"))
    result = ADRValidator(project_root=ROOT).validate_file(path, mode="complete")
    assert result.valid, result.errors
    governance = adr.get("governance") or {}
    if adr["status"] == "proposed":
        assert governance.get("approved_by") is None
        assert governance.get("approved_date") is None
    elif adr["status"] == "accepted":
        assert isinstance(governance.get("approved_by"), str)
        assert governance["approved_by"].strip()
        assert governance.get("approved_date") is not None


def test_lifecycle_identities_and_human_gate() -> None:
    assert_governed_lifecycle(ADR)
    adr = document()
    assert adr["alias_id"] == "ADR-L-0038"
    assert [d["alias_id"] for d in adr["decisions"]] == [f"DEC-{n}" for n in range(9009, 9017)]
    assert [d["alias_id"] for d in adr["invariants"]] == [f"INV-{n:04}" for n in range(301, 309)]
    ids = [adr["id"]] + [x["id"] for k in ("decisions", "invariants") for x in adr[k]]
    assert len(ids) == len(set(ids)) == 17
    text = " ".join("\n".join(d["rationale"] for d in adr["decisions"]).lower().split())
    for phrase in (
        "BLOCKED",
        "not a producer",
        "allOf/oneOf/if/then",
        "input types and presence",
        "independent output comparison",
        "contextual provenance dependencies",
        "whole-ledger",
        "AI 1.4",
        "ACC 1.4",
        "NM 2.5",
        "Human architectural acceptance",
        "Unresolved requires",
        "label duplication only",
        "no substantive",
    ):
        assert phrase.lower() in text


@pytest.mark.parametrize("status", ["proposed", "accepted"])
def test_lifecycle_allows_governed_metadata_and_later_acceptance(
    tmp_path: Path, status: str
) -> None:
    # Synthetic fixtures are not approval of ADR-L-0038; the source is never written.
    adr = document()
    adr["status"] = status
    adr["governance"] = {"implementation_authority": "advisory"}
    if status == "accepted":
        adr["governance"].update(
            approved_by="fixture-reviewer", approved_date="2026-10-24T12:00:00Z"
        )
    path = tmp_path / "lifecycle.yaml"
    path.write_text(yaml.safe_dump(adr), encoding="utf-8")
    assert_governed_lifecycle(path)


@pytest.mark.parametrize(
    ("status", "governance"),
    [
        ("proposed", {"approved_by": "fixture-reviewer"}),
        ("proposed", {"approved_date": "2026-10-24T12:00:00Z"}),
        ("proposed", {"approved_by": "fixture-reviewer", "approved_date": "2026-10-24T12:00:00Z"}),
        ("accepted", {}),
        ("accepted", {"approved_by": "fixture-reviewer"}),
        ("accepted", {"approved_date": "2026-10-24T12:00:00Z"}),
        ("accepted", {"approved_by": " ", "approved_date": "2026-10-24T12:00:00Z"}),
        ("accepted", {"approved_by": "fixture-reviewer", "approved_date": "not-a-date"}),
        (
            "accepted",
            {
                "approved_by": "fixture-reviewer",
                "approved_date": "2026-10-24T12:00:00Z",
                "steelman_review_required": True,
                "steelman_review_completed": True,
            },
        ),
    ],
)
def test_lifecycle_rejects_fabricated_or_incomplete_acceptance_metadata(
    tmp_path: Path, status: str, governance: dict[str, Any]
) -> None:
    adr = document()
    adr.update(status=status, governance=governance)
    path = tmp_path / "lifecycle.yaml"
    path.write_text(yaml.safe_dump(adr), encoding="utf-8")
    with pytest.raises(AssertionError):
        assert_governed_lifecycle(path)


def test_all_27_types_have_one_explicit_branch_and_label_policy() -> None:
    rows = matrix()
    assert not matrix_errors(rows)
    assert Counter(r["category"] for r in rows) == {
        "regular": 17,
        "normative-proposition": 1,
        "canonical-relationship": 1,
        "compatibility-relationship": 6,
        "owner-local-value": 1,
        "proposition-value": 1,
    }
    regular = [r for r in rows if r["category"] == "regular"]
    assert sum(r["name"].startswith("R:") for r in regular) == 9
    assert sum(r["summary"].startswith("R:") for r in regular) == 15
    assert sum(r["name"].startswith("R:") and r["summary"].startswith("R:") for r in regular) == 7
    for row in rows:
        if row["name"].startswith("R:"):
            assert row["name"] == "R:alias_name"
    system = next(r for r in rows if r["semantic_type"] == "entity/system")
    assert system["summary"] == "R:alias_name"
    assert set(source_shape(system["source_schema"])["properties"]) == {
        "id",
        "alias_id",
        "alias_name",
    }


def test_label_sources_are_required_strings_under_exact_schema_references() -> None:
    schemas = registry()
    for row in matrix():
        if row["category"] not in ("regular", "normative-proposition"):
            continue
        filename = row["source_schema"].split("#", 1)[0]
        root = load_semantic_resource("authoring/1.7/schema/" + filename.removesuffix(".json"))
        for field in (row["name"].split(":")[1], row["summary"].split(":")[1]):
            pointer = row["source_schema"].partition("#")[2] + "/properties/" + field
            validator = Draft7Validator({"$ref": root["$id"] + "#" + pointer}, registry=schemas)
            assert not validator.is_valid(17)
            assert not validator.is_valid({"text": "invented"})
            assert validator.is_valid("qualified-label")


def test_every_summary_has_the_approved_substantive_or_label_source() -> None:
    expected = {
        "adr/logical": "R:context",
        "adr/physical-system": "R:context",
        "adr/physical-component": "R:context",
        "entity/boundary": "R:description",
        "entity/capability": "R:description",
        "entity/component": "R:responsibilities",
        "entity/contract": "R:guarantees",
        "entity/data_flow": "R:description",
        "entity/decision": "A:summary",
        "entity/evidence_expectation": "R:description",
        "entity/extension": "R:rationale",
        "entity/gap": "R:question",
        "entity/implementation_decision": "A:summary",
        "entity/interface": "R:specification",
        "entity/invariant": "R:statement",
        "entity/system": "R:alias_name",
        "entity/system_boundary": "R:description",
        "entity/normative_proposition": "R:statement",
    }
    assert {
        r["semantic_type"]: r["summary"]
        for r in matrix()
        if r["category"] in ("regular", "normative-proposition")
    } == expected


@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "source", "blocked", "optional", "placement", "nonentity"]
)
def test_incomplete_or_competing_entries_do_not_satisfy_coverage(mutation: str) -> None:
    rows = copy.deepcopy(matrix())
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif mutation == "source":
        rows[0]["source_schema"] = "adr-logical.schema.json#/missing"
    elif mutation == "blocked":
        rows[0]["summary"] = "BLOCKED"
    elif mutation == "optional":
        rows[0]["summary"] = "R:modified_date"
    elif mutation == "placement":
        rows[0]["summary"] = "A:context"
    else:
        next(r for r in rows if r["category"] == "proposition-value")["name"] = "R:alias_name"
    assert matrix_errors(rows)


def test_complete_nm_branches_and_source_permitted_strings() -> None:
    nm = load_semantic_resource("normalized-model/2.5/schema/normalized-entity.schema")
    Draft7Validator.check_schema(nm)
    regular, proposition = nm["oneOf"]
    assert len(regular["required"]) == 14
    assert {"name", "summary", "lifecycle_stage"} <= set(regular["required"])
    assert "lifecycle_stage" not in proposition["properties"]
    assert {"declaring_adr", "source_artifact", "source_contract"} <= set(proposition["required"])
    # Schema probes only, not candidate production or interpretation conformance.
    for value in ("", "Complete untruncated text " * 1000):
        assert Draft7Validator(regular["properties"]["summary"]).is_valid(value)
        assert Draft7Validator(
            source_shape("adr-logical.schema.json#")["properties"]["context"]
        ).is_valid(value)
    relationship = load_semantic_resource("normalized-model/2.5/schema/relationship-record.schema")
    for branch in relationship["oneOf"]:
        assert "name" not in branch["required"] and "summary" not in branch["required"]
    assert regular["allOf"] and relationship["oneOf"][0]["allOf"]


@pytest.mark.parametrize(
    ("family", "version", "fingerprint", "count"),
    [
        (
            "authoring-construction",
            "1.3",
            "5828fe0c3b1692240726152f57ca6de037a1e07f38bb8f9ecda223af105d1b49",
            94,
        ),
        (
            "architecture-interpretation",
            "1.3",
            "d4a60e843c3069cfd7eb869a4d924d3a70bf900079d3a2ad86ae28884c6ac167",
            52,
        ),
        (
            "normalized-model",
            "2.5",
            "bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7",
            7,
        ),
    ],
)
def test_historical_authorities_remain_exact_independent_of_successor_publication(
    family: str, version: str, fingerprint: str, count: int
) -> None:
    contract = get_semantic_contract(family, version)
    assert contract.semantic_contract_fingerprint == "scf:v1:sha256:" + fingerprint
    assert verify_semantic_contract(contract).success
    assert len(contract.resource_manifest) == count
    bundle = [
        {
            "canonicalResourceKey": e.canonical_resource_key,
            "content": load_semantic_resource(e.canonical_resource_key),
        }
        for e in contract.resource_manifest
    ]
    assert validate_semantic_resource_closure(contract, bundle).closure_valid
    # Successor discovery is deliberately irrelevant to historical integrity.
    # Neither publication nor acceptance establishes any executable capability
    # or Constructed result; those need independently qualified runtime evidence.
