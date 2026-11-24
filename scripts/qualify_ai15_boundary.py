"""Explicit revision-scoped AI 1.5 PR boundary; not a permanent Git baseline."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXACT = {
    "scripts/generate_ai15_publication.py",
    "scripts/qualify_ai15_publication.py",
    "scripts/qualify_ai15_boundary.py",
    "scripts/generate_semantic_contract_assets.py",
    "scripts/run_pr_feedback.py",
    "src/adr_kit/semantic_contract/__init__.py",
    "packages/node/src/node/semantic-contract.ts",
    "packages/node/test/ai15-publication.test.mjs",
    "tests/test_architecture_interpretation_v15_publication.py",
    "tests/fixtures/ai15-publication-byte-baseline.json",
    "docs/contributors/ai15-identity-representation-publication.md",
    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.5.json",
    "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.5.json",
    "src/adr_kit/semantic_contract/v1_0/architecture-interpretation-1.5.json",
}
PREFIXES = (
    "contracts/architecture-interpretation/v1.5/",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.5-",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.5-",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")


def qualify(base: str, head: str) -> dict[str, object]:
    base = git("rev-parse", "--verify", base + "^{commit}").strip()
    head = git("rev-parse", "--verify", head + "^{commit}").strip()
    paths = git("diff", "--name-only", base, head).splitlines()
    unexpected = [p for p in paths if p not in EXACT and not p.startswith(PREFIXES)]
    if unexpected:
        raise ValueError("unauthorized changed paths: " + repr(unexpected))
    # Existing execution/selection behavior must not change outside resource lookup.
    for path, start, end in (
        ("src/adr_kit/semantic_contract/__init__.py", "def load_semantic_resource(", "\n__all__"),
        (
            "packages/node/src/node/semantic-contract.ts",
            "export function loadSemanticResource(",
            "",
        ),
    ):
        before, after = (git("show", rev + ":" + path) for rev in (base, head))
        if before.split(start)[0] != after.split(start)[0]:
            raise ValueError("non-resource API or selection changed: " + path)
        if end and before.split(end)[-1] != after.split(end)[-1]:
            raise ValueError("public exports changed: " + path)
    for path in ("scripts/run_pr_feedback.py", "scripts/generate_semantic_contract_assets.py"):
        patch = git("diff", "--unified=0", base, head, "--", path).splitlines()
        removed = [line for line in patch if line.startswith("-") and not line.startswith("---")]
        if removed:
            raise ValueError(
                "historical tooling changed rather than additive registration: " + path
            )
    return {
        "base": base,
        "head": head,
        "changed_files": paths,
        "historical_authorities_selection_runtime_and_WASM": "unchanged",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    print(json.dumps(qualify(args.base, args.head), indent=2))
