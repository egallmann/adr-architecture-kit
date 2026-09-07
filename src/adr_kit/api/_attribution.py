"""Public attribution-shim operation backed by the canonical semantic core."""

from __future__ import annotations

from hashlib import sha256
from typing import Any, cast

from .. import __version__
from ..core import execute_attribution_shim_generation
from ..semantic_attribution.vocabulary import shim_vocabulary
from ._contracts import (
    API_CONTRACT_VERSION,
    AttributionShimRequest,
    AttributionShimResult,
    Diagnostic,
)
from ._errors import OperationError


def _diagnostic_from(value: object) -> Diagnostic:
    item = value if isinstance(value, dict) else {}
    severity = str(item.get("severity", "error"))
    if severity not in {"info", "warning", "error"}:
        severity = "error"
    return Diagnostic(
        severity=cast(Any, severity),
        code=str(item.get("code", "attribution_shim.invalid_request")),
        message=str(item.get("message", "attribution shim generation failed")),
        path=str(item["path"]) if item.get("path") is not None else None,
    )


def generate_attribution_shim(request: AttributionShimRequest) -> AttributionShimResult:
    """Generate a deterministic Python or TypeScript attribution shim.

    The host only loads the canonical vocabulary and maps the immutable public
    request into the semantic-core transport contract. Rendering and all
    byte-sensitive source semantics remain in the shared core.
    """

    if not isinstance(request, AttributionShimRequest):
        raise TypeError("request must be an AttributionShimRequest")
    try:
        core_result = execute_attribution_shim_generation(
            language=request.language,
            vocabulary=shim_vocabulary(),
        )
    except Exception as exc:
        raise OperationError("Attribution shim generation could not complete") from exc

    diagnostics = tuple(_diagnostic_from(item) for item in core_result.get("diagnostics", []))
    if not core_result.get("success", False):
        message = (
            "; ".join(item.message for item in diagnostics) or "attribution shim generation failed"
        )
        raise OperationError(message)
    content = core_result.get("content")
    language = core_result.get("language")
    if not isinstance(content, str) or language != request.language:
        raise OperationError("Semantic core returned an invalid attribution shim result")
    return AttributionShimResult(
        request=request,
        success=True,
        language=cast(Any, language),
        content=content,
        sha256=sha256(content.encode("utf-8")).hexdigest(),
        diagnostics=diagnostics,
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
    )
