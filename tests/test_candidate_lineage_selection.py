"""Current graph selection and separately reproducible historical evidence."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from scripts import candidate_contract_assets as assets
from scripts import qualify_ai15_publication as ai
from scripts import qualify_acc15_publication as acc
from adr_kit.semantic_contract import verify_semantic_contract, validate_semantic_resource_closure

ROOT = Path(__file__).resolve().parents[1]


def test_current_closures_follow_edges_not_predecessor_manifests() -> None:
    for family, qualifier in (("architecture-interpretation", ai), ("authoring-construction", acc)):
        definition, values = assets.assemble(ROOT, family)
        roots = {k: v for k, v in values.items() if k.startswith(family + "/1.5/")}
        assert set(values) == assets.dependency_closure(ROOT, roots, assets.canonical_resource)
        assert qualifier.BASE + "contract" not in values
        assert qualifier.BASE + "conformance" not in values
        # The actual rule and structural fragments retain their real identities.
        assert "architecture-interpretation/1.3/lifecycle-ownership" in values
        assert "architecture-interpretation/1.4/required-output-derivations" in values
        assert verify_semantic_contract(definition).success
        assert validate_semantic_resource_closure(
            definition, [{"canonicalResourceKey": k, "content": v} for k, v in values.items()]
        ).closure_valid


def test_historical_manifests_are_evidence_not_transitive_imports() -> None:
    values = {
        "x/1.5/root": {"semanticDependencies": ["x/1.4/contract"]},
        "x/1.4/contract": {"resourceManifest": [{"canonicalResourceKey": "x/1.4/not-selected"}]},
    }
    assert assets.dependency_closure(
        ROOT, {"x/1.5/root": values["x/1.5/root"]}, lambda _, k: values[k]
    ) == set(values)


def test_history_is_exact_and_independent_of_current_nm(monkeypatch: pytest.MonkeyPatch) -> None:
    key = "normalized-model/2.5/schema/normalized-entity.schema"
    old = assets.historical_resource(ROOT, key)
    changed = copy.deepcopy(old)
    changed["description"] = "Another current revision"
    original = assets.canonical_resource
    monkeypatch.setattr(
        assets, "canonical_resource", lambda root, k: changed if k == key else original(root, k)
    )
    assert assets.historical_resource(ROOT, key) == old
    ai.exact_history(ROOT)
    for family, version in (
        ("architecture-interpretation", "1.4"),
        ("authoring-construction", "1.4"),
    ):
        d = assets.historical_resource(ROOT, f"{family}/{version}/contract")
        bundle = [
            {
                "canonicalResourceKey": m["canonicalResourceKey"],
                "content": assets.historical_resource(ROOT, m["canonicalResourceKey"]),
            }
            for m in d["resourceManifest"]
        ]
        assert validate_semantic_resource_closure(d, bundle).closure_valid
        bundle[0]["content"] = {"forged": True}
        assert not validate_semantic_resource_closure(d, bundle).closure_valid


@pytest.mark.parametrize("field", ["description", "title"])
def test_annotation_filter_cannot_erase_instance_property_constraints(field: str) -> None:
    before = {"properties": {field: {"type": "string"}}, "description": "annotation"}
    after = {"properties": {field: {"type": "integer"}}, "description": "new annotation"}
    assert ai.schema_constraints(before) != ai.schema_constraints(after)
    assert ai.schema_constraints(before) == ai.schema_constraints({**before, "description": "new"})


def revise_nm_cohort(
    monkeypatch: pytest.MonkeyPatch, *, unauthorized: bool = False
) -> dict[str, Any]:
    """A test-only atomic candidate revision; maintained NM bytes never change."""
    values: dict[str, Any] = {}
    definitions = {}
    for family in ("architecture-interpretation", "authoring-construction", "normalized-model"):
        version = "2.5" if family == "normalized-model" else "1.5"
        d = assets.canonical_resource(ROOT, f"{family}/{version}/contract")
        definitions[family] = copy.deepcopy(d)
        values[f"{family}/{version}/contract"] = copy.deepcopy(d)
        for m in d["resourceManifest"]:
            values[m["canonicalResourceKey"]] = copy.deepcopy(
                assets.canonical_resource(ROOT, m["canonicalResourceKey"])
            )
    key = "normalized-model/2.5/schema/normalized-entity.schema"
    values[key]["description"] = "Legitimate same-version annotation revision"
    if unauthorized:
        values[key]["oneOf"][0]["properties"]["lifecycle_stage"]["enum"].append("invented")

    def commit(family: str) -> dict[str, Any]:
        previous = definitions[family]
        manifest = [
            {
                **m,
                "contentDigest": assets.digest(values[m["canonicalResourceKey"]]),
                "dependencies": [
                    {"canonicalResourceKey": k, "contentDigest": assets.digest(values[k])}
                    for k in sorted(
                        assets.discovered_dependencies(
                            m["canonicalResourceKey"], values[m["canonicalResourceKey"]]
                        )
                    )
                ],
            }
            for m in previous["resourceManifest"]
        ]
        d = assets.definition(
            family,
            manifest,
            previous["frozenNormativeConformanceResources"],
            version=previous["semanticContractVersion"],
        )
        values[f"{family}/{previous['semanticContractVersion']}/contract"] = d
        return d

    old_nm = definitions["normalized-model"]["semanticContractFingerprint"]
    nm = commit("normalized-model")
    original_read = assets.canonical_resource

    def selected(root: Path, k: str) -> Any:
        return values[k] if k in values else original_read(root, k)

    def refresh_family(family: str, old_ai: str = "") -> None:
        prefix = family + "/1.5/"
        own = {k for k in values if k.startswith(prefix) and not k.endswith("/contract")}
        done: set[str] = set()
        hashes: dict[str, str] = {}

        def content_digest(k: str) -> str:
            if k not in hashes:
                hashes[k] = assets.digest(update(k))
            return hashes[k]

        def update(k: str) -> Any:
            if k not in own or k in done:
                return selected(ROOT, k)
            done.add(k)

            def visit(node: Any) -> Any:
                if isinstance(node, list):
                    return [visit(v) for v in node]
                if isinstance(node, str):
                    if node == old_nm:
                        return nm["semanticContractFingerprint"]
                    if old_ai and node == old_ai:
                        return values[ai.PREFIX + "contract"]["semanticContractFingerprint"]
                    return node
                if not isinstance(node, dict):
                    return node
                result = {a: visit(b) for a, b in node.items()}
                target = node.get("canonical_resource_key")
                if isinstance(target, str) and "content_digest" in node:
                    result["content_digest"] = content_digest(target)
                if (
                    isinstance(target, dict)
                    and isinstance(target.get("const"), str)
                    and isinstance(node.get("content_digest"), dict)
                    and "const" in node["content_digest"]
                ):
                    result["content_digest"] = {"const": content_digest(target["const"])}
                return result

            values[k] = visit(values[k])
            return values[k]

        for k in sorted(own):
            update(k)

    refresh_family("architecture-interpretation")
    new_ai = commit("architecture-interpretation")
    members = [
        {"canonical_resource_key": m["canonicalResourceKey"], "content_digest": m["contentDigest"]}
        for m in new_ai["resourceManifest"]
    ]
    values[acc.PREFIX + "schema"]["$defs"]["exact_ai15_closure"]["properties"]["resources"][
        "items"
    ] = {"enum": members}
    refresh_family(
        "authoring-construction",
        definitions["architecture-interpretation"]["semanticContractFingerprint"],
    )
    commit("authoring-construction")
    monkeypatch.setattr(ai, "read", selected)
    monkeypatch.setattr(acc, "read", selected)
    monkeypatch.setattr(ai, "canonical_resource", selected)
    monkeypatch.setattr(acc, "canonical_resource", selected)
    return values


def test_full_current_cohort_accepts_same_version_nm_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = assets.historical_resource(ROOT, ai.NM)
    values = revise_nm_cohort(monkeypatch)
    assert values[ai.NM]["semanticContractFingerprint"] != old["semanticContractFingerprint"]
    for module in (ai, acc):
        report = module.qualify(ROOT, candidate_definition=values[module.PREFIX + "contract"])
        assert report["complete_interpretation"] == "Unavailable"
    for key, content in values.items():
        if key.startswith(
            (
                "architecture-interpretation/1.3/",
                "architecture-interpretation/1.4/",
                "authoring-construction/1.3/",
            )
        ):
            assert content == assets.historical_resource(ROOT, key)
    assert assets.historical_resource(ROOT, ai.NM) == old


def test_rehashed_unauthorized_nm_semantics_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    values = revise_nm_cohort(monkeypatch, unauthorized=True)
    assert verify_semantic_contract(values[ai.NM]).success
    with pytest.raises(ai.PublicationError, match="unauthorized_current_NM_semantic_change"):
        ai.qualify(ROOT, candidate_definition=values[ai.PREFIX + "contract"])


@pytest.mark.parametrize("module", [ai, acc])
def test_rehashed_predecessor_manifest_import_is_not_current_authority(module: Any) -> None:
    current = assets.canonical_resource(ROOT, module.PREFIX + "contract")
    key = module.BASE + "contract"
    historical = assets.historical_resource(ROOT, key)
    manifest = [
        *current["resourceManifest"],
        {
            "canonicalResourceKey": key,
            "contentDigest": assets.digest(historical),
            "role": "normative-definition",
            "dependencies": [],
        },
    ]
    forged = assets.definition(
        current["semanticContractFamily"],
        manifest,
        current["frozenNormativeConformanceResources"],
        version="1.5",
    )
    assert verify_semantic_contract(forged).success
    with pytest.raises(ai.PublicationError, match="incomplete_extra_or_duplicate"):
        module.qualify(ROOT, candidate_definition=forged)


def test_historical_evidence_scope_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    key = ai.PREFIX + "rules"
    changed = copy.deepcopy(ai.read(ROOT, key))
    changed["inherits"]["caller_verified"] = True
    original = ai.read
    monkeypatch.setattr(ai, "read", lambda root, k: changed if k == key else original(root, k))
    with pytest.raises(ai.PublicationError, match="unapproved_inherited_semantic_delta"):
        ai.qualify(ROOT, published=False)


def test_current_rules_carry_complete_inherited_policy_projections() -> None:
    rules = ai.read(ROOT, ai.PREFIX + "rules")
    original = assets.historical_resource(ROOT, ai.BASE + "rules")
    for name in ("verified_representation_duplication", "whole_ledger", "v0_13_objective"):
        assert rules[name] == original[name]
    assert rules["required_output_policy"] == {
        **original["required_output_coverage"],
        "catalog": ai.PREFIX + ai.CATALOG,
        "schema": ai.PREFIX + ai.CATALOG + ".schema",
    }
    for name, source in rules["inherits"]["policy_sources"].items():
        assert source == {
            "canonical_resource_key": ai.BASE + "rules",
            "content_digest": assets.digest(original),
            "schema_pointer": "/" + name,
        }


def test_validly_rehashed_weakened_policy_projection_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    key = ai.PREFIX + "rules"
    changed = copy.deepcopy(ai.read(ROOT, key))
    changed["required_output_policy"]["complete_entity_schema_validation_required"] = False
    original_read = ai.read

    def selected(root: Path, k: str) -> Any:
        return changed if k == key else original_read(root, k)

    current = assets.canonical_resource(ROOT, ai.PREFIX + "contract")
    manifest = [
        {
            **m,
            "contentDigest": assets.digest(selected(ROOT, m["canonicalResourceKey"])),
            "dependencies": [
                {"canonicalResourceKey": dep, "contentDigest": assets.digest(selected(ROOT, dep))}
                for dep in sorted(
                    assets.discovered_dependencies(
                        m["canonicalResourceKey"], selected(ROOT, m["canonicalResourceKey"])
                    )
                )
            ],
        }
        for m in current["resourceManifest"]
    ]
    forged = assets.definition(
        "architecture-interpretation",
        manifest,
        current["frozenNormativeConformanceResources"],
        version="1.5",
    )
    assert verify_semantic_contract(forged).success
    assert validate_semantic_resource_closure(
        forged,
        [
            {
                "canonicalResourceKey": m["canonicalResourceKey"],
                "content": selected(ROOT, m["canonicalResourceKey"]),
            }
            for m in manifest
        ],
    ).closure_valid
    monkeypatch.setattr(ai, "read", selected)
    with pytest.raises(ai.PublicationError, match="weakened_inherited_output_policy"):
        ai.qualify(ROOT, candidate_definition=forged)
