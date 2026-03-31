"""Bundle validation pass extracted from the architecture index generator."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.architecture_discovery import (
    NormalizedEntityRegistry,
    RelationshipRegistry,
    UnresolvedRegistry,
)
from ..diagnostics import Diagnostic, DiagnosticLevel, DiagnosticLog


@dataclass(frozen=True)
class BundleValidationResult:
    """Deterministic validation output for a compiled registry bundle."""

    diagnostics: list[Diagnostic]

    @property
    def is_valid(self) -> bool:
        return not any(item.level == DiagnosticLevel.ERROR for item in self.diagnostics)

    @property
    def first_error(self) -> Diagnostic | None:
        for item in self.diagnostics:
            if item.level == DiagnosticLevel.ERROR:
                return item
        return None


class ValidateBundlePass:
    """Pass-shaped helper for bundle integrity validation."""

    name = "validate_bundle"
    required = True
    depends_on: tuple[str, ...] = ()
    halts_on_error = True

    def run(
        self,
        entity_registry: NormalizedEntityRegistry,
        relationship_registry: RelationshipRegistry,
        unresolved_registry: UnresolvedRegistry,
        *,
        diagnostics: DiagnosticLog | None = None,
    ) -> BundleValidationResult:
        return validate_bundle(
            entity_registry,
            relationship_registry,
            unresolved_registry,
            diagnostics=diagnostics,
        )


def validate_bundle(
    entity_registry: NormalizedEntityRegistry,
    relationship_registry: RelationshipRegistry,
    unresolved_registry: UnresolvedRegistry,
    *,
    diagnostics: DiagnosticLog | None = None,
) -> BundleValidationResult:
    """Validate registry bundle integrity and return deterministic diagnostics."""

    log = diagnostics or DiagnosticLog()
    entity_ids = {entity.id for entity in entity_registry.entities}
    entity_lookup = {entity.id: entity for entity in entity_registry.entities}
    relationship_keys = {
        (item.relationship_type, item.from_entity_id, item.to_entity_id)
        for item in relationship_registry.relationships
    }
    unresolved_ids = [item.id for item in unresolved_registry.unresolved]

    if len(unresolved_ids) != len(set(unresolved_ids)):
        duplicates = sorted(item for item in set(unresolved_ids) if unresolved_ids.count(item) > 1)
        log.error(
            "E401",
            f"Duplicate unresolved IDs detected: {', '.join(duplicates)}",
            source_ref="unresolved_registry",
        )

    for relationship in relationship_registry.relationships:
        if relationship.from_entity_id not in entity_ids or relationship.to_entity_id not in entity_ids:
            log.error(
                "E402",
                f"Relationship references unknown entity: {relationship.relationship_id}",
                source_ref=relationship.relationship_id,
            )

    for entity in entity_registry.entities:
        for relationship_type, targets in entity.relationships.model_dump(mode="json").items():
            for target_id in targets:
                if target_id not in entity_ids:
                    log.error(
                        "E403",
                        f"Entity relationship summary references unknown entity: "
                        f"{entity.id}.{relationship_type} -> {target_id}",
                        source_ref=f"{entity.id}.{relationship_type}",
                    )
                    continue
                if (relationship_type, entity.id, target_id) not in relationship_keys:
                    log.error(
                        "E404",
                        f"Entity relationship summary missing registry edge: "
                        f"{entity.id}.{relationship_type} -> {target_id}",
                        source_ref=f"{entity.id}.{relationship_type}",
                    )

    for unresolved in unresolved_registry.unresolved:
        if unresolved.source_entity_id not in entity_lookup:
            log.error(
                "E405",
                f"Unresolved record references unknown source entity: "
                f"{unresolved.id} -> {unresolved.source_entity_id}",
                source_ref=unresolved.id,
            )

    return BundleValidationResult(diagnostics=log.as_list())
