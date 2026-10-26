"""Governance specification tests, never operational release/acceptance fixtures."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from adr_kit.semantic_contract import (
    calculate_semantic_contract_fingerprint,
    canonicalize_semantic_json,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)
from scripts import check_semantic_contract_lifecycle_design as design

ROOT = Path(__file__).resolve().parents[1]


def documents():
    return [design.read(p) for p in sorted((ROOT / "adrs/logical").glob("*.yaml"))]


def proposed():
    return design.read(ROOT / design.ADR_PATH)


def mapping():
    return design.read(ROOT / design.MAP_PATH)


def test_repository_design_is_bound_and_authenticates_before_activation():
    document = proposed()
    # Real canonical acceptance must actually verify, not merely demonstrate that
    # an invalid accepted state would raise an error. No synthetic proof bypass.
    canonical_result = design.qualify_repository()
    if document["status"] == "proposed":
        result = canonical_result
        assert result["activation"] == "inactive_without_independent_human_evidence"
        assert result["effective_replacements"] == []
        assert "governance" not in document
    else:
        assert canonical_result["activation"] == "verified_exact_mapped_scope_only"
        assert canonical_result["acceptance"]["reviewed_revision"]
    result = design.qualify_precedence(document, mapping(), documents())
    assert result["mapped_clauses"] == 29
    assert result["mapped_members"] == 17
    residual = "\n".join(x["unmapped_text"] for x in result["unmapped_obligations"])
    assert "Byte equality, digest equality" in residual
    assert any(x["alias"] == "DEC-0271" for x in result["unmapped_obligations"])


@pytest.mark.parametrize(
    "mutation",
    [
        "anchor",
        "digest",
        "uuid",
        "adr",
        "alias",
        "field",
        "replacement",
        "requirement",
        "scope",
        "family",
        "topic",
        "unknown",
        "duplicate",
        "overlap",
        "cycle",
    ],
)
def test_exact_precedence_rejects_adversarial_mutations(mutation):
    value = mapping()
    row = value["rules"][0]
    if mutation == "anchor":
        row["original"]["anchor"] += "changed"
    elif mutation == "digest":
        row["original"]["anchor_digest"] = "sha256:" + "0" * 64
    elif mutation == "uuid":
        row["original"]["member_id"] = proposed()["id"]
    elif mutation == "adr":
        row["original"]["adr_id"] = proposed()["id"]
    elif mutation == "alias":
        row["original"]["member_alias"] = "DEC-0271"
    elif mutation == "field":
        row["original"]["field"] = "statement"
    elif mutation == "replacement":
        row["replacement"]["member_id"] = row["original"]["member_id"]
    elif mutation == "requirement":
        row["replacement"]["requirement"] = "DEC-9026"
    elif mutation == "scope":
        row["applicability"]["authority_scope"][0]["versions"] = ["1.0"]
    elif mutation == "family":
        row["applicability"]["authority_scope"][0]["family"] = "custom-entity"
    elif mutation == "topic":
        row["applicability"]["topic"] = "semantic_equality"
    elif mutation == "unknown":
        row["applicability"]["automatic_override"] = True
    elif mutation == "duplicate":
        value["rules"].append(copy.deepcopy(row))
    elif mutation == "overlap":
        extra = copy.deepcopy(row)
        extra["id"] = "LC40-99"
        value["rules"].append(extra)
    elif mutation == "cycle":
        row["original"]["member_id"] = proposed()["decisions"][0]["id"]
    with pytest.raises(design.DesignError):
        design.qualify_precedence(proposed(), value, documents())


def test_ambiguous_structural_anchor_and_canonical_identity_fail():
    ds = documents()
    value = mapping()
    old = value["rules"][0]["original"]
    owner = next(d for d in ds if d["id"] == old["adr_id"])
    member = next(m for m in owner["decisions"] if m["id"] == old["member_id"])
    member[old["field"]] += "\n" + old["anchor"]
    with pytest.raises(design.DesignError, match="ambiguous"):
        design.qualify_precedence(proposed(), value, ds)
    ds = documents()
    ds.append(copy.deepcopy(ds[0]))
    with pytest.raises(design.DesignError, match="ambiguous canonical"):
        design.qualify_precedence(proposed(), value, ds)


def test_synthetic_accepted_fixture_cannot_activate_real_governance():
    synthetic = proposed()
    synthetic["status"] = "accepted"
    synthetic["governance"] = {
        "approved_by": "fixture-human",
        "approved_date": "2026-10-26T00:00:00Z",
    }
    result = design.qualify_precedence(synthetic, mapping(), documents())
    assert result["effective_replacements"] == []
    assert result["activation"] == "inactive_without_independent_human_evidence"


def review_fixture(monkeypatch, tmp_path):
    """Mock transport only; never writes canonical accepted content or approval."""
    revision = "a" * 40
    url = f"https://github.com/{design.REPOSITORY}/pull/999#pullrequestreview-123"
    before = proposed()
    before.pop("governance", None)
    before["status"] = "proposed"
    accepted = copy.deepcopy(before)
    accepted["status"] = "accepted"
    accepted["governance"] = {
        "approved_by": "fixture-human",
        "approved_date": "2026-10-26T00:00:00Z",
    }
    policy = {"integrations": {"scm": {"required_approvers": ["@fixture-human"]}}}
    review = {
        "html_url": url,
        "state": "APPROVED",
        "commit_id": revision,
        "user": {"login": "fixture-human", "type": "User"},
        "body": "Approve ADR-L-0040 lifecycle governance and activation.",
        "submitted_at": "2026-10-26T00:00:00Z",
    }
    request = {
        "user": {"login": "different-author"},
        "base": {"repo": {"full_name": design.REPOSITORY}, "ref": "develop", "sha": "b" * 40},
    }

    def api(args, **kwargs):
        return json.dumps(review if "/reviews/" in args[-1] else request).encode()

    def git(root, rev, path):
        if path == design.ADR_PATH:
            return yaml.safe_dump(before).encode()
        if path == "PROJECT.yaml":
            return yaml.safe_dump(policy).encode()
        return (ROOT / path).read_bytes()

    original_read = design.read

    def read(path):
        if path == ROOT / design.ADR_PATH:
            return accepted
        if path == ROOT / "PROJECT.yaml":
            return policy
        return original_read(path)

    monkeypatch.setattr(design.subprocess, "check_output", api)
    monkeypatch.setattr(design, "_git", git)
    monkeypatch.setattr(design, "read", read)
    return revision, url, review, request, accepted, before


def test_live_review_transport_contract_qualifies_exact_review(monkeypatch, tmp_path):
    revision, url, *_ = review_fixture(monkeypatch, tmp_path)
    proof = design.verify_live_acceptance(ROOT, revision, url)
    assert proof["actor"] == "fixture-human"
    assert proof["reviewed_revision"] == revision


@pytest.mark.parametrize(
    "mutation",
    [
        "dismissed",
        "commit",
        "bot",
        "unauthorized",
        "self",
        "scope",
        "body",
        "metadata",
        "semantic",
        "date",
    ],
)
def test_forged_or_stale_review_never_activates(monkeypatch, tmp_path, mutation):
    revision, url, review, request, accepted, _ = review_fixture(monkeypatch, tmp_path)
    if mutation == "dismissed":
        review["state"] = "DISMISSED"
    elif mutation == "commit":
        review["commit_id"] = "b" * 40
    elif mutation == "bot":
        review["user"]["type"] = "Bot"
    elif mutation == "unauthorized":
        review["user"]["login"] = "intruder"
    elif mutation == "self":
        request["user"]["login"] = "fixture-human"
    elif mutation == "scope":
        request["base"]["ref"] = "main"
    elif mutation == "body":
        review["body"] = "LGTM"
    elif mutation == "metadata":
        accepted["governance"]["approved_by"] = "assistant"
    elif mutation == "semantic":
        accepted["decisions"][0]["rationale"] += "Altered semantics."
    elif mutation == "date":
        accepted["governance"]["approved_date"] = "2025-01-01T00:00:00Z"
    with pytest.raises(design.DesignError):
        design.verify_live_acceptance(ROOT, revision, url)


def promotion_fixture():
    payloads = {"fixture.whl": b"fixture payload, not a real release"}
    artifacts = [
        {"name": k, "size": len(v), "digest": design.digest(v)} for k, v in payloads.items()
    ]
    authorities = []
    for family, scf in [
        ("architecture-interpretation", "scf:v1:sha256:" + "1" * 64),
        ("custom-entity", None),
    ]:
        authorities.append(
            {
                "family": family,
                "version": "1.0",
                "scf": scf,
                "resources": [{"key": family + "/1.0/rules", "digest": "sha256:" + "2" * 64}],
                "placements": [
                    {
                        "artifact": "fixture.whl",
                        "locator": "semantic-core.wasm:qualified-resource",
                        "digest": "sha256:" + "3" * 64,
                        "encoding": "embedded-wasm",
                    }
                ],
                "disposition": "candidate" if scf else "released",
            }
        )
    inventory = {
        "schema_version": "1.0",
        "kind": "packaged-semantic-authority-inventory",
        "source_commit": "a" * 40,
        "artifacts": artifacts,
        "authorities": authorities,
    }
    ib = design.canonical_bytes(inventory)
    manifest = design.canonical_bytes(
        {"source_commit": "a" * 40, "artifacts": artifacts, "inventory_digest": design.digest(ib)}
    )
    bundle = b"finalized fixture bundle"  # contract test; operational archive discovery is deferred
    attestation = {
        "schema_version": "1.0",
        "kind": "semantic-authority-promotion-attestation",
        "source_commit": "a" * 40,
        "qualification": {
            "repository": design.REPOSITORY,
            "source_commit": "a" * 40,
            "ref": "refs/heads/main",
            "event": "push",
            "run_id": 1,
            "workflow_path": ".github/workflows/release-certification.yml",
            "conclusion": "success",
        },
        "retained_bundle": {
            "artifact_id": "fixture:1",
            "digest": design.digest(bundle),
            "manifest_digest": design.digest(manifest),
            "inventory_digest": design.digest(ib),
        },
        "artifacts": copy.deepcopy(artifacts),
        "approved_authorities": copy.deepcopy(authorities),
        "human_approval": {
            "provider": "protected-human-environment",
            "evidence_url": f"https://github.com/{design.REPOSITORY}/actions/runs/1",
            "actor": "fixture-human",
            "reviewed_source_commit": "a" * 40,
        },
        "publication_mode": "promote-retained-payloads-only",
    }
    return attestation, inventory, payloads, bundle, manifest, ib


def test_external_attestation_contract_cohort_without_claiming_publisher_gate():
    args = promotion_fixture()
    result = design.qualify_attestation_contract(*args)
    assert result == {
        "specification_qualified": True,
        "human_approval": "not_verified",
        "publisher_enforcement": "not_implemented",
        "promotion_authorized": False,
    }
    assert args[1]["authorities"][1]["scf"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "extra",
        "different",
        "duplicate",
        "payload",
        "bundle",
        "manifest",
        "inventory",
        "source",
        "branch",
        "event",
        "workflow",
        "conclusion",
        "approval",
        "selfhash",
        "selflocator",
        "unapproved",
        "noncanonical",
    ],
)
def test_attestation_mismatch_requires_new_bundle(mutation):
    a, i, p, b, m, ib = promotion_fixture()
    if mutation == "missing":
        a["approved_authorities"].pop()
    elif mutation == "extra":
        a["approved_authorities"].append(copy.deepcopy(a["approved_authorities"][0]))
    elif mutation == "different":
        a["approved_authorities"][0]["scf"] = "scf:v1:sha256:" + "9" * 64
    elif mutation == "duplicate":
        i["authorities"].append(copy.deepcopy(i["authorities"][0]))
    elif mutation == "payload":
        p["fixture.whl"] += b"changed"
    elif mutation == "bundle":
        b += b"stripped authority"
    elif mutation == "manifest":
        m += b" "
    elif mutation == "inventory":
        ib += b" "
    elif mutation == "source":
        a["qualification"]["source_commit"] = "b" * 40
    elif mutation == "branch":
        a["qualification"]["ref"] = "refs/heads/develop"
    elif mutation == "event":
        a["qualification"]["event"] = "workflow_dispatch"
    elif mutation == "workflow":
        a["qualification"]["workflow_path"] = ".github/workflows/pr-feedback.yml"
    elif mutation == "conclusion":
        a["qualification"]["conclusion"] = "skipped"
    elif mutation == "approval":
        a["human_approval"]["reviewed_source_commit"] = "b" * 40
    elif mutation == "selfhash":
        a["own_digest"] = "sha256:" + "0" * 64
    elif mutation == "selflocator":
        i["authorities"][0]["placements"][0]["locator"] = "$attestation"
    elif mutation == "unapproved":
        a["approved_authorities"][0]["disposition"] = "released"
    elif mutation == "noncanonical":
        ib = json.dumps(i, indent=2).encode()
        a["retained_bundle"]["inventory_digest"] = design.digest(ib)
    with pytest.raises(design.DesignError):
        design.qualify_attestation_contract(a, i, p, b, m, ib)


def test_manifest_cannot_include_enclosing_bundle_or_future_attestation():
    a, i, p, b, m, ib = promotion_fixture()
    changed = json.loads(m)
    changed["bundle_digest"] = design.digest(b)
    m = design.canonical_bytes(changed)
    a["retained_bundle"]["manifest_digest"] = design.digest(m)
    with pytest.raises(design.DesignError, match="cycle"):
        design.qualify_attestation_contract(a, i, p, b, m, ib)


def snapshot(revision=1):
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "string",
        "description": f"candidate revision {revision}",
    }
    key = "architecture-interpretation/1.5/development-test.schema"
    canonical = canonicalize_semantic_json(schema)
    assert canonical.success
    content_digest = design.digest(canonical.canonical_preimage_json.encode())
    conformance = {"cases": [], "semanticDependencies": [key]}
    cd = design.digest(design.canonical_bytes(conformance))
    ck = "architecture-interpretation/1.5/development-test-conformance"
    definition = {
        "semanticContractFamily": "architecture-interpretation",
        "semanticContractVersion": "1.5",
        "fingerprintScheme": "scf:v1:sha256",
        "resourceManifest": [
            {
                "canonicalResourceKey": key,
                "contentDigest": content_digest,
                "role": "source-contract-schema",
                "dependencies": [],
            },
            {
                "canonicalResourceKey": ck,
                "contentDigest": cd,
                "role": "interpretation-conformance",
                "dependencies": [{"canonicalResourceKey": key, "contentDigest": content_digest}],
            },
        ],
        "frozenNormativeConformanceResources": [ck],
    }
    calculated = calculate_semantic_contract_fingerprint(definition)
    assert calculated.success
    definition["semanticContractFingerprint"] = calculated.semantic_contract_fingerprint
    resources = [
        {"canonicalResourceKey": key, "content": schema},
        {"canonicalResourceKey": ck, "content": conformance},
    ]
    assert validate_semantic_resource_closure(definition, resources).success
    return definition, resources


def test_same_version_revision_new_scf_exact_closure_and_promoted_freeze():
    old, resources = snapshot(1)
    new, changed = snapshot(2)
    assert old["semanticContractVersion"] == new["semanticContractVersion"] == "1.5"
    assert old["semanticContractFingerprint"] != new["semanticContractFingerprint"]
    assert not validate_semantic_resource_closure(new, resources).success
    assert not validate_semantic_resource_closure(old, changed).success
    design.qualify_transition_spec(old, new, None)
    with pytest.raises(design.DesignError, match="promoted same-version"):
        design.qualify_transition_spec(old, new, copy.deepcopy(old))
    forged = copy.deepcopy(new)
    forged["candidate"] = True
    with pytest.raises(design.DesignError):
        design.qualify_transition_spec(old, forged, old)


def test_candidate_dependency_edges_require_new_qualified_digest():
    old, resources = snapshot(1)
    new, changed = snapshot(2)
    stale = copy.deepcopy(new)
    stale["resourceManifest"][1]["dependencies"] = copy.deepcopy(
        old["resourceManifest"][1]["dependencies"]
    )
    stale.pop("semanticContractFingerprint")
    calc = calculate_semantic_contract_fingerprint(stale)
    if calc.success:
        stale["semanticContractFingerprint"] = calc.semantic_contract_fingerprint
        assert not validate_semantic_resource_closure(stale, changed).success
    else:
        assert any("dependency" in d.code for d in calc.diagnostics)


def test_old_candidate_content_reproduces_from_recorded_git_commit(tmp_path):
    # Temporary history only: no permanent baseline comparison or repository edit.
    repo = tmp_path / "history"
    repo.mkdir()

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=repo)

    git("init", "--quiet")
    git("config", "user.name", "Lifecycle fixture")
    git("config", "user.email", "fixture@example.invalid")
    old, resources = snapshot(1)
    path = repo / "candidate.json"
    path.write_bytes(design.canonical_bytes({"definition": old, "resources": resources}))
    git("add", "candidate.json")
    git("commit", "--quiet", "-m", "candidate revision 1")
    commit = git("rev-parse", "HEAD").decode().strip()
    new, changed = snapshot(2)
    path.write_bytes(design.canonical_bytes({"definition": new, "resources": changed}))
    recovered = json.loads(git("show", f"{commit}:candidate.json"))
    assert recovered["definition"] == old
    assert verify_semantic_contract(recovered["definition"]).success
    assert validate_semantic_resource_closure(
        recovered["definition"], recovered["resources"]
    ).success


def test_released_authorities_and_closures_remain_exact():
    c = design.read(ROOT / design.CLASS_PATH)
    result = design.qualify_released_evidence(c)
    assert result["released_contracts"] == 6
    assert result["released_files"] == 70
    for row in c["released_contracts"]:
        d = design.read(ROOT / row["definition_path"])
        assert verify_semantic_contract(d).success
        resources = [
            {
                "canonicalResourceKey": e["canonicalResourceKey"],
                "content": load_semantic_resource(e["canonicalResourceKey"]),
            }
            for e in d["resourceManifest"]
        ]
        assert validate_semantic_resource_closure(d, resources).success
    assert all(x["classification"] != "RELEASED" for x in c["development_lineage"])


def test_historical_release_mutations_fail(tmp_path):
    c = design.read(ROOT / design.CLASS_PATH)
    row = c["released_contracts"][0]
    destination = tmp_path / row["definition_path"]
    destination.parent.mkdir(parents=True)
    destination.write_bytes((ROOT / row["definition_path"]).read_bytes() + b" ")
    with pytest.raises(design.DesignError, match="released definition mutation"):
        design.qualify_released_evidence(c, tmp_path)


def test_valid_content_hash_does_not_authorize_semantic_policy_change():
    old, _ = snapshot()
    new, resources = snapshot()
    # Cryptographically consistent schema change is still not approval of a
    # lifecycle/semantic choice: exact reviewed governance is independently bound.
    ds = documents()
    m = mapping()
    assert verify_semantic_contract(new).success
    assert validate_semantic_resource_closure(new, resources).success
    m["rules"][0]["original"]["anchor"] = "Unreviewed replacement"
    m["rules"][0]["original"]["anchor_digest"] = design.digest(b"Unreviewed replacement")
    with pytest.raises(design.DesignError):
        design.qualify_precedence(proposed(), m, ds)


def test_fixture_approval_is_not_an_activation_cli_input():
    result = subprocess.run(
        [
            __import__("sys").executable,
            str(ROOT / "scripts/check_semantic_contract_lifecycle_design.py"),
            "--allow-fixtures",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr


def test_recomputed_companion_hash_does_not_replace_exact_human_review(monkeypatch, tmp_path):
    revision, url, _, _, _, _ = review_fixture(monkeypatch, tmp_path)
    original = (ROOT / design.MAP_PATH).read_bytes()
    real_read_bytes = Path.read_bytes
    original_git = design._git

    def changed_bytes(path):
        if path == ROOT / design.MAP_PATH:
            return original + b"# unreviewed even with a newly computed digest\n"
        return real_read_bytes(path)

    def reviewed_git(root, rev, path):
        if path == design.MAP_PATH:
            return original
        return original_git(root, rev, path)

    monkeypatch.setattr(Path, "read_bytes", changed_bytes)
    monkeypatch.setattr(design, "_git", reviewed_git)
    with pytest.raises(design.DesignError, match="reviewed policy changed"):
        design.verify_live_acceptance(ROOT, revision, url)


def test_history_snapshots_are_git_evidence_not_current_version_byte_pins():
    classification = design.read(ROOT / design.CLASS_PATH)
    assert design.qualify_history_evidence(classification) == 9
    bad = copy.deepcopy(classification)
    bad["development_lineage"][0]["definition_digest"] = "sha256:" + "0" * 64
    with pytest.raises(design.DesignError, match="historical Git content"):
        design.qualify_history_evidence(bad)


def test_only_explicit_scope_matches_and_released_context_is_not_replaced():
    value = mapping()
    row = value["rules"][0]
    args = (value, row["original"]["member_id"])
    assert row["id"] in design.matching_design_clauses(
        *args, "architecture-interpretation", "1.5", "snapshot_identity"
    )
    assert (
        design.matching_design_clauses(
            *args, "architecture-interpretation", "1.0", "snapshot_identity"
        )
        == []
    )
    assert (
        design.matching_design_clauses(
            *args, "architecture-interpretation", "1.5", "candidate_selection"
        )
        == []
    )
    assert (
        design.matching_design_clauses(
            value, proposed()["id"], "architecture-interpretation", "1.5", "snapshot_identity"
        )
        == []
    )
    with pytest.raises(design.DesignError):
        design.matching_design_clauses(
            *args, "architecture-interpretation", "1.5", "natural-language-override"
        )


def test_canonical_accepted_state_requires_reference_and_live_proof(monkeypatch):
    before = proposed()
    synthetic = copy.deepcopy(before)
    synthetic["status"] = "accepted"
    synthetic["governance"] = {
        "approved_by": "fixture-human",
        "approved_date": "2026-10-26T00:00:00Z",
    }
    original_read = design.read

    def read(path):
        return synthetic if path == ROOT / design.ADR_PATH else original_read(path)

    def missing(*args):
        raise design.DesignError("independent acceptance reference required")

    monkeypatch.setattr(design, "read", read)
    monkeypatch.setattr(design, "acceptance_reference", missing)
    with pytest.raises(design.DesignError, match="independent acceptance reference"):
        design.qualify_repository()


@pytest.mark.parametrize("mutation", ["missing", "self_verified", "wrong_adr", "duplicate_member"])
def test_acceptance_reference_is_not_self_certified(tmp_path, mutation):
    path = tmp_path / design.ACCEPTANCE_PATH
    reference = {
        "schema_version": "1.0",
        "kind": "canonical-governance-acceptance-reference",
        "governing_adr_id": proposed()["id"],
        "reviewed_revision": "a" * 40,
        "approval_review_url": f"https://github.com/{design.REPOSITORY}/pull/999#pullrequestreview-123",
    }
    if mutation != "missing":
        path.parent.mkdir(parents=True)
        if mutation == "self_verified":
            reference["verified"] = True
        if mutation == "wrong_adr":
            reference["governing_adr_id"] = proposed()["decisions"][0]["id"]
        content = json.dumps(reference)
        if mutation == "duplicate_member":
            content = content[:-1] + ', "reviewed_revision": "' + "b" * 40 + '"}'
        path.write_bytes(content.encode())
    with pytest.raises(design.DesignError):
        design.acceptance_reference(tmp_path, proposed()["id"])


def owner_comment_fixture(monkeypatch, tmp_path):
    """Synthetic transport responses only; no real comment or acceptance is written."""
    revision, _, _, request, accepted, before = review_fixture(monkeypatch, tmp_path)
    request["user"]["login"] = "fixture-human"  # owner/PR author can authorize architecture
    request["number"] = 187
    request["html_url"] = f"https://github.com/{design.REPOSITORY}/pull/187"
    comment_id = 6406500216  # exercise GitHub's 64-bit fullDatabaseId, not databaseId
    url = request["html_url"] + f"#issuecomment-{comment_id}"
    body = (
        f"I approve ADR-L-0040 lifecycle governance and activation at reviewed commit {revision}."
    )
    comment = {
        "id": comment_id,
        "author_login": "fixture-human",
        "created_at": "2026-10-26T00:00:00Z",
        "source_url": url,
        "body_digest": design.digest(body.encode()),
    }
    record = {
        "id": comment_id,
        "node_id": "IC_fixture",
        "html_url": url,
        "url": f"https://api.github.com/repos/{design.REPOSITORY}/issues/comments/{comment_id}",
        "issue_url": f"https://api.github.com/repos/{design.REPOSITORY}/issues/187",
        "user": {"login": "fixture-human", "type": "User"},
        "performed_via_github_app": None,
        "body": body,
        "created_at": comment["created_at"],
        "updated_at": comment["created_at"],
    }
    node = {
        "__typename": "IssueComment",
        "id": "IC_fixture",
        "fullDatabaseId": str(comment_id),
        "url": url,
        "createdAt": comment["created_at"],
        "updatedAt": comment["created_at"],
        "lastEditedAt": None,
        "editor": None,
        "isMinimized": False,
        "body": body,
        "author": {"login": "fixture-human", "__typename": "User"},
    }
    calls = []
    commits = [[{"sha": revision}]]

    def api(args, **kwargs):
        assert args[:4] == ["gh", "api", "--hostname", "github.com"]
        calls.append(list(args))
        if "graphql" in args:
            assert any(a.startswith("query=query(") and "lastEditedAt" in a for a in args)
            return json.dumps({"data": {"node": node}}).encode()
        if "/commits?" in args[-1]:
            return json.dumps(commits).encode()
        if "/issues/comments/" in args[-1]:
            return json.dumps(record).encode()
        return json.dumps(request).encode()

    monkeypatch.setattr(design.subprocess, "check_output", api)
    return {
        "revision": revision,
        "comment": comment,
        "record": record,
        "node": node,
        "request": request,
        "accepted": accepted,
        "before": before,
        "calls": calls,
        "commits": commits,
    }


def test_authenticated_owner_comment_is_architectural_not_github_review_approval(
    monkeypatch, tmp_path
):
    fixture = owner_comment_fixture(monkeypatch, tmp_path)
    proof = design.verify_live_owner_comment(ROOT, fixture["revision"], fixture["comment"])
    assert proof["actor"] == fixture["request"]["user"]["login"]
    assert proof["evidence_kind"] == "authorized_pr_comment"
    assert proof["github_approved_review"] is False
    assert proof["comment_id"] == fixture["record"]["id"]
    assert proof["approved_at"] == fixture["record"]["created_at"]
    assert proof["source_url"] == fixture["record"]["html_url"]
    assert len(fixture["calls"]) == 4
    # Every qualification retrieves actual provider evidence again, never a cached flag.
    assert design.verify_live_owner_comment(ROOT, fixture["revision"], fixture["comment"]) == proof
    assert len(fixture["calls"]) == 8
    with pytest.raises(design.DesignError, match="exact GitHub review URL"):
        design.verify_live_acceptance(ROOT, fixture["revision"], fixture["comment"]["source_url"])


@pytest.mark.parametrize(
    "mutation",
    [
        "bot",
        "app",
        "unauthorized",
        "wrong_author",
        "wrong_commit",
        "short_commit",
        "nonhex_commit",
        "wrong_repository",
        "wrong_pr",
        "absent_pr_commit",
        "wrong_api_origin",
        "wrong_comment_id",
        "wrong_html_url",
        "edited_rest",
        "edited_same_second",
        "missing_edit_proof",
        "wrong_graphql_type",
        "wrong_graphql_id",
        "wrong_graphql_body",
        "wrong_graphql_author",
        "wrong_graphql_time",
        "minimized",
        "wrong_digest",
        "retimed_reference",
        "proxy_statement",
        "wrong_scope",
        "semantic_change",
        "metadata",
        "date",
    ],
)
def test_owner_comment_forgery_edits_and_stale_content_fail(monkeypatch, tmp_path, mutation):
    f = owner_comment_fixture(monkeypatch, tmp_path)
    revision = f["revision"]
    c, r, n = f["comment"], f["record"], f["node"]
    if mutation == "bot":
        r["user"]["type"] = "Bot"
    elif mutation == "app":
        r["performed_via_github_app"] = {"slug": "automated-agent"}
    elif mutation == "unauthorized":
        r["user"]["login"] = c["author_login"] = "intruder"
        n["author"]["login"] = "intruder"
    elif mutation == "wrong_author":
        c["author_login"] = "different-owner"
    elif mutation == "wrong_commit":
        revision = "b" * 40
    elif mutation == "short_commit":
        revision = "a" * 39
    elif mutation == "nonhex_commit":
        revision = "x" * 40
    elif mutation == "wrong_repository":
        c["source_url"] = c["source_url"].replace("adr-architecture-kit", "other-repo")
    elif mutation == "wrong_pr":
        r["issue_url"] = r["issue_url"].replace("/187", "/188")
    elif mutation == "absent_pr_commit":
        f["commits"][0][0]["sha"] = "b" * 40
    elif mutation == "wrong_api_origin":
        r["url"] = "https://api.github.com/repos/other/repo/issues/comments/1"
    elif mutation == "wrong_comment_id":
        r["id"] += 1
    elif mutation == "wrong_html_url":
        r["html_url"] = r["html_url"].replace("/187", "/188")
    elif mutation == "edited_rest":
        r["updated_at"] = "2026-10-26T00:00:01Z"
    elif mutation == "edited_same_second":
        n["lastEditedAt"] = r["created_at"]
        n["editor"] = {"login": "fixture-human"}
    elif mutation == "missing_edit_proof":
        n.pop("lastEditedAt")
    elif mutation == "wrong_graphql_type":
        n["__typename"] = "PullRequestReview"
    elif mutation == "wrong_graphql_id":
        n["fullDatabaseId"] = "123"
    elif mutation == "wrong_graphql_body":
        n["body"] += "changed"
    elif mutation == "wrong_graphql_author":
        n["author"]["login"] = "different-human"
    elif mutation == "wrong_graphql_time":
        n["createdAt"] = "2026-10-26T00:00:01Z"
    elif mutation == "minimized":
        n["isMinimized"] = True
    elif mutation == "wrong_digest":
        c["body_digest"] = "sha256:" + "0" * 64
    elif mutation == "retimed_reference":
        c["created_at"] = "2026-10-26T00:00:01Z"
    elif mutation == "proxy_statement":
        r["body"] = "Codex approves on behalf of the owner. " + r["body"]
    elif mutation == "wrong_scope":
        f["request"]["base"]["repo"]["full_name"] = "other/repository"
    elif mutation == "semantic_change":
        f["accepted"]["decisions"][0]["rationale"] += "Unreviewed policy."
    elif mutation == "metadata":
        f["accepted"]["governance"]["approved_by"] = "assistant"
    elif mutation == "date":
        f["accepted"]["governance"]["approved_date"] = "2026-10-26T00:00:01Z"
    with pytest.raises(design.DesignError):
        design.verify_live_owner_comment(ROOT, revision, c)


def test_synthetic_unretrievable_comment_cannot_become_approval(monkeypatch, tmp_path):
    f = owner_comment_fixture(monkeypatch, tmp_path)

    def absent(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0], stderr=b"HTTP 404")

    monkeypatch.setattr(design.subprocess, "check_output", absent)
    with pytest.raises(subprocess.CalledProcessError):
        design.verify_live_owner_comment(ROOT, f["revision"], f["comment"])


def test_owner_comment_cannot_cover_changed_companion_bytes(monkeypatch, tmp_path):
    f = owner_comment_fixture(monkeypatch, tmp_path)
    before = (ROOT / design.MAP_PATH).read_bytes()
    original_git = design._git
    read_bytes = Path.read_bytes

    def git(root, revision, path):
        return before if path == design.MAP_PATH else original_git(root, revision, path)

    def changed(path):
        return (
            before + b"# changed after authorization\n"
            if path == ROOT / design.MAP_PATH
            else read_bytes(path)
        )

    monkeypatch.setattr(design, "_git", git)
    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(design.DesignError, match="reviewed policy changed"):
        design.verify_live_owner_comment(ROOT, f["revision"], f["comment"])


def test_closed_comment_reference_records_provider_identity_without_local_trust(tmp_path):
    comment = {
        "id": 6406500216,
        "author_login": "fixture-human",
        "created_at": "2026-10-26T00:00:00Z",
        "source_url": f"https://github.com/{design.REPOSITORY}/pull/187#issuecomment-6406500216",
        "body_digest": "sha256:" + "0" * 64,
    }
    reference = {
        "schema_version": "1.0",
        "kind": "canonical-governance-acceptance-reference",
        "governing_adr_id": proposed()["id"],
        "reviewed_revision": "a" * 40,
        "owner_comment": comment,
    }
    path = tmp_path / design.ACCEPTANCE_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(json.dumps(reference).encode())
    assert design.acceptance_reference(tmp_path, proposed()["id"]) == reference
    # The reference cannot combine code-review and architectural-comment evidence.
    reference["approval_review_url"] = (
        f"https://github.com/{design.REPOSITORY}/pull/187#pullrequestreview-123"
    )
    path.write_bytes(json.dumps(reference).encode())
    with pytest.raises(design.DesignError):
        design.acceptance_reference(tmp_path, proposed()["id"])
    reference.pop("approval_review_url")
    reference["owner_comment"]["verified"] = True
    path.write_bytes(json.dumps(reference).encode())
    with pytest.raises(design.DesignError):
        design.acceptance_reference(tmp_path, proposed()["id"])


@pytest.mark.parametrize("evidence_kind", ["review", "owner_comment"])
def test_canonical_dispatch_retrieves_either_real_provider_path_in_transport_fixture(
    monkeypatch, tmp_path, evidence_kind
):
    # Simulated provider only. The actual canonical ADR is never modified/accepted.
    if evidence_kind == "owner_comment":
        f = owner_comment_fixture(monkeypatch, tmp_path)
        reference = {"reviewed_revision": f["revision"], "owner_comment": f["comment"]}
    else:
        revision, url, *_ = review_fixture(monkeypatch, tmp_path)
        reference = {"reviewed_revision": revision, "approval_review_url": url}
    monkeypatch.setattr(design, "acceptance_reference", lambda *args: reference)
    result = design.qualify_repository()
    proof = result["acceptance"]
    assert proof["evidence_kind"] == (
        "authorized_pr_comment" if evidence_kind == "owner_comment" else "approved_review"
    )
    assert proof["github_approved_review"] is (evidence_kind == "review")
    # A simulated result does not change canonical governance or persist a receipt.
    canonical = yaml.safe_load((ROOT / design.ADR_PATH).read_text(encoding="utf-8"))
    if canonical["status"] == "proposed":
        assert "governance" not in canonical
