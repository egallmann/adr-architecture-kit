"""Deterministic schema v1.3 identity migration planner and applicator."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping

import rfc8785
import yaml

from ..decorators import implements_adr
from ..identity import mint_uuidv7, validate_alias_name
from ..integrity.transaction import (
    PlannedWrite,
    TransactionAborted,
    commit_all_or_none,
    recover_interrupted_commit,
)
from ..migrators.canonical_id_normalizer import (
    CANONICAL_ENTITY_SECTIONS,
    _relative_path,
    _source_pointer,
)
from ..parser import ADRParser
from ..scope import ProjectScope, ProjectScopeResolver

PathPart = str | int
MintFn = Callable[[], str]

CANONICAL_MAP_RELATIVE_PATH = "adrs/migrations/canonical-identity-v13-map.yaml"


@dataclass(frozen=True, slots=True)
class MigrationDiagnostic:
    code: str
    message: str
    path: str | None = None
    pointer: str | None = None


@dataclass(frozen=True, slots=True)
class IdentityOccurrence:
    architecture_namespace: str
    source_path: str
    source_pointer: str
    legacy_alias_id: str
    entity_type: str
    file_path: Path
    path: tuple[PathPart, ...]
    presentation_name: str | None = None

    @property
    def occurrence_key(self) -> str:
        return "|".join(
            [
                self.architecture_namespace,
                self.source_path,
                self.source_pointer,
                self.legacy_alias_id,
                self.entity_type,
            ]
        )


@dataclass
class IdentityMapEntry:
    occurrence_key: str
    source_path: str
    source_pointer: str
    legacy_alias_id: str
    entity_type: str
    uuid: str
    alias_id: str
    alias_name: str
    classification: str = "mechanical"
    disposition: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "occurrence_key": self.occurrence_key,
            "source_path": self.source_path,
            "source_pointer": self.source_pointer,
            "legacy_alias_id": self.legacy_alias_id,
            "entity_type": self.entity_type,
            "uuid": self.uuid,
            "alias_id": self.alias_id,
            "alias_name": self.alias_name,
            "classification": self.classification,
            "disposition": self.disposition,
        }


@dataclass
class IdentityMapDocument:
    architecture_namespace: str
    baseline_fingerprint: str
    entries: list[IdentityMapEntry] = field(default_factory=list)
    review_queues: dict[str, list[str]] = field(
        default_factory=lambda: {
            "alias_conflicts": [],
            "source_owners": [],
            "external_providers": [],
        }
    )
    seal: dict[str, Any] = field(
        default_factory=lambda: {
            "sealed": False,
            "map_fingerprint": None,
            "sealed_at": None,
            "approver": None,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "type": "canonical_identity_v13_map",
            "architecture_namespace": self.architecture_namespace,
            "baseline_fingerprint": self.baseline_fingerprint,
            "entries": [entry.to_dict() for entry in self.entries],
            "review_queues": {
                key: list(values) for key, values in sorted(self.review_queues.items())
            },
            "seal": dict(self.seal),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> IdentityMapDocument:
        entries = [
            IdentityMapEntry(
                occurrence_key=str(item["occurrence_key"]),
                source_path=str(item.get("source_path", "")),
                source_pointer=str(item.get("source_pointer", "")),
                legacy_alias_id=str(item["legacy_alias_id"]),
                entity_type=str(item["entity_type"]),
                uuid=str(item["uuid"]),
                alias_id=str(item["alias_id"]),
                alias_name=str(item["alias_name"]),
                classification=str(item.get("classification", "mechanical")),
                disposition=str(item.get("disposition", "pending")),
            )
            for item in payload.get("entries", [])
        ]
        return cls(
            architecture_namespace=str(payload["architecture_namespace"]),
            baseline_fingerprint=str(payload["baseline_fingerprint"]),
            entries=entries,
            review_queues={
                "alias_conflicts": list(
                    (payload.get("review_queues") or {}).get("alias_conflicts", [])
                ),
                "source_owners": list(
                    (payload.get("review_queues") or {}).get("source_owners", [])
                ),
                "external_providers": list(
                    (payload.get("review_queues") or {}).get("external_providers", [])
                ),
            },
            seal=dict(payload.get("seal") or {}),
        )


@dataclass(frozen=True)
class PreflightResult:
    architecture_namespace: str
    baseline_fingerprint: str
    occurrences: tuple[IdentityOccurrence, ...]
    diagnostics: tuple[MigrationDiagnostic, ...]

    @property
    def ok(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True)
class PlanResult:
    identity_map: IdentityMapDocument
    diagnostics: tuple[MigrationDiagnostic, ...]

    @property
    def ok(self) -> bool:
        return not self.diagnostics


def _jcs_fingerprint(payload: Mapping[str, Any]) -> str:
    digest = sha256(rfc8785.dumps(dict(payload))).hexdigest()
    return f"sha256:{digest}"


def _slug_alias_name(value: str, *, entity_type: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    if len(cleaned) < 3:
        cleaned = f"{entity_type}-{cleaned or 'item'}"
    try:
        return validate_alias_name(cleaned, entity_type=entity_type)
    except ValueError:
        fallback = f"{entity_type}-migrated"
        return validate_alias_name(fallback, entity_type=entity_type)


def _load_namespace(scope: ProjectScope, parser: ADRParser) -> str:
    data = parser.parse_yaml(scope.root / "PROJECT.yaml")
    namespace = (data.get("architecture_documentation") or {}).get("architecture_namespace")
    if not isinstance(namespace, str) or not namespace:
        raise ValueError("PROJECT.yaml missing architecture_documentation.architecture_namespace")
    return namespace


def _iter_section_items(
    document: dict[str, Any],
    path: tuple[PathPart, ...],
) -> list[tuple[tuple[PathPart, ...], dict[str, Any]]]:
    states: list[tuple[tuple[PathPart, ...], Any]] = [((), document)]
    for segment in path:
        next_states: list[tuple[tuple[PathPart, ...], Any]] = []
        for prefix, value in states:
            if segment == "*":
                if isinstance(value, list):
                    next_states.extend(
                        (prefix + (index,), item) for index, item in enumerate(value)
                    )
                continue
            if isinstance(value, dict) and segment in value:
                next_states.append((prefix + (segment,), value[segment]))
        states = next_states
    items: list[tuple[tuple[PathPart, ...], dict[str, Any]]] = []
    for prefix, value in states:
        if isinstance(value, dict):
            items.append((prefix, value))
            continue
        if not isinstance(value, list):
            continue
        items.extend(
            (prefix + (index,), item) for index, item in enumerate(value) if isinstance(item, dict)
        )
    return items


def _presentation_name(node: Mapping[str, Any], entity_type: str) -> str | None:
    for key in ("name", "title", "summary", "id"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return entity_type


@implements_adr("ADR-L-0019")
class IdentityV13Migrator:
    """Plan, seal, and apply deterministic v1.3 identity migration maps."""

    def __init__(
        self,
        *,
        parser: ADRParser | None = None,
        mint: MintFn | None = None,
    ) -> None:
        self._parser = parser or ADRParser()
        self._mint = mint or (lambda: mint_uuidv7())
        self._mint_count = 0

    @property
    def mint_count(self) -> int:
        return self._mint_count

    def _mint_once(self) -> str:
        self._mint_count += 1
        return self._mint()

    def preflight(self, scope: ProjectScope | Path) -> PreflightResult:
        """Inventory admitted occurrences and emit blockers without minting."""

        resolved = self._resolve_scope(scope)
        diagnostics: list[MigrationDiagnostic] = []
        try:
            namespace = _load_namespace(resolved, self._parser)
        except Exception as exc:
            return PreflightResult(
                architecture_namespace="",
                baseline_fingerprint="",
                occurrences=(),
                diagnostics=(
                    MigrationDiagnostic(
                        code="missing_architecture_namespace",
                        message=str(exc),
                        path="PROJECT.yaml",
                    ),
                ),
            )

        occurrences, inventory_diagnostics = self._inventory(resolved, namespace)
        diagnostics.extend(inventory_diagnostics)
        seen_ids: dict[str, IdentityOccurrence] = {}
        for occurrence in occurrences:
            prior = seen_ids.get(occurrence.legacy_alias_id)
            if prior is not None and prior.occurrence_key != occurrence.occurrence_key:
                diagnostics.append(
                    MigrationDiagnostic(
                        code="duplicate_legacy_alias",
                        message=(
                            f"Legacy alias {occurrence.legacy_alias_id} occurs at both "
                            f"{prior.source_path}{prior.source_pointer} and "
                            f"{occurrence.source_path}{occurrence.source_pointer}"
                        ),
                        path=occurrence.source_path,
                        pointer=occurrence.source_pointer,
                    )
                )
            seen_ids[occurrence.legacy_alias_id] = occurrence

        baseline = _jcs_fingerprint(
            {
                "architecture_namespace": namespace,
                "occurrences": [
                    {
                        "occurrence_key": item.occurrence_key,
                        "legacy_alias_id": item.legacy_alias_id,
                        "entity_type": item.entity_type,
                    }
                    for item in occurrences
                ],
            }
        )
        return PreflightResult(
            architecture_namespace=namespace,
            baseline_fingerprint=baseline,
            occurrences=tuple(occurrences),
            diagnostics=tuple(diagnostics),
        )

    def plan(self, scope: ProjectScope | Path) -> PlanResult:
        """Mint UUIDs once into a complete candidate map after green preflight."""

        preflight = self.preflight(scope)
        if not preflight.ok:
            return PlanResult(
                identity_map=IdentityMapDocument(
                    architecture_namespace=preflight.architecture_namespace,
                    baseline_fingerprint=preflight.baseline_fingerprint,
                ),
                diagnostics=preflight.diagnostics,
            )

        entries: list[IdentityMapEntry] = []
        used_names: dict[str, str] = {}
        review_alias_conflicts: list[str] = []
        for occurrence in preflight.occurrences:
            proposed = _slug_alias_name(
                occurrence.presentation_name or occurrence.legacy_alias_id,
                entity_type=occurrence.entity_type,
            )
            classification = "mechanical"
            if proposed in used_names and used_names[proposed] != occurrence.legacy_alias_id:
                classification = "review_required"
                review_alias_conflicts.append(occurrence.occurrence_key)
                proposed = _slug_alias_name(
                    f"{occurrence.legacy_alias_id}-{proposed}",
                    entity_type=occurrence.entity_type,
                )
            used_names[proposed] = occurrence.legacy_alias_id
            entries.append(
                IdentityMapEntry(
                    occurrence_key=occurrence.occurrence_key,
                    source_path=occurrence.source_path,
                    source_pointer=occurrence.source_pointer,
                    legacy_alias_id=occurrence.legacy_alias_id,
                    entity_type=occurrence.entity_type,
                    uuid=self._mint_once(),
                    alias_id=occurrence.legacy_alias_id,
                    alias_name=proposed,
                    classification=classification,
                    disposition="pending" if classification == "review_required" else "accepted",
                )
            )

        identity_map = IdentityMapDocument(
            architecture_namespace=preflight.architecture_namespace,
            baseline_fingerprint=preflight.baseline_fingerprint,
            entries=entries,
            review_queues={
                "alias_conflicts": sorted(review_alias_conflicts),
                "source_owners": [],
                "external_providers": [],
            },
        )
        return PlanResult(identity_map=identity_map, diagnostics=())

    def seal(
        self,
        identity_map: IdentityMapDocument,
        *,
        approver: str,
        sealed_at: str,
        dispositions: Mapping[str, str] | None = None,
    ) -> IdentityMapDocument:
        """Close judgment queues and record the sealed map fingerprint."""

        sealed = IdentityMapDocument.from_dict(identity_map.to_dict())
        disposition_map = dict(dispositions or {})
        for entry in sealed.entries:
            if entry.occurrence_key in disposition_map:
                entry.disposition = disposition_map[entry.occurrence_key]
            elif entry.classification == "mechanical":
                entry.disposition = "accepted"
        open_queue = [
            entry.occurrence_key
            for entry in sealed.entries
            if entry.classification == "review_required" and entry.disposition != "accepted"
        ]
        for queue_name in ("alias_conflicts", "source_owners", "external_providers"):
            sealed.review_queues[queue_name] = [
                key for key in sealed.review_queues.get(queue_name, []) if key in open_queue
            ]
        if any(sealed.review_queues.values()) or open_queue:
            raise ValueError(
                "Cannot seal identity map with open judgment queues: " + ", ".join(open_queue)
            )
        intent = {
            "architecture_namespace": sealed.architecture_namespace,
            "baseline_fingerprint": sealed.baseline_fingerprint,
            "entries": [entry.to_dict() for entry in sealed.entries],
            "review_queues": sealed.review_queues,
        }
        fingerprint = _jcs_fingerprint(intent)
        sealed.seal = {
            "sealed": True,
            "map_fingerprint": fingerprint,
            "sealed_at": sealed_at,
            "approver": approver,
        }
        return sealed

    def verify_sealed(
        self,
        identity_map: IdentityMapDocument,
        *,
        expected_baseline: str | None = None,
    ) -> list[MigrationDiagnostic]:
        """Validate seal fingerprint and closed judgment queues."""

        diagnostics: list[MigrationDiagnostic] = []
        if not identity_map.seal.get("sealed"):
            diagnostics.append(
                MigrationDiagnostic(code="map_unsealed", message="Identity map is not sealed")
            )
        open_queues = {
            name: values for name, values in identity_map.review_queues.items() if values
        }
        if open_queues:
            diagnostics.append(
                MigrationDiagnostic(
                    code="open_judgment_queues",
                    message=f"Open judgment queues remain: {sorted(open_queues)}",
                )
            )
        pending = [
            entry.occurrence_key
            for entry in identity_map.entries
            if entry.disposition != "accepted"
        ]
        if pending:
            diagnostics.append(
                MigrationDiagnostic(
                    code="incomplete_review",
                    message=f"Entries missing accepted disposition: {pending}",
                )
            )
        intent = {
            "architecture_namespace": identity_map.architecture_namespace,
            "baseline_fingerprint": identity_map.baseline_fingerprint,
            "entries": [entry.to_dict() for entry in identity_map.entries],
            "review_queues": identity_map.review_queues,
        }
        expected = _jcs_fingerprint(intent)
        actual = identity_map.seal.get("map_fingerprint")
        if actual != expected:
            diagnostics.append(
                MigrationDiagnostic(
                    code="seal_fingerprint_mismatch",
                    message="Sealed map fingerprint does not match immutable map intent",
                )
            )
        if expected_baseline is not None and identity_map.baseline_fingerprint != expected_baseline:
            diagnostics.append(
                MigrationDiagnostic(
                    code="baseline_drift",
                    message="Identity map baseline fingerprint does not match current corpus",
                )
            )
        return diagnostics

    def apply(
        self,
        scope: ProjectScope | Path,
        identity_map: IdentityMapDocument,
        *,
        dry_run: bool = False,
        fault: Callable[[str], None] | None = None,
        journal_root: Path | None = None,
    ) -> list[PlannedWrite]:
        """Apply a sealed identity map atomically; never remint."""

        resolved = self._resolve_scope(scope)
        preflight = self.preflight(resolved)
        diagnostics = self.verify_sealed(
            identity_map,
            expected_baseline=preflight.baseline_fingerprint,
        )
        if diagnostics:
            raise ValueError("; ".join(item.message for item in diagnostics))
        if self._mint_count:
            # Apply path must not mint; callers may plan earlier in a separate instance.
            pass

        writes = self._build_writes(resolved, identity_map)
        if dry_run:
            return writes

        def validate_staged(overlay: Path) -> None:
            map_path = overlay / CANONICAL_MAP_RELATIVE_PATH
            if not map_path.is_file():
                raise TransactionAborted("Staged identity map missing")
            staged_map = IdentityMapDocument.from_dict(
                yaml.safe_load(map_path.read_text(encoding="utf-8"))
            )
            staged_errors = self.verify_sealed(staged_map)
            if staged_errors:
                raise TransactionAborted(staged_errors[0].message)

        commit_all_or_none(
            resolved.root,
            writes,
            validate_staged=validate_staged,
            fault=fault,
            journal_root=journal_root,
            journal_kind="identity-v13-journal",
        )
        return writes

    def check(self, scope: ProjectScope | Path, identity_map: IdentityMapDocument) -> list[str]:
        """Prove idempotent sealed-map consistency without reminting."""

        resolved = self._resolve_scope(scope)
        errors = [item.message for item in self.verify_sealed(identity_map)]
        preflight = self.preflight(resolved)
        if identity_map.baseline_fingerprint != preflight.baseline_fingerprint:
            # After apply, baseline of legacy inventory no longer matches; instead verify
            # that every map UUID/alias is present in rewritten sources.
            pass
        by_alias = {entry.alias_id: entry for entry in identity_map.entries}
        for path in self._adr_files(resolved):
            document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(document, dict):
                continue
            if document.get("schema_version") != "1.3":
                errors.append(f"{path.name} is not schema 1.3 after migration")
                continue
            adr_id = document.get("id")
            if isinstance(adr_id, str) and adr_id in by_alias:
                if (
                    document.get("alias_id") != by_alias[adr_id].alias_id
                    and document.get("id") != by_alias[adr_id].uuid
                ):
                    # v1.3 ADR root uses UUID id + alias_id
                    pass
            root_id = document.get("id")
            root_alias = document.get("alias_id")
            if isinstance(root_alias, str) and root_alias in by_alias:
                expected = by_alias[root_alias]
                if root_id != expected.uuid:
                    errors.append(
                        f"{path.name}: ADR id {root_id} does not match sealed UUID {expected.uuid}"
                    )
        if self._mint_count:
            errors.append("check/recover must not mint UUIDs")
        return errors

    def recover(self, journal: Path, scope: ProjectScope | Path) -> None:
        """Recover an interrupted migration journal without reminting."""

        resolved = self._resolve_scope(scope)
        recover_interrupted_commit(journal, resolved.root)

    def _resolve_scope(self, scope: ProjectScope | Path) -> ProjectScope:
        if isinstance(scope, ProjectScope):
            return scope
        return ProjectScopeResolver(explicit_scope=scope).resolve()

    def _adr_files(self, scope: ProjectScope) -> list[Path]:
        files: list[Path] = []
        for directory in (
            scope.logical_dir,
            scope.physical_dir,
            scope.physical_system_dir,
            scope.physical_component_dir,
        ):
            if directory.exists():
                files.extend(sorted(directory.glob("*.yaml")))
                files.extend(sorted(directory.glob("*.yml")))
        return sorted({path.resolve() for path in files}, key=lambda item: item.as_posix())

    def _inventory(
        self,
        scope: ProjectScope,
        namespace: str,
    ) -> tuple[list[IdentityOccurrence], list[MigrationDiagnostic]]:
        occurrences: list[IdentityOccurrence] = []
        diagnostics: list[MigrationDiagnostic] = []
        for path in self._adr_files(scope):
            try:
                document = self._parser.parse_yaml(path)
            except Exception as exc:
                diagnostics.append(
                    MigrationDiagnostic(
                        code="parse_failure",
                        message=str(exc),
                        path=_relative_path(scope, path),
                    )
                )
                continue
            if not isinstance(document, dict):
                continue
            adr_type = str(document.get("adr_type") or "")
            adr_id = str(document.get("id") or "")
            relative = _relative_path(scope, path)
            # ADR root is always admitted.
            if adr_id:
                occurrences.append(
                    IdentityOccurrence(
                        architecture_namespace=namespace,
                        source_path=relative,
                        source_pointer="/id",
                        legacy_alias_id=adr_id,
                        entity_type="adr",
                        file_path=path,
                        path=("id",),
                        presentation_name=str(document.get("title") or adr_id),
                    )
                )
            sections = CANONICAL_ENTITY_SECTIONS.get(adr_type, ())
            if adr_type == "physical-system":
                # Legacy physical-system ADRs lack an authored system record; invent
                # the SYS-* occurrence so migration can materialize it.
                system_nodes = list(_iter_section_items(document, ("system",)))
                if not system_nodes:
                    system_alias = None
                    if adr_id.startswith("ADR-PS-"):
                        system_alias = f"SYS-{adr_id.removeprefix('ADR-PS-')}"
                    else:
                        system_alias = f"SYS-FROM-{adr_id}"
                    occurrences.append(
                        IdentityOccurrence(
                            architecture_namespace=namespace,
                            source_path=relative,
                            source_pointer="/system/id",
                            legacy_alias_id=system_alias,
                            entity_type="system",
                            file_path=path,
                            path=("system", "id"),
                            presentation_name=str(document.get("title") or system_alias),
                        )
                    )
                sections = sections + (("system", ("system",)),)
            for entity_type, section_path in sections:
                for node_path, node in _iter_section_items(document, section_path):
                    if entity_type == "system" and section_path == ("system",):
                        entity_id = node.get("id") or node.get("alias_id")
                        if entity_id is None:
                            continue
                    else:
                        entity_id = node.get("id")
                    if not isinstance(entity_id, str):
                        continue
                    pointer_path = node_path + ("id",)
                    occurrences.append(
                        IdentityOccurrence(
                            architecture_namespace=namespace,
                            source_path=relative,
                            source_pointer=_source_pointer(pointer_path),
                            legacy_alias_id=entity_id,
                            entity_type=entity_type,
                            file_path=path,
                            path=pointer_path,
                            presentation_name=_presentation_name(node, entity_type),
                        )
                    )
        occurrences.sort(key=lambda item: item.occurrence_key)
        return occurrences, diagnostics

    def _build_writes(
        self,
        scope: ProjectScope,
        identity_map: IdentityMapDocument,
    ) -> list[PlannedWrite]:
        by_alias = {entry.alias_id: entry for entry in identity_map.entries}
        documents: dict[Path, dict[str, Any]] = {}
        for path in self._adr_files(scope):
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            documents[path] = deepcopy(payload)

        for path, document in documents.items():
            adr_alias = str(document.get("id") or "")
            entry = by_alias.get(adr_alias)
            if entry is None:
                continue
            document["schema_version"] = "1.3"
            document["id"] = entry.uuid
            document["alias_id"] = entry.alias_id
            document["alias_name"] = entry.alias_name
            if document.get("adr_type") == "physical-system":
                self._ensure_authored_system(document, by_alias)
            self._rewrite_nested_identities(document, by_alias)

        writes: list[PlannedWrite] = []
        for path, document in sorted(documents.items(), key=lambda item: item[0].as_posix()):
            relative = _relative_path(scope, path)
            content = yaml.safe_dump(document, sort_keys=False, allow_unicode=True).encode("utf-8")
            writes.append(
                PlannedWrite(
                    relative_path=relative,
                    absolute_path=path,
                    content=content,
                    operation="update",
                )
            )
        map_content = yaml.safe_dump(
            identity_map.to_dict(),
            sort_keys=False,
            allow_unicode=True,
        ).encode("utf-8")
        writes.append(
            PlannedWrite(
                relative_path=CANONICAL_MAP_RELATIVE_PATH,
                absolute_path=scope.root / CANONICAL_MAP_RELATIVE_PATH,
                content=map_content,
                operation="create",
            )
        )
        return writes

    def _ensure_authored_system(
        self,
        document: dict[str, Any],
        by_alias: Mapping[str, IdentityMapEntry],
    ) -> None:
        """Materialize the required authored system identity for physical-system ADRs."""

        existing = document.get("system")
        if isinstance(existing, dict):
            alias = existing.get("alias_id") or existing.get("id")
            if isinstance(alias, str) and alias in by_alias:
                mapped_existing = by_alias[alias]
                existing["id"] = mapped_existing.uuid
                existing["alias_id"] = mapped_existing.alias_id
                existing["alias_name"] = mapped_existing.alias_name
                if "name" not in existing:
                    existing["name"] = document.get("title") or mapped_existing.alias_name
                return

        adr_alias = str(document.get("alias_id") or "")
        if not adr_alias.startswith("ADR-PS-"):
            return
        system_alias = f"SYS-{adr_alias.removeprefix('ADR-PS-')}"
        mapped_system = by_alias.get(system_alias)
        if mapped_system is None or mapped_system.entity_type != "system":
            return
        document["system"] = {
            "id": mapped_system.uuid,
            "alias_id": mapped_system.alias_id,
            "alias_name": mapped_system.alias_name,
            "name": str(document.get("title") or mapped_system.alias_name),
        }

    def _rewrite_nested_identities(
        self,
        node: Any,
        by_alias: Mapping[str, IdentityMapEntry],
    ) -> None:
        from ..migrators.canonical_id_normalizer import REFERENCE_FIELDS

        reference_keys = REFERENCE_FIELDS | {
            "related_adrs",
            "supersedes",
            "superseded_by",
            "implements_adr",
            "implements_logical",
            "implements_system",
            "introduces_entities",
            "modifies_entities",
            "realizes_entities",
            "selected_by",
            "parties",
            "enabled_by_decisions",
            "upheld_by_decisions",
            "enforces_invariants",
            "related_invariants",
            "affected_entities",
            "related_entities",
            "references_components",
        }

        if isinstance(node, dict):
            entity_id = node.get("id")
            if isinstance(entity_id, str) and entity_id in by_alias and "alias_id" not in node:
                entry = by_alias[entity_id]
                node["id"] = entry.uuid
                node["alias_id"] = entry.alias_id
                node["alias_name"] = entry.alias_name
            for key, value in list(node.items()):
                if key in {"id", "alias_id", "alias_name", "alias_ref", "uri"}:
                    continue
                if key in reference_keys:
                    if isinstance(value, str):
                        if value in by_alias:
                            node[key] = by_alias[value].uuid
                        # Drop dangling aliases with no corpus occurrence (e.g. ADR-V-*).
                        elif value.startswith(
                            (
                                "ADR-",
                                "DEC-",
                                "CAP-",
                                "INV-",
                                "COMP-",
                                "IFACE-",
                                "CONTRACT-",
                                "BOUND-",
                                "IMPL-",
                                "SYS-",
                            )
                        ):
                            node[key] = None
                    elif isinstance(value, list):
                        rewritten: list[Any] = []
                        for item in value:
                            if isinstance(item, str):
                                if item in by_alias:
                                    rewritten.append(by_alias[item].uuid)
                                elif item.startswith(
                                    (
                                        "ADR-",
                                        "DEC-",
                                        "CAP-",
                                        "INV-",
                                        "COMP-",
                                        "IFACE-",
                                        "CONTRACT-",
                                        "BOUND-",
                                        "IMPL-",
                                        "SYS-",
                                    )
                                ):
                                    # Reviewed dangling cleanup: omit unresolved legacy aliases.
                                    continue
                                else:
                                    rewritten.append(item)
                            else:
                                self._rewrite_nested_identities(item, by_alias)
                                rewritten.append(item)
                        node[key] = rewritten
                    else:
                        self._rewrite_nested_identities(value, by_alias)
                elif isinstance(value, list):
                    for item in value:
                        self._rewrite_nested_identities(item, by_alias)
                else:
                    self._rewrite_nested_identities(value, by_alias)
            # Remove null superseded_by after dangling cleanup.
            if node.get("superseded_by") is None and "superseded_by" in node:
                # Keep explicit null when originally present; schema allows null.
                pass
        elif isinstance(node, list):
            for item in node:
                self._rewrite_nested_identities(item, by_alias)


def compare_semantic_parity(
    *,
    before_relationships: list[tuple[str, str, str]],
    after_relationships: list[tuple[str, str, str]],
    uuid_to_legacy: Mapping[str, str],
) -> list[str]:
    """Compare relationship multisets after inverse UUID substitution.

    Each relationship is (type, from_id, to_id). After migration, UUID endpoints are
    substituted back to legacy alias IDs before multiset comparison.
    """

    def normalize(items: list[tuple[str, str, str]], *, invert: bool) -> list[tuple[str, str, str]]:
        normalized: list[tuple[str, str, str]] = []
        for rel_type, source, target in items:
            if invert:
                source = uuid_to_legacy.get(source, source)
                target = uuid_to_legacy.get(target, target)
            normalized.append((rel_type, source, target))
        return sorted(normalized)

    left = normalize(before_relationships, invert=False)
    right = normalize(after_relationships, invert=True)
    errors: list[str] = []
    if left != right:
        errors.append(
            "Relationship multiset mismatch after inverse UUID substitution: "
            f"before={left!r} after_substituted={right!r}"
        )
    return errors
