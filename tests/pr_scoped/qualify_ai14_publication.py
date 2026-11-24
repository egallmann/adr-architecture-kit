"""Explicit PR #181 boundary check; never part of permanent PR Feedback tests.

Pass the actual PR base/head revisions. Future authorized publication/runtime
work is not subject to this publication-only allowlist unless explicitly invoked.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMES = (
    "rules",
    "required-output-derivations",
    "required-output-derivations.schema",
    "conformance",
    "conformance.schema",
)
ALLOWED = {
    "contracts/architecture-interpretation/v1.4/contract.json",
    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.4.json",
    "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.4.json",
    "src/adr_kit/semantic_contract/v1_0/architecture-interpretation-1.4.json",
    "docs/contributors/ai14-required-output-authority.md",
    "packages/node/src/node/semantic-contract.ts",
    "packages/node/test/ai13-publication.test.mjs",
    "packages/node/test/ai14-publication.test.mjs",
    "scripts/generate_semantic_contract_assets.py",
    "scripts/qualify_ai14_publication.py",
    "scripts/run_pr_feedback.py",
    "src/adr_kit/semantic_contract/__init__.py",
    "tests/test_architecture_interpretation_v13_publication.py",
    "tests/test_architecture_interpretation_v14_publication.py",
    "tests/pr_scoped/qualify_ai14_publication.py",
}
for name in NAMES:
    ALLOWED.add(f"contracts/architecture-interpretation/v1.4/resources/{name}.json")
    for directory in (
        "contracts/semantic-contract/v1.0/resources",
        "src/adr_kit/semantic_contract/v1_0/resources",
    ):
        ALLOWED.add(f"{directory}/architecture-interpretation-1.4-{name}.json")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")


def validate_changed_paths(paths: list[str]) -> None:
    forbidden = sorted(set(paths) - ALLOWED)
    if forbidden:
        raise ValueError("Outside PR #181 allowlist: " + ", ".join(forbidden))


def validate_cleanup_paths(paths: list[str]) -> None:
    allowed = {
        "tests/test_architecture_interpretation_v14_publication.py",
        "packages/node/test/ai14-publication.test.mjs",
        "tests/pr_scoped/qualify_ai14_publication.py",
    }
    if set(paths) - allowed:
        raise ValueError("Cleanup changed a non-test publication file")


def qualify(base: str, head: str, reviewed_head: str | None = None) -> dict[str, object]:
    base = git("rev-parse", "--verify", base + "^{commit}").strip()
    head = git("rev-parse", "--verify", head + "^{commit}").strip()
    subprocess.run(["git", "merge-base", "--is-ancestor", base, head], cwd=ROOT, check=True)
    changed = git("diff", "--name-only", base, head).splitlines()
    validate_changed_paths(changed)
    cleanup: list[str] | None = None
    if reviewed_head is not None:
        reviewed_head = git("rev-parse", "--verify", reviewed_head + "^{commit}").strip()
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", reviewed_head, head], cwd=ROOT, check=True
        )
        cleanup = git("diff", "--name-only", reviewed_head, head).splitlines()
        validate_cleanup_paths(cleanup)
    # Selection data is PR-scoped; a future explicitly selected AI 1.4 is valid.
    for directory in (
        "current",
        "sets",
        "catalog",
        "policy",
        "profiles",
        "qualifications",
    ):
        for root in ("contracts/semantic-contract/v1.0", "src/adr_kit/semantic_contract/v1_0"):
            path = root + "/" + directory
            if git("ls-tree", "-r", base, "--", path) != git("ls-tree", "-r", head, "--", path):
                raise ValueError("Current PR changed selection assets: " + path)
    python_path = "src/adr_kit/semantic_contract/__init__.py"
    selected = []
    for revision in (base, head):
        tree = ast.parse(git("show", revision + ":" + python_path))
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "list_semantic_contracts"
        )
        selected.append(ast.dump(function, include_attributes=False))
    if selected[0] != selected[1]:
        raise ValueError("Current PR changed Python selection logic")
    node_path = "packages/node/src/node/semantic-contract.ts"
    selected_node = []
    for revision in (base, head):
        source = git("show", revision + ":" + node_path).replace("\r\n", "\n")
        function = re.search(
            r"export function listSemanticContracts\([^)]*\)[^{]*\{.*?^\}",
            source,
            re.MULTILINE | re.DOTALL,
        )
        if function is None:
            raise ValueError("Cannot independently inspect Node selection logic")
        selected_node.append(function.group())
    if selected_node[0] != selected_node[1]:
        raise ValueError("Current PR changed Node selection logic")
    return {
        "base": base,
        "head": head,
        "changed_files": changed,
        "selection_preserved": True,
        "reviewed_head": reviewed_head,
        "cleanup_changed_files": cleanup,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--reviewed-head")
    arguments = parser.parse_args()
    print(json.dumps(qualify(arguments.base, arguments.head, arguments.reviewed_head), indent=2))
