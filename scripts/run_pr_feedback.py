"""Run the explicit semantic/source test collection for pull requests.

This collection is intentionally maintained by semantic responsibility rather
than by a broad filename exclusion.  It exercises the Python public surface,
the contract/schema boundary, repository behavior, and Python/TypeScript
consumer-facing parity early in review.  The complete suite remains an
integration and release assurance responsibility.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Keep this list explicit.  A new public or contract-facing subsystem must be
# added here deliberately; silently relying on a naming convention would make
# the PR gate look fast while allowing a semantic surface to go untested.
SEMANTIC_TESTS: tuple[str, ...] = (
    "tests/test_import_namespace.py",
    "tests/test_version_authority.py",
    "tests/test_schema_contract_taxonomy.py",
    "tests/test_schema_validation.py",
    "tests/test_schema_v12.py",
    "tests/test_schema_v13.py",
    "tests/test_kernel_contract_schemas.py",
    "tests/test_kernel_contract_validation.py",
    "tests/test_semantic_core_protocol.py",
    "tests/test_semantic_core_conformance.py",
    "tests/test_semantic_adapter.py",
    "tests/test_public_sdk_contract.py",
    "tests/test_public_sdk_governance.py",
    "tests/test_public_sdk_operations.py",
    "tests/test_host_capability_parity.py",
    "tests/test_consumer_binding_conformance.py",
    "tests/test_consumer_binding_vocabulary_versions.py",
    "tests/test_authoring_v15_contract.py",
    "tests/test_authoring_v15_runtime.py",
    "tests/test_normalized_entity_serialization_conformance.py",
    "tests/test_normalized_model_v2.py",
    "tests/test_normalized_v22_runtime.py",
    "tests/test_architecture_repository.py",
    "tests/test_entity_validator.py",
    "tests/test_adr_validator.py",
    "tests/test_architecture_ir_publication.py",
    "tests/test_phase0_compatibility.py",
    "tests/test_compatibility_resource_parity.py",
    "tests/test_scope_resolver.py",
    "tests/test_canonical_id_normalizer.py",
)


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "pytest",
        *SEMANTIC_TESTS,
        "--durations=30",
        "-q",
    ]
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, cwd=REPO_ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
