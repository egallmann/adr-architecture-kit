from __future__ import annotations

from pathlib import Path

from tests.golden.helpers import GOLDEN_KEYS, generate_deterministic_outputs

REPO_ROOT = Path(__file__).resolve().parents[2]


def _normalize_newlines(data: bytes) -> bytes:
    """Git may check out tracked projections with CRLF on Windows."""
    return data.replace(b"\r\n", b"\n")


def test_current_outputs_are_fresh_and_deterministic(tmp_path: Path) -> None:
    first_paths = generate_deterministic_outputs(REPO_ROOT, tmp_path / "run-one")
    second_paths = generate_deterministic_outputs(REPO_ROOT, tmp_path / "run-two")
    for key in GOLDEN_KEYS:
        if key == "legacy_entity_registry":
            expected = REPO_ROOT / "tests/golden/expected/legacy_entity_registry.yaml"
        elif key == "manifest":
            expected = REPO_ROOT / "adrs/manifest.yaml"
        else:
            expected = REPO_ROOT / "adrs/index" / f"{key.replace('_', '-')}.yaml"

        assert expected.is_file(), f"Missing expected output: {expected}"
        first_bytes = first_paths[key].read_bytes()
        assert first_bytes == second_paths[key].read_bytes(), f"Nondeterministic output: {key}"
        assert _normalize_newlines(first_bytes) == _normalize_newlines(
            expected.read_bytes()
        ), f"Stale or changed output: {expected}"
