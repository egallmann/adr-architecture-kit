"""Deterministic migration from name-keyed to stable physical topology identity."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import os
from pathlib import Path
import tempfile
from typing import Any

import yaml

from ..models import PhysicalSystemADR
from ..parser import ADRParser
from ..scope import ProjectScope


@dataclass(frozen=True)
class TopologyMigrationChange:
    """One reviewable topology migration change."""

    file_path: Path
    pointer: str
    before: object
    after: object


@dataclass(frozen=True)
class TopologyMigrationDiagnostic:
    """One blocking topology migration diagnostic."""

    file_path: Path
    pointer: str
    code: str
    message: str


@dataclass(frozen=True)
class TopologyMigrationPlan:
    """Deterministic, non-writing topology migration plan."""

    changes: tuple[TopologyMigrationChange, ...] = ()
    diagnostics: tuple[TopologyMigrationDiagnostic, ...] = ()
    changed_files: tuple[Path, ...] = ()
    documents: dict[Path, dict[str, Any]] = field(default_factory=dict, compare=False, repr=False)


class TopologyIdentityMigrator:
    """Allocate stable topology IDs and rewrite uniquely resolvable references."""

    @staticmethod
    def _files(scope: ProjectScope) -> list[Path]:
        return sorted(
            [
                *scope.physical_system_dir.glob("*.yaml"),
                *scope.physical_system_dir.glob("*.yml"),
            ],
            key=lambda item: item.as_posix(),
        )

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected YAML mapping in {path}")
        return payload

    @staticmethod
    def _next_id(used_ids: set[str]) -> str:
        number = 1
        while f"TOPO-{number:04d}" in used_ids:
            number += 1
        allocated = f"TOPO-{number:04d}"
        used_ids.add(allocated)
        return allocated

    def plan(self, scope: ProjectScope) -> TopologyMigrationPlan:
        """Build a deterministic plan without modifying canonical source."""

        source_documents = {path: self._load(path) for path in self._files(scope) if path.is_file()}
        documents = {path: deepcopy(payload) for path, payload in source_documents.items()}
        changes: list[TopologyMigrationChange] = []
        diagnostics: list[TopologyMigrationDiagnostic] = []
        used_ids: set[str] = set()
        id_locations: dict[str, tuple[Path, str]] = {}

        for path, document in documents.items():
            topology = document.get("component_topology")
            if not isinstance(topology, dict):
                continue
            components = topology.get("components", [])
            if not isinstance(components, list):
                continue
            for index, component in enumerate(components):
                if not isinstance(component, dict) or not isinstance(component.get("id"), str):
                    continue
                component_id = component["id"]
                pointer = f"/component_topology/components/{index}/id"
                if component_id in id_locations:
                    diagnostics.append(
                        TopologyMigrationDiagnostic(
                            path,
                            pointer,
                            "duplicate_id",
                            f"Topology ID {component_id!r} is declared more than once",
                        )
                    )
                else:
                    id_locations[component_id] = (path, pointer)
                used_ids.add(component_id)

        for path, document in documents.items():
            if document.get("adr_type") != "physical-system":
                continue
            topology = document.get("component_topology")
            if not isinstance(topology, dict):
                continue
            components = topology.get("components", [])
            if not isinstance(components, list):
                continue

            if document.get("schema_version") != "1.2":
                changes.append(
                    TopologyMigrationChange(
                        path, "/schema_version", document.get("schema_version"), "1.2"
                    )
                )
                document["schema_version"] = "1.2"

            for index, component in enumerate(components):
                if not isinstance(component, dict):
                    continue
                if not isinstance(component.get("id"), str):
                    allocated = self._next_id(used_ids)
                    component["id"] = allocated
                    changes.append(
                        TopologyMigrationChange(
                            path,
                            f"/component_topology/components/{index}/id",
                            None,
                            allocated,
                        )
                    )

            candidates: dict[str, list[str]] = {}
            for component in components:
                if not isinstance(component, dict):
                    continue
                component_id = component.get("id")
                name = component.get("name")
                if not isinstance(component_id, str):
                    continue
                candidates.setdefault(component_id, []).append(component_id)
                if isinstance(name, str):
                    candidates.setdefault(name, []).append(component_id)

            def resolve(value: object, pointer: str) -> object:
                if not isinstance(value, str):
                    diagnostics.append(
                        TopologyMigrationDiagnostic(
                            path,
                            pointer,
                            "dangling_reference",
                            f"Topology reference {value!r} is not a string",
                        )
                    )
                    return value
                matches = sorted(set(candidates.get(value, [])))
                if not matches:
                    diagnostics.append(
                        TopologyMigrationDiagnostic(
                            path,
                            pointer,
                            "dangling_reference",
                            f"Topology reference {value!r} does not resolve",
                        )
                    )
                    return value
                if len(matches) > 1:
                    diagnostics.append(
                        TopologyMigrationDiagnostic(
                            path,
                            pointer,
                            "ambiguous_name",
                            f"Topology name {value!r} resolves to {', '.join(matches)}",
                        )
                    )
                    return value
                return matches[0]

            relationships = topology.get("relationships", [])
            if isinstance(relationships, list):
                for relationship_index, relationship in enumerate(relationships):
                    if not isinstance(relationship, dict):
                        continue
                    for field_name in ("from", "to"):
                        if field_name not in relationship:
                            continue
                        pointer = (
                            f"/component_topology/relationships/{relationship_index}/"
                            f"{field_name}"
                        )
                        before = relationship[field_name]
                        after = resolve(before, pointer)
                        if before != after:
                            relationship[field_name] = after
                            changes.append(TopologyMigrationChange(path, pointer, before, after))

            data_flows = document.get("data_flows", [])
            if isinstance(data_flows, list):
                for flow_index, flow in enumerate(data_flows):
                    if not isinstance(flow, dict) or not isinstance(flow.get("path"), list):
                        continue
                    for item_index, before in enumerate(flow["path"]):
                        pointer = f"/data_flows/{flow_index}/path/{item_index}"
                        after = resolve(before, pointer)
                        if before != after:
                            flow["path"][item_index] = after
                            changes.append(TopologyMigrationChange(path, pointer, before, after))

        changed_files = tuple(sorted({item.file_path for item in changes}, key=str))
        return TopologyMigrationPlan(
            changes=tuple(changes),
            diagnostics=tuple(diagnostics),
            changed_files=changed_files,
            documents={path: documents[path] for path in changed_files},
        )

    @staticmethod
    def _validate(documents: dict[Path, dict[str, Any]]) -> None:
        parser = ADRParser()
        for document in documents.values():
            parser.validate_against_schema(document, "physical_system_v1_2")
            PhysicalSystemADR.model_validate(document)

    @staticmethod
    def _write_atomic(documents: dict[Path, dict[str, Any]]) -> None:
        staged: list[tuple[Path, Path]] = []
        try:
            for path, document in sorted(documents.items(), key=lambda item: str(item[0])):
                content = yaml.safe_dump(document, sort_keys=False, allow_unicode=True)
                descriptor, temp_name = tempfile.mkstemp(
                    prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
                )
                temp_path = Path(temp_name)
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)
                staged.append((temp_path, path))
            for temp_path, path in staged:
                os.replace(temp_path, path)
        finally:
            for temp_path, _ in staged:
                if temp_path.exists():
                    temp_path.unlink()

    def apply(self, scope: ProjectScope) -> TopologyMigrationPlan:
        """Validate and atomically apply a topology migration plan."""

        plan = self.plan(scope)
        if plan.diagnostics:
            raise ValueError("Topology migration blocked by unresolved references")
        self._validate(plan.documents)
        self._write_atomic(plan.documents)
        return plan
