from __future__ import annotations

import pytest

from adr_kit.api import AttributionShimRequest, InvalidRequestError, generate_attribution_shim


@pytest.mark.parametrize(
    ("language", "length", "digest"),
    [
        ("PYTHON", 7043, "f73973e57552e4a1fe11d3a849c7e69d1f69efd6234dba1722143277250e8779"),
        (" TypeScript ", 1474, "e678b77b69c777d8e44fb063141db040e5153e36768e73da7911e9e8d4da0449"),
    ],
)
def test_public_attribution_shim_is_deterministic_and_immutable(
    language: str, length: int, digest: str
) -> None:
    result = generate_attribution_shim(AttributionShimRequest(language))
    assert result.success is True
    assert result.language == language.strip().lower()
    assert len(result.content) == length
    assert result.sha256 == digest
    assert result.content.encode("utf-8")


def test_public_attribution_shim_request_rejects_unsupported_language() -> None:
    with pytest.raises(InvalidRequestError, match="Unsupported shim language"):
        AttributionShimRequest("rust")
