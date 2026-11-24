"""Current-candidate PR-only preservation gate. Explicit revisions, no permanent base."""

from __future__ import annotations

import argparse
import json
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
EXISTING = {
    "tests/test_semantic_contract_lifecycle_design.py",
    "tests/test_architecture_interpretation_v15_publication.py",
    "tests/fixtures/ai15-publication-byte-baseline.json",
    "packages/node/test/ai15-publication.test.mjs",
    "scripts/generate_ai15_publication.py",
    "scripts/qualify_ai15_publication.py",
    "scripts/generate_semantic_contract_assets.py",
    "scripts/run_pr_feedback.py",
    "src/adr_kit/semantic_contract/__init__.py",
    "packages/node/src/node/semantic-contract.ts",
    "contracts/architecture-interpretation/v1.5/contract.json",
    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.5.json",
    "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.5.json",
    "src/adr_kit/semantic_contract/v1_0/architecture-interpretation-1.5.json",
}
for schema in (
    "rules",
    "required-output-derivations",
    "identity-representation-recipes",
    "conformance",
    "required-output-derivations.schema",
    "identity-representation-recipes.schema",
    "conformance.schema",
):
    EXISTING.add("contracts/architecture-interpretation/v1.5/resources/" + schema + ".json")
    for directory in (
        "contracts/semantic-contract/v1.0/resources",
        "src/adr_kit/semantic_contract/v1_0/resources",
    ):
        EXISTING.add(directory + "/architecture-interpretation-1.5-" + schema + ".json")
ALLOWED = EXISTING | {
    "tests/test_candidate_schema_selectors.py",
    "tests/test_candidate_lineage_selection.py",
    "scripts/candidate_contract_assets.py",
    "tests/test_current_candidate_assets.py",
    "scripts/generate_acc15_publication.py",
    "scripts/qualify_acc15_publication.py",
    "tests/pr_scoped/qualify_acc15_publication.py",
    "tests/test_authoring_construction_v15_publication.py",
    "tests/fixtures/acc15-publication-byte-baseline.json",
    "packages/node/test/acc15-publication.test.mjs",
    "docs/contributors/acc15-publication.md",
    "contracts/authoring-construction/v1.5/contract.json",
    "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.5.json",
    "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.5.json",
    "src/adr_kit/semantic_contract/v1_0/authoring-construction-1.5.json",
}
for name in NAMES:
    ALLOWED.add(
        "contracts/authoring-construction/v1.5/"
        + ("schema.json" if name == "schema" else "resources/" + name + ".json")
    )
    for folder in (
        "contracts/semantic-contract/v1.0/resources",
        "src/adr_kit/semantic_contract/v1_0/resources",
    ):
        ALLOWED.add(folder + "/authoring-construction-1.5-" + name + ".json")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")


def qualify(base: str, head: str) -> dict[str, object]:
    base, head = (
        git("rev-parse", "--verify", revision + "^{commit}").strip() for revision in (base, head)
    )
    subprocess.run(["git", "merge-base", "--is-ancestor", base, head], cwd=ROOT, check=True)
    changed = git("diff", "--name-only", base, head).splitlines()
    if bad := set(changed) - ALLOWED:
        raise ValueError("Outside current candidate checkpoint inventory: " + repr(sorted(bad)))
    before = {
        line.split("\t", 1)[1]: line.split()[2] for line in git("ls-tree", "-r", base).splitlines()
    }
    after = {
        line.split("\t", 1)[1]: line.split()[2] for line in git("ls-tree", "-r", head).splitlines()
    }
    protected = {p: h for p, h in before.items() if p not in EXISTING}
    if altered := [p for p, h in protected.items() if after.get(p) != h]:
        raise ValueError("Historical/selection/runtime files changed: " + repr(altered))
    for path, start, end in (
        ("src/adr_kit/semantic_contract/__init__.py", "def load_semantic_resource(", "\n__all__"),
        (
            "packages/node/src/node/semantic-contract.ts",
            "export function loadSemanticResource(",
            "",
        ),
    ):
        old, new = (git("show", rev + ":" + path) for rev in (base, head))
        if old.split(start)[0] != new.split(start)[0] or (
            end and old.split(end)[-1] != new.split(end)[-1]
        ):
            raise ValueError("Non-discovery API/current selection changed: " + path)
    for path in ("scripts/generate_semantic_contract_assets.py", "scripts/run_pr_feedback.py"):
        patch = git("diff", "--unified=0", base, head, "--", path).splitlines()
        if any(line.startswith("-") and not line.startswith("---") for line in patch):
            raise ValueError(
                "Historical tooling modified rather than additive registration: " + path
            )
    return {
        "base": base,
        "head": head,
        "changed_files": changed,
        "protected_blobs": len(protected),
        "historical_authorities_current_selection_runtime_protocol_and_WASM": "unchanged",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    print(json.dumps(qualify(args.base, args.head), indent=2))
