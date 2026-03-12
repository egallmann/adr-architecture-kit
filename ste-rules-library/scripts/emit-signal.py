#!/usr/bin/env python3
"""
Emit cooperative signals for agent coordination.
Authority: adr-architecture-kit ADR-L-0006, ste-rules-library ADR-L-0001.
Schema: schema/signal.schema.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root() -> Path:
    """Find consumer project root (where .codex or .cursor exists)."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".codex").exists() or (parent / ".cursor").exists():
            return parent
        if (parent / "ste-rules-library").exists():
            return parent
    return cwd


def _signal_dir(workspace: str = "codex") -> Path:
    root = _find_repo_root()
    return root / f".{workspace}" / "signals"


def emit(
    signal_type: str,
    adr_id: str,
    component_id: str | None = None,
    agent: str = "codex",
    metadata: dict | None = None,
    workspace: str = "codex",
) -> Path:
    """Emit a cooperative signal. Returns path to written file."""
    valid_types = ("claim", "progress", "complete", "wave_complete", "validation_ready")
    if signal_type not in valid_types:
        raise ValueError(f"signal_type must be one of {valid_types}")

    signal = {
        "signal_type": signal_type,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent": agent,
    }
    if adr_id:
        signal["adr_id"] = adr_id
    if component_id:
        signal["component_id"] = component_id
    if metadata:
        signal["metadata"] = metadata

    base = _signal_dir(workspace) / adr_id
    base.mkdir(parents=True, exist_ok=True)

    if signal_type == "wave_complete":
        wave_num = (metadata or {}).get("wave_num", 1)
        filename = f"wave-{wave_num}.complete.json"
    elif signal_type == "validation_ready":
        filename = "validation-ready.json"
    elif component_id:
        filename = f"{component_id}.{signal_type}.json"
    else:
        filename = f"{signal_type}.json"

    path = base / filename
    path.write_text(json.dumps(signal, indent=2))
    return path


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Emit cooperative signal")
    p.add_argument("signal_type", choices=["claim", "progress", "complete", "wave_complete", "validation_ready"])
    p.add_argument("adr_id", help="ADR ID (e.g. ADR-P-0004)")
    p.add_argument("--component", "-c", help="Component ID (e.g. COMP-0005)")
    p.add_argument("--agent", "-a", default="codex", choices=["codex", "cursor", "claude", "gpt"])
    p.add_argument("--workspace", "-w", default="codex", choices=["codex", "cursor"])
    p.add_argument("--metadata", "-m", type=json.loads, default={}, help="JSON metadata")
    args = p.parse_args()

    try:
        path = emit(
            signal_type=args.signal_type,
            adr_id=args.adr_id,
            component_id=args.component,
            agent=args.agent,
            metadata=args.metadata,
            workspace=args.workspace,
        )
        print(f"Emitted: {path}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
