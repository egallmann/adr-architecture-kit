"""Provider-side scoped amendment embodiment checks (deterministic, fail-closed)."""

from __future__ import annotations

from typing import Any

ANNOTATION_ONLY_MARKER = "v1.3 identity promotion scope recorded"

_IDENTITY_V13_JOURNAL = "DJ-adr-kit-canonical-entity-identity-v13"

# Required semantic markers derived from locked A-N2 mutation map (not free-form LLM prose).
_MUTATION_MARKERS: dict[str, tuple[str, ...]] = {
    "M-02": (
        "alias",
        "uuid",
        "canonical machine identity",
    ),
    "M-03": (
        "architecture_namespace",
        "uuid",
        "routing",
    ),
    "M-04": (
        "model 2.0",
        "uuid",
        "alias",
    ),
    "M-05": (
        "model 2.0",
        "uuid",
        "alias",
        "fail closed",
    ),
    "M-06": ("phase 2.5",),
    "M-07": (
        "alias",
        "uuid",
    ),
}

_FORBIDDEN_ACTIVE_CONTRADICTIONS: dict[str, tuple[str, ...]] = {
    "M-02": ("graph node identity requires unique ids",),
    "M-03": ("workspacerepokey:adr-l-",),
    "M-07": ("adr identifiers are architectural identity",),
}


def reject_annotation_only_candidate(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Raise when an amend candidate only appends the historical annotation marker."""
    after_notes = after.get("notes") or ""
    if not isinstance(after_notes, str):
        return
    if ANNOTATION_ONLY_MARKER not in after_notes:
        return
    # Compare core authority excluding notes
    before_core = {key: value for key, value in before.items() if key != "notes"}
    after_core = {key: value for key, value in after.items() if key != "notes"}
    if before_core == after_core:
        raise ValueError(
            "ANNOTATION_ONLY_AMENDMENT: candidate preserves target authority and only "
            f"records '{ANNOTATION_ONLY_MARKER}'"
        )


def _blob(document: dict[str, Any]) -> str:
    import yaml

    return yaml.safe_dump(document, sort_keys=False).lower()


def assert_amendment_embodied(
    *,
    mutation_id: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | str,
    journal_id: str | None,
) -> list[str]:
    """Return embodiment errors; empty list means pass."""
    errors: list[str] = []
    if journal_id != _IDENTITY_V13_JOURNAL and mutation_id.startswith("M-0"):
        # Non-identity journals must still not ship annotation-only amends.
        if isinstance(after, dict) and before is not None:
            try:
                reject_annotation_only_candidate(before, after)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    if isinstance(after, str):
        text = after
        after_doc: dict[str, Any] | None = None
    else:
        after_doc = after
        text = _blob(after)

    if ANNOTATION_ONLY_MARKER in text and before is not None and after_doc is not None:
        try:
            reject_annotation_only_candidate(before, after_doc)
        except ValueError as exc:
            errors.append(str(exc))

    markers = _MUTATION_MARKERS.get(mutation_id, ())
    lowered = text.lower()
    missing = [marker for marker in markers if marker not in lowered]
    if missing:
        errors.append(f"missing required scoped amendment markers for {mutation_id}: {missing}")

    for forbidden in _FORBIDDEN_ACTIVE_CONTRADICTIONS.get(mutation_id, ()):
        if forbidden in lowered:
            errors.append(
                f"contradictory preserved authority remains active in {mutation_id}: {forbidden}"
            )

    if mutation_id.startswith("M-") and mutation_id != "M-01" and before is not None:
        if after_doc is None:
            errors.append(f"{mutation_id}: amend candidate is not a complete mapping document")
        elif before == after_doc:
            errors.append(f"{mutation_id}: amend candidate is identical to source authority")
        elif after_doc is not None and ANNOTATION_ONLY_MARKER in str(after_doc.get("notes", "")):
            before_core = {key: value for key, value in before.items() if key != "notes"}
            after_core = {key: value for key, value in after_doc.items() if key != "notes"}
            if before_core == after_core:
                errors.append(
                    f"ANNOTATION_ONLY_AMENDMENT: {mutation_id} did not embody scoped amendments"
                )

    return errors
