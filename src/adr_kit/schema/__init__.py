"""Schema utilities for derived contract artifacts."""

from typing import Any

__all__ = [
    "ImplementationAttributionIssue",
    "ImplementationAttributionValidationResult",
    "normalize_attribution_evidence",
    "validate_implementation_attribution_evidence",
]


def __getattr__(name: str) -> Any:
    if name in {
        "ImplementationAttributionIssue",
        "ImplementationAttributionValidationResult",
        "validate_implementation_attribution_evidence",
    }:
        from .implementation_attribution_validation import (
            ImplementationAttributionIssue,
            ImplementationAttributionValidationResult,
            validate_implementation_attribution_evidence,
        )

        mapping = {
            "ImplementationAttributionIssue": ImplementationAttributionIssue,
            "ImplementationAttributionValidationResult": ImplementationAttributionValidationResult,
            "validate_implementation_attribution_evidence": validate_implementation_attribution_evidence,
        }
        return mapping[name]
    if name == "normalize_attribution_evidence":
        from adr_kit.semantic_attribution.normalize import normalize_attribution_evidence

        return normalize_attribution_evidence
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
