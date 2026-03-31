"""Normalize canonical entity ID collisions across ADR YAML artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import re

import yaml

from ..generators._yaml_support import ADRYamlDumper
from ..parser import ADRParser
from ..scope import ProjectScope, ProjectScopeResolver


CANONICAL_ENTITY_SECTIONS = {
    "logical": (
        ("capability", ("capabilities",)),
        ("decision", ("decisions",)),
        ("invariant", ("invariants",)),
    ),
    "physical-component": (
        ("component", ("component_specifications",)),
    ),
}


@dataclass
class CanonicalEntityOccurrence:
    """Canonical entity occurrence inside an ADR document."""

    adr_id: str
    file_path: Path
    adr_type: str
    entity_type: str
    entity_id: str
    path: tuple[str, int, str]


@dataclass
class CanonicalIdRemap:
    """Single canonical ID remap."""

    entity_type: str
    adr_id: str
    file_path: Path
    old_id: str
    new_id: str


class CanonicalIdNormalizer:
    """Detect and normalize canonical ID collisions in ADR YAML files."""

    def __init__(self, parser: ADRParser = None, scope_resolver: ProjectScopeResolver = None):
        self.parser = parser or ADRParser()
        self.scope_resolver = scope_resolver or ProjectScopeResolver()

    def _discover_adr_files(self, adr_dir: Path) -> list[Path]:
        files: list[Path] = []
        for dirname in ("logical", "physical", "physical-system", "physical-component"):
            base = adr_dir / dirname
            if base.exists():
                files.extend(sorted(path for path in base.glob("*.yaml") if path.is_file()))
        return list(dict.fromkeys(path.resolve() for path in files))

    def _iter_occurrences(self, data: dict, file_path: Path) -> list[CanonicalEntityOccurrence]:
        adr_id = data["id"]
        adr_type = data.get("adr_type")
        sections = CANONICAL_ENTITY_SECTIONS.get(adr_type, ())
        occurrences: list[CanonicalEntityOccurrence] = []
        for entity_type, (section_name,) in sections:
            section = data.get(section_name) or []
            if not isinstance(section, list):
                continue
            for index, item in enumerate(section):
                if not isinstance(item, dict):
                    continue
                canonical_field = "component_id" if entity_type == "component" and item.get("component_id") else "id"
                entity_id = item.get(canonical_field)
                if not isinstance(entity_id, str):
                    continue
                occurrences.append(
                    CanonicalEntityOccurrence(
                        adr_id=adr_id,
                        file_path=file_path,
                        adr_type=adr_type,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        path=(section_name, index, canonical_field),
                    )
                )
        return occurrences

    def _replace_exact_string(self, value: Any, old_id: str, new_id: str) -> Any:
        if isinstance(value, str):
            return new_id if value == old_id else value
        if isinstance(value, list):
            return [self._replace_exact_string(item, old_id, new_id) for item in value]
        if isinstance(value, dict):
            return {key: self._replace_exact_string(item, old_id, new_id) for key, item in value.items()}
        return value

    def _next_id(self, old_id: str, used_ids: set[str]) -> str:
        numeric_match = re.match(r"^([A-Z]+)-(\d{4})$", old_id)
        if numeric_match:
            prefix, number = numeric_match.groups()
            counter = int(number)
            while True:
                counter += 1
                candidate = f"{prefix}-{counter:04d}"
                if candidate not in used_ids:
                    return candidate

        symbolic_match = re.match(r"^([A-Z]+-[A-Z0-9-]+?)(?:-(\d+))?$", old_id)
        if symbolic_match:
            base = symbolic_match.group(1)
            counter = int(symbolic_match.group(2) or "1")
            while True:
                counter += 1
                candidate = f"{base}-{counter}"
                if candidate not in used_ids:
                    return candidate

        raise ValueError(f"Cannot increment canonical entity ID: {old_id}")

    def detect_collisions(self, scope: Optional[ProjectScope] = None) -> dict[tuple[str, str], list[CanonicalEntityOccurrence]]:
        scope = scope or self.scope_resolver.resolve()
        collisions: dict[tuple[str, str], list[CanonicalEntityOccurrence]] = {}
        for file_path in self._discover_adr_files(scope.adr_dir):
            data = self.parser.parse_yaml(file_path)
            for occurrence in self._iter_occurrences(data, file_path):
                key = (occurrence.entity_type, occurrence.entity_id)
                collisions.setdefault(key, []).append(occurrence)
        return {
            key: sorted(value, key=lambda item: item.adr_id)
            for key, value in collisions.items()
            if len(value) > 1
        }

    def normalize(self, scope: Optional[ProjectScope] = None) -> list[CanonicalIdRemap]:
        scope = scope or self.scope_resolver.resolve()
        collisions = self.detect_collisions(scope)
        if not collisions:
            return []

        all_occurrences: dict[str, list[CanonicalEntityOccurrence]] = {}
        file_data: dict[Path, dict] = {}
        used_ids_by_type: dict[str, set[str]] = {}

        for file_path in self._discover_adr_files(scope.adr_dir):
            data = self.parser.parse_yaml(file_path)
            file_data[file_path] = data
            occurrences = self._iter_occurrences(data, file_path)
            all_occurrences[data["id"]] = occurrences
            for occurrence in occurrences:
                used_ids_by_type.setdefault(occurrence.entity_type, set()).add(occurrence.entity_id)

        remaps: list[CanonicalIdRemap] = []

        for (entity_type, _), occurrences in sorted(collisions.items(), key=lambda item: (item[0][0], item[0][1])):
            sorted_group = sorted(occurrences, key=lambda item: item.adr_id)
            keeper = sorted_group[0]
            for occurrence in sorted_group[1:]:
                old_id = occurrence.entity_id
                new_id = self._next_id(old_id, used_ids_by_type[entity_type])
                used_ids_by_type[entity_type].add(new_id)

                data = file_data[occurrence.file_path]
                updated = self._replace_exact_string(data, old_id, new_id)
                migration_origin = updated.setdefault("migration_origin", {})
                remapped_entities = migration_origin.setdefault("remapped_entities", [])
                remapped_entities.append(
                    {
                        "entity_type": entity_type,
                        "from": old_id,
                        "to": new_id,
                    }
                )
                if entity_type == "capability" and "original_capability_id" not in migration_origin:
                    migration_origin["original_capability_id"] = old_id

                file_data[occurrence.file_path] = updated
                remaps.append(
                    CanonicalIdRemap(
                        entity_type=entity_type,
                        adr_id=occurrence.adr_id,
                        file_path=occurrence.file_path,
                        old_id=old_id,
                        new_id=new_id,
                    )
                )

        if not remaps:
            return []

        for file_path, data in sorted(file_data.items(), key=lambda item: str(item[0])):
            rendered = yaml.dump(data, Dumper=ADRYamlDumper, default_flow_style=False, sort_keys=False, allow_unicode=True)
            file_path.write_text(rendered, encoding="utf-8", newline="\n")

        self._write_ledger(scope, remaps)
        return remaps

    def _write_ledger(self, scope: ProjectScope, remaps: Iterable[CanonicalIdRemap]) -> Path:
        ledger_path = scope.adr_dir / "migrations" / "canonical-id-remap.yaml"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        entries = [
            {
                "entity_type": item.entity_type,
                "adr_id": item.adr_id,
                "file_path": str(item.file_path.resolve().relative_to(scope.root.resolve())).replace("\\", "/"),
                "from": item.old_id,
                "to": item.new_id,
            }
            for item in sorted(remaps, key=lambda entry: (entry.entity_type, entry.old_id, entry.adr_id))
        ]
        ledger = {
            "schema_version": "1.0",
            "type": "canonical_id_remap",
            "entries": entries,
        }
        ledger_path.write_text(
            yaml.dump(ledger, Dumper=ADRYamlDumper, default_flow_style=False, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
            newline="\n",
        )
        return ledger_path
