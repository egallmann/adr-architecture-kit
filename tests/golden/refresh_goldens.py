from __future__ import annotations

import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.golden.helpers import GOLDEN_KEYS, generate_deterministic_outputs


def main() -> int:
    repo_root = REPO_ROOT
    expected_dir = Path(__file__).resolve().parent / "expected"
    temp_root = Path(__file__).resolve().parent / ".tmp-refresh"

    if temp_root.exists():
        shutil.rmtree(temp_root)
    if expected_dir.exists():
        shutil.rmtree(expected_dir)

    generated = generate_deterministic_outputs(repo_root, temp_root / "workspace")
    expected_dir.mkdir(parents=True, exist_ok=True)
    for key in GOLDEN_KEYS:
        shutil.copy2(generated[key], expected_dir / f"{key}.yaml")

    shutil.rmtree(temp_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
