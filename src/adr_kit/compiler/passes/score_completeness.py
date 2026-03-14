"""Completeness scoring pass helper."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.architecture_discovery import Completeness


@dataclass(frozen=True)
class ScoreCompletenessPass:
    """Pass-shaped helper for completeness scoring."""

    name = "score_completeness"
    required = True
    depends_on: tuple[str, ...] = ()
    halts_on_error = False

    def run(self, missing_fields: list[str] | None = None) -> Completeness:
        return score_completeness(missing_fields)


def score_completeness(missing_fields: list[str] | None = None) -> Completeness:
    """Preserve current generator completeness semantics exactly."""

    missing = missing_fields or []
    return Completeness(status="complete" if not missing else "partial", missing_fields=missing)
