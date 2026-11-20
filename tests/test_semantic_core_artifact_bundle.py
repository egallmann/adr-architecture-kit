"""Commit and byte identity for semantic-core artifact fanout."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.semantic_core_artifact_bundle import (
    ARTIFACT_DESTINATIONS,
    WASM_NAME,
    consume_bundle,
    create_bundle,
    create_bootstrap_bundle,
    install_bootstrap_bundle,
)

pytestmark = pytest.mark.fast

COMMIT = "bcc299cffea4fd0355a7e2edf908036f16900602"


def test_bundle_fans_out_exact_commit_bound_bytes(tmp_path: Path) -> None:
    wasm = b"source-built wasm bytes"
    artifact = tmp_path / "built.wasm"
    artifact.write_bytes(wasm)
    bundle = tmp_path / "bundle"
    manifest = create_bundle(artifact, bundle, COMMIT)
    checkout = tmp_path / "checkout"

    consumed = consume_bundle(bundle, COMMIT, checkout)

    assert consumed == manifest
    assert json.loads((bundle / "manifest.json").read_text(encoding="utf-8")) == manifest
    for relative_path in ARTIFACT_DESTINATIONS:
        assert (checkout / relative_path).read_bytes() == wasm
    assert (bundle / WASM_NAME).read_bytes() == wasm


def test_bundle_rejects_an_artifact_from_another_commit_before_writing(tmp_path: Path) -> None:
    artifact = tmp_path / "built.wasm"
    artifact.write_bytes(b"qualified artifact")
    bundle = tmp_path / "bundle"
    create_bundle(artifact, bundle, COMMIT)
    checkout = tmp_path / "checkout"

    with pytest.raises(ValueError, match="source commit"):
        consume_bundle(bundle, "a" * 40, checkout)

    assert not checkout.exists()


def test_bundle_rejects_tampered_bytes_before_writing(tmp_path: Path) -> None:
    artifact = tmp_path / "built.wasm"
    artifact.write_bytes(b"qualified artifact")
    bundle = tmp_path / "bundle"
    create_bundle(artifact, bundle, COMMIT)
    (bundle / WASM_NAME).write_bytes(b"tampered artifact")
    checkout = tmp_path / "checkout"

    with pytest.raises(ValueError, match="do not match"):
        consume_bundle(bundle, COMMIT, checkout)

    assert not checkout.exists()


def test_bootstrap_is_explicitly_unqualified_and_installs_only_host_copies(tmp_path: Path) -> None:
    artifact = tmp_path / "linux-built.wasm"
    artifact.write_bytes(b"Linux source build")
    bundle = tmp_path / "bootstrap"
    manifest = create_bootstrap_bundle(artifact, bundle, COMMIT)
    checkout = tmp_path / "checkout"

    installed = install_bootstrap_bundle(bundle, COMMIT, checkout)

    assert installed == manifest
    assert manifest["qualification"] == "UNQUALIFIED"
    assert manifest["source_commit"] == COMMIT
    assert manifest["size_bytes"] == len(artifact.read_bytes())
    for relative_path in ARTIFACT_DESTINATIONS[1:]:
        assert (checkout / relative_path).read_bytes() == artifact.read_bytes()
    assert not (checkout / ARTIFACT_DESTINATIONS[0]).exists()
    with pytest.raises(ValueError, match="unexpected shape"):
        consume_bundle(bundle, COMMIT, checkout)


@pytest.mark.parametrize("failure", ["commit", "bytes"])
def test_bootstrap_rejects_wrong_commit_or_tampering_before_writing(
    tmp_path: Path, failure: str
) -> None:
    artifact = tmp_path / "linux-built.wasm"
    artifact.write_bytes(b"Linux source build")
    bundle = tmp_path / "bootstrap"
    create_bootstrap_bundle(artifact, bundle, COMMIT)
    if failure == "bytes":
        (bundle / WASM_NAME).write_bytes(b"tampered")
    checkout = tmp_path / "checkout"

    with pytest.raises(
        ValueError, match="source commit" if failure == "commit" else "do not match"
    ):
        install_bootstrap_bundle(bundle, "a" * 40 if failure == "commit" else COMMIT, checkout)
    assert not checkout.exists()
