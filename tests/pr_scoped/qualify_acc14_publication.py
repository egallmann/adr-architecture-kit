"""Explicit ACC 1.4 PR boundary; pass actual base/head, never run permanently."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMES = (
    "schema",
    "rules",
    "compatibility",
    "composition-bindings",
    "composition-bindings.schema",
    "conformance",
    "conformance.schema",
)
ALLOWED = {
    "tests/test_authoring_construction_v12_contract.py",
    "tests/test_architecture_interpretation_v13_publication.py",
    "packages/node/test/acc12-publication.test.mjs",
    "packages/node/test/ai13-publication.test.mjs",
    "contracts/authoring-construction/v1.4/contract.json",
    "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.4.json",
    "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.4.json",
    "src/adr_kit/semantic_contract/v1_0/authoring-construction-1.4.json",
    "docs/contributors/acc14-publication.md",
    "scripts/qualify_acc14_publication.py",
    "scripts/generate_semantic_contract_assets.py",
    "scripts/run_pr_feedback.py",
    "src/adr_kit/semantic_contract/__init__.py",
    "packages/node/src/node/semantic-contract.ts",
    "tests/test_authoring_construction_v14_publication.py",
    "tests/test_authoring_construction_v13_publication.py",
    "packages/node/test/acc14-publication.test.mjs",
    "packages/node/test/acc13-publication.test.mjs",
    "tests/pr_scoped/qualify_acc14_publication.py",
}
for name in NAMES:
    ALLOWED.add(
        "contracts/authoring-construction/v1.4/"
        + ("schema.json" if name == "schema" else f"resources/{name}.json")
    )
    for folder in (
        "contracts/semantic-contract/v1.0/resources",
        "src/adr_kit/semantic_contract/v1_0/resources",
    ):
        ALLOWED.add(f"{folder}/authoring-construction-1.4-{name}.json")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")


def validate_changed_paths(paths: list[str]) -> None:
    if outside := sorted(set(paths) - ALLOWED):
        raise ValueError("Outside ACC 1.4 publication PR inventory: " + ", ".join(outside))


def qualify(base: str, head: str) -> dict[str, object]:
    base = git("rev-parse", "--verify", base + "^{commit}").strip()
    head = git("rev-parse", "--verify", head + "^{commit}").strip()
    subprocess.run(["git", "merge-base", "--is-ancestor", base, head], cwd=ROOT, check=True)
    changed = git("diff", "--name-only", base, head).splitlines()
    validate_changed_paths(changed)
    # Every pre-existing authority/schema byte, selected set and runtime file
    # is protected for THIS PR. No permanent test pins future work to this base.
    protected = {}
    for line in git("ls-tree", "-r", base).splitlines():
        meta, path = line.split("\t", 1)
        if path.startswith(
            ("contracts/", "schema/", "src/adr_kit/semantic_contract/v1_0/", "core/")
        ) or path.endswith("semantic-core.wasm"):
            protected[path] = meta.split()[2]
    after = {
        line.split("\t", 1)[1]: line.split()[2] for line in git("ls-tree", "-r", head).splitlines()
    }
    if bad := [path for path, blob in protected.items() if after.get(path) != blob]:
        raise ValueError("Historical authority/selection/runtime bytes changed: " + ", ".join(bad))
    selected = []
    for revision in (base, head):
        tree = ast.parse(git("show", revision + ":src/adr_kit/semantic_contract/__init__.py"))
        function = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "list_semantic_contracts"
        )
        selected.append(ast.dump(function, include_attributes=False))
    if selected[0] != selected[1]:
        raise ValueError("Python selected-contract behavior changed")
    node = []
    for revision in (base, head):
        source = git("show", revision + ":packages/node/src/node/semantic-contract.ts").replace(
            "\r\n", "\n"
        )
        match = re.search(
            r"export function listSemanticContracts\([^)]*\)[^{]*\{.*?^\}",
            source,
            re.MULTILINE | re.DOTALL,
        )
        if match is None:
            raise ValueError("Cannot independently qualify Node selection")
        node.append(match.group())
    if node[0] != node[1]:
        raise ValueError("Node selected-contract behavior changed")
    return {
        "base": base,
        "head": head,
        "changed_files": changed,
        "protected_blobs": len(protected),
        "selection_preserved": True,
        "runtime_preserved": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    print(json.dumps(qualify(args.base, args.head), indent=2))
