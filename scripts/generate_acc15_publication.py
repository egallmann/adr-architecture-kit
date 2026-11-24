"""Derive current candidate views from canonical inputs; never author semantic rules."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.candidate_contract_assets import assemble, distribute
from scripts.qualify_acc15_publication import qualify

ROOT = Path(__file__).resolve().parents[1]


def publish(root: Path = ROOT) -> None:
    result, contents = assemble(root, "authoring-construction")
    # The proposed definition receives complete independent semantic, schema,
    # manifest and closure qualification BEFORE any derived view is replaced.
    report = qualify(root, candidate_definition=result)
    distribute(root, "authoring-construction", result, contents)
    print(
        json.dumps(
            {"SCF": result["semanticContractFingerprint"], "resources": len(contents), **report},
            indent=2,
        )
    )


if __name__ == "__main__":
    publish()
