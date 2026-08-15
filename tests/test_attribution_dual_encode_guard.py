"""Selective dogfood must not dual-encode equivalent legacy + UUID edges."""

from __future__ import annotations

import ast
from pathlib import Path

from adr_kit.identity import UUIDV7_PATTERN
from adr_kit.repository import ArchitectureRepository

SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "adr_kit"

LEGACY_IMPLEMENTS = {"implements_adr", "implements_adrs"}
UUID_IMPLEMENTS = {"implements", "implements_uuids"}
LEGACY_ENFORCES = {"enforces_invariant", "enforces_invariants"}
UUID_ENFORCES = {"enforces", "enforces_uuids"}


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _string_args(call: ast.Call) -> list[str]:
    values: list[str] = []
    for arg in call.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            values.append(arg.value)
        elif isinstance(arg, ast.List):
            for elt in arg.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    values.append(elt.value)
    return values


def _iter_decorated_edges() -> list[tuple[str, str, str, str]]:
    """Return (path, qualname, family, token) for attribution decorators."""
    edges: list[tuple[str, str, str, str]] = []
    for path in SRC_ROOT.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                name = _call_name(decorator.func)
                if name is None:
                    continue
                if name in LEGACY_IMPLEMENTS or name in UUID_IMPLEMENTS:
                    family = "implements"
                elif name in LEGACY_ENFORCES or name in UUID_ENFORCES:
                    family = "enforces"
                elif name in {"embodies", "embodies_uuids"}:
                    family = "embodies"
                else:
                    continue
                for token in _string_args(decorator):
                    edges.append((path.as_posix(), node.name, family, token))
    return edges


def test_no_equivalent_legacy_and_uuid_dual_encode() -> None:
    repo = ArchitectureRepository(project_root=".")
    repo.load()
    by_surface: dict[tuple[str, str, str], dict[str, set[str]]] = {}
    for path, name, family, token in _iter_decorated_edges():
        key = (path, name, family)
        bucket = by_surface.setdefault(key, {"legacy": set(), "uuid": set()})
        if UUIDV7_PATTERN.match(token):
            bucket["uuid"].add(token)
        else:
            bucket["legacy"].add(token)

    collisions: list[str] = []
    for (path, name, family), bucket in sorted(by_surface.items()):
        uuid_aliases: set[str] = set()
        for uuid in bucket["uuid"]:
            entity = repo.find_entity_by_uuid(uuid)
            if entity is not None and entity.alias_id:
                uuid_aliases.add(entity.alias_id)
        overlap = bucket["legacy"] & uuid_aliases
        if overlap:
            collisions.append(f"{path}::{name} {family} {sorted(overlap)}")
    assert collisions == []
