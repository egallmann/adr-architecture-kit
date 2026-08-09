"""Candidate complete post-image construction for create/amend/supersede."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from ..api._errors import OperationError
from .allocation import allocate_child_ids
from .targets import ResolvedTarget, resolve_target


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise OperationError(f"PROMOTION_INVALID_TARGET: expected mapping in {path}")
    return payload


def _dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def build_create_adr_post_image(
    *,
    adr_id: str,
    title: str,
    decisions: list[dict[str, Any]],
    invariants: list[dict[str, Any]],
    schema_version: str = "1.2",
) -> str:
    document = {
        "schema_version": schema_version,
        "id": adr_id,
        "title": title,
        "status": "accepted",
        "date": "2026-08-09",
        "decisions": decisions,
        "invariants": invariants,
        "capabilities": [],
        "notes": "Promoted from Design Journal via adr_kit.api promotion provider.",
    }
    return _dump_yaml(document)


def build_amend_post_image(
    existing_path: Path,
    *,
    replace_children: dict[str, list[dict[str, Any]]] | None = None,
    set_fields: dict[str, Any] | None = None,
    preserve_unscoped: bool = True,
) -> str:
    document = _load_yaml(existing_path)
    original = copy.deepcopy(document)
    if set_fields:
        for key, value in set_fields.items():
            document[key] = value
    if replace_children:
        for key, children in replace_children.items():
            existing = document.get(key)
            if not isinstance(existing, list):
                existing = []
            by_id = {
                item.get("id"): item
                for item in existing
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
            for child in children:
                child_id = child.get("id")
                if not isinstance(child_id, str):
                    raise OperationError("PROMOTION_INVALID_CHILD: child missing id")
                by_id[child_id] = child
            ordered: list[dict[str, Any]] = []
            seen: set[str] = set()
            for item in existing:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    ordered.append(by_id[item["id"]])
                    seen.add(item["id"])
            for child in children:
                if child["id"] not in seen:
                    ordered.append(child)
            document[key] = ordered
    if preserve_unscoped:
        for key, value in original.items():
            if set_fields and key in set_fields:
                continue
            if replace_children and key in replace_children:
                continue
            document[key] = value
    return _dump_yaml(document)


def build_supersede_post_image(
    *,
    replacement_path: Path | None,
    replacement_document: dict[str, Any],
    superseded_id: str,
) -> str:
    document = copy.deepcopy(replacement_document)
    links = document.get("supersedes")
    if not isinstance(links, list):
        links = []
    if superseded_id not in links:
        links.append(superseded_id)
    document["supersedes"] = links
    del replacement_path  # reserved for future path-aware supersede helpers
    return _dump_yaml(document)


def resolve_mutation_target(
    project_root: Path,
    mutation: dict[str, Any],
    *,
    create_title: str | None = None,
) -> ResolvedTarget:
    return resolve_target(
        project_root,
        mutation["provider_target_ref"],
        operation=mutation["operation"],
        create_title=create_title,
    )


def allocate_for_identity_create(project_root: Path) -> tuple[list[str], list[str]]:
    return allocate_child_ids(project_root, dec_count=19, inv_count=18)
