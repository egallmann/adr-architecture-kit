"""Install the adr-architecture-kit pre-push hook into .git/hooks."""

from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_HOOK = REPO_ROOT / ".githooks" / "pre-push"
TARGET_HOOK = REPO_ROOT / ".git" / "hooks" / "pre-push"


def main() -> int:
    if not SOURCE_HOOK.exists():
        raise FileNotFoundError(f"Missing source hook: {SOURCE_HOOK}")
    if not TARGET_HOOK.parent.exists():
        raise FileNotFoundError(f"Git hooks directory not found: {TARGET_HOOK.parent}")

    shutil.copyfile(SOURCE_HOOK, TARGET_HOOK)
    TARGET_HOOK.chmod(0o755)
    print(f"Installed pre-push hook: {TARGET_HOOK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
