"""Audit proposed recipe authority; never execute NM materialization."""

from __future__ import annotations

import copy
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from adr_kit.semantic_contract import (
    get_semantic_contract,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)
from adr_kit.validators.adr_validator import ADRValidator
from tests.test_required_output_authority_design import registry

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "adrs/logical/ADR-L-0039-forward-identity-representation-recipes.yaml"
CATALOG = "architecture-interpretation/1.4/required-output-derivations"
RECIPES = {
    "/alias_ref": {
        "operation": "literal_alias_join",
        "inputs": ["/alias_id", "/alias_name"],
        "separator": ":",
        "transformation": "none",
    },
    "/uri": {
        "operation": "literal_entity_uri",
        "inputs": ["qualified_context.architecture_namespace", "established_identity.id"],
        "prefix": "adr://",
        "separator": "/entities/",
        "namespace_encoding": "exact_json_string_no_uri_normalization_or_percent_encoding",
    },
    "/created_at": {
        "operation": "uuidv7_unix_milliseconds_to_rfc3339_utc",
        "inputs": ["established_identity.id"],
        "timestamp_bits": 48,
        "timestamp_unit": "unix_milliseconds",
        "output_format": "YYYY-MM-DDTHH:mm:ss.SSSZ",
        "fraction_digits": 3,
        "timezone": "UTC",
        "minimum_timestamp_ms": 0,
        "maximum_timestamp_ms": 253402300799999,
        "out_of_range": "Unavailable",
    },
}
CODES = {
    "/alias_ref": "alias_ref_recipe",
    "/uri": "uri_recipe",
    "/created_at": "created_at_encoding",
}


def document() -> dict[str, Any]:
    return yaml.safe_load(ADR.read_text(encoding="utf-8"))


def blocks() -> list[Any]:
    result = []
    for decision in document()["decisions"]:
        text = decision["rationale"]
        if "```yaml\n" in text:
            result.append(yaml.safe_load(text.split("```yaml\n", 1)[1].split("```", 1)[0]))
    return result


def impact_errors(rows: list[dict[str, Any]]) -> list[str]:
    """Compare the governance appendix to the exact historical catalog, not instances."""
    catalog = load_semantic_resource(CATALOG)
    types = {t["semantic_type"]: t for t in catalog["types"]}
    errors = []
    counts = Counter(row["semantic_type"] for row in rows)
    if set(counts) != set(types) or any(n != 1 for n in counts.values()):
        errors.append("catalog membership")
    for row in rows:
        if row["semantic_type"] not in types:
            continue
        source = types[row["semantic_type"]]
        if row["output_branch"] != source["output_branch"]:
            errors.append("branch")
        if row["source_schema"] != source["source_schema"]:
            errors.append("source qualification")
        expected = [
            {
                "destination": o["destination"],
                "blocked_code": o["blocked"]["code"],
                "destination_schema": o["destination_schema"],
            }
            for o in source["outputs"]
            if o["destination"] in CODES
        ]
        if row["affected_destinations"] != expected:
            errors.append("destination/blocker qualification")
        if row["root_permission"] != "not_granted_by_recipe":
            errors.append("synthetic root")
        prerequisites = row["instance_prerequisites"]
        if expected:
            for required in (
                "sealed_source_and_exact_source_schema",
                "established_canonical_uuidv7",
                "unique_unit_and_producer_applicability",
                "qualified_interpretation_provider_context",
            ):
                if required not in prerequisites:
                    errors.append("instance evidence")
            if row["semantic_type"] == "entity/system" and (
                "shared_identity_producer_competition_remains_BLOCKED" not in prerequisites
            ):
                errors.append("shared identity")
            if row["semantic_type"] == "entity/extension" and (
                "exact_CEC_selection_not_registry_invention" not in prerequisites
                or "custom_lifecycle_remains_BLOCKED" not in prerequisites
            ):
                errors.append("custom prerequisites")
            if row["semantic_type"] == "entity/normative_proposition" and (
                "lifecycle_prohibited" not in prerequisites
            ):
                errors.append("proposition lifecycle")
        elif prerequisites:
            errors.append("invented entity prerequisite")
    return errors


