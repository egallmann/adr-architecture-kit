"""Read-only multi-provider resolution by architecture_namespace."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

from ..decorators import implements_adr
from ..identity import UUIDV7_PATTERN, derive_entity_uri, validate_uuidv7
from ..models.v2_0 import NormalizedEntityV2
from .architecture_repository import ArchitectureRegistryError, ArchitectureRepository


@dataclass(frozen=True, slots=True)
class ProviderBinding:
    """One workspace routing key bound to a loaded architecture repository."""

    workspace_key: str
    architecture_namespace: str
    project_root: Path
    repository: ArchitectureRepository


@implements_adr("ADR-L-0019", "ADR-L-0012")
class ProviderRegistry:
    """Read-only map of workspace keys → repositories, indexed by namespace.

    Does not mutate provider data or absorb ste-kernel orchestration.
    """

    def __init__(self, bindings: tuple[ProviderBinding, ...]) -> None:
        if not bindings:
            raise ArchitectureRegistryError("Provider registry requires at least one provider")
        by_key: dict[str, ProviderBinding] = {}
        by_namespace: dict[str, ProviderBinding] = {}
        for binding in bindings:
            if binding.workspace_key in by_key:
                raise ArchitectureRegistryError(
                    f"Duplicate workspace routing key: {binding.workspace_key}"
                )
            if binding.architecture_namespace in by_namespace:
                raise ArchitectureRegistryError(
                    "Duplicate architecture_namespace across providers: "
                    f"{binding.architecture_namespace}"
                )
            by_key[binding.workspace_key] = binding
            by_namespace[binding.architecture_namespace] = binding
        self._by_key = by_key
        self._by_namespace = by_namespace
        self._bindings = bindings

    @classmethod
    def from_workspace_roots(
        cls,
        workspace_roots: Mapping[str, str | Path],
    ) -> ProviderRegistry:
        """Open repositories for each workspace key and index by PROJECT.yaml namespace."""

        bindings: list[ProviderBinding] = []
        for key in sorted(workspace_roots):
            root = Path(workspace_roots[key]).expanduser().resolve()
            namespace = _load_architecture_namespace(root)
            repository = ArchitectureRepository(project_root=root)
            repository.load()
            bindings.append(
                ProviderBinding(
                    workspace_key=key,
                    architecture_namespace=namespace,
                    project_root=root,
                    repository=repository,
                )
            )
        return cls(tuple(bindings))

    def list_providers(self) -> tuple[ProviderBinding, ...]:
        """Return deterministic provider bindings."""

        return self._bindings

    def get_repository(self, workspace_key: str) -> ArchitectureRepository:
        """Return the repository for a workspace routing key."""

        binding = self._by_key.get(workspace_key)
        if binding is None:
            raise ArchitectureRegistryError(f"Unknown workspace routing key: {workspace_key}")
        return binding.repository

    def get_repository_by_namespace(self, architecture_namespace: str) -> ArchitectureRepository:
        """Return the repository for a provider architecture_namespace."""

        binding = self._by_namespace.get(architecture_namespace)
        if binding is None:
            raise ArchitectureRegistryError(
                f"Unknown architecture_namespace: {architecture_namespace}"
            )
        return binding.repository

    def resolve_entity(
        self,
        architecture_namespace: str,
        uuid: str,
    ) -> NormalizedEntityV2:
        """Resolve (namespace, UUID) through the owning provider repository."""

        validate_uuidv7(uuid)
        repository = self.get_repository_by_namespace(architecture_namespace)
        entity = repository.find_entity_by_uuid(uuid)
        if entity is None:
            raise ArchitectureRegistryError(
                f"Entity not found for namespace={architecture_namespace!r} uuid={uuid}"
            )
        expected_uri = derive_entity_uri(architecture_namespace, uuid)
        if entity.uri != expected_uri:
            raise ArchitectureRegistryError(
                f"Provider URI mismatch for {uuid}: expected {expected_uri}, got {entity.uri}"
            )
        return entity

    def resolve_uri(self, uri: str) -> NormalizedEntityV2:
        """Resolve an adr:// URI by provider namespace ownership."""

        namespace, uuid = _parse_entity_uri(uri)
        return self.resolve_entity(namespace, uuid)


def _load_architecture_namespace(project_root: Path) -> str:
    project_path = project_root / "PROJECT.yaml"
    if not project_path.is_file():
        raise ArchitectureRegistryError(f"PROJECT.yaml missing for provider root: {project_root}")
    try:
        data = yaml.safe_load(project_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ArchitectureRegistryError(
            f"Failed to read PROJECT.yaml at {project_path}: {exc}"
        ) from exc
    namespace = (data.get("architecture_documentation") or {}).get("architecture_namespace")
    if not isinstance(namespace, str) or not namespace:
        raise ArchitectureRegistryError(
            f"PROJECT.yaml missing architecture_documentation.architecture_namespace: {project_path}"
        )
    return namespace


_URI_PATTERN_PREFIX = "adr://"


def _parse_entity_uri(uri: str) -> tuple[str, str]:
    if not isinstance(uri, str) or not uri.startswith(_URI_PATTERN_PREFIX):
        raise ArchitectureRegistryError(f"Not an adr:// entity URI: {uri!r}")
    remainder = uri[len(_URI_PATTERN_PREFIX) :]
    marker = "/entities/"
    if marker not in remainder:
        raise ArchitectureRegistryError(f"Not an adr:// entity URI: {uri!r}")
    namespace, uuid = remainder.split(marker, 1)
    if not namespace or not UUIDV7_PATTERN.match(uuid):
        raise ArchitectureRegistryError(f"Not an adr:// entity URI: {uri!r}")
    return namespace, uuid
