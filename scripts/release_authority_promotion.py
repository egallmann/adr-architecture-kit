"""Operational cohort admission shared by BOTH promotion-only publishers.

No trust flag, package repair, publisher, or release-version allocation lives here.
The companion attestation is external to the source and finalized retained bundle.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import urllib.error
import urllib.request
import tomllib
from pathlib import Path
from typing import Any

import yaml

from scripts import resolve_qualified_release_bundle as github
from scripts.check_semantic_contract_lifecycle_design import (
    canonical_bytes,
    digest,
    read_json,
    require,
    qualify_repository,
)
from scripts.release_authority_inventory import (
    ROOT,
    archive_members,
    create_cohort,
    package_payloads,
    verify_cohort,
)
from scripts.release_manifest import verify_manifest

REPOSITORY = "egallmann/adr-architecture-kit"
ENVIRONMENT = "semantic-authority-promotion"
WORKFLOW = ".github/workflows/authority-promotion.yml"


def api(path: str) -> Any:
    require(github._api_base() == "https://api.github.com", "unsupported approval API origin")
    require(github._repository() == REPOSITORY, "wrong promotion repository")
    return github._request_json(
        f"https://api.github.com/repos/{REPOSITORY}/{path}", github._token()
    )[0]


def api_list(path: str) -> list[dict[str, Any]]:
    """Read every page of an authenticated list without trusting redirect origins."""
    api("git/ref/heads/main")  # Enforce the configured repository/API/token boundary.
    prefix = f"https://api.github.com/repos/{REPOSITORY}/"
    url: str | None = prefix + path
    result: list[dict[str, Any]] = []
    while url:
        require(url.startswith(prefix), "foreign evidence pagination")
        payload, headers = github._request_json(url, github._token())
        require(
            isinstance(payload, list) and all(isinstance(x, dict) for x in payload),
            "invalid evidence list",
        )
        result.extend(payload)
        url = github._next_link(headers)
    return result


def qualified_bundle(run_id: int, source: str) -> dict[str, Any]:
    run = api(f"actions/runs/{run_id}")
    require(
        github._is_qualifying_run(run, sha=source, branch="main", event="push"),
        "not successful main-push certification",
    )
    require(
        run["path"] == ".github/workflows/release-certification.yml", "wrong certification workflow"
    )
    require(
        run["repository"]["full_name"] == REPOSITORY
        and run["head_repository"]["full_name"] == REPOSITORY,
        "foreign certification repository",
    )
    artifacts = github._paginate(
        f"https://api.github.com/repos/{REPOSITORY}/actions/runs/{run_id}/artifacts?per_page=100",
        github._token(),
        "artifacts",
    )
    matches = [a for a in artifacts if a["name"] == "release-bundle"]
    require(
        len(matches) == 1 and not matches[0]["expired"], "missing/expired/ambiguous retained bundle"
    )
    artifact = matches[0]
    require(
        re.fullmatch(r"sha256:[0-9a-f]{64}", artifact.get("digest", "")) is not None,
        "unqualified retained archive digest",
    )
    require(
        artifact["workflow_run"]["id"] == run_id and artifact["workflow_run"]["head_sha"] == source,
        "artifact source mismatch",
    )
    return artifact


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: Any, msg: Any, headers: Any, newurl: Any
    ) -> None:
        return None


def download_bundle(run_id: int, source: str, destination: Path) -> dict[str, Any]:
    artifact = qualified_bundle(run_id, source)
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{artifact['id']}/zip",
        headers=github._headers(github._token()),
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=60) as response:
            data = response.read(512 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as redirect:
        require(redirect.code == 302, "retained artifact download failed")
        location = redirect.headers["Location"]
        parsed = urllib.parse.urlparse(location)
        require(
            parsed.scheme == "https"
            and parsed.hostname is not None
            and (
                parsed.hostname.endswith(".blob.core.windows.net")
                or parsed.hostname.endswith(".actions.githubusercontent.com")
            ),
            "untrusted artifact redirect",
        )
        # Never forward the GitHub bearer token to the signed blob URL.
        with urllib.request.urlopen(location, timeout=60) as response:
            data = response.read(512 * 1024 * 1024 + 1)
    require(
        len(data) <= 512 * 1024 * 1024 and digest(data) == artifact["digest"],
        "retained archive mutation",
    )
    members = archive_members(data, True)
    require(not destination.exists(), "bundle destination must be fresh")
    destination.with_suffix(".zip").write_bytes(data)
    destination.mkdir(parents=True)
    for name, payload in members.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return artifact


def verify_source(source: str, root: Path) -> None:
    require(re.fullmatch(r"[0-9a-f]{40}", source) is not None, "invalid source identity")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    require(actual == source, "source checkout differs from certified source")
    governance = qualify_repository(root)
    require(
        bool(governance["effective_replacements"])
        and governance["activation"] != "inactive_without_independent_human_evidence",
        "ADR-L-0040 governance is not authentically active",
    )
    require(
        subprocess.run(
            [
                "git",
                "diff",
                "--quiet",
                "HEAD",
                "--",
                "contracts",
                "schema",
                "PROJECT.yaml",
                "pyproject.toml",
                "packages/node/package.json",
                "src/adr_kit/semantic_contract",
                "src/adr_kit/promotion/rules",
                "adrs/migrations/semantic-contract-lifecycle-classification.json",
            ],
            cwd=root,
            check=False,
        ).returncode
        == 0,
        "changed source authority",
    )


def bundle_evidence(bundle: Path, source: str, run_id: int, root: Path = ROOT) -> dict[str, Any]:
    verify_source(source, root)
    metadata = qualified_bundle(run_id, source)
    archive = bundle.with_suffix(".zip").read_bytes()
    require(digest(archive) == metadata["digest"], "retained ZIP differs from certified artifact")
    original = archive_members(archive, True)
    material = {
        p.relative_to(bundle).as_posix(): p.read_bytes() for p in bundle.rglob("*") if p.is_file()
    }
    require(material == original, "retained bundle bytes changed after download")
    inventory = verify_cohort(bundle, source, root)
    enforce_promoted(inventory, qualified_prior_promotions(source, root, live=True))
    payloads = package_payloads(bundle)
    expected = set(payloads) | {
        "authority-inventory.json",
        "authority-manifest.json",
        "release-manifest.json",
    }
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()}
    require(actual == expected, "extra or missing retained bundle material")
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    verify_manifest(
        bundle / "python-dist", bundle / "release-manifest.json", source, version, f"v{version}"
    )
    npm = next(v for k, v in payloads.items() if k.endswith(".tgz"))
    node_metadata = read_json(archive_members(npm, False)["package/package.json"])
    selected_node = read_json((root / "packages/node/package.json").read_bytes())
    require(
        node_metadata["version"] == version and node_metadata["name"] == selected_node["name"],
        "npm source/version mismatch",
    )
    return {
        "schema_version": "1.0",
        "kind": "semantic-authority-promotion-attestation",
        "source_commit": source,
        "qualification": {
            "repository": REPOSITORY,
            "source_commit": source,
            "ref": "refs/heads/main",
            "event": "push",
            "run_id": run_id,
            "workflow_path": ".github/workflows/release-certification.yml",
            "conclusion": "success",
        },
        "retained_bundle": {
            "artifact_id": str(metadata["id"]),
            "digest": metadata["digest"],
            "manifest_digest": digest((bundle / "authority-manifest.json").read_bytes()),
            "inventory_digest": digest((bundle / "authority-inventory.json").read_bytes()),
        },
        "artifacts": inventory["artifacts"],
        "approved_authorities": inventory["authorities"],
        "publication_mode": "promote-retained-payloads-only",
    }


def approval_statement(evidence: dict[str, Any]) -> str:
    # Hash the exact approval subject, without the future approval reference.
    return f"I approve semantic authority promotion for source {evidence['source_commit']} and exact retained cohort {digest(canonical_bytes(evidence))}."


def authorized_approval(
    evidence: dict[str, Any], run_id: int, root: Path = ROOT, *, issuing: bool = False
) -> dict[str, str]:
    run = api(f"actions/runs/{run_id}")
    require(
        run["path"] == WORKFLOW
        and run["event"] == "workflow_dispatch"
        and run["head_branch"] == "main"
        and run["head_sha"] == evidence["source_commit"],
        "wrong promotion run/source",
    )
    require(
        run["repository"]["full_name"] == REPOSITORY
        and run["head_repository"]["full_name"] == REPOSITORY,
        "foreign promotion run",
    )
    require(
        (run["status"] == "completed" and run["conclusion"] == "success")
        or (issuing and run["status"] == "in_progress"),
        "incomplete promotion run",
    )
    environment = api(f"environments/{ENVIRONMENT}")
    required = [p for p in environment["protection_rules"] if p["type"] == "required_reviewers"]
    require(
        len(required) == 1 and required[0].get("prevent_self_review") is False,
        "missing owner-usable human environment protection",
    )
    require(environment.get("can_admins_bypass") is False, "environment permits protection bypass")
    policy = yaml.safe_load((root / "PROJECT.yaml").read_text(encoding="utf-8"))
    actors = {x.removeprefix("@") for x in policy["integrations"]["scm"]["required_approvers"]}
    reviewers = {
        r["reviewer"]["id"]
        for r in required[0]["reviewers"]
        if r["type"] == "User" and r["reviewer"]["login"] in actors
    }
    require(bool(reviewers), "no authorized human environment reviewer")
    reviews = api(f"actions/runs/{run_id}/approvals")
    matches = [
        r
        for r in reviews
        if any(e["id"] == environment["id"] and e["name"] == ENVIRONMENT for e in r["environments"])
    ]
    require(len(matches) == 1, "missing or ambiguous promotion approval")
    approval = matches[0]
    user = approval["user"]
    require(
        approval["state"] == "approved"
        and user["type"] == "User"
        and user["login"] in actors
        and user["id"] in reviewers,
        "unauthorized promotion actor",
    )
    require(
        approval["comment"] == approval_statement(evidence),
        "stale or wrong authority-cohort approval",
    )
    return {
        "provider": "protected-human-environment",
        "evidence_url": f"https://github.com/{REPOSITORY}/actions/runs/{run_id}",
        "actor": user["login"],
        "reviewed_source_commit": evidence["source_commit"],
    }


def issue_attestation(
    bundle: Path, source: str, certification: int, promotion: int, root: Path = ROOT
) -> dict[str, Any]:
    evidence = bundle_evidence(bundle, source, certification, root)
    evidence["human_approval"] = authorized_approval(evidence, promotion, root, issuing=True)
    return evidence


def retrieve_attestation(source: str) -> dict[str, Any]:
    # Evidence-only later Git history; never replace source S or rebuild payload P.
    path = f"contents/.github/authority-promotions/{source}.json?ref=main"
    payload = api(path)
    require(
        payload["type"] == "file" and payload["encoding"] == "base64",
        "missing durable promotion record",
    )
    data = base64.b64decode(payload["content"], validate=False)
    attestation = read_json(data)
    require(data == canonical_bytes(attestation), "noncanonical promotion record")
    history = api(f"commits?path=.github/authority-promotions/{source}.json&sha=main&per_page=100")
    require(
        isinstance(history, list) and len(history) == 1,
        "promotion record changed after durable recording",
    )
    commit = history[0]["sha"]
    ancestry = api(f"compare/{source}...{commit}")
    require(
        ancestry["status"] == "ahead" and ancestry["merge_base_commit"]["sha"] == source,
        "promotion record is not external later evidence",
    )
    frozen = api(f"contents/.github/authority-promotions/{source}.json?ref={commit}")
    require(
        frozen["sha"] == payload["sha"] and frozen["content"] == payload["content"],
        "changed promotion record snapshot",
    )
    require(isinstance(attestation, dict), "invalid promotion record")
    return dict(attestation)


def recorded_promotion_sources(source: str, root: Path, *, live: bool = False) -> list[str]:
    """Retain prior immutable evidence; deletion cannot erase a compatibility duty."""
    prefix = ".github/authority-promotions/"
    history = subprocess.check_output(
        ["git", "log", "--format=", "--name-only", source, "--", prefix], cwd=root, text=True
    )
    names = {n for n in history.splitlines() if n.endswith(".json")}
    present = set(
        subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", source, "--", prefix], cwd=root, text=True
        ).splitlines()
    )
    require(names <= present, "deleted promotion evidence in certified source history")
    if live:
        snapshot = api("git/ref/heads/main")["object"]["sha"]
        require(re.fullmatch(r"[0-9a-f]{40}", snapshot) is not None, "invalid evidence snapshot")
        live_history = api_list(f"commits?path={prefix}&sha={snapshot}&per_page=100")
        for commit in live_history:
            files = github._paginate(
                f"https://api.github.com/repos/{REPOSITORY}/commits/{commit['sha']}?per_page=100",
                github._token(),
                "files",
            )
            require(len(files) < 3000, "unqualified promotion evidence history")
            for item in files:
                if item["filename"].startswith(prefix) and item["filename"].endswith(".json"):
                    require(
                        item["status"] == "added", "changed/deleted historical promotion record"
                    )
                    names.add(item["filename"])
        github_directory = api(f"contents/.github?ref={snapshot}")
        directories = [p for p in github_directory if p["name"] == "authority-promotions"]
        if directories:
            require(
                len(directories) == 1 and directories[0]["type"] == "dir",
                "ambiguous promotion evidence location",
            )
            files = api(f"contents/.github/authority-promotions?ref={snapshot}")
            require(
                isinstance(files, list) and len(files) < 1000,
                "unqualified promotion evidence listing",
            )
            live_names = {
                p["path"] for p in files if p["type"] == "file" and p["name"].endswith(".json")
            }
            require(names <= live_names, "deleted durable promotion evidence")
            names.update(live_names)
        else:
            require(not names, "missing durable promotion evidence directory")
    result = []
    for name in sorted(names):
        match = re.fullmatch(r"\.github/authority-promotions/([0-9a-f]{40})\.json", name)
        require(match is not None, "unsupported promotion evidence record")
        assert match is not None
        if match[1] != source:
            result.append(match[1])
    return result


def qualified_prior_promotions(
    source: str, root: Path = ROOT, *, live: bool = False
) -> list[dict[str, Any]]:
    """Historical approval only tightens freezes; it never admits a new publisher.

    Archived artifacts may expire after promotion. Their immutable identity remains
    bound by the durable canonical record, exact successful source/approval runs,
    original source authorization policy and actual non-editable environment review.
    Current publication additionally requires its retained ZIP to remain available.
    """
    from scripts.check_semantic_contract_lifecycle_design import validate_shape

    result = []
    for previous in recorded_promotion_sources(source, root, live=live):
        record = retrieve_attestation(previous)
        validate_shape(record, "authority-promotion-attestation")
        require(
            record["source_commit"] == previous
            and record["qualification"]["source_commit"] == previous,
            "prior promotion source mismatch",
        )
        qualification = record["qualification"]
        run = api(f"actions/runs/{qualification['run_id']}")
        require(
            github._is_qualifying_run(run, sha=previous, branch="main", event="push")
            and run["path"] == ".github/workflows/release-certification.yml"
            and run["repository"]["full_name"] == REPOSITORY
            and run["head_repository"]["full_name"] == REPOSITORY,
            "unverified historical main-push qualification",
        )
        reference = record["human_approval"]
        match = re.fullmatch(
            rf"https://github.com/{REPOSITORY}/actions/runs/([1-9][0-9]*)",
            reference["evidence_url"],
        )
        require(
            match is not None
            and reference["provider"] == "protected-human-environment"
            and reference["reviewed_source_commit"] == previous,
            "unsupported historical promotion approval",
        )
        assert match is not None
        approved_run = api(f"actions/runs/{match[1]}")
        require(
            github._is_qualifying_run(
                approved_run, sha=previous, branch="main", event="workflow_dispatch"
            )
            and approved_run["path"] == WORKFLOW
            and approved_run["repository"]["full_name"] == REPOSITORY
            and approved_run["head_repository"]["full_name"] == REPOSITORY,
            "unverified historical approval run",
        )
        policy_file = api(f"contents/PROJECT.yaml?ref={previous}")
        policy = yaml.safe_load(base64.b64decode(policy_file["content"]).decode("utf-8"))
        actors = {a.removeprefix("@") for a in policy["integrations"]["scm"]["required_approvers"]}
        reviews = api(f"actions/runs/{match[1]}/approvals")
        reviews = [r for r in reviews if any(e["name"] == ENVIRONMENT for e in r["environments"])]
        require(len(reviews) == 1, "missing/ambiguous historical human approval")
        review = reviews[0]
        subject = {k: v for k, v in record.items() if k != "human_approval"}
        require(
            review["state"] == "approved"
            and review["user"]["type"] == "User"
            and review["user"]["login"] == reference["actor"]
            and reference["actor"] in actors
            and review["comment"] == approval_statement(subject),
            "forged historical human approval",
        )
        result.append(record)
    return result


def enforce_promoted(inventory: dict[str, Any], prior: list[dict[str, Any]]) -> None:
    """Released/promoted exact content cannot be replaced at the same identity."""
    current = {(r["family"], r["version"]): r for r in inventory["authorities"]}
    for record in prior:
        for old in record["approved_authorities"]:
            identity = old["family"], old["version"]
            require(identity in current, f"missing previously promoted authority {identity}")
            selected = current[identity]
            require(
                selected["scf"] == old["scf"] and selected["resources"] == old["resources"],
                f"immutable promoted authority changed: {identity}; qualify a successor",
            )


def verify_promotion(
    bundle: Path, source: str, certification: int, root: Path = ROOT
) -> dict[str, Any]:
    evidence = bundle_evidence(bundle, source, certification, root)
    attestation = retrieve_attestation(source)
    expected_subject = {k: v for k, v in attestation.items() if k != "human_approval"}
    require(
        expected_subject == evidence, "attestation differs from exact qualified retained cohort"
    )
    reference = attestation["human_approval"]
    match = re.fullmatch(
        rf"https://github.com/{REPOSITORY}/actions/runs/([1-9][0-9]*)", reference["evidence_url"]
    )
    require(match is not None, "unsupported promotion approval location")
    assert match is not None
    require(
        reference == authorized_approval(evidence, int(match[1]), root), "forged approval reference"
    )
    # Validate the closed accepted contract, in addition to independent live trust.
    # The design helper accepts the exact retained ZIP commitment; operational
    # download_bundle already verified that archive against GitHub's immutable ID.
    require(
        attestation["retained_bundle"]["digest"]
        == qualified_bundle(certification, source)["digest"],
        "changed retained archive",
    )
    from scripts.check_semantic_contract_lifecycle_design import validate_shape

    validate_shape(attestation, "authority-promotion-attestation")
    return {
        "promotion_authorized": True,
        "source_commit": source,
        "inventory_digest": evidence["retained_bundle"]["inventory_digest"],
        "artifact_id": evidence["retained_bundle"]["artifact_id"],
        "approval": reference,
        "attestation_digest": digest(canonical_bytes(attestation)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "prepare", "attest", "verify", "download"))
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--certification-run", type=int)
    parser.add_argument("--promotion-run", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-attestation-digest")
    args = parser.parse_args()
    try:
        if args.command == "inventory":
            verify_source(args.source, ROOT)
            result = create_cohort(args.bundle, args.source)
        else:
            require(args.certification_run is not None, "certification run required")
            if args.command == "download":
                result = download_bundle(args.certification_run, args.source, args.bundle)
            elif args.command == "prepare":
                result = bundle_evidence(args.bundle, args.source, args.certification_run)
                print(approval_statement(result))
            elif args.command == "attest":
                require(args.promotion_run is not None, "promotion run required")
                result = issue_attestation(
                    args.bundle, args.source, args.certification_run, args.promotion_run
                )
            else:
                result = verify_promotion(args.bundle, args.source, args.certification_run)
                if args.expected_attestation_digest:
                    require(
                        result["attestation_digest"] == args.expected_attestation_digest,
                        "promotion attestation changed between publisher stages",
                    )
        if args.output:
            args.output.write_bytes(canonical_bytes(result))
        elif args.command != "prepare":
            print(json.dumps(result, indent=2))
        return 0
    except (
        ValueError,
        RuntimeError,
        OSError,
        KeyError,
        TypeError,
        subprocess.CalledProcessError,
    ) as error:
        parser.exit(1, f"promotion qualification failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