def recipe_errors(recipes: list[dict[str, Any]]) -> list[str]:
    expected = [
        {
            "destination": destination,
            **recipe,
            "output_type": "string",
            "fallback": False,
            "independent_semantic_owner": False,
        }
        for destination, recipe in RECIPES.items()
    ]
    return [] if recipes == expected else ["missing, competing or changed recipe"]


def test_governed_lifecycle_and_canonical_identity() -> None:
    adr = document()
    validation = ADRValidator(project_root=ROOT).validate_file(ADR, mode="complete")
    assert validation.valid, validation.errors
    assert adr["alias_id"] == "ADR-L-0039"
    assert [d["alias_id"] for d in adr["decisions"]] == [f"DEC-{n}" for n in range(9017, 9023)]
    assert [d["alias_id"] for d in adr["invariants"]] == [f"INV-{n:04}" for n in range(309, 315)]
    ids = [adr["id"]] + [x["id"] for k in ("decisions", "invariants") for x in adr[k]]
    assert len(set(ids)) == len(ids) == 13
    governance = adr.get("governance") or {}
    if adr["status"] == "proposed":
        assert not governance.get("approved_by")
        assert not governance.get("approved_date")
    elif adr["status"] == "accepted":
        assert isinstance(governance.get("approved_by"), str)
        assert governance["approved_by"].strip()
        assert governance.get("approved_date")


def test_complete_static_impact_is_not_instance_coverage() -> None:
    rows = blocks()[-1]
    assert impact_errors(rows) == []
    assert len(rows) == 27
    assert Counter(row["output_branch"] for row in rows) == {
        "regular": 17,
        "normative-proposition": 1,
        "canonical-relationship": 1,
        "compatibility-relationship": 6,
        "proposition-owned-value": 1,
        "owner-local-value": 1,
    }
    assert Counter(
        d["blocked_code"] for row in rows for d in row["affected_destinations"]
    ) == dict.fromkeys(CODES.values(), 18)
    for row in rows:
        if not row["affected_destinations"]:
            continue
        qualification = row["source_schema"]
        schema = load_semantic_resource(qualification["canonical_resource_key"])
        shape = schema
        pointer = qualification["schema_pointer"]
        for token in pointer.strip("/").split("/") if pointer else []:
            shape = shape[token.replace("~1", "/").replace("~0", "~")]
        assert {"id", "alias_id", "alias_name"} <= set(shape["required"])
        assert all(field in shape["properties"] for field in ("id", "alias_id", "alias_name"))
        for field in ("id", "alias_id", "alias_name"):
            node = shape["properties"][field]
            if "$ref" in node:
                node = registry().resolver(base_uri=schema["$id"]).lookup(node["$ref"]).contents
            assert node["type"] == "string"


@pytest.mark.parametrize("fault", range(11))
def test_impact_mutations_cannot_qualify(fault: int) -> None:
    rows = copy.deepcopy(blocks()[-1])
    if fault == 0:
        rows.pop()
    elif fault == 1:
        rows.append(copy.deepcopy(rows[0]))
    elif fault == 2:
        rows[0]["source_schema"]["schema_pointer"] = "/wrong"
    elif fault == 3:
        rows[0]["source_schema"]["content_digest"] = "sha256:" + "0" * 64
    elif fault == 4:
        rows[0]["affected_destinations"].pop()
    elif fault == 5:
        rows[0]["affected_destinations"][0]["blocked_code"] = "producer"
    elif fault == 6:
        rows[0]["affected_destinations"][0]["destination_schema"]["schema_pointer"] = "/oneOf/1"
    elif fault == 7:
        rows[-1]["output_branch"] = "regular"
    elif fault == 8:
        rows[0]["root_permission"] = "root"
    elif fault == 9:
        rows[0]["instance_prerequisites"] = []
    else:
        rows[-1]["affected_destinations"] = rows[0]["affected_destinations"]
    assert impact_errors(rows)


