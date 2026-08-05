"""Functional contract for deterministic Phase 0 benchmark scaffolding."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase0_benchmark_smoke_is_deterministic(tmp_path: Path) -> None:
    script = ROOT / "benchmarks" / "phase0.py"
    assert script.is_file(), "missing Phase 0 benchmark harness"
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    command = [
        sys.executable,
        str(script),
        "--corpus",
        "synthetic",
        "--sizes",
        "2",
        "--warmups",
        "0",
        "--repeats",
        "1",
    ]
    for output in (first, second):
        result = subprocess.run(
            [*command, "--json-out", str(output)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    first_payload = json.loads(first.read_text(encoding="utf-8"))
    second_payload = json.loads(second.read_text(encoding="utf-8"))
    assert first_payload["fingerprints"] == second_payload["fingerprints"]
    assert first_payload["deterministic"] is True
    for stage in (
        "schema_validation",
        "parsing",
        "normalization",
        "extraction",
        "relationship_derivation",
        "registry_generation",
        "graph_generation",
        "serialization",
        "filesystem_writes",
        "full_compilation",
        "repository_loading",
        "representative_queries",
    ):
        assert stage in first_payload["results"][0]["stages"]
