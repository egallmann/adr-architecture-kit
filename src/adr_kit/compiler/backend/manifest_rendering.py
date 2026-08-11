"""Compiler-owned manifest rendering helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

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
from ..frontend.adr_access import (
    field_get,
    field_list,
    is_physical_adr,
    is_physical_component_adr,
    is_physical_system_adr,
)


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
            logical_adr = parser.parse_logical_adr(file_path)
            logical_adrs.append((logical_adr, file_path.resolve()))
        except Exception as exc:
            print(f"Warning: Failed to parse {file_path}: {exc}")

    for file_path in physical_candidate_files:
        try:
            parsed = parser.parse_adr(file_path)
            if is_physical_component_adr(parsed):
                physical_component_adrs.append(
                    (cast(PhysicalComponentADR, parsed), file_path)
                )
            elif is_physical_system_adr(parsed):
                physical_system_adrs.append((cast(PhysicalSystemADR, parsed), file_path))
            elif is_physical_adr(parsed):
                physical_adrs.append((cast(PhysicalADR, parsed), file_path))
        except Exception as exc:
            print(f"Warning: Failed to parse {file_path}: {exc}")

    manifest_entries: List[ManifestADREntry] = []

    def _presentation_id(obj: Any) -> str:
        alias = field_get(obj, "alias_id")
        if isinstance(alias, str) and alias:
            return alias
        value = field_get(obj, "id")
        return value if isinstance(value, str) else str(obj)

    uuid_to_alias: Dict[str, str] = {}
    all_parsed_adrs: List[
        Tuple[LogicalADR | PhysicalADR | PhysicalSystemADR | PhysicalComponentADR, Path]
    ] = [
        *logical_adrs,
        *physical_adrs,
        *physical_system_adrs,
        *physical_component_adrs,
    ]
    for parsed_adr, _ in all_parsed_adrs:
        alias = field_get(parsed_adr, "alias_id")
        adr_id = field_get(parsed_adr, "id")
        if isinstance(alias, str) and isinstance(adr_id, str):
            uuid_to_alias[adr_id] = alias
        authored = field_get(parsed_adr, "system")
        if authored is not None:
            sys_id = field_get(authored, "id")
            sys_alias = field_get(authored, "alias_id")
            if isinstance(sys_id, str) and isinstance(sys_alias, str):
                uuid_to_alias[sys_id] = sys_alias

    def _ref_id(value: str) -> str:
        return uuid_to_alias.get(value, value)

    def _manifest_governance_fields(adr: Any) -> dict[str, Any]:
        governance = field_get(adr, "governance")
        related_ledgers = field_list(governance, "related_ledgers") if governance else field_list(
            adr, "related_ledgers"
        )
        impl_auth = field_get(governance, "implementation_authority") if governance else None
        return {
            "implementation_authority": (
                getattr(impl_auth, "value", None) if impl_auth is not None else None
            ),
            "related_reviews": field_list(governance, "related_reviews") if governance else [],
            "related_overrides": field_list(governance, "related_overrides") if governance else [],
            "related_ledgers": related_ledgers,
        }

    def _gap_stats(adr: Any) -> tuple[int, int]:
        gaps = field_list(adr, "gaps")
        return len(gaps), sum(1 for gap in gaps if field_get(gap, "blocking"))

    for logical_adr, file_path in logical_adrs:
        gap_count, blocking_gaps = _gap_stats(logical_adr)
        manifest_entries.append(
            ManifestADREntry(
                id=_presentation_id(logical_adr),
                type="logical",
                title=logical_adr.title,
                status=logical_adr.status,
                file_path=relative_manifest_path(file_path, adr_dir),
                domains=field_list(logical_adr, "domains"),
                tags=field_list(logical_adr, "tags"),
                decision_count=len(field_list(logical_adr, "decisions")),
                invariant_count=len(field_list(logical_adr, "invariants")),
                gap_count=gap_count,
                blocking_gaps=blocking_gaps,
                **_manifest_governance_fields(logical_adr),
            )
        )

    for physical_adr, file_path in physical_adrs:
        gap_count, blocking_gaps = _gap_stats(physical_adr)
        manifest_entries.append(
            ManifestADREntry(
                id=_presentation_id(physical_adr),
                type="physical",
                title=physical_adr.title,
                status=physical_adr.status,
                file_path=relative_manifest_path(file_path, adr_dir),
                domains=field_list(physical_adr, "domains"),
                tags=field_list(physical_adr, "tags"),
                implements_logical=[
                    _ref_id(item) for item in field_list(physical_adr, "implements_logical")
                ],
                technologies=field_list(physical_adr, "technologies"),
                component_count=len(field_list(physical_adr, "component_specifications")),
                gap_count=gap_count,
                blocking_gaps=blocking_gaps,
                **_manifest_governance_fields(physical_adr),
            )
        )

    for system_adr, file_path in physical_system_adrs:
        gap_count, blocking_gaps = _gap_stats(system_adr)
        manifest_entries.append(
            ManifestADREntry(
                id=_presentation_id(system_adr),
                type="physical-system",
                title=system_adr.title,
                status=system_adr.status,
                file_path=relative_manifest_path(file_path, adr_dir),
                domains=field_list(system_adr, "domains"),
                tags=field_list(system_adr, "tags"),
                implements_logical=[
                    _ref_id(item) for item in field_list(system_adr, "implements_logical")
                ],
                technologies=field_list(system_adr, "technologies"),
                gap_count=gap_count,
                blocking_gaps=blocking_gaps,
                **_manifest_governance_fields(system_adr),
            )
        )

    for component_adr, file_path in physical_component_adrs:
        gap_count, blocking_gaps = _gap_stats(component_adr)
        manifest_entries.append(
            ManifestADREntry(
                id=_presentation_id(component_adr),
                type="physical-component",
                title=component_adr.title,
                status=component_adr.status,
                file_path=relative_manifest_path(file_path, adr_dir),
                domains=field_list(component_adr, "domains"),
                tags=field_list(component_adr, "tags"),
                implements_logical=[
                    _ref_id(item) for item in field_list(component_adr, "implements_logical")
                ],
                technologies=field_list(component_adr, "technologies"),
                component_count=len(field_list(component_adr, "component_specifications")),
                gap_count=gap_count,
                blocking_gaps=blocking_gaps,
                **_manifest_governance_fields(component_adr),
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
    for physical_adr, _ in physical_adrs:
        for logical_id in field_list(physical_adr, "implements_logical"):
            logical_to_physical.setdefault(_ref_id(logical_id), []).append(
                _presentation_id(physical_adr)
            )
    for system_adr, _ in physical_system_adrs:
        for logical_id in field_list(system_adr, "implements_logical"):
            logical_to_physical.setdefault(_ref_id(logical_id), []).append(
                _presentation_id(system_adr)
            )
    for component_adr, _ in physical_component_adrs:
        for logical_id in field_list(component_adr, "implements_logical"):
            logical_to_physical.setdefault(_ref_id(logical_id), []).append(
                _presentation_id(component_adr)
            )

    system_to_components: Dict[str, List[str]] = {}
    for component_adr, _ in physical_component_adrs:
        for system_id in field_list(component_adr, "implements_system"):
            # implements_system may reference ADR-PS UUID; map to system or ADR alias.
            system_to_components.setdefault(_ref_id(system_id), []).append(
                _presentation_id(component_adr)
            )

    manifest_invariants: List[ManifestInvariant] = []
    for logical_adr, _ in logical_adrs:
        for inv in field_list(logical_adr, "invariants"):
            manifest_invariants.append(
                ManifestInvariant(
                    id=_presentation_id(inv),
                    statement=field_get(inv, "statement") or "",
                    defined_in=_presentation_id(logical_adr),
                    enforced_by=[],
                    enforcement_level=(
                        inv.enforcement_level.value
                        if hasattr(field_get(inv, "enforcement_level"), "value")
                        else str(field_get(inv, "enforcement_level"))
                    ),
                )
            )

    entity_map: Dict[str, ManifestEntity] = {}
    for logical_adr, _ in logical_adrs:
        status_value = (
            logical_adr.status.value
            if hasattr(logical_adr.status, "value")
            else str(logical_adr.status)
        )
        introduced_by = _presentation_id(logical_adr)
        for cap in field_list(logical_adr, "capabilities"):
            entity_map.setdefault(
                _presentation_id(cap),
                ManifestEntity(
                    entity_id=_presentation_id(cap),
                    entity_type="capability",
                    name=field_get(cap, "name") or _presentation_id(cap),
                    introduced_by=introduced_by,
                    lifecycle_stage=status_value,
                ),
            )
        for bound in field_list(logical_adr, "architectural_boundaries"):
            entity_map.setdefault(
                _presentation_id(bound),
                ManifestEntity(
                    entity_id=_presentation_id(bound),
                    entity_type="boundary",
                    name=field_get(bound, "name") or _presentation_id(bound),
                    introduced_by=introduced_by,
                    lifecycle_stage=status_value,
                ),
            )
        for contract in field_list(logical_adr, "interaction_contracts"):
            parties = field_list(contract, "parties")
            entity_map.setdefault(
                _presentation_id(contract),
                ManifestEntity(
                    entity_id=_presentation_id(contract),
                    entity_type="contract",
                    name=parties[0] if parties else "Unknown",
                    introduced_by=introduced_by,
                    lifecycle_stage=status_value,
                ),
            )
        for const in field_list(logical_adr, "constraints"):
            # Constraints are not admitted in v1.3 identity; skip non-alias entities.
            const_id = _presentation_id(const)
            if not str(const_id).startswith(("CONST-", "CONSTRAINT-")) and "-" in str(const_id) and len(str(const_id)) > 20:
                continue
            entity_map.setdefault(
                const_id,
                ManifestEntity(
                    entity_id=const_id,
                    entity_type="constraint",
                    name=field_get(const, "type") or const_id,
                    introduced_by=introduced_by,
                    lifecycle_stage=status_value,
                ),
            )
        for nfr in field_list(logical_adr, "non_functional_requirements"):
            nfr_id = _presentation_id(nfr)
            if not str(nfr_id).startswith("NFR-") and len(str(nfr_id)) > 20:
                continue
            entity_map.setdefault(
                nfr_id,
                ManifestEntity(
                    entity_id=nfr_id,
                    entity_type="nfr",
                    name=field_get(nfr, "category") or nfr_id,
                    introduced_by=introduced_by,
                    lifecycle_stage=status_value,
                ),
            )
        for dec in field_list(logical_adr, "decisions"):
            entity_map.setdefault(
                _presentation_id(dec),
                ManifestEntity(
                    entity_id=_presentation_id(dec),
                    entity_type="decision",
                    name=field_get(dec, "summary") or _presentation_id(dec),
                    introduced_by=introduced_by,
                    lifecycle_stage=status_value,
                ),
            )
        for gap in field_list(logical_adr, "gaps"):
            gap_id = field_get(gap, "id")
            if not isinstance(gap_id, str) or not gap_id.startswith("GAP-"):
                continue
            question = field_get(gap, "question") or gap_id
            entity_map.setdefault(
                gap_id,
                ManifestEntity(
                    entity_id=gap_id,
                    entity_type="gap",
                    name=str(question)[:50],
                    introduced_by=introduced_by,
                    lifecycle_stage=status_value,
                ),
            )

    for physical_like, _ in [*physical_adrs, *physical_component_adrs]:
        status_value = (
            physical_like.status.value
            if hasattr(physical_like.status, "value")
            else str(physical_like.status)
        )
        introduced_by = _presentation_id(physical_like)
        for comp in field_list(physical_like, "component_specifications"):
            comp_id = _presentation_id(comp)
            if not str(comp_id).startswith(("COMP-", "COMP")):
                # Prefer alias; skip raw UUIDs without alias.
                alias = field_get(comp, "alias_id")
                if not isinstance(alias, str) or not alias.startswith("COMP-"):
                    continue
                comp_id = alias
            entity_map.setdefault(
                comp_id,
                ManifestEntity(
                    entity_id=comp_id,
                    entity_type="component",
                    name=field_get(comp, "name") or comp_id,
                    introduced_by=introduced_by,
                    lifecycle_stage=status_value,
                ),
            )
            for iface in field_list(comp, "interfaces"):
                iface_id = _presentation_id(iface)
                if not str(iface_id).startswith("IFACE-"):
                    continue
                entity_map.setdefault(
                    iface_id,
                    ManifestEntity(
                        entity_id=iface_id,
                        entity_type="interface",
                        name=f"{field_get(comp, 'name') or comp_id} {field_get(iface, 'type') or ''}".strip(),
                        introduced_by=introduced_by,
                        lifecycle_stage=status_value,
                    ),
                )
        for integ in field_list(physical_like, "integration_points"):
            integ_id = field_get(integ, "id")
            if not isinstance(integ_id, str) or not integ_id.startswith(("INT-", "INTEG-")):
                continue
            systems = field_list(integ, "systems")
            entity_map.setdefault(
                integ_id,
                ManifestEntity(
                    entity_id=integ_id,
                    entity_type="integration",
                    name=" → ".join(str(item) for item in systems) if systems else integ_id,
                    introduced_by=introduced_by,
                    lifecycle_stage=status_value,
                ),
            )
        for impl_dec in field_list(physical_like, "implementation_decisions"):
            impl_id = _presentation_id(impl_dec)
            if not str(impl_id).startswith("IMPL-"):
                continue
            entity_map.setdefault(
                impl_id,
                ManifestEntity(
                    entity_id=impl_id,
                    entity_type="implementation_decision",
                    name=field_get(impl_dec, "summary") or impl_id,
                    introduced_by=introduced_by,
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
                    related_adr=_ref_id(override.related_adr),
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
                    target_adr=_ref_id(review.target_adr),
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
