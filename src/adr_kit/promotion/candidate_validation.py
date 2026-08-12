"""Authoritative validation of exact promotion candidate post-images."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from ..generators.scaffold_generator import ScaffoldGenerator
from ..validators import ADRValidator


def default_create_adr_authors() -> list[str]:
    """Deterministic authors for provider-created ADRs.

    Derived from ScaffoldGenerator's logical scaffold convention, which matches
    the repository's dominant corpus authoring metadata for kit-produced ADRs.
    """

    authors = ScaffoldGenerator().scaffold("logical").get("authors")
    if not isinstance(authors, list) or not authors:
        raise RuntimeError("CREATE_ADR_AUTHORS_AUTHORITY_GAP: scaffold authors unavailable")
    return [str(item) for item in authors]


def default_create_adr_context() -> str:
    """Deterministic context for provider-created logical ADRs.

    Logical ADR schema requires ``context``. The scaffold convention supplies the
    kit's default problem-space placeholder for create candidates.
    """

    context = ScaffoldGenerator().scaffold("logical").get("context")
    if not isinstance(context, str) or not context.strip():
        raise RuntimeError("CREATE_ADR_CONTEXT_AUTHORITY_GAP: scaffold context unavailable")
    return context.strip()


def required_logical_create_metadata_complete(document: dict[str, Any]) -> list[str]:
    """Bounded check that required top-level logical create metadata is present."""

    missing: list[str] = []
    for key in (
        "schema_version",
        "adr_type",
        "id",
        "title",
        "status",
        "created_date",
        "authors",
        "context",
        "decisions",
    ):
        if key not in document or document[key] in (None, "", []):
            missing.append(key)
    return missing


def validate_adr_payload_bytes(content: bytes, *, relative_path: str) -> list[str]:
    """Validate the exact ADR bytes that will be fingerprinted and bound.

    Uses the same ADRValidator / schema dispatch path that governs canonical
    repository validation after apply.
    """

    suffix = ".yaml"
    if relative_path.endswith(".yml"):
        suffix = ".yml"
    with tempfile.TemporaryDirectory(prefix="adr-kit-promotion-validate-") as tmp:
        path = Path(tmp) / Path(relative_path).name
        if not path.suffix:
            path = path.with_suffix(suffix)
        path.write_bytes(content)
        result = ADRValidator().validate_file(path, mode="complete")
        errors: list[str] = []
        for item in result.errors:
            errors.append(f"{item.rule}: {item.message}")
        return errors


def validate_projected_authority_overlay(
    project_root: Path,
    images: dict[str, tuple[str, bytes]],
) -> list[str]:
    """Validate the complete projected post-state for adr: mutations.

    ROADMAP candidates are validated separately via roadmap file rules.
    Discovery matches ADRValidator's logical/physical ADR walk used by
    ``adr validate --cross-references``.
    """

    root = project_root.resolve()
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="adr-kit-promotion-overlay-") as tmp_name:
        overlay = Path(tmp_name)
        adrs_src = root / "adrs"
        if adrs_src.is_dir():
            shutil.copytree(adrs_src, overlay / "adrs")
        roadmap = root / "ROADMAP.md"
        if roadmap.is_file():
            shutil.copy2(roadmap, overlay / "ROADMAP.md")
        for relative_path, content in images.values():
            target = overlay / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        validator = ADRValidator()
        adr_root = overlay / "adrs"
        if adr_root.is_dir():
            logical_files, physical_files = validator._discover_adr_files(adr_root)
            for path in logical_files + physical_files:
                result = validator.validate_file(path, mode="complete")
                for item in result.errors:
                    rel = path.relative_to(overlay).as_posix()
                    errors.append(f"{rel}: {item.rule}: {item.message}")
            cross = validator.validate_cross_references(adr_root)
            if not cross.valid:
                for item in cross.errors:
                    errors.append(f"cross-references: {item.rule}: {item.message}")
    return errors


def candidate_validation_result(errors: list[str]) -> str:
    return "valid" if not errors else "invalid"
