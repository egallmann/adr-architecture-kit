"""Path and stem helpers for ADR human projections."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ...decorators import implements_adr
from ...models.common import ADRType
from ..frontend.adr_access import adr_type_of, field_get, presentation_id

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def kebab_slug(text: str) -> str:
    """Return a lowercase kebab-case slug for titles and names."""
    normalized = _NON_ALNUM.sub("-", text.strip().lower()).strip("-")
    return normalized or "untitled"


@implements_adr("ADR-L-0007")
def projection_subdir_for_adr(adr: Any) -> str:
    """Return the adr-projection subdirectory for one ADR type."""
    adr_type = adr_type_of(adr)
    if adr_type == ADRType.LOGICAL:
        return "logical"
    if adr_type == ADRType.PHYSICAL:
        return "physical"
    if adr_type == ADRType.PHYSICAL_SYSTEM:
        return "physical-system"
    if adr_type == ADRType.PHYSICAL_COMPONENT:
        return "physical-component"
    raise ValueError(f"Unsupported ADR type for projection path: {type(adr)}")


@implements_adr("ADR-L-0007")
def slug_for_adr(adr: Any) -> str:
    """Derive the filename slug from alias_name, title, alias_id, or id."""
    alias_id = field_get(adr, "alias_id")
    alias_name = field_get(adr, "alias_name")
    if isinstance(alias_name, str) and alias_name.strip():
        slug = alias_name.strip()
        if (
            isinstance(alias_id, str)
            and alias_id
            and slug.lower().startswith(f"{alias_id.lower()}-")
        ):
            slug = slug[len(alias_id) + 1 :]
        return (
            kebab_slug(slug) if slug else kebab_slug(alias_id or str(field_get(adr, "id") or "adr"))
        )
    title = field_get(adr, "title")
    if isinstance(title, str) and title.strip():
        return kebab_slug(title)
    if isinstance(alias_id, str) and alias_id:
        return kebab_slug(alias_id)
    entity_id = field_get(adr, "id")
    return kebab_slug(str(entity_id or "adr"))


@implements_adr("ADR-L-0007")
def projection_stem_for_adr(adr: Any) -> str:
    """Return `{alias_or_id}-{slug}` stem without extension."""
    alias_or_id = field_get(adr, "alias_id") or field_get(adr, "id")
    return f"{alias_or_id}-{slug_for_adr(adr)}"


@implements_adr("ADR-L-0007")
def projection_filename(adr: Any) -> str:
    """Return the projection markdown filename."""
    return f"{projection_stem_for_adr(adr)}.md"


@implements_adr("ADR-L-0007")
def projection_relative_path(adr: Any) -> Path:
    """Return project-relative path under adrs/adr-projection/."""
    return Path("adrs/adr-projection") / projection_subdir_for_adr(adr) / projection_filename(adr)


@implements_adr("ADR-L-0007")
def stem_matches_adr(adr: Any, stem: str) -> bool:
    """True when a projection stem matches id, alias_id, or `{id|alias}-slug`."""
    entity_id = field_get(adr, "id")
    alias_id = field_get(adr, "alias_id")
    if entity_id and stem == entity_id:
        return True
    if alias_id and stem == alias_id:
        return True
    if alias_id and stem.startswith(f"{alias_id}-"):
        return True
    if entity_id and stem.startswith(f"{entity_id}-"):
        return True
    return False


def human_label_for_adr(adr: Any) -> str:
    """Preferred human label for links and cards."""
    return presentation_id(adr)
