"""Generate a normalized repository through ADR-Kit's public compiler API."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests" / "fixtures" / "v1_3" / "logical-minimal.yaml"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from adr_kit.api import CompilationRequest, compile_architecture  # noqa: E402


def generate_repository(output_root: Path, authoring_version: str) -> Path:
    """Compile a minimal authoring corpus and return its emitted entity registry."""

    if authoring_version not in {"1.4", "1.5"}:
        raise ValueError(f"unsupported authoring version: {authoring_version}")

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "PROJECT.yaml").write_text(
        'schema_version: "1.0"\n'
        "type: project_metadata\n"
        "project:\n"
        "  name: conformance-fixture\n"
        "architecture_documentation:\n"
        "  architecture_namespace: conformance-fixture\n",
        encoding="utf-8",
    )
    logical_dir = output_root / "adrs" / "logical"
    logical_dir.mkdir(parents=True, exist_ok=True)
    source = SOURCE.read_text(encoding="utf-8")
    source = source.replace('schema_version: "1.3"', f'schema_version: "{authoring_version}"')
    source = source.replace("v1.3", f"v{authoring_version}")
    (logical_dir / "minimal.yaml").write_text(source, encoding="utf-8")

    result = compile_architecture(
        CompilationRequest(
            project_root=output_root,
            write=True,
            timestamp="2026-09-05T00:00:00Z",
        )
    )
    if not result.success:
        diagnostics = "; ".join(item.message for item in result.diagnostics)
        raise RuntimeError(f"compiler failed: {diagnostics}")
    return output_root / "adrs" / "index" / "entity-registry.yaml"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("authoring_version", choices=("1.4", "1.5"))
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    generate_repository(args.output_root, args.authoring_version)


if __name__ == "__main__":
    main()
