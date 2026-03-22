from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.adr_kit.compiler import compile_logical_adr_ir_fragments


ADR_SOURCE_PATH = REPO_ROOT / "adrs" / "logical" / "ADR-L-9000-kernel-boot-publication-surface.yaml"
OUTPUT_PATH = REPO_ROOT / "dist" / "architecture-ir" / "adr-ir-fragments.json"
NAMESPACE = "repo:ste-workspace:boot"
LAST_UPDATED = "2026-03-21T00:00:00.000Z"
ARTIFACT_KIND = "logical-adr"


def publish_architecture_ir_fragments(output_path: Path = OUTPUT_PATH) -> Path:
    result = compile_logical_adr_ir_fragments(
        adr_file_paths=[ADR_SOURCE_PATH],
        namespace=NAMESPACE,
        artifact_kind=ARTIFACT_KIND,
        last_updated=LAST_UPDATED,
        scope_root=REPO_ROOT,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result.canonical_fragment_bytes)
    return output_path


def main() -> int:
    output_path = publish_architecture_ir_fragments()
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
