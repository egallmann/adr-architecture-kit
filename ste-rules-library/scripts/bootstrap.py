#!/usr/bin/env python3
"""
Bootstrap ste-rules-library for consumer projects.
Authority: ADR-L-0001. Creates signal directories and integration snippet.
Assumes ste-rules-library is available as a sibling workspace folder.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _find_consumer_root() -> Path:
    """Find consumer project root (caller's cwd or parent with ste-rules-library)."""
    cwd = Path.cwd()
    if (cwd / "ste-rules-library").exists():
        return cwd
    if cwd.name == "ste-rules-library":
        return cwd.parent
    return cwd


def bootstrap() -> int:
    root = _find_consumer_root()
    lib = root / "ste-rules-library"
    if not lib.exists():
        print(
            "ste-rules-library folder not found. Run from a consumer project root "
            "that has a sibling ste-rules-library checkout.",
            file=sys.stderr,
        )
        return 1

    # Create signal directories
    for ws in (".codex", ".cursor"):
        sig_dir = root / ws / "signals"
        sig_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created: {sig_dir}")

    # Output integration instructions
    snippet = root / "ste-rules-library" / "integration-snippet.md"
    content = """# ste-rules-library Integration

## Signal Emission

Agents can emit cooperative signals via:

```bash
python ste-rules-library/scripts/emit-signal.py claim ADR-P-0004 --component COMP-0005 --agent codex
python ste-rules-library/scripts/emit-signal.py complete ADR-P-0004 --component COMP-0005 --agent codex
```

## Signal Schema

Schema: `ste-rules-library/schema/signal.schema.json`

Types: claim, progress, complete, wave_complete, validation_ready
"""
    snippet.write_text(content)
    print(f"Created: {snippet}")

    print("Bootstrap complete.")
    return 0


if __name__ == "__main__":
    sys.exit(bootstrap())
