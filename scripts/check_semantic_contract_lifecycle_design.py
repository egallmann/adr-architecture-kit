"""Bounded ADR-L-0040 design qualification; never a release publisher or scanner.

Exact clause anchors and immutable release evidence are checked mechanically.
Unmapped prose is reported, never interpreted by a natural-language heuristic.
Live acceptance is independently retrieved; local fixture data cannot activate it.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
ADR_PATH = "adrs/logical/ADR-L-0040-semantic-contract-candidate-and-promotion-lifecycle.yaml"
MAP_PATH = "adrs/migrations/semantic-contract-lifecycle-precedence.yaml"
CLASS_PATH = "adrs/migrations/semantic-contract-lifecycle-classification.json"
SPEC_PATH = "docs/contributors/semantic-contract-lifecycle.md"
SCHEMAS = Path("scripts/schemas")
SCHEMA_NAMES = (
    "lifecycle-precedence",
    "packaged-authority-inventory",
    "authority-promotion-attestation",
    "governance-acceptance-reference",
)
COMPANIONS = (
    MAP_PATH,
    CLASS_PATH,
    SPEC_PATH,
    *(f"scripts/schemas/{name}.schema.json" for name in SCHEMA_NAMES),
)
ACCEPTANCE_PATH = "adrs/migrations/semantic-contract-lifecycle-acceptance.json"
REPOSITORY = "egallmann/adr-architecture-kit"
SCOPE = {
    "architecture-interpretation": {"1.2", "1.3", "1.4", "1.5"},
    "authoring-construction": {"1.1", "1.2", "1.3", "1.4", "1.5"},
    "normalized-model": {"2.5"},
}
TOPIC_TARGET = {
    "snapshot_identity": "DEC-9023",
    "candidate_version_finality": "DEC-9023",
    "candidate_selection": "DEC-9026",
    "prototype_retention": "DEC-9026",
}


class DesignError(ValueError):
    """An exact governance proof could not be established."""


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def read(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DesignError(message)


def validate_shape(value: Any, name: str, root: Path = ROOT) -> None:
    schema = read(root / SCHEMAS / f"{name}.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(value), key=str)
    require(not errors, f"{name}: {errors[0].message if errors else ''}")


def qualify_precedence(
    document: dict[str, Any], mapping: dict[str, Any], documents: list[dict[str, Any]]
) -> dict[str, Any]:
    """Pure design validation: accepted synthetic fixtures STILL have no effect."""
    validate_shape(mapping, "lifecycle-precedence")
    require(mapping["governing_adr_id"] == document["id"], "governing ADR identity")
    require(document["alias_id"] == "ADR-L-0040", "governing alias")
    members: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    adr_ids: set[str] = set()
    for adr in documents:
        require(adr["id"] not in adr_ids, "ambiguous canonical ADR")
        adr_ids.add(adr["id"])
        for field in ("decisions", "invariants"):
            for member in adr.get(field, []):
                require(member["id"] not in members, "ambiguous canonical member")
                members[member["id"]] = (adr, member)
    replacements = {x["id"]: x for x in document["decisions"]}
    ids: set[str] = set()
    spans: dict[tuple[str, str, str, str], list[tuple[int, int]]] = {}
    mapped = set()
    for rule in mapping["rules"]:
        require(rule["id"] not in ids, "duplicate precedence identity")
        ids.add(rule["id"])
        original, replacement = rule["original"], rule["replacement"]
        require(original["member_id"] in members, "missing original canonical member")
        adr, member = members[original["member_id"]]
        require(adr["id"] == original["adr_id"], "original ADR UUID")
        require(member["alias_id"] == original["member_alias"], "original member alias")
        require(adr["id"] != document["id"], "precedence cycle")
        require(adr["status"] == "accepted", "original authority not accepted")
        expected_field = "rationale" if member["alias_id"].startswith("DEC-") else "statement"
        require(original["field"] == expected_field, "wrong governed field")
        source = member[expected_field]
        anchor = original["anchor"]
        require(source.count(anchor) == 1, "missing or ambiguous exact anchor")
        require(digest(anchor.encode("utf-8")) == original["anchor_digest"], "anchor digest")
        require(replacement["adr_id"] == document["id"], "replacement ADR UUID")
        require(replacement["member_id"] in replacements, "missing replacement UUID")
        target = replacements[replacement["member_id"]]
        require(target["alias_id"] == replacement["requirement"], "replacement identity")
        topic = rule["applicability"]["topic"]
        require(target["alias_id"] == TOPIC_TARGET[topic], "replacement requirement scope")
        families = set()
        start = source.index(anchor)
        for selection in rule["applicability"]["authority_scope"]:
            family = selection["family"]
            require(family not in families, "duplicate family scope")
            families.add(family)
            require(set(selection["versions"]) <= SCOPE[family], "released/unknown scope")
            for version in selection["versions"]:
                key = (member["id"], expected_field, family, version)
                prior = spans.setdefault(key, [])
                require(
                    all(start + len(anchor) <= a or start >= b for a, b in prior),
                    "overlapping replacement scope",
                )
                prior.append((start, start + len(anchor)))
        mapped.add(member["id"])
    # Full unaltered member text is reported for every member, including residual
    # text of mapped members. No unrecognized MUST is silently suppressed.
    obligations = [
        {
            "adr_id": adr["id"],
            "member_id": member["id"],
            "alias": member["alias_id"],
            "mapped_spans_only": member["id"] in mapped,
            "unmapped_text": _residual(member, mapping),
        }
        for adr, member in members.values()
        if adr["status"] == "accepted"
    ]
    return {
        "design_qualified": True,
        "mapped_clauses": len(ids),
        "mapped_members": len(mapped),
        "unmapped_obligations": sorted(obligations, key=lambda x: x["member_id"]),
        "activation": "inactive_without_independent_human_evidence",
        "effective_replacements": [],
    }


def matching_design_clauses(
    mapping: dict[str, Any], member_id: str, family: str, version: str, topic: str
) -> list[str]:
    """Resolve declared scope only; returned design matches are NEVER activation.

    Released contexts are excluded by the closed family/version allowlist. A
    consumer still needs independently verified acceptance and promotion evidence.
    """
    require(topic in TOPIC_TARGET, "unknown policy topic")
    return sorted(
        rule["id"]
        for rule in mapping["rules"]
        if rule["original"]["member_id"] == member_id
        and rule["applicability"]["topic"] == topic
        and any(
            s["family"] == family and version in s["versions"]
            for s in rule["applicability"]["authority_scope"]
        )
    )


def _residual(member: dict[str, Any], mapping: dict[str, Any]) -> str:
    field = "rationale" if member["alias_id"].startswith("DEC-") else "statement"
    text = member[field]
    for rule in mapping["rules"]:
        if rule["original"]["member_id"] == member["id"]:
            text = text.replace(rule["original"]["anchor"], "[explicitly mapped clause]")
    return str(text)


def qualify_released_evidence(classification: dict[str, Any], root: Path = ROOT) -> dict[str, int]:
    """Verify positive recorded release evidence, never infer release from HEAD."""
    require(
        classification["kind"] == "semantic-contract-lifecycle-classification", "classification"
    )
    evidence = {x["id"]: x for x in classification["release_evidence"]}
    require(len(evidence) == len(classification["release_evidence"]), "duplicate release evidence")
    for row in evidence.values():
        require(bool(re.fullmatch(r"[0-9a-f]{64}", row["sha256"])), "artifact hash")
        require(row["source_commit"] and row["registry"].startswith("https://"), "release evidence")
    identities = set()
    for row in classification["released_contracts"]:
        identity = (row["family"], row["version"])
        require(identity not in identities, "duplicate released identity")
        identities.add(identity)
        require(row["classification"] == "RELEASED", "released disposition")
        require(
            row["evidence"] and set(row["evidence"]) <= evidence.keys(), "missing artifact evidence"
        )
        path = root / row["definition_path"]
        require(
            digest(path.read_bytes()) == row["definition_digest"], "released definition mutation"
        )
        definition = read(path)
        require(definition["semanticContractFingerprint"] == row["scf"], "released SCF mutation")
        require(
            digest(canonical_bytes(definition["resourceManifest"]))
            == row["resource_manifest_digest"]
            and len(definition["resourceManifest"]) == row["resource_count"],
            "released closure mutation",
        )
    for row in (
        classification["released_schema_files"] + classification["embedded_resource_authorities"]
    ):
        content = (root / row["path"]).read_bytes().replace(b"\r\n", b"\n")
        require(digest(content) == row["content_digest"], "released resource mutation")
    return {
        "released_contracts": len(identities),
        "released_files": len(classification["released_schema_files"]),
    }


def qualify_history_evidence(classification: dict[str, Any], root: Path = ROOT) -> int:
    """Audit retained Git snapshots, not ongoing current-version compatibility."""
    revision = classification["audit_source_commit"]
    for row in classification["development_lineage"]:
        raw = _git(root, revision, row["definition_path"])
        require(digest(raw) == row["definition_digest"], "historical Git content mismatch")
        definition = json.loads(raw)
        require(
            definition["semanticContractFingerprint"] == row["scf"], "historical Git SCF mismatch"
        )
        require(
            digest(canonical_bytes(definition["resourceManifest"]))
            == row["resource_manifest_digest"],
            "historical Git graph mismatch",
        )
    return len(classification["development_lineage"])


def qualify_inventory(inventory: dict[str, Any], payloads: dict[str, bytes]) -> None:
    """Validate the declared inventory against payload bytes, NOT discover its cohort.

    Operational wheel/npm/WASM discovery must independently establish completeness
    in the later release-controls checkpoint. This helper cannot authorize release.
    """
    validate_shape(inventory, "packaged-authority-inventory")
    names = [x["name"] for x in inventory["artifacts"]]
    require(names == sorted(set(names)), "artifact inventory order/uniqueness")
    require(set(names) == payloads.keys(), "payload inventory mismatch")
    for artifact in inventory["artifacts"]:
        data = payloads[artifact["name"]]
        require(
            artifact["digest"] == digest(data) and artifact["size"] == len(data), "payload mutation"
        )
    identities = [(x["family"], x["version"]) for x in inventory["authorities"]]
    require(identities == sorted(set(identities)), "authority inventory order/uniqueness")
    for authority in inventory["authorities"]:
        resources = authority["resources"]
        keys = [x["key"] for x in resources]
        require(keys == sorted(set(keys)), "resource inventory order/uniqueness")
        placements = authority["placements"]
        locators = [(x["artifact"], x["locator"]) for x in placements]
        require(locators == sorted(set(locators)), "placement order/uniqueness")
        require(all(x["artifact"] in payloads for x in placements), "unknown placement artifact")
        for placement in placements:
            require(
                placement["locator"] not in {"$inventory", "$manifest", "$bundle", "$attestation"},
                "inventory self-reference",
            )


def qualify_attestation_contract(
    attestation: dict[str, Any],
    inventory: dict[str, Any],
    payloads: dict[str, bytes],
    bundle: bytes,
    manifest: bytes,
    inventory_bytes: bytes,
) -> dict[str, Any]:
    """Specification/cohort validation only: human trust/publish gating NOT established."""
    validate_shape(attestation, "authority-promotion-attestation")
    qualify_inventory(inventory, payloads)
    require(read_json(inventory_bytes) == inventory, "inventory bytes")
    require(inventory_bytes == canonical_bytes(inventory), "noncanonical inventory bytes")
    require(manifest == canonical_bytes(read_json(manifest)), "noncanonical manifest bytes")
    source = inventory["source_commit"]
    require(
        source == attestation["source_commit"] == attestation["qualification"]["source_commit"],
        "source qualification mismatch",
    )
    require(
        attestation["human_approval"]["reviewed_source_commit"] == source,
        "approval source mismatch",
    )
    require(
        attestation["approved_authorities"] == inventory["authorities"],
        "authority cohort mismatch; qualify a new bundle",
    )
    require(attestation["artifacts"] == inventory["artifacts"], "artifact cohort mismatch")
    retained = attestation["retained_bundle"]
    require(retained["digest"] == digest(bundle), "retained bundle mutation")
    require(retained["manifest_digest"] == digest(manifest), "manifest mutation")
    require(retained["inventory_digest"] == digest(inventory_bytes), "inventory mutation")
    # Manifest is already finalized: it may commit payload/inventory hashes only.
    m = read_json(manifest)
    require(
        set(m) == {"source_commit", "artifacts", "inventory_digest"},
        "manifest cycle or unknown field",
    )
    require(
        m
        == {
            "source_commit": source,
            "artifacts": inventory["artifacts"],
            "inventory_digest": digest(inventory_bytes),
        },
        "manifest commitment",
    )
    return {
        "specification_qualified": True,
        "human_approval": "not_verified",
        "publisher_enforcement": "not_implemented",
        "promotion_authorized": False,
    }


def canonical_bytes(value: Any) -> bytes:
    """Use the existing Rust-owned canonical JSON, never a new serializer."""
    from adr_kit.semantic_contract import canonicalize_semantic_json

    result = canonicalize_semantic_json(value)
    require(result.success and result.canonical_preimage_json is not None, "canonical envelope")
    assert result.canonical_preimage_json is not None
    return result.canonical_preimage_json.encode("utf-8")


def read_json(data: bytes) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, "duplicate envelope member")
            result[key] = value
        return result

    return json.loads(data.decode("utf-8"), object_pairs_hook=unique)


def qualify_transition_spec(
    previous: dict[str, Any], revision: dict[str, Any], promoted_snapshot: dict[str, Any] | None
) -> None:
    """Pure lifecycle contract test seam, not a promotion registry/authorization."""
    from adr_kit.semantic_contract import verify_semantic_contract

    require(
        verify_semantic_contract(previous).success and verify_semantic_contract(revision).success,
        "invalid revision SCF",
    )
    if promoted_snapshot is not None:
        # This parameter denotes a separately authenticated promotion snapshot;
        # the helper cannot establish that trust or perform a promotion.
        require(previous == promoted_snapshot, "promotion snapshot mismatch")
        same = (previous["semanticContractFamily"], previous["semanticContractVersion"]) == (
            revision["semanticContractFamily"],
            revision["semanticContractVersion"],
        )
        require(not same or revision == promoted_snapshot, "promoted same-version replacement")


def _git(root: Path, revision: str, path: str) -> bytes:
    require(bool(re.fullmatch(r"[0-9a-f]{40}", revision)), "exact reviewed Git revision required")
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=root)


def _github_api(root: Path, *arguments: str) -> Any:
    """Authenticated fixed-host read-only API retrieval, never local proof flags."""
    return read_json(
        subprocess.check_output(
            ["gh", "api", "--hostname", "github.com", *arguments], cwd=root, timeout=30
        )
    )


def _verify_acceptance_content(
    root: Path, revision: str, actor: str, approved_at: str, request: dict[str, Any]
) -> None:
    """Shared exact authorization/content checks for either real evidence source."""
    reviewed_project = yaml.safe_load(_git(root, revision, "PROJECT.yaml"))
    current_project = read(root / "PROJECT.yaml")
    require(reviewed_project == current_project, "authorization policy changed since review")
    base_policy = yaml.safe_load(_git(root, request["base"]["sha"], "PROJECT.yaml"))
    require(current_project == base_policy, "unadmitted authorization policy")
    authorized = current_project["integrations"]["scm"]["required_approvers"]
    require("@" + actor in authorized, "unauthorized reviewer")
    require(
        request["base"]["repo"]["full_name"] == REPOSITORY and request["base"]["ref"] == "develop",
        "review repository/base",
    )
    reviewed = yaml.safe_load(_git(root, revision, ADR_PATH))
    current = read(root / ADR_PATH)
    require(
        reviewed["status"] == "proposed" and "governance" not in reviewed,
        "reviewed proposed revision",
    )
    require(current["status"] == "accepted", "accepted status required")
    metadata = current.get("governance", {})
    require(
        set(metadata) == {"approved_by", "approved_date"} and metadata["approved_by"] == actor,
        "authentic paired acceptance metadata",
    )
    from datetime import datetime

    require(
        datetime.fromisoformat(metadata["approved_date"].replace("Z", "+00:00"))
        == datetime.fromisoformat(approved_at.replace("Z", "+00:00")),
        "approval date mismatch",
    )
    current = copy.deepcopy(current)
    current["status"] = "proposed"
    current.pop("governance")
    require(current == reviewed, "reviewed architecture changed")
    for path in COMPANIONS:
        require(_git(root, revision, path) == (root / path).read_bytes(), "reviewed policy changed")


def verify_live_acceptance(root: Path, revision: str, review_url: str) -> dict[str, Any]:
    """Retain the independent APPROVED-review path, with its original constraints."""
    require(bool(re.fullmatch(r"[0-9a-f]{40}", revision)), "exact reviewed Git revision required")
    match = re.fullmatch(
        r"https://github.com/egallmann/adr-architecture-kit/pull/(\d+)#pullrequestreview-(\d+)",
        review_url,
    )
    require(match is not None, "exact GitHub review URL required")
    assert match is not None
    pr, review = match.groups()
    record = _github_api(root, f"repos/{REPOSITORY}/pulls/{pr}/reviews/{review}")
    request = _github_api(root, f"repos/{REPOSITORY}/pulls/{pr}")
    require(record.get("html_url") == review_url, "review origin")
    require(
        record.get("state") == "APPROVED" and record.get("commit_id") == revision,
        "review state/revision",
    )
    require(record.get("user", {}).get("type") == "User", "human review required")
    actor = record["user"]["login"]
    require(request["user"]["login"] != actor, "self-review is not independent approval")
    require(
        "Approve ADR-L-0040 lifecycle governance and activation." in record.get("body", ""),
        "explicit lifecycle approval missing",
    )
    _verify_acceptance_content(root, revision, actor, record["submitted_at"], request)
    return {
        "actor": actor,
        "reviewed_revision": revision,
        "review_url": review_url,
        "evidence_kind": "approved_review",
        "github_approved_review": True,
    }


def verify_live_owner_comment(root: Path, revision: str, comment: dict[str, Any]) -> dict[str, Any]:
    """Architectural authorization only; cannot establish a GitHub code-review approval.

    The actual human must post this comment. This code only reads it, and never
    creates evidence. REST and GraphQL must agree, including an unedited history.
    """
    require(bool(re.fullmatch(r"[0-9a-f]{40}", revision)), "exact reviewed Git revision required")
    validate_shape(
        {
            "schema_version": "1.0",
            "kind": "canonical-governance-acceptance-reference",
            "governing_adr_id": read(root / ADR_PATH)["id"],
            "reviewed_revision": revision,
            "owner_comment": comment,
        },
        "governance-acceptance-reference",
    )
    url = comment["source_url"]
    match = re.fullmatch(
        r"https://github.com/egallmann/adr-architecture-kit/pull/(\d+)#issuecomment-(\d+)", url
    )
    require(match is not None, "exact GitHub PR comment URL required")
    assert match is not None
    pr, comment_id = match.groups()
    require(pr == "187", "governing comment PR")
    require(type(comment["id"]) is int and str(comment["id"]) == comment_id, "comment identity")
    record = _github_api(root, f"repos/{REPOSITORY}/issues/comments/{comment_id}")
    request = _github_api(root, f"repos/{REPOSITORY}/pulls/{pr}")
    pages = _github_api(
        root, "--paginate", "--slurp", f"repos/{REPOSITORY}/pulls/{pr}/commits?per_page=100"
    )
    require(
        isinstance(pages, list) and all(isinstance(page, list) for page in pages),
        "comment PR commit proof unavailable",
    )
    require(
        any(
            isinstance(commit, dict) and commit.get("sha") == revision
            for page in pages
            for commit in page
        ),
        "reviewed commit absent from governing PR",
    )
    require(
        record.get("id") == comment["id"] and record.get("html_url") == url,
        "comment identity/origin",
    )
    require(
        record.get("url")
        == f"https://api.github.com/repos/{REPOSITORY}/issues/comments/{comment_id}",
        "comment API origin",
    )
    require(
        record.get("issue_url") == f"https://api.github.com/repos/{REPOSITORY}/issues/{pr}",
        "comment PR association",
    )
    require(
        str(request.get("number")) == pr
        and request.get("html_url") == f"https://github.com/{REPOSITORY}/pull/{pr}",
        "comment PR origin",
    )
    require(
        record.get("user", {}).get("type") == "User"
        and record.get("performed_via_github_app") is None,
        "human comment required",
    )
    actor = record["user"]["login"]
    require(actor == comment["author_login"], "comment author mismatch")
    require(
        record.get("created_at") == comment["created_at"]
        and record.get("updated_at") == comment["created_at"],
        "edited or retimed comment",
    )
    body = record.get("body")
    expected = (
        f"I approve ADR-L-0040 lifecycle governance and activation at reviewed commit {revision}."
    )
    require(
        isinstance(body, str) and body.strip() == expected,
        "explicit exact-revision comment approval missing",
    )
    require(digest(body.encode("utf-8")) == comment["body_digest"], "comment body digest")
    require(
        isinstance(record.get("node_id"), str) and bool(record["node_id"]), "comment node identity"
    )
    query = """query($id:ID!){node(id:$id){__typename ... on IssueComment {
      id fullDatabaseId url createdAt updatedAt lastEditedAt isMinimized body
      author {login __typename} editor {login}
    }}}"""
    response = _github_api(root, "graphql", "-f", f"query={query}", "-f", f"id={record['node_id']}")
    require(not response.get("errors"), "comment edit-history proof unavailable")
    node = response.get("data", {}).get("node")
    require(
        isinstance(node, dict) and node.get("__typename") == "IssueComment",
        "comment edit-history proof unavailable",
    )
    require(
        node.get("id") == record["node_id"]
        and str(node.get("fullDatabaseId")) == comment_id
        and node.get("url") == url,
        "comment cross-API identity",
    )
    require(
        "lastEditedAt" in node
        and node["lastEditedAt"] is None
        and "editor" in node
        and node["editor"] is None
        and node.get("isMinimized") is False,
        "edited or unavailable comment",
    )
    require(
        node.get("createdAt") == comment["created_at"] == node.get("updatedAt"),
        "comment cross-API timestamp",
    )
    require(
        node.get("author") == {"login": actor, "__typename": "User"} and node.get("body") == body,
        "comment cross-API author/body",
    )
    _verify_acceptance_content(root, revision, actor, comment["created_at"], request)
    return {
        "actor": actor,
        "reviewed_revision": revision,
        "evidence_kind": "authorized_pr_comment",
        "comment_id": comment["id"],
        "approved_at": comment["created_at"],
        "source_url": url,
        "body_digest": comment["body_digest"],
        "github_approved_review": False,
    }


def acceptance_reference(root: Path, governing_id: str) -> dict[str, Any]:
    """An external evidence locator is a pointer, NEVER self-certified approval."""
    path = root / ACCEPTANCE_PATH
    require(path.is_file(), "independent acceptance reference required")
    reference = read_json(path.read_bytes())
    validate_shape(reference, "governance-acceptance-reference")
    require(reference["governing_adr_id"] == governing_id, "acceptance ADR identity")
    return dict(reference)


def qualify_repository(
    root: Path = ROOT, revision: str | None = None, review: str | None = None
) -> dict[str, Any]:
    document = read(root / ADR_PATH)
    mapping = read(root / MAP_PATH)
    documents = [read(p) for p in sorted((root / "adrs/logical").glob("*.yaml"))]
    result = qualify_precedence(document, mapping, documents)
    result["release_evidence"] = qualify_released_evidence(read(root / CLASS_PATH), root)
    result["historical_snapshots"] = qualify_history_evidence(read(root / CLASS_PATH), root)
    companions = COMPANIONS
    bindings = document["decisions"][5]["rationale"]
    for path in companions:
        require(f"{path} {digest((root / path).read_bytes())}" in bindings, "unbound companion")
    if document["status"] == "proposed":
        require("governance" not in document, "fabricated proposed acceptance metadata")
        require(revision is None and review is None, "proposed ADR cannot activate")
    elif document["status"] == "accepted":
        if revision is None and review is None:
            reference = acceptance_reference(root, document["id"])
            revision = reference["reviewed_revision"]
            if "owner_comment" in reference:
                result["acceptance"] = verify_live_owner_comment(
                    root, revision, reference["owner_comment"]
                )
            else:
                result["acceptance"] = verify_live_acceptance(
                    root, revision, reference["approval_review_url"]
                )
        else:
            require(
                revision is not None and review is not None,
                "complete independent acceptance evidence required",
            )
            assert revision is not None and review is not None
            result["acceptance"] = verify_live_acceptance(root, revision, review)
        result["activation"] = "verified_exact_mapped_scope_only"
        result["effective_replacements"] = mapping["rules"]
    else:
        raise DesignError("unsupported governance lifecycle")
    result["publisher_enforcement"] = "not_implemented"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed-revision")
    parser.add_argument("--approval-review-url")
    args = parser.parse_args()
    try:
        result = qualify_repository(
            revision=args.reviewed_revision, review=args.approval_review_url
        )
        print(json.dumps(result, indent=2))
        return 0
    except (DesignError, OSError, subprocess.CalledProcessError, ValueError, KeyError) as error:
        print(f"Lifecycle design qualification failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