def test_recipe_declarations_are_closed_and_type_specific() -> None:
    assert recipe_errors(blocks()[:3]) == []
    # Independent arithmetic audit of the proposed RFC3339 representability bound.
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    end = datetime(9999, 12, 31, 23, 59, 59, 999000, tzinfo=timezone.utc)
    delta = end - epoch
    maximum = (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000
    assert maximum == RECIPES["/created_at"]["maximum_timestamp_ms"]
    assert maximum < (1 << 48) - 1


@pytest.mark.parametrize(
    ("index", "key", "value"),
    [
        (0, "fallback", True),
        (0, "transformation", "trim"),
        (0, "separator", "-"),
        (0, "inputs", ["/title", "/alias_name"]),
        (1, "inputs", ["source_ref", "established_identity.id"]),
        (1, "namespace_encoding", "URL_normalize"),
        (1, "independent_semantic_owner", True),
        (2, "inputs", ["/created_date"]),
        (2, "fraction_digits", 0),
        (2, "maximum_timestamp_ms", (1 << 48) - 1),
        (2, "out_of_range", "Rejected"),
    ],
)
def test_changed_recipe_authority_is_not_accepted(index: int, key: str, value: Any) -> None:
    recipes = copy.deepcopy(blocks()[:3])
    recipes[index][key] = value
    assert recipe_errors(recipes)
    assert recipe_errors(recipes + [copy.deepcopy(recipes[0])])


def test_inherited_lineage_and_remaining_gates_are_explicit() -> None:
    text = " ".join(" ".join(d["rationale"] for d in document()["decisions"]).split())
    for phrase in (
        "DEC-0093",
        "DEC-0098",
        "DEC-0099",
        "DEC-0107",
        "INV-0084",
        "INV-0087",
        "Classification B",
        "(C)",
        "AI 1.5",
        "ACC 1.5",
        "NM 2.5",
        "architecture-interpretation/1.3/detached-context",
        "scope_root",
        "No source pointer",
        "whole-ledger equality",
        "five authored-field",
        "No automatic acceptance or merge",
        "Unavailable",
        "Unresolved requires",
        "fingerprint_preimage",
        "source_envelope_recipe",
        "completeness_recipe",
        "custom_lifecycle",
        "declaring_context",
        "shared_identity",
        "relationship_branch",
        "relationship_envelope",
        "nonselected_output",
        "owner_local_context",
        "custom_qualification",
    ):
        assert phrase in text


@pytest.mark.parametrize(
    ("family", "version", "fingerprint", "count"),
    [
        (
            "architecture-interpretation",
            "1.4",
            "5c338d24961946d7f7d4350d5bfbbfb9e3882c56c8be09ba4d242169163acdd7",
            60,
        ),
        (
            "authoring-construction",
            "1.4",
            "19e267c5c77477a594414168bde9f733b1b9e547c06fc6836ad09392a248ea6d",
            108,
        ),
        (
            "normalized-model",
            "2.5",
            "bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7",
            7,
        ),
    ],
)
def test_exact_historical_authorities_remain_qualified(
    family: str, version: str, fingerprint: str, count: int
) -> None:
    definition = get_semantic_contract(family, version)
    assert definition.semantic_contract_fingerprint == "scf:v1:sha256:" + fingerprint
    assert verify_semantic_contract(definition).success
    resources = [
        {
            "canonicalResourceKey": member.canonical_resource_key,
            "content": load_semantic_resource(member.canonical_resource_key),
        }
        for member in definition.resource_manifest
    ]
    assert len(resources) == count
    assert validate_semantic_resource_closure(definition, resources).closure_valid
    if family == "architecture-interpretation":
        catalog = load_semantic_resource(CATALOG)
        assert Counter(o["status"] for t in catalog["types"] for o in t["outputs"]) == {
            "QUALIFIED": 186,
            "BLOCKED": 269,
        }
        assert len(catalog["blockers"]) == 14
