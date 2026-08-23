"""Tests for exact-version npm publication idempotence."""

from __future__ import annotations

import base64
import hashlib

import pytest

from scripts.check_npm_publication import NpmPublicationError, decide_publication


def _integrity(payload: bytes) -> str:
    digest = hashlib.sha512(payload).digest()
    return "sha512-" + base64.b64encode(digest).decode("ascii")


def test_missing_package_or_version_requires_publication() -> None:
    integrity = _integrity(b"qualified tarball")
    assert decide_publication(
        package_name="@system-of-thought/adr-kit",
        package_version="0.6.0",
        tarball_integrity=integrity,
        metadata=None,
    ) == "publish"
    assert decide_publication(
        package_name="@system-of-thought/adr-kit",
        package_version="0.6.0",
        tarball_integrity=integrity,
        metadata={"versions": {}},
    ) == "publish"


def test_exact_existing_version_is_an_intentional_noop() -> None:
    integrity = _integrity(b"qualified tarball")
    assert decide_publication(
        package_name="@system-of-thought/adr-kit",
        package_version="0.6.0",
        tarball_integrity=integrity,
        metadata={"versions": {"0.6.0": {"dist": {"integrity": integrity}}}},
    ) == "noop"


def test_mismatched_existing_version_fails_closed() -> None:
    with pytest.raises(NpmPublicationError, match="does not match"):
        decide_publication(
            package_name="@system-of-thought/adr-kit",
            package_version="0.6.0",
            tarball_integrity=_integrity(b"qualified tarball"),
            metadata={
                "versions": {
                    "0.6.0": {"dist": {"integrity": _integrity(b"different tarball")}}
                }
            },
        )


def test_existing_version_without_integrity_fails_closed() -> None:
    with pytest.raises(NpmPublicationError, match="does not match"):
        decide_publication(
            package_name="@system-of-thought/adr-kit",
            package_version="0.6.0",
            tarball_integrity=_integrity(b"qualified tarball"),
            metadata={"versions": {"0.6.0": {"dist": {}}}},
        )
