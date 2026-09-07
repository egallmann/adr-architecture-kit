"""Compatibility wrappers for the public attribution-shim operation.

The renderer was moved behind the canonical semantic-core boundary. These
names remain for existing internal callers and tests, but they no longer own a
second Python implementation of the generated source.
"""

from __future__ import annotations

from typing import Literal, cast

from .api import AttributionShimRequest, generate_attribution_shim


def generate_shim(language: str) -> str:
    """Return generated shim source through the supported Python API."""

    return generate_attribution_shim(
        AttributionShimRequest(cast(Literal["python", "typescript"], language))
    ).content


def generate_python_shim() -> str:
    """Compatibility alias for ``generate_shim(\"python\")``."""

    return generate_shim("python")


def generate_typescript_shim() -> str:
    """Compatibility alias for ``generate_shim(\"typescript\")``."""

    return generate_shim("typescript")
