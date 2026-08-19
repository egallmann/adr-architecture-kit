"""Plan and repair canonical entity-ID collisions across ADR YAML artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional
import os
import re
import tempfile

import yaml

from ..generators._yaml_support import ADRYamlDumper
from ..parser import ADRParser
from ..scope import ProjectScope, ProjectScopeResolver

PathPart = str | int
DefinitionSpec = tuple[str, tuple[PathPart, ...]]

CANONICAL_ENTITY_SECTIONS: dict[str, tuple[DefinitionSpec, ...]] = {
    "logical": (
        ("capability", ("capabilities",)),
        ("decision", ("decisions",)),
        ("invariant", ("invariants",)),
        ("boundary", ("architectural_boundaries",)),
        ("contract", ("interaction_contracts",)),
    ),
    "physical": (
        ("component", ("component_specifications",)),
        ("interface", ("component_specifications", "*", "interfaces")),
        ("implementation_decision", ("implementation_decisions",)),
    ),
    "physical-component": (
        ("component", ("component_specifications",)),
        ("interface", ("component_specifications", "*", "interfaces")),
        ("implementation_decision", ("implementation_decisions",)),
    ),
}

# Only schema-typed identity/reference fields participate. Narrative strings are
# intentionally excluded because changing prose cannot be proven semantically safe.
REFERENCE_FIELDS = {
    "affected_entities",
    "contract_reference",
    "dependencies",
    "enabled_by_decisions",
    "enables_capabilities",
    "enforced_by",
    "enforces_invariants",
    "exposed_interfaces",
    "governs_components",
    "implements_capabilities",
    "implements_invariants",
    "introduces_entities",
    "parties",
    "realizes_entities",
    "related_entities",
    "related_invariants",
    "selected_by",
    "supersedes",
    "superseded_by",
    "upheld_by_decisions",
}


def _source_pointer(path: tuple[PathPart, ...]) -> str:
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in path)


def _numeric_id(entity_id: str) -> tuple[str, int] | None:
    match = re.fullmatch(r"([A-Z]+)-(\d{4})", entity_id)
    if match is None:
        return None
    return match.group(1), int(match.group(2))


def _relative_path(scope: ProjectScope, path: Path) -> str:
    return str(path.resolve().relative_to(scope.root.resolve())).replace("\\", "/")


def _allocation_identity(item: dict[str, Any], canonical_field: str) -> str | None:
    """Return the governed TYPE-NNNN identity used by the allocation ledger.

    Schema v1.3 stores UUIDv7 in ``id``/``component_id`` and keeps the governed
    presentation identifier in ``alias_id``. Allocation ledgers remain keyed by
    those presentation IDs.
    """
    alias = item.get("alias_id")
    if isinstance(alias, str) and alias:
        return alias
    entity_id = item.get(canonical_field)
    return entity_id if isinstance(entity_id, str) and entity_id else None


def _equivalent_allocation_pointers(pointer: str) -> tuple[str, ...]:
    """Accept legacy ``.../id`` ledger pointers alongside v1.3 ``.../alias_id``."""
    if pointer.endswith("/alias_id"):
        return (pointer, f"{pointer[: -len('/alias_id')]}/id")
    if pointer.endswith("/id"):
        return (pointer, f"{pointer[: -len('/id')]}/alias_id")
    if pointer.endswith("/component_id"):
        return (pointer, f"{pointer[: -len('/component_id')]}/alias_id")
    return (pointer,)


@dataclass(frozen=True)
class CanonicalEntityOccurrence:
    """Canonical entity definition at a stable structural source pointer."""

    adr_id: str
    created_date: str
    file_path: Path
    adr_type: str
    entity_type: str
    entity_id: str
    path: tuple[PathPart, ...]

    @property
    def source_pointer(self) -> str:
        return _source_pointer(self.path)


@dataclass(frozen=True)
class CanonicalReferenceOccurrence:
    """Schema-typed local reference that names a colliding entity ID."""

    adr_id: str
    file_path: Path
    entity_id: str
    path: tuple[PathPart, ...]

    @property
    def source_pointer(self) -> str:
        return _source_pointer(self.path)


@dataclass(frozen=True)
class CanonicalIdRemap:
    """Single occurrence-scoped canonical ID remap."""

    entity_type: str
    adr_id: str
    file_path: Path
    old_id: str
    new_id: str
    source_pointer: str = ""


@dataclass(frozen=True)
class CanonicalReferenceRewrite:
    """Reference rewrite resolved to one remapped definition."""

    adr_id: str
    file_path: Path
    source_pointer: str
    old_id: str
    new_id: str
    target_source_pointer: str


@dataclass(frozen=True)
class CanonicalReferenceAmbiguity:
    """Reference that cannot be assigned to exactly one colliding definition."""

    adr_id: str
    file_path: Path
    source_pointer: str
    entity_id: str
    candidate_source_pointers: tuple[str, ...]


@dataclass
class CanonicalRepairPlan:
    """Deterministic, non-writing canonical identity repair plan."""

    remaps: list[CanonicalIdRemap] = field(default_factory=list)
    rewrites: list[CanonicalReferenceRewrite] = field(default_factory=list)
    ambiguities: list[CanonicalReferenceAmbiguity] = field(default_factory=list)
    high_water_marks: dict[str, int] = field(default_factory=dict)


class CanonicalIdNormalizer:
    """Detect, plan, and apply ADR Kit-owned canonical identity repairs."""

    def __init__(
        self,
        parser: ADRParser | None = None,
        scope_resolver: ProjectScopeResolver | None = None,
    ):
        self.parser = parser or ADRParser()
        self.scope_resolver = scope_resolver or ProjectScopeResolver()

    def _discover_adr_files(self, adr_dir: Path) -> list[Path]:
        files: list[Path] = []
        for dirname in ("logical", "physical", "physical-system", "physical-component"):
            base = adr_dir / dirname
            if base.exists():
                files.extend(sorted(path for path in base.glob("*.yaml") if path.is_file()))
        return list(dict.fromkeys(path.resolve() for path in files))

    def _iter_section_items(
        self,
        data: dict[str, Any],
        section_path: tuple[PathPart, ...],
    ) -> list[tuple[tuple[PathPart, ...], dict[str, Any]]]:
        states: list[tuple[tuple[PathPart, ...], Any]] = [((), data)]
        for segment in section_path:
            next_states: list[tuple[tuple[PathPart, ...], Any]] = []
            for path, value in states:
                if segment == "*":
                    if isinstance(value, list):
                        next_states.extend(
                            (path + (index,), item) for index, item in enumerate(value)
                        )
                    continue
                if isinstance(value, dict) and segment in value:
                    next_states.append((path + (segment,), value[segment]))
            states = next_states
        items: list[tuple[tuple[PathPart, ...], dict[str, Any]]] = []
        for path, value in states:
            if not isinstance(value, list):
                continue
            items.extend(
                (path + (index,), item)
                for index, item in enumerate(value)
                if isinstance(item, dict)
            )
        return items

    def _iter_occurrences(
        self, data: dict[str, Any], file_path: Path
    ) -> list[CanonicalEntityOccurrence]:
        adr_id = str(data["id"])
        adr_type = str(data.get("adr_type", ""))
        created_date = str(data.get("created_date", ""))
        occurrences: list[CanonicalEntityOccurrence] = []
        for entity_type, section_path in CANONICAL_ENTITY_SECTIONS.get(adr_type, ()):
            for item_path, item in self._iter_section_items(data, section_path):
                canonical_field = (
                    "component_id"
                    if entity_type == "component" and item.get("component_id")
                    else "id"
                )
                entity_id = _allocation_identity(item, canonical_field)
                if entity_id is None:
                    continue
                identity_field = (
                    "alias_id"
                    if isinstance(item.get("alias_id"), str) and item.get("alias_id")
                    else canonical_field
                )
                occurrences.append(
                    CanonicalEntityOccurrence(
                        adr_id=adr_id,
                        created_date=created_date,
                        file_path=file_path,
                        adr_type=adr_type,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        path=item_path + (identity_field,),
                    )
                )
        return occurrences

    def _walk_typed_references(
        self,
        value: Any,
        *,
        path: tuple[PathPart, ...] = (),
        reference_field: str | None = None,
    ) -> Iterable[tuple[tuple[PathPart, ...], str]]:
        if isinstance(value, dict):
            for key, item in value.items():
                active_field = key if key in REFERENCE_FIELDS else None
                yield from self._walk_typed_references(
                    item,
                    path=path + (key,),
                    reference_field=active_field,
                )
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                yield from self._walk_typed_references(
                    item,
                    path=path + (index,),
                    reference_field=reference_field,
                )
            return
        if isinstance(value, str) and reference_field is not None:
            yield path, value

    def _all_occurrences(
        self, scope: ProjectScope
    ) -> tuple[dict[Path, dict[str, Any]], list[CanonicalEntityOccurrence]]:
        file_data: dict[Path, dict[str, Any]] = {}
        occurrences: list[CanonicalEntityOccurrence] = []
        for file_path in self._discover_adr_files(scope.adr_dir):
            data = self.parser.parse_yaml(file_path)
            if not isinstance(data, dict):
                continue
            file_data[file_path] = data
            occurrences.extend(self._iter_occurrences(data, file_path))
        return file_data, occurrences

    def detect_collisions(
        self, scope: Optional[ProjectScope] = None
    ) -> dict[tuple[str, str], list[CanonicalEntityOccurrence]]:
        scope = scope or self.scope_resolver.resolve()
        _, occurrences = self._all_occurrences(scope)
        grouped: dict[tuple[str, str], list[CanonicalEntityOccurrence]] = {}
        for occurrence in occurrences:
            grouped.setdefault((occurrence.entity_type, occurrence.entity_id), []).append(
                occurrence
            )
        return {
            key: sorted(value, key=lambda item: self._occurrence_sort_key(scope, item))
            for key, value in grouped.items()
            if len(value) > 1
        }

    def _occurrence_sort_key(
        self, scope: ProjectScope, occurrence: CanonicalEntityOccurrence
    ) -> tuple[str, str, str, str]:
        return (
            occurrence.created_date,
            occurrence.adr_id,
            _relative_path(scope, occurrence.file_path),
            occurrence.source_pointer,
        )

    def _load_yaml_mapping(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        payload = self.parser.parse_yaml(path)
        return payload if isinstance(payload, dict) else {}

    def _historical_high_water_marks(
        self,
        scope: ProjectScope,
        occurrences: Iterable[CanonicalEntityOccurrence],
    ) -> dict[str, int]:
        marks: dict[str, int] = {}

        def reserve(entity_id: Any) -> None:
            if not isinstance(entity_id, str):
                return
            parsed = _numeric_id(entity_id)
            if parsed is None:
                return
            prefix, number = parsed
            marks[prefix] = max(marks.get(prefix, 0), number)

        for occurrence in occurrences:
            reserve(occurrence.entity_id)

        allocation = self._load_yaml_mapping(
            scope.adr_dir / "migrations" / "canonical-id-allocation.yaml"
        )
        for prefix, value in (allocation.get("high_water_marks") or {}).items():
            if isinstance(prefix, str) and isinstance(value, int):
                marks[prefix] = max(marks.get(prefix, 0), value)
        for item in allocation.get("allocations") or []:
            if isinstance(item, dict):
                reserve(item.get("id"))

        remap = self._load_yaml_mapping(scope.adr_dir / "migrations" / "canonical-id-remap.yaml")
        for item in remap.get("entries") or []:
            if isinstance(item, dict):
                reserve(item.get("from"))
                reserve(item.get("to"))
        return marks

    def _next_id(
        self,
        old_id: str,
        used_ids: set[str],
        high_water_marks: dict[str, int],
    ) -> str:
        parsed = _numeric_id(old_id)
        if parsed is not None:
            prefix, _ = parsed
            counter = high_water_marks.get(prefix, 0)
            while True:
                counter += 1
                candidate = f"{prefix}-{counter:04d}"
                if candidate not in used_ids:
                    high_water_marks[prefix] = counter
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

    @staticmethod
    def _common_prefix_length(left: tuple[PathPart, ...], right: tuple[PathPart, ...]) -> int:
        count = 0
        for left_part, right_part in zip(left, right):
            if left_part != right_part:
                break
            count += 1
        return count

    def _resolve_reference(
        self,
        scope: ProjectScope,
        reference: CanonicalReferenceOccurrence,
        candidates: list[CanonicalEntityOccurrence],
        reference_resolutions: dict[tuple[str, str], str],
    ) -> CanonicalEntityOccurrence | None:
        reference_key = (
            _relative_path(scope, reference.file_path),
            reference.source_pointer,
        )
        explicit_target = reference_resolutions.get(reference_key)
        if explicit_target is not None:
            for candidate in candidates:
                candidate_key = (
                    f"{_relative_path(scope, candidate.file_path)}#" f"{candidate.source_pointer}"
                )
                if candidate_key == explicit_target:
                    return candidate
            raise ValueError(
                f"Resolution target {explicit_target!r} is not a candidate for "
                f"{reference_key[0]}#{reference_key[1]}"
            )
        same_adr = [item for item in candidates if item.adr_id == reference.adr_id]
        if len(same_adr) == 1:
            return same_adr[0]
        if len(same_adr) > 1:
            scores = [
                (self._common_prefix_length(reference.path, item.path), item) for item in same_adr
            ]
            best_score = max(score for score, _ in scores)
            best = [item for score, item in scores if score == best_score]
            if best_score > 1 and len(best) == 1:
                return best[0]
        return None

    def _load_resolution_map(
        self,
        scope: ProjectScope,
        resolution_map: Path | dict[str, Any] | None,
    ) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str], str]]:
        if resolution_map is None:
            return {}, {}
        payload = (
            self._load_yaml_mapping(resolution_map)
            if isinstance(resolution_map, Path)
            else resolution_map
        )
        if payload.get("type") != "canonical_id_resolution":
            raise ValueError("Resolution map type must be canonical_id_resolution")
        keepers: dict[tuple[str, str], str] = {}
        for item in payload.get("keepers") or []:
            if not isinstance(item, dict):
                raise ValueError("Resolution-map keeper entries must be objects")
            key = (str(item.get("entity_type", "")), str(item.get("id", "")))
            target = str(item.get("target", ""))
            if not all(key) or not target:
                raise ValueError("Resolution-map keeper entry is incomplete")
            if key in keepers:
                raise ValueError(f"Duplicate keeper resolution for {key[0]} {key[1]}")
            keepers[key] = target
        references: dict[tuple[str, str], str] = {}
        for item in payload.get("references") or []:
            if not isinstance(item, dict):
                raise ValueError("Resolution-map reference entries must be objects")
            key = (str(item.get("file_path", "")), str(item.get("source_pointer", "")))
            target = str(item.get("target", ""))
            if not all(key) or not target:
                raise ValueError("Resolution-map reference entry is incomplete")
            if key in references:
                raise ValueError(f"Duplicate reference resolution for {key[0]}#{key[1]}")
            references[key] = target
        return keepers, references

    def plan(
        self,
        scope: Optional[ProjectScope] = None,
        *,
        resolution_map: Path | dict[str, Any] | None = None,
    ) -> CanonicalRepairPlan:
        """Build a deterministic repair plan without writing any artifact."""
        scope = scope or self.scope_resolver.resolve()
        keeper_resolutions, reference_resolutions = self._load_resolution_map(scope, resolution_map)
        file_data, occurrences = self._all_occurrences(scope)
        collisions: dict[tuple[str, str], list[CanonicalEntityOccurrence]] = {}
        for occurrence in occurrences:
            collisions.setdefault((occurrence.entity_type, occurrence.entity_id), []).append(
                occurrence
            )
        collisions = {
            key: sorted(value, key=lambda item: self._occurrence_sort_key(scope, item))
            for key, value in collisions.items()
            if len(value) > 1
        }

        high_water_marks = self._historical_high_water_marks(scope, occurrences)
        used_ids = {item.entity_id for item in occurrences}
        remaps: list[CanonicalIdRemap] = []
        remap_by_target: dict[tuple[Path, str], CanonicalIdRemap] = {}
        for (entity_type, entity_id), group in sorted(collisions.items()):
            explicit_keeper = keeper_resolutions.get((entity_type, entity_id))
            if explicit_keeper is not None:
                selected = [
                    item
                    for item in group
                    if f"{_relative_path(scope, item.file_path)}#{item.source_pointer}"
                    == explicit_keeper
                ]
                if len(selected) != 1:
                    raise ValueError(
                        f"Keeper target {explicit_keeper!r} is not a unique candidate "
                        f"for {entity_type} {entity_id}"
                    )
                keeper = selected[0]
                group = [keeper] + [item for item in group if item != keeper]
            for occurrence in group[1:]:
                new_id = self._next_id(occurrence.entity_id, used_ids, high_water_marks)
                used_ids.add(new_id)
                remap = CanonicalIdRemap(
                    entity_type=entity_type,
                    adr_id=occurrence.adr_id,
                    file_path=occurrence.file_path,
                    old_id=occurrence.entity_id,
                    new_id=new_id,
                    source_pointer=occurrence.source_pointer,
                )
                remaps.append(remap)
                remap_by_target[(occurrence.file_path, occurrence.source_pointer)] = remap

        collision_ids = {entity_id for _, entity_id in collisions}
        definition_paths = {
            (item.file_path, item.path) for group in collisions.values() for item in group
        }
        rewrites: list[CanonicalReferenceRewrite] = []
        ambiguities: list[CanonicalReferenceAmbiguity] = []
        candidates_by_id: dict[str, list[CanonicalEntityOccurrence]] = {}
        for group in collisions.values():
            for candidate in group:
                candidates_by_id.setdefault(candidate.entity_id, []).append(candidate)

        for file_path, data in sorted(file_data.items(), key=lambda item: str(item[0])):
            adr_id = str(data.get("id", ""))
            for path, entity_id in self._walk_typed_references(data):
                if entity_id not in collision_ids or (file_path, path) in definition_paths:
                    continue
                reference = CanonicalReferenceOccurrence(
                    adr_id=adr_id,
                    file_path=file_path,
                    entity_id=entity_id,
                    path=path,
                )
                candidates = sorted(
                    candidates_by_id[entity_id],
                    key=lambda item: self._occurrence_sort_key(scope, item),
                )
                target = self._resolve_reference(
                    scope, reference, candidates, reference_resolutions
                )
                if target is None:
                    ambiguities.append(
                        CanonicalReferenceAmbiguity(
                            adr_id=adr_id,
                            file_path=file_path,
                            source_pointer=reference.source_pointer,
                            entity_id=entity_id,
                            candidate_source_pointers=tuple(
                                f"{_relative_path(scope, item.file_path)}#{item.source_pointer}"
                                for item in candidates
                            ),
                        )
                    )
                    continue
                target_remap = remap_by_target.get((target.file_path, target.source_pointer))
                if target_remap is not None:
                    rewrites.append(
                        CanonicalReferenceRewrite(
                            adr_id=adr_id,
                            file_path=file_path,
                            source_pointer=reference.source_pointer,
                            old_id=entity_id,
                            new_id=target_remap.new_id,
                            target_source_pointer=(
                                f"{_relative_path(scope, target.file_path)}#{target.source_pointer}"
                            ),
                        )
                    )

        return CanonicalRepairPlan(
            remaps=sorted(
                remaps,
                key=lambda item: (
                    item.entity_type,
                    item.old_id,
                    item.adr_id,
                    str(item.file_path),
                    item.source_pointer,
                ),
            ),
            rewrites=sorted(
                rewrites,
                key=lambda item: (str(item.file_path), item.source_pointer),
            ),
            ambiguities=sorted(
                ambiguities,
                key=lambda item: (str(item.file_path), item.source_pointer),
            ),
            high_water_marks=dict(sorted(high_water_marks.items())),
        )

    @staticmethod
    def _pointer_parts(pointer: str) -> tuple[PathPart, ...]:
        parts: list[PathPart] = []
        for encoded in pointer.removeprefix("/").split("/"):
            decoded = encoded.replace("~1", "/").replace("~0", "~")
            parts.append(int(decoded) if decoded.isdigit() else decoded)
        return tuple(parts)

    @staticmethod
    def _set_path(data: Any, path: tuple[PathPart, ...], value: str) -> None:
        target = data
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value

    def _render_yaml(self, data: dict[str, Any]) -> str:
        return yaml.dump(
            data,
            Dumper=ADRYamlDumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    def _updated_remap_ledger(
        self, scope: ProjectScope, remaps: list[CanonicalIdRemap]
    ) -> dict[str, Any]:
        path = scope.adr_dir / "migrations" / "canonical-id-remap.yaml"
        existing = self._load_yaml_mapping(path)
        entries = list(existing.get("entries") or [])
        known = {
            (
                item.get("entity_type"),
                item.get("adr_id"),
                item.get("file_path"),
                item.get("from"),
                item.get("to"),
                item.get("source_pointer", ""),
            )
            for item in entries
            if isinstance(item, dict)
        }
        for item in remaps:
            entry = {
                "entity_type": item.entity_type,
                "adr_id": item.adr_id,
                "file_path": _relative_path(scope, item.file_path),
                "source_pointer": item.source_pointer,
                "from": item.old_id,
                "to": item.new_id,
            }
            key = (
                entry["entity_type"],
                entry["adr_id"],
                entry["file_path"],
                entry["from"],
                entry["to"],
                entry["source_pointer"],
            )
            if key not in known:
                entries.append(entry)
        entries.sort(
            key=lambda item: (
                str(item.get("entity_type", "")),
                str(item.get("from", "")),
                str(item.get("adr_id", "")),
                str(item.get("file_path", "")),
                str(item.get("source_pointer", "")),
            )
        )
        return {
            "schema_version": "1.0",
            "type": "canonical_id_remap",
            "entries": entries,
        }

    def _updated_allocation_ledger(
        self,
        scope: ProjectScope,
        file_data: dict[Path, dict[str, Any]],
        high_water_marks: dict[str, int],
    ) -> dict[str, Any]:
        path = scope.adr_dir / "migrations" / "canonical-id-allocation.yaml"
        existing = self._load_yaml_mapping(path)
        prior = {
            (
                str(item.get("file_path", "")),
                str(item.get("source_pointer", "")),
            ): dict(item)
            for item in existing.get("allocations") or []
            if isinstance(item, dict)
        }
        active: dict[tuple[str, str], dict[str, Any]] = {}
        consumed_prior: set[tuple[str, str]] = set()
        for file_path, data in file_data.items():
            for occurrence in self._iter_occurrences(data, file_path):
                file_rel = _relative_path(scope, file_path)
                equivalent_keys = [
                    (file_rel, pointer)
                    for pointer in _equivalent_allocation_pointers(
                        occurrence.source_pointer
                    )
                ]
                prior_keys = [key for key in equivalent_keys if key in prior]
                # Preserve the historical ledger location when an in-place v1.3
                # promotion moved the presentation identity from ``id`` to
                # ``alias_id``. Both pointers name the same allocation.
                key = min(
                    prior_keys or [equivalent_keys[0]],
                    key=lambda item: (not item[1].endswith("/id"), item[1]),
                )
                consumed_prior.update(prior_keys)
                entry = dict(prior.get(key, {}))
                entry.update({
                    "id": occurrence.entity_id,
                    "entity_type": occurrence.entity_type,
                    "file_path": key[0],
                    "source_pointer": key[1],
                    "state": "active",
                })
                entry.setdefault("adr_id", occurrence.adr_id)
                active[key] = entry
        for key, item in prior.items():
            if key not in consumed_prior and key not in active:
                item["state"] = "retired"
                active[key] = item

        marks = dict(high_water_marks)
        for item in active.values():
            parsed = _numeric_id(str(item.get("id", "")))
            if parsed is not None:
                prefix, number = parsed
                marks[prefix] = max(marks.get(prefix, 0), number)
        return {
            "schema_version": "1.0",
            "type": "canonical_id_allocation",
            "high_water_marks": dict(sorted(marks.items())),
            "allocations": sorted(
                active.values(),
                key=lambda item: (
                    str(item.get("id", "")),
                    str(item.get("file_path", "")),
                    str(item.get("source_pointer", "")),
                ),
            ),
        }

    def _write_atomically(self, payloads: dict[Path, str]) -> None:
        staged: list[tuple[Path, Path]] = []
        try:
            for path, content in sorted(payloads.items(), key=lambda item: str(item[0])):
                path.parent.mkdir(parents=True, exist_ok=True)
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

    def repair(
        self,
        scope: Optional[ProjectScope] = None,
        *,
        apply: bool = False,
        resolution_map: Path | dict[str, Any] | None = None,
    ) -> CanonicalRepairPlan:
        """Plan repairs and optionally apply them through ADR Kit-owned writes."""
        scope = scope or self.scope_resolver.resolve()
        plan = self.plan(scope, resolution_map=resolution_map)
        if not apply:
            return plan
        if plan.ambiguities:
            details = ", ".join(
                f"{_relative_path(scope, item.file_path)}#{item.source_pointer}"
                for item in plan.ambiguities
            )
            raise ValueError(
                "Ambiguous canonical entity references require a resolution map: " f"{details}"
            )

        file_data, _ = self._all_occurrences(scope)
        changed_paths: set[Path] = set()
        for remap in plan.remaps:
            document = file_data[remap.file_path]
            changed_paths.add(remap.file_path)
            self._set_path(
                document,
                self._pointer_parts(remap.source_pointer),
                remap.new_id,
            )
            migration_origin = document.setdefault("migration_origin", {})
            remapped_entities = migration_origin.setdefault("remapped_entities", [])
            remap_evidence = {
                "entity_type": remap.entity_type,
                "from": remap.old_id,
                "to": remap.new_id,
                "source_pointer": remap.source_pointer,
            }
            if remap_evidence not in remapped_entities:
                remapped_entities.append(remap_evidence)
            if (
                remap.entity_type == "capability"
                and "original_capability_id" not in migration_origin
            ):
                migration_origin["original_capability_id"] = remap.old_id
        for rewrite in plan.rewrites:
            changed_paths.add(rewrite.file_path)
            self._set_path(
                file_data[rewrite.file_path],
                self._pointer_parts(rewrite.source_pointer),
                rewrite.new_id,
            )

        allocation_ledger = self._updated_allocation_ledger(scope, file_data, plan.high_water_marks)
        payloads = {path: self._render_yaml(file_data[path]) for path in changed_paths}
        if plan.remaps:
            remap_ledger = self._updated_remap_ledger(scope, plan.remaps)
            payloads[scope.adr_dir / "migrations" / "canonical-id-remap.yaml"] = (
                self._render_yaml(remap_ledger)
            )
        payloads[scope.adr_dir / "migrations" / "canonical-id-allocation.yaml"] = self._render_yaml(
            allocation_ledger
        )
        self._write_atomically(payloads)
        return plan

    def validate_allocations(self, scope: Optional[ProjectScope] = None) -> list[str]:
        """Return deterministic CI findings for collisions and allocation drift."""
        scope = scope or self.scope_resolver.resolve()
        findings: list[str] = []
        collisions = self.detect_collisions(scope)
        for (entity_type, entity_id), occurrences in sorted(collisions.items()):
            locations = ", ".join(
                f"{_relative_path(scope, item.file_path)}#{item.source_pointer}"
                for item in occurrences
            )
            findings.append(f"canonical collision {entity_type} {entity_id}: {locations}")

        ledger_path = scope.adr_dir / "migrations" / "canonical-id-allocation.yaml"
        ledger = self._load_yaml_mapping(ledger_path)
        if not ledger:
            findings.append("missing canonical ID allocation ledger")
            return findings
        if ledger.get("type") != "canonical_id_allocation":
            findings.append("allocation ledger type must be canonical_id_allocation")

        raw_marks = ledger.get("high_water_marks")
        marks = raw_marks if isinstance(raw_marks, dict) else {}
        if not isinstance(raw_marks, dict):
            findings.append("allocation ledger high_water_marks must be an object")
        raw_allocations = ledger.get("allocations")
        allocations = raw_allocations if isinstance(raw_allocations, list) else []
        if not isinstance(raw_allocations, list):
            findings.append("allocation ledger allocations must be an array")

        file_data, occurrences = self._all_occurrences(scope)
        del file_data
        active_by_location: dict[tuple[str, str], dict[str, Any]] = {}
        allocations_by_id: dict[str, list[dict[str, Any]]] = {}
        for index, item in enumerate(allocations):
            if not isinstance(item, dict):
                findings.append(f"allocation entry {index} must be an object")
                continue
            raw_entity_id = item.get("id")
            raw_file_path = item.get("file_path")
            raw_pointer = item.get("source_pointer")
            raw_state = item.get("state")
            if not (
                isinstance(raw_entity_id, str)
                and raw_entity_id
                and isinstance(raw_file_path, str)
                and raw_file_path
                and isinstance(raw_pointer, str)
                and raw_pointer
                and isinstance(raw_state, str)
                and raw_state
            ):
                findings.append(f"allocation entry {index} is incomplete")
                continue
            entity_id = raw_entity_id
            file_path = raw_file_path
            pointer = raw_pointer
            state = raw_state
            allocations_by_id.setdefault(entity_id, []).append(item)
            if state == "active":
                key = (file_path, pointer)
                if key in active_by_location:
                    findings.append(f"duplicate active allocation location {file_path}#{pointer}")
                active_by_location[key] = item
            elif state != "retired":
                findings.append(f"allocation {entity_id} has unsupported state {state!r}")

        for occurrence in occurrences:
            file_rel = _relative_path(scope, occurrence.file_path)
            location = (file_rel, occurrence.source_pointer)
            allocation = None
            matched_pointer = occurrence.source_pointer
            for pointer in _equivalent_allocation_pointers(occurrence.source_pointer):
                candidate = active_by_location.get((file_rel, pointer))
                if candidate is not None:
                    allocation = candidate
                    matched_pointer = pointer
                    break
            if allocation is None:
                findings.append(f"missing active allocation for {location[0]}#{location[1]}")
                continue
            if allocation.get("id") != occurrence.entity_id:
                findings.append(
                    f"allocation drift at {location[0]}#{matched_pointer}: "
                    f"{allocation.get('id')} != {occurrence.entity_id}"
                )
            if allocation.get("entity_type") != occurrence.entity_type:
                findings.append(f"allocation type drift at {location[0]}#{matched_pointer}")

        for entity_id, entries in sorted(allocations_by_id.items()):
            active = [item for item in entries if item.get("state") == "active"]
            if len(active) > 1:
                findings.append(f"ID {entity_id} has multiple active allocations")
            if active and any(item.get("state") == "retired" for item in entries):
                findings.append(f"retired ID {entity_id} was reused")

        historical_marks = self._historical_high_water_marks(scope, occurrences)
        for prefix, required in sorted(historical_marks.items()):
            actual = marks.get(prefix)
            if not isinstance(actual, int) or actual < required:
                findings.append(
                    f"high-water mark {prefix} must be at least {required}; got {actual!r}"
                )
        for prefix, actual in sorted(marks.items()):
            if not isinstance(prefix, str) or not isinstance(actual, int) or actual < 0:
                findings.append(f"invalid high-water mark {prefix!r}: {actual!r}")

        return sorted(set(findings))

    def normalize(self, scope: Optional[ProjectScope] = None) -> list[CanonicalIdRemap]:
        """Compatibility apply entry point retained for the historical CLI."""
        return self.repair(scope, apply=True).remaps

    def _write_ledger(self, scope: ProjectScope, remaps: Iterable[CanonicalIdRemap]) -> Path:
        """Compatibility helper retained for callers of the previous implementation."""
        ledger_path = scope.adr_dir / "migrations" / "canonical-id-remap.yaml"
        ledger = self._updated_remap_ledger(scope, list(remaps))
        self._write_atomically({ledger_path: self._render_yaml(ledger)})
        return ledger_path
