"""Compiler-owned manifest rendering helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from ...integrity import (
    ArtifactKind,
    GENERATED_MARKER,
    HASH_ALGORITHM,
    INTEGRITY_SCHEMA_VERSION,
    GeneratorIdentity,
    build_yaml_header,
    compute_rendered_hash,
    compute_source_hash,
)
from ...models import (
    GapSummaryByADR,
    GapsSummary,
    LogicalADR,
    Manifest,
    ManifestADREntry,
    ManifestDecisionLedger,
    ManifestEntity,
    ManifestInvariant,
    ManifestObjectionOverride,
    ManifestSteelmanReview,
    ManifestRequirementsSnapshot,
    ManifestStatistics,
    PhysicalADR,
    PhysicalComponentADR,
    PhysicalSystemADR,
)
from ...parser import ADRParser
from ...pathing import manifest_relative_path
from ...scope import ProjectScope, ProjectScopeResolver


MANIFEST_GENERATOR_IDENTITY = GeneratorIdentity("adr-manifest", 1)


def discover_manifest_adr_files(adr_dir: Path) -> Tuple[List[Path], List[Path]]:
    """Discover logical and physical ADR files deterministically."""
    logical_files = sorted((adr_dir / "logical").glob("*.yaml")) if (adr_dir / "logical").exists() else []

    physical_files: List[Path] = []
    for dirname in ("physical", "physical-system", "physical-component"):
        candidate_dir = adr_dir / dirname
        if candidate_dir.exists():
            physical_files.extend(sorted(candidate_dir.glob("*.yaml")))

    deduped_physical = sorted(dict.fromkeys(path.resolve() for path in physical_files))
    return logical_files, [Path(path) for path in deduped_physical]


def relative_manifest_path(file_path: Path, adr_dir: Path) -> str:
    """Return the manifest-relative path for a discovered ADR file."""
    return manifest_relative_path(adr_dir.parent, file_path)


def build_manifest_from_directory(
    adr_dir: Path,
    *,
    parser: ADRParser,
    scope: Optional[ProjectScope] = None,
    scope_resolver: ProjectScopeResolver | None = None,
    generated_at: Optional[datetime] = None,
) -> Manifest:
    """Build the manifest model for one ADR directory."""
    adr_dir = Path(adr_dir).resolve()
    if not adr_dir.exists():
        raise ValueError(f"ADR directory not found: {adr_dir}")

    if scope is None:
        resolver = scope_resolver or ProjectScopeResolver()
        scope = resolver.resolve(adr_dir.parent)
        print(f"Auto-detected project scope: {scope.name} at {scope.root}")

    logical_files, physical_candidate_files = discover_manifest_adr_files(adr_dir)
    req_snapshot_files = (
        list((adr_dir / "requirements" / "snapshots").glob("*.yaml"))
        if (adr_dir / "requirements" / "snapshots").exists()
        else []
    )
    decision_ledger_files = (
        list((adr_dir / "decisions" / "ledgers").glob("*.yaml"))
        if (adr_dir / "decisions" / "ledgers").exists()
        else []
    )
    objection_override_files = (
        list((adr_dir / "decisions" / "overrides").glob("*.yaml"))
        if (adr_dir / "decisions" / "overrides").exists()
        else []
    )
    steelman_review_files = (
        list((adr_dir / "decisions" / "reviews").glob("*.yaml"))
        if (adr_dir / "decisions" / "reviews").exists()
        else []
    )

    logical_adrs: List[Tuple[LogicalADR, Path]] = []
    physical_adrs: List[Tuple[PhysicalADR, Path]] = []
    physical_system_adrs: List[Tuple[PhysicalSystemADR, Path]] = []
    physical_component_adrs: List[Tuple[PhysicalComponentADR, Path]] = []

    for file_path in logical_files:
        try:
            adr = parser.parse_logical_adr(file_path)
            logical_adrs.append((adr, file_path.resolve()))
        except Exception as exc:
            print(f"Warning: Failed to parse {file_path}: {exc}")

    for file_path in physical_candidate_files:
        try:
            adr = parser.parse_adr(file_path)
            if isinstance(adr, PhysicalComponentADR):
                physical_component_adrs.append((adr, file_path))
            elif isinstance(adr, PhysicalSystemADR):
                physical_system_adrs.append((adr, file_path))
            elif isinstance(adr, PhysicalADR):
                physical_adrs.append((adr, file_path))
        except Exception as exc:
            print(f"Warning: Failed to parse {file_path}: {exc}")

    manifest_entries: List[ManifestADREntry] = []

    for adr, file_path in logical_adrs:
        governance = adr.governance
        manifest_entries.append(
            ManifestADREntry(
                id=adr.id,
                type="logical",
                title=adr.title,
                status=adr.status,
                file_path=relative_manifest_path(file_path, adr_dir),
                domains=adr.domains,
                tags=adr.tags,
                decision_count=len(adr.decisions),
                invariant_count=len(adr.invariants),
                gap_count=len(adr.gaps),
                blocking_gaps=sum(1 for gap in adr.gaps if gap.blocking),
                implementation_authority=governance.implementation_authority.value if governance and governance.implementation_authority else None,
                related_reviews=list(governance.related_reviews) if governance else [],
                related_overrides=list(governance.related_overrides) if governance else [],
                related_ledgers=list(governance.related_ledgers) if governance else list(adr.related_ledgers),
            )
        )

    for adr, file_path in physical_adrs:
        governance = adr.governance
        manifest_entries.append(
            ManifestADREntry(
                id=adr.id,
                type="physical",
                title=adr.title,
                status=adr.status,
                file_path=relative_manifest_path(file_path, adr_dir),
                domains=adr.domains,
                tags=adr.tags,
                implements_logical=adr.implements_logical,
                technologies=adr.technologies,
                component_count=len(adr.component_specifications),
                gap_count=len(adr.gaps),
                blocking_gaps=sum(1 for gap in adr.gaps if gap.blocking),
                implementation_authority=governance.implementation_authority.value if governance and governance.implementation_authority else None,
                related_reviews=list(governance.related_reviews) if governance else [],
                related_overrides=list(governance.related_overrides) if governance else [],
                related_ledgers=list(governance.related_ledgers) if governance else list(adr.related_ledgers),
            )
        )

    for adr, file_path in physical_system_adrs:
        governance = adr.governance
        manifest_entries.append(
            ManifestADREntry(
                id=adr.id,
                type="physical-system",
                title=adr.title,
                status=adr.status,
                file_path=relative_manifest_path(file_path, adr_dir),
                domains=adr.domains,
                tags=adr.tags,
                implements_logical=adr.implements_logical,
                technologies=adr.technologies,
                gap_count=len(adr.gaps),
                blocking_gaps=sum(1 for gap in adr.gaps if gap.blocking),
                implementation_authority=governance.implementation_authority.value if governance and governance.implementation_authority else None,
                related_reviews=list(governance.related_reviews) if governance else [],
                related_overrides=list(governance.related_overrides) if governance else [],
                related_ledgers=list(governance.related_ledgers) if governance else list(adr.related_ledgers),
            )
        )

    for adr, file_path in physical_component_adrs:
        governance = adr.governance
        manifest_entries.append(
            ManifestADREntry(
                id=adr.id,
                type="physical-component",
                title=adr.title,
                status=adr.status,
                file_path=relative_manifest_path(file_path, adr_dir),
                domains=adr.domains,
                tags=adr.tags,
                implements_logical=adr.implements_logical,
                technologies=adr.technologies,
                component_count=len(adr.component_specifications),
                gap_count=len(adr.gaps),
                blocking_gaps=sum(1 for gap in adr.gaps if gap.blocking),
                implementation_authority=governance.implementation_authority.value if governance and governance.implementation_authority else None,
                related_reviews=list(governance.related_reviews) if governance else [],
                related_overrides=list(governance.related_overrides) if governance else [],
                related_ledgers=list(governance.related_ledgers) if governance else list(adr.related_ledgers),
            )
        )

    by_domain: Dict[str, List[str]] = {}
    by_status: Dict[str, List[str]] = {}
    by_technology: Dict[str, List[str]] = {}
    for entry in manifest_entries:
        for domain in entry.domains:
            by_domain.setdefault(domain, []).append(entry.id)
        status_key = entry.status.value if hasattr(entry.status, "value") else str(entry.status)
        by_status.setdefault(status_key, []).append(entry.id)
        for tech in entry.technologies:
            by_technology.setdefault(tech, []).append(entry.id)

    logical_to_physical: Dict[str, List[str]] = {}
    for adr, _ in physical_adrs:
        for logical_id in adr.implements_logical:
            logical_to_physical.setdefault(logical_id, []).append(adr.id)
    for adr, _ in physical_system_adrs:
        for logical_id in adr.implements_logical:
            logical_to_physical.setdefault(logical_id, []).append(adr.id)
    for adr, _ in physical_component_adrs:
        for logical_id in adr.implements_logical:
            logical_to_physical.setdefault(logical_id, []).append(adr.id)

    system_to_components: Dict[str, List[str]] = {}
    for adr, _ in physical_component_adrs:
        for system_id in adr.implements_system:
            system_to_components.setdefault(system_id, []).append(adr.id)

    manifest_invariants: List[ManifestInvariant] = []
    for adr, _ in logical_adrs:
        for inv in adr.invariants:
            manifest_invariants.append(
                ManifestInvariant(
                    id=inv.id,
                    statement=inv.statement,
                    defined_in=adr.id,
                    enforced_by=[],
                    enforcement_level=inv.enforcement_level.value if hasattr(inv.enforcement_level, "value") else str(inv.enforcement_level),
                )
            )

    entity_map: Dict[str, ManifestEntity] = {}
    for adr, _ in logical_adrs:
        status_value = adr.status.value if hasattr(adr.status, "value") else str(adr.status)
        for cap in adr.capabilities:
            entity_map.setdefault(
                cap.id,
                ManifestEntity(entity_id=cap.id, entity_type="capability", name=cap.name, introduced_by=adr.id, lifecycle_stage=status_value),
            )
        for bound in adr.architectural_boundaries:
            entity_map.setdefault(
                bound.id,
                ManifestEntity(entity_id=bound.id, entity_type="boundary", name=bound.name, introduced_by=adr.id, lifecycle_stage=status_value),
            )
        for contract in adr.interaction_contracts:
            entity_map.setdefault(
                contract.id,
                ManifestEntity(
                    entity_id=contract.id,
                    entity_type="contract",
                    name=contract.parties[0] if contract.parties else "Unknown",
                    introduced_by=adr.id,
                    lifecycle_stage=status_value,
                ),
            )
        for const in adr.constraints:
            entity_map.setdefault(
                const.id,
                ManifestEntity(entity_id=const.id, entity_type="constraint", name=const.type, introduced_by=adr.id, lifecycle_stage=status_value),
            )
        for nfr in adr.non_functional_requirements:
            entity_map.setdefault(
                nfr.id,
                ManifestEntity(entity_id=nfr.id, entity_type="nfr", name=nfr.category, introduced_by=adr.id, lifecycle_stage=status_value),
            )
        for dec in adr.decisions:
            entity_map.setdefault(
                dec.id,
                ManifestEntity(entity_id=dec.id, entity_type="decision", name=dec.summary, introduced_by=adr.id, lifecycle_stage=status_value),
            )
        for gap in adr.gaps:
            entity_map.setdefault(
                gap.id,
                ManifestEntity(entity_id=gap.id, entity_type="gap", name=gap.question[:50], introduced_by=adr.id, lifecycle_stage=status_value),
            )

    for adr, _ in physical_adrs:
        status_value = adr.status.value if hasattr(adr.status, "value") else str(adr.status)
        for comp in adr.component_specifications:
            entity_map.setdefault(
                comp.id,
                ManifestEntity(entity_id=comp.id, entity_type="component", name=comp.name, introduced_by=adr.id, lifecycle_stage=status_value),
            )
            for iface in comp.interfaces:
                entity_map.setdefault(
                    iface.id,
                    ManifestEntity(
                        entity_id=iface.id,
                        entity_type="interface",
                        name=f"{comp.name} {iface.type}",
                        introduced_by=adr.id,
                        lifecycle_stage=status_value,
                    ),
                )
        for integ in adr.integration_points:
            entity_map.setdefault(
                integ.id,
                ManifestEntity(
                    entity_id=integ.id,
                    entity_type="integration",
                    name=" → ".join(integ.systems),
                    introduced_by=adr.id,
                    lifecycle_stage=status_value,
                ),
            )
        for impl_dec in adr.implementation_decisions:
            entity_map.setdefault(
                impl_dec.id,
                ManifestEntity(
                    entity_id=impl_dec.id,
                    entity_type="implementation_decision",
                    name=impl_dec.summary,
                    introduced_by=adr.id,
                    lifecycle_stage=status_value,
                ),
            )

    manifest_req_snapshots: List[ManifestRequirementsSnapshot] = []
    for file_path in sorted(req_snapshot_files):
        try:
            snapshot = parser.parse_requirements_snapshot(file_path)
            manifest_req_snapshots.append(
                ManifestRequirementsSnapshot(
                    snapshot_id=snapshot.snapshot_id,
                    domains=snapshot.domains or [],
                    capability_count=len(snapshot.required_capabilities or []),
                )
            )
        except Exception as exc:
            print(f"Warning: Failed to parse requirements snapshot {file_path}: {exc}")

    manifest_decision_ledgers: List[ManifestDecisionLedger] = []
    for file_path in sorted(decision_ledger_files):
        try:
            ledger = parser.parse_decision_ledger(file_path)
            manifest_decision_ledgers.append(
                ManifestDecisionLedger(
                    ledger_id=ledger.ledger_id,
                    target_logical_adr=ledger.target_logical_adr,
                    decision_count=len(ledger.required_decisions),
                )
            )
        except Exception as exc:
            print(f"Warning: Failed to parse decision ledger {file_path}: {exc}")

    manifest_objection_overrides: List[ManifestObjectionOverride] = []
    for file_path in sorted(objection_override_files):
        try:
            override = parser.parse_objection_override(file_path)
            manifest_objection_overrides.append(
                ManifestObjectionOverride(
                    id=override.id,
                    related_adr=override.related_adr,
                    related_review=override.related_review,
                    implementation_effect=override.implementation_effect.value,
                )
            )
        except Exception as exc:
            print(f"Warning: Failed to parse objection override {file_path}: {exc}")

    manifest_steelman_reviews: List[ManifestSteelmanReview] = []
    for file_path in sorted(steelman_review_files):
        try:
            review = parser.parse_steelman_review(file_path)
            manifest_steelman_reviews.append(
                ManifestSteelmanReview(
                    id=review.id,
                    target_adr=review.target_adr,
                    review_kind=review.review_kind,
                    overall_recommendation=review.overall_recommendation,
                    objection_count=len(review.objections),
                    blocking_objections=sum(1 for objection in review.objections if objection.disposition.value == "blocking"),
                )
            )
        except Exception as exc:
            print(f"Warning: Failed to parse steelman review {file_path}: {exc}")

    gaps_by_adr: Dict[str, GapSummaryByADR] = {}
    total_gaps = 0
    total_blocking = 0
    for entry in manifest_entries:
        if entry.gap_count > 0:
            gaps_by_adr[entry.id] = GapSummaryByADR(total=entry.gap_count, blocking=entry.blocking_gaps)
            total_gaps += entry.gap_count
            total_blocking += entry.blocking_gaps

    statistics = ManifestStatistics(
        total_adrs=len(manifest_entries),
        logical_adrs=len(logical_adrs),
        physical_adrs=len(physical_adrs) + len(physical_system_adrs) + len(physical_component_adrs),
        physical_system_adrs=len(physical_system_adrs),
        physical_component_adrs=len(physical_component_adrs),
        decision_adrs=0,
        total_decisions=sum(len(adr.decisions) for adr, _ in logical_adrs),
        total_invariants=len(manifest_invariants),
        total_components=sum(len(adr.component_specifications) for adr, _ in physical_adrs)
        + sum(len(adr.component_specifications) for adr, _ in physical_component_adrs),
        total_gaps=total_gaps,
        blocking_gaps=total_blocking,
        total_entities=len(entity_map),
        total_requirements_snapshots=len(manifest_req_snapshots),
        total_decision_ledgers=len(manifest_decision_ledgers),
        total_objection_overrides=len(manifest_objection_overrides),
        total_steelman_reviews=len(manifest_steelman_reviews),
    )

    return Manifest(
        schema_version="1.0",
        type="manifest",
        generated_date=(generated_at or datetime.now(timezone.utc).replace(microsecond=0)),
        generated_from="adrs/**/*.yaml",
        adrs=manifest_entries,
        by_domain=by_domain,
        by_status=by_status,
        by_technology=by_technology,
        logical_to_physical_map=logical_to_physical,
        system_to_components_map=system_to_components,
        invariants=manifest_invariants,
        entities=list(entity_map.values()),
        requirements_snapshots=manifest_req_snapshots,
        decision_ledgers=manifest_decision_ledgers,
        objection_overrides=manifest_objection_overrides,
        steelman_reviews=manifest_steelman_reviews,
        gaps_summary=GapsSummary(total=total_gaps, blocking=total_blocking, by_adr=gaps_by_adr),
        statistics=statistics,
    )


def build_manifest_from_scope(
    *,
    parser: ADRParser,
    scope: ProjectScope,
    scope_resolver: ProjectScopeResolver | None = None,
    generated_at: datetime | None = None,
) -> Manifest:
    """Build the manifest model for one scope."""
    return build_manifest_from_directory(
        scope.adr_dir,
        parser=parser,
        scope=scope,
        scope_resolver=scope_resolver,
        generated_at=generated_at,
    )


def discover_manifest_source_inputs(adr_dir: Path) -> List[Path]:
    """Discover canonical manifest inputs for a scope."""
    adr_dir = Path(adr_dir).resolve()
    sources: List[Path] = []
    for relative in (
        Path("logical"),
        Path("physical"),
        Path("physical-system"),
        Path("physical-component"),
        Path("invariants"),
        Path("requirements") / "snapshots",
        Path("decisions") / "ledgers",
        Path("decisions") / "overrides",
        Path("decisions") / "reviews",
    ):
        base = adr_dir / relative
        if not base.exists():
            continue
        for file_path in sorted(base.glob("*.yaml")):
            if file_path.is_file() and not file_path.is_symlink():
                sources.append(file_path.resolve())
    return sources


def render_manifest_yaml(manifest: Manifest) -> str:
    """Render the manifest body without the integrity header."""
    manifest_dict = manifest.model_dump(mode="json", exclude_none=True)
    lines = [
        "# manifest.yaml - GENERATED FROM ADRs, DO NOT EDIT",
        "# This file is automatically generated by 'adr generate-manifest'",
        "# To update: modify ADRs, then regenerate manifest",
        "",
    ]
    return "\n".join(lines) + yaml.dump(
        manifest_dict,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )


def render_manifest_for_scope(
    *,
    parser: ADRParser,
    scope: ProjectScope,
    scope_resolver: ProjectScopeResolver | None = None,
    generated_at: datetime | None = None,
) -> tuple[str, List[Path]]:
    """Render manifest body and return canonical source inputs."""
    manifest = build_manifest_from_scope(
        parser=parser,
        scope=scope,
        scope_resolver=scope_resolver,
        generated_at=generated_at,
    )
    return render_manifest_yaml(manifest), discover_manifest_source_inputs(scope.adr_dir)


def build_manifest_integrity_header(scope: ProjectScope, body: str, source_inputs: List[Path]) -> str:
    """Build the manifest integrity header."""
    header_fields = {
        "integrity_schema_version": str(INTEGRITY_SCHEMA_VERSION),
        "generated": GENERATED_MARKER,
        "artifact_kind": ArtifactKind.MANIFEST.value,
        "generator_id": MANIFEST_GENERATOR_IDENTITY.generator_id,
        "generator_version": str(MANIFEST_GENERATOR_IDENTITY.generator_version),
        "hash_algorithm": HASH_ALGORITHM,
        "source_hash": compute_source_hash(scope.root, source_inputs, MANIFEST_GENERATOR_IDENTITY),
        "rendered_hash": compute_rendered_hash(body),
    }
    return build_yaml_header(header_fields)
