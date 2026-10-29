"""Current schema ownership, exact selection and independent migration proofs."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from adr_kit.semantic_contract import validate_semantic_resource_closure, verify_semantic_contract
from scripts import candidate_contract_assets as assets
from scripts import qualify_ai15_publication as ai

ROOT = Path(__file__).resolve().parents[1]


def raw_schemas() -> dict[str, Any]:
    return {n: copy.deepcopy(ai.read(ROOT, ai.PREFIX + n)) for n in ai.NAMES}


@pytest.mark.parametrize(
    "value",
    [
        {
            "canonical_resource_key": "authoring/1.7/schema/adr-logical.schema",
            "content_digest": "sha256:" + "0" * 64,
            "schema_pointer": "",
        },
        {
            "canonical_resource_key": "x" * 4096,
            "content_digest": "sha256:" + "a" * 64,
            "schema_pointer": "/æ—¥æœ¬èªž/~0~1",
        },
        {},
        {
            "canonical_resource_key": {},
            "content_digest": "sha256:" + "0" * 64,
            "schema_pointer": "",
        },
        {"canonical_resource_key": "x", "content_digest": "sha256:wrong", "schema_pointer": ""},
        {
            "canonical_resource_key": "x",
            "content_digest": "sha256:" + "0" * 64,
            "schema_pointer": 1,
        },
        {
            "canonical_resource_key": "x",
            "content_digest": "sha256:" + "0" * 64,
            "schema_pointer": "",
            "forged": True,
        },
    ],
)
def test_qualified_record_validation_is_preserved_at_the_new_selector(value: Any) -> None:
    original = ai.read(ROOT, ai.BASE + ai.CATALOG + ".schema")["properties"]["field_dispositions"]
    views, registry = ai.schema_registry(ROOT, raw_schemas())
    current = Draft202012Validator(
        {"$ref": views[ai.PREFIX + ai.CATALOG + ".schema"]["$id"] + "#/$defs/qualified_resource"},
        registry=registry,
    )
    assert current.is_valid(value) == Draft202012Validator(original).is_valid(value)


def test_all_type_branches_preserve_original_fragment_validation() -> None:
    original = ai.read(ROOT, ai.BASE + ai.CATALOG + ".schema")["properties"]["types"]["items"]
    current = ai.read(ROOT, ai.PREFIX + ai.CATALOG + ".schema")["$defs"]["coverage_output_type"]
    before, after = Draft202012Validator(original), Draft202012Validator(current)
    for row in ai.read(ROOT, ai.BASE + ai.CATALOG)["types"]:
        assert before.is_valid(row) and after.is_valid(row)
        invalid = {**row, "output_branch": "fabricated"}
        assert not before.is_valid(invalid) and not after.is_valid(invalid)


@pytest.mark.parametrize("version", ["1.3", "1.4", "1.6"])
def test_predecessor_or_unselected_schema_cannot_supply_the_local_fragment(version: str) -> None:
    raw = raw_schemas()
    raw[ai.CATALOG + ".schema"]["properties"]["field_dispositions"] = {
        "$ref": f"../{version}/required-output-derivations.schema.json#/properties/field_dispositions"
    }
    with pytest.raises(ai.PublicationError, match="unsealed_companion_reference"):
        ai.qualify_schemas(ROOT, raw)


def test_rehashed_weakened_local_schema_does_not_qualify(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {ai.PREFIX + n: v for n, v in raw_schemas().items()}
    key = ai.PREFIX + ai.CATALOG + ".schema"
    values[key]["$defs"]["qualified_resource"]["properties"]["content_digest"][
        "pattern"
    ] = "^sha256:.+$"
    original_read = ai.read
    monkeypatch.setattr(
        ai, "read", lambda root, k: values[k] if k in values else original_read(root, k)
    )
    current = assets.canonical_resource(ROOT, ai.PREFIX + "contract")
    manifest = [
        {
            **m,
            "contentDigest": assets.digest(ai.read(ROOT, m["canonicalResourceKey"])),
            "dependencies": [
                {"canonicalResourceKey": dep, "contentDigest": assets.digest(ai.read(ROOT, dep))}
                for dep in sorted(
                    assets.discovered_dependencies(
                        m["canonicalResourceKey"], ai.read(ROOT, m["canonicalResourceKey"])
                    )
                )
            ],
        }
        for m in current["resourceManifest"]
    ]
    forged = assets.definition(
        "architecture-interpretation", manifest, [ai.PREFIX + "conformance"], version="1.5"
    )
    assert verify_semantic_contract(forged).success
    assert validate_semantic_resource_closure(
        forged,
        [
            {
                "canonicalResourceKey": m["canonicalResourceKey"],
                "content": ai.read(ROOT, m["canonicalResourceKey"]),
            }
            for m in manifest
        ],
    ).closure_valid
    with pytest.raises(ai.PublicationError, match="changed_validation_fragment_qualified_resource"):
        ai.qualify(ROOT, candidate_definition=forged)


@pytest.fixture
def nm_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict[str, Any]]:
    if os.name == "nt" and not str(tmp_path).startswith("\\\\?\\"):
        tmp_path = Path("\\\\?\\" + str(tmp_path.resolve()))
    monkeypatch.setattr(
        ai, "historical_resource", lambda _, key: assets.historical_resource(ROOT, key)
    )
    original = assets.canonical_resource(ROOT, ai.NM)
    contents = {
        m["canonicalResourceKey"]: copy.deepcopy(
            assets.canonical_resource(ROOT, m["canonicalResourceKey"])
        )
        for m in original["resourceManifest"]
    }
    # Test-only annotation; no maintained NM source or schema meaning changes.
    contents["normalized-model/2.5/schema/normalized-entity.schema"][
        "description"
    ] = "Same-version qualified candidate revision."
    for key, value in contents.items():
        name = key.removeprefix("normalized-model/2.5/")
        path = tmp_path / (
            "schema/normalized-model/v2.5/" + name.removeprefix("schema/") + ".json"
            if name.startswith("schema/")
            else "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-conformance.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
    manifest = [
        {
            **m,
            "contentDigest": assets.digest(contents[m["canonicalResourceKey"]]),
            "dependencies": [
                {"canonicalResourceKey": dep, "contentDigest": assets.digest(contents[dep])}
                for dep in sorted(
                    assets.discovered_dependencies(
                        m["canonicalResourceKey"], contents[m["canonicalResourceKey"]]
                    )
                )
            ],
        }
        for m in original["resourceManifest"]
    ]
    revised = assets.definition(
        "normalized-model", manifest, original["frozenNormativeConformanceResources"], version="2.5"
    )
    assert revised["semanticContractFingerprint"] != original["semanticContractFingerprint"]
    definition_path = (
        tmp_path / "contracts/semantic-contract/v1.0/definitions/normalized-model-2.5.json"
    )
    definition_path.parent.mkdir(parents=True, exist_ok=True)
    definition_path.write_text(json.dumps(revised), encoding="utf-8")
    supplied = {**contents, ai.NM: revised}
    monkeypatch.setattr(ai, "read", lambda root, key: supplied[key])
    return tmp_path, supplied


def test_current_NM_selection_accepts_a_qualified_same_version_revision(nm_candidate) -> None:
    root, supplied = nm_candidate
    result = ai.qualify_current_nm25(root)
    assert result == supplied[ai.NM]
    assert ai.selected_nm_fingerprint(root) == result["semanticContractFingerprint"]


def test_rehashed_unselected_NM_definition_cannot_replace_maintained_authority(
    nm_candidate,
) -> None:
    root, supplied = nm_candidate
    changed = copy.deepcopy(supplied[ai.NM])
    next(
        m
        for m in changed["resourceManifest"]
        if m["canonicalResourceKey"].endswith("/schema/normalized-entity.schema")
    )["role"] = "normative-definition"
    supplied[ai.NM] = assets.definition(
        "normalized-model",
        changed["resourceManifest"],
        changed["frozenNormativeConformanceResources"],
        version="2.5",
    )
    assert verify_semantic_contract(supplied[ai.NM]).success
    with pytest.raises(ai.PublicationError, match="inconsistent_current_NM_definition"):
        ai.qualify_current_nm25(root)


def test_wrong_version_NM_resource_is_rejected(nm_candidate) -> None:
    root, supplied = nm_candidate
    key = "normalized-model/2.5/schema/normalized-entity.schema"
    supplied[key] = assets.canonical_resource(
        ROOT, "normalized-model/2.4/schema/normalized-entity.schema"
    )
    with pytest.raises(ai.PublicationError, match="inconsistent_current_NM_resource"):
        ai.qualify_current_nm25(root)


def test_stale_NM_mirror_cannot_replace_missing_canonical_schema(nm_candidate) -> None:
    root, supplied = nm_candidate
    path = root / "schema/normalized-model/v2.5/normalized-entity.schema.json"
    path.unlink()
    mirror = (
        root
        / "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-normalized-entity.schema.json"
    )
    mirror.write_text(
        json.dumps(supplied["normalized-model/2.5/schema/normalized-entity.schema"]),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing exact canonical resource"):
        ai.qualify_current_nm25(root)
