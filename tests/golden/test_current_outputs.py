from __future__ import annotations

import yaml

from tests.golden.helpers import GOLDEN_KEYS, generate_deterministic_outputs


def _expected_dir():
    return __import__("pathlib").Path(__file__).resolve().parent / "expected"


def _repo_root():
    return __import__("pathlib").Path(__file__).resolve().parents[2]


def _load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_current_outputs_match_expected_semantically(tmp_path):
    generated_paths = generate_deterministic_outputs(_repo_root(), tmp_path / "workspace")
    expected_dir = _expected_dir()

    for key in GOLDEN_KEYS:
        expected_path = expected_dir / f"{key}.yaml"
        assert expected_path.exists(), f"Missing golden snapshot: {expected_path}"
        assert _load_yaml(generated_paths[key]) == _load_yaml(expected_path), key


def test_current_outputs_match_expected_bytes(tmp_path):
    generated_paths = generate_deterministic_outputs(_repo_root(), tmp_path / "workspace")
    expected_dir = _expected_dir()

    for key in GOLDEN_KEYS:
        expected_bytes = (expected_dir / f"{key}.yaml").read_bytes()
        actual_bytes = generated_paths[key].read_bytes()
        assert actual_bytes == expected_bytes, key


def test_deterministic_generation_is_byte_identical(tmp_path):
    first_paths = generate_deterministic_outputs(_repo_root(), tmp_path / "run-one")
    second_paths = generate_deterministic_outputs(_repo_root(), tmp_path / "run-two")

    for key in GOLDEN_KEYS:
        assert first_paths[key].read_bytes() == second_paths[key].read_bytes(), key
