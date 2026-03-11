"""Manifest generator - creates manifest.yaml from ADR directory (SYS-14: Index Currency).

Implements ADR-L-0007: Multi-scope ADR architecture.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ..models import (
    GapsSummary,
    GapSummaryByADR,
    LogicalADR,
    Manifest,
    ManifestADREntry,
    ManifestEntity,
    ManifestInvariant,
    ManifestRequirementsSnapshot,
    ManifestDecisionLedger,
    ManifestStatistics,
    PhysicalADR,
    PhysicalSystemADR,
    PhysicalComponentADR,
)
from ..parser import ADRParser
from ..scope import ProjectScopeResolver, ProjectScope


class ManifestGenerator:
    """Generate manifest from ADR directory.
    
    Supports multi-scope operation per ADR-L-0007.
    """
    
    def __init__(self, parser: ADRParser = None, scope_resolver: ProjectScopeResolver = None):
        """Initialize generator.
        
        Args:
            parser: ADR parser (creates new one if not provided)
            scope_resolver: Project scope resolver (creates new one if not provided)
        """
        self.parser = parser or ADRParser()
        self.scope_resolver = scope_resolver or ProjectScopeResolver()
    
    def generate_from_directory(self, adr_dir: Path, scope: Optional[ProjectScope] = None) -> Manifest:
        """Generate manifest from ADR directory.
        
        Args:
            adr_dir: Path to adrs/ directory
            scope: Project scope (auto-detected if not provided)
            
        Returns:
            Generated Manifest model
        """
        adr_dir = Path(adr_dir)
        
        # Auto-detect scope if not provided (ADR-L-0007: CAP-0001)
        if scope is None:
            scope = self.scope_resolver.resolve(adr_dir.parent)
            print(f"Auto-detected project scope: {scope.name} at {scope.root}")
        
        if not adr_dir.exists():
            raise ValueError(f"ADR directory not found: {adr_dir}")
        
        # Discover all ADR files
        logical_files = list((adr_dir / "logical").glob("*.yaml")) if (adr_dir / "logical").exists() else []
        physical_files = list((adr_dir / "physical").glob("*.yaml")) if (adr_dir / "physical").exists() else []
        physical_system_files = list((adr_dir / "physical-system").glob("*.yaml")) if (adr_dir / "physical-system").exists() else []
        physical_component_files = list((adr_dir / "physical-component").glob("*.yaml")) if (adr_dir / "physical-component").exists() else []
        
        # Discover requirements snapshots and decision ledgers
        req_snapshot_files = list((adr_dir / "requirements" / "snapshots").glob("*.yaml")) if (adr_dir / "requirements" / "snapshots").exists() else []
        decision_ledger_files = list((adr_dir / "decisions" / "ledgers").glob("*.yaml")) if (adr_dir / "decisions" / "ledgers").exists() else []
        
        # Parse all ADRs
        logical_adrs: List[LogicalADR] = []
        physical_adrs: List[PhysicalADR] = []
        physical_system_adrs: List[PhysicalSystemADR] = []
        physical_component_adrs: List[PhysicalComponentADR] = []
        
        for file_path in logical_files:
            try:
                adr = self.parser.parse_logical_adr(file_path)
                logical_adrs.append(adr)
            except Exception as e:
                print(f"Warning: Failed to parse {file_path}: {e}")
        
        for file_path in physical_files:
            try:
                adr = self.parser.parse_physical_adr(file_path)
                physical_adrs.append(adr)
            except Exception as e:
                print(f"Warning: Failed to parse {file_path}: {e}")
        
        for file_path in physical_system_files:
            try:
                adr = self.parser.parse_physical_system_adr(file_path)
                physical_system_adrs.append(adr)
            except Exception as e:
                print(f"Warning: Failed to parse {file_path}: {e}")
        
        for file_path in physical_component_files:
            try:
                adr = self.parser.parse_physical_component_adr(file_path)
                physical_component_adrs.append(adr)
            except Exception as e:
                print(f"Warning: Failed to parse {file_path}: {e}")
        
        # Build manifest entries
        manifest_entries: List[ManifestADREntry] = []
        
        for adr in logical_adrs:
            entry = ManifestADREntry(
                id=adr.id,
                type="logical",
                title=adr.title,
                status=adr.status,
                file_path=str(Path("adrs/logical") / f"{adr.id}-{self._slugify(adr.title)}.yaml"),
                domains=adr.domains,
                tags=adr.tags,
                decision_count=len(adr.decisions),
                invariant_count=len(adr.invariants),
                gap_count=len(adr.gaps),
                blocking_gaps=sum(1 for g in adr.gaps if g.blocking),
            )
            manifest_entries.append(entry)
        
        for adr in physical_adrs:
            entry = ManifestADREntry(
                id=adr.id,
                type="physical",
                title=adr.title,
                status=adr.status,
                file_path=str(Path("adrs/physical") / f"{adr.id}-{self._slugify(adr.title)}.yaml"),
                domains=adr.domains,
                tags=adr.tags,
                implements_logical=adr.implements_logical,
                technologies=adr.technologies,
                component_count=len(adr.component_specifications),
                gap_count=len(adr.gaps),
                blocking_gaps=sum(1 for g in adr.gaps if g.blocking),
            )
            manifest_entries.append(entry)
        
        for adr in physical_system_adrs:
            entry = ManifestADREntry(
                id=adr.id,
                type="physical-system",
                title=adr.title,
                status=adr.status,
                file_path=str(Path("adrs/physical-system") / f"{adr.id}-{self._slugify(adr.title)}.yaml"),
                domains=adr.domains,
                tags=adr.tags,
                implements_logical=adr.implements_logical,
                technologies=adr.technologies,
                gap_count=len(adr.gaps),
                blocking_gaps=sum(1 for g in adr.gaps if g.blocking),
            )
            manifest_entries.append(entry)
        
        for adr in physical_component_adrs:
            entry = ManifestADREntry(
                id=adr.id,
                type="physical-component",
                title=adr.title,
                status=adr.status,
                file_path=str(Path("adrs/physical-component") / f"{adr.id}-{self._slugify(adr.title)}.yaml"),
                domains=adr.domains,
                tags=adr.tags,
                implements_logical=adr.implements_logical,
                technologies=adr.technologies,
                component_count=len(adr.component_specifications),
                gap_count=len(adr.gaps),
                blocking_gaps=sum(1 for g in adr.gaps if g.blocking),
            )
            manifest_entries.append(entry)
        
        # Build discovery indexes
        by_domain: Dict[str, List[str]] = {}
        by_status: Dict[str, List[str]] = {}
        by_technology: Dict[str, List[str]] = {}
        
        for entry in manifest_entries:
            for domain in entry.domains:
                by_domain.setdefault(domain, []).append(entry.id)
            
            status_key = entry.status.value if hasattr(entry.status, 'value') else str(entry.status)
            by_status.setdefault(status_key, []).append(entry.id)
            
            for tech in entry.technologies:
                by_technology.setdefault(tech, []).append(entry.id)
        
        # Build logical to physical map
        logical_to_physical: Dict[str, List[str]] = {}
        for adr in physical_adrs:
            for logical_id in adr.implements_logical:
                logical_to_physical.setdefault(logical_id, []).append(adr.id)
        for adr in physical_system_adrs:
            for logical_id in adr.implements_logical:
                logical_to_physical.setdefault(logical_id, []).append(adr.id)
        for adr in physical_component_adrs:
            for logical_id in adr.implements_logical:
                logical_to_physical.setdefault(logical_id, []).append(adr.id)
        
        # Build system to component map
        system_to_components: Dict[str, List[str]] = {}
        for adr in physical_component_adrs:
            for system_id in adr.implements_system:
                system_to_components.setdefault(system_id, []).append(adr.id)
        
        # Extract all invariants
        manifest_invariants: List[ManifestInvariant] = []
        for adr in logical_adrs:
            for inv in adr.invariants:
                manifest_inv = ManifestInvariant(
                    id=inv.id,
                    statement=inv.statement,
                    defined_in=adr.id,
                    enforced_by=[],
                    enforcement_level=inv.enforcement_level.value if hasattr(inv.enforcement_level, 'value') else str(inv.enforcement_level),
                )
                manifest_invariants.append(manifest_inv)
        
        # Extract all entities from ADRs
        manifest_entities: List[ManifestEntity] = []
        entity_map: Dict[str, ManifestEntity] = {}
        
        # Extract from Logical ADRs (capabilities, boundaries, contracts, etc.)
        for adr in logical_adrs:
            for cap in adr.capabilities:
                if cap.id not in entity_map:
                    entity_map[cap.id] = ManifestEntity(
                        entity_id=cap.id,
                        entity_type="capability",
                        name=cap.name,
                        introduced_by=adr.id,
                        lifecycle_stage=adr.status.value if hasattr(adr.status, 'value') else str(adr.status),
                    )
            
            for bound in adr.architectural_boundaries:
                if bound.id not in entity_map:
                    entity_map[bound.id] = ManifestEntity(
                        entity_id=bound.id,
                        entity_type="boundary",
                        name=bound.name,
                        introduced_by=adr.id,
                        lifecycle_stage=adr.status.value if hasattr(adr.status, 'value') else str(adr.status),
                    )
            
            for contract in adr.interaction_contracts:
                if contract.id not in entity_map:
                    entity_map[contract.id] = ManifestEntity(
                        entity_id=contract.id,
                        entity_type="contract",
                        name=contract.participants[0] if contract.participants else "Unknown",
                        introduced_by=adr.id,
                        lifecycle_stage=adr.status.value if hasattr(adr.status, 'value') else str(adr.status),
                    )
            
            for const in adr.constraints:
                if const.id not in entity_map:
                    entity_map[const.id] = ManifestEntity(
                        entity_id=const.id,
                        entity_type="constraint",
                        name=const.type,
                        introduced_by=adr.id,
                        lifecycle_stage=adr.status.value if hasattr(adr.status, 'value') else str(adr.status),
                    )
            
            for nfr in adr.non_functional_requirements:
                if nfr.id not in entity_map:
                    entity_map[nfr.id] = ManifestEntity(
                        entity_id=nfr.id,
                        entity_type="nfr",
                        name=nfr.category,
                        introduced_by=adr.id,
                        lifecycle_stage=adr.status.value if hasattr(adr.status, 'value') else str(adr.status),
                    )
            
            for dec in adr.decisions:
                if dec.id not in entity_map:
                    entity_map[dec.id] = ManifestEntity(
                        entity_id=dec.id,
                        entity_type="decision",
                        name=dec.summary,
                        introduced_by=adr.id,
                        lifecycle_stage=adr.status.value if hasattr(adr.status, 'value') else str(adr.status),
                    )
            
            for gap in adr.gaps:
                if gap.id not in entity_map:
                    entity_map[gap.id] = ManifestEntity(
                        entity_id=gap.id,
                        entity_type="gap",
                        name=gap.question[:50],
                        introduced_by=adr.id,
                        lifecycle_stage=adr.status.value if hasattr(adr.status, 'value') else str(adr.status),
                    )
        
        # Extract from Physical ADRs (components, interfaces, integrations, impl decisions)
        for adr in physical_adrs:
            for comp in adr.component_specifications:
                if comp.id not in entity_map:
                    entity_map[comp.id] = ManifestEntity(
                        entity_id=comp.id,
                        entity_type="component",
                        name=comp.name,
                        introduced_by=adr.id,
                        lifecycle_stage=adr.status.value if hasattr(adr.status, 'value') else str(adr.status),
                    )
                
                for iface in comp.interfaces:
                    if iface.id not in entity_map:
                        entity_map[iface.id] = ManifestEntity(
                            entity_id=iface.id,
                            entity_type="interface",
                            name=f"{comp.name} {iface.type}",
                            introduced_by=adr.id,
                            lifecycle_stage=adr.status.value if hasattr(adr.status, 'value') else str(adr.status),
                        )
            
            for integ in adr.integration_points:
                if integ.id not in entity_map:
                    entity_map[integ.id] = ManifestEntity(
                        entity_id=integ.id,
                        entity_type="integration",
                        name=" → ".join(integ.systems),
                        introduced_by=adr.id,
                        lifecycle_stage=adr.status.value if hasattr(adr.status, 'value') else str(adr.status),
                    )
            
            for impl_dec in adr.implementation_decisions:
                if impl_dec.id not in entity_map:
                    entity_map[impl_dec.id] = ManifestEntity(
                        entity_id=impl_dec.id,
                        entity_type="implementation_decision",
                        name=impl_dec.summary,
                        introduced_by=adr.id,
                        lifecycle_stage=adr.status.value if hasattr(adr.status, 'value') else str(adr.status),
                    )
        
        manifest_entities = list(entity_map.values())
        
        # Parse requirements snapshots
        manifest_req_snapshots: List[ManifestRequirementsSnapshot] = []
        for file_path in req_snapshot_files:
            try:
                snapshot = self.parser.parse_requirements_snapshot(file_path)
                manifest_req_snapshots.append(ManifestRequirementsSnapshot(
                    snapshot_id=snapshot.snapshot_id,
                    domains=snapshot.domains or [],
                    capability_count=len(snapshot.required_capabilities or []),
                ))
            except Exception as e:
                print(f"Warning: Failed to parse requirements snapshot {file_path}: {e}")
        
        # Parse decision ledgers
        manifest_decision_ledgers: List[ManifestDecisionLedger] = []
        for file_path in decision_ledger_files:
            try:
                ledger = self.parser.parse_decision_ledger(file_path)
                manifest_decision_ledgers.append(ManifestDecisionLedger(
                    ledger_id=ledger.ledger_id,
                    target_logical_adr=ledger.target_logical_adr,
                    decision_count=len(ledger.required_decisions),
                ))
            except Exception as e:
                print(f"Warning: Failed to parse decision ledger {file_path}: {e}")
        
        # Build gaps summary
        gaps_by_adr: Dict[str, GapSummaryByADR] = {}
        total_gaps = 0
        total_blocking = 0
        
        for entry in manifest_entries:
            if entry.gap_count > 0:
                gaps_by_adr[entry.id] = GapSummaryByADR(
                    total=entry.gap_count,
                    blocking=entry.blocking_gaps
                )
                total_gaps += entry.gap_count
                total_blocking += entry.blocking_gaps
        
        gaps_summary = GapsSummary(
            total=total_gaps,
            blocking=total_blocking,
            by_adr=gaps_by_adr
        )
        
        # Build statistics
        statistics = ManifestStatistics(
            total_adrs=len(manifest_entries),
            logical_adrs=len(logical_adrs),
            physical_adrs=len(physical_adrs),
            physical_system_adrs=len(physical_system_adrs),
            physical_component_adrs=len(physical_component_adrs),
            decision_adrs=0,
            total_decisions=sum(len(adr.decisions) for adr in logical_adrs),
            total_invariants=len(manifest_invariants),
            total_components=sum(len(adr.component_specifications) for adr in physical_adrs) + 
                           sum(len(adr.component_specifications) for adr in physical_component_adrs),
            total_gaps=total_gaps,
            blocking_gaps=total_blocking,
            total_entities=len(manifest_entities),
            total_requirements_snapshots=len(manifest_req_snapshots),
            total_decision_ledgers=len(manifest_decision_ledgers),
        )
        
        # Create manifest with scope metadata (ADR-L-0007: CAP-0002)
        manifest = Manifest(
            schema_version="1.0",
            type="manifest",
            generated_date=datetime.now(timezone.utc),
            generated_from="adrs/**/*.yaml",
            adrs=manifest_entries,
            by_domain=by_domain,
            by_status=by_status,
            by_technology=by_technology,
            logical_to_physical_map=logical_to_physical,
            system_to_components_map=system_to_components,
            invariants=manifest_invariants,
            entities=manifest_entities,
            requirements_snapshots=manifest_req_snapshots,
            decision_ledgers=manifest_decision_ledgers,
            gaps_summary=gaps_summary,
            statistics=statistics,
        )
        
        return manifest
    
    def generate_from_scope(self, scope: Optional[ProjectScope] = None) -> Manifest:
        """Generate manifest for project scope (ADR-L-0007: CAP-0002).
        
        Args:
            scope: Project scope (auto-detected if not provided)
            
        Returns:
            Generated Manifest model
        """
        if scope is None:
            scope = self.scope_resolver.resolve()
        
        return self.generate_from_directory(scope.adr_dir, scope)
    
    def generate_recursive(self, scope: Optional[ProjectScope] = None) -> Dict[str, Manifest]:
        """Generate manifests for all scopes recursively (ADR-L-0007: CAP-0002).
        
        Args:
            scope: Root project scope (auto-detected if not provided)
            
        Returns:
            Dict mapping scope name to Manifest
        """
        if scope is None:
            scope = self.scope_resolver.resolve()
        
        scopes = self.scope_resolver.resolve_recursive(scope.root)
        manifests = {}
        
        for s in scopes:
            if s.adr_dir.exists():
                try:
                    manifest = self.generate_from_directory(s.adr_dir, s)
                    manifests[s.name or str(s.root)] = manifest
                except Exception as e:
                    print(f"Warning: Failed to generate manifest for {s.name}: {e}")
        
        return manifests
    
    def _slugify(self, text: str) -> str:
        """Convert title to slug for filename."""
        return text.lower().replace(" ", "-").replace(":", "")[:50]
    
    def save_manifest(self, manifest: Manifest, output_path: Path):
        """Save manifest to YAML file.
        
        Args:
            manifest: Manifest model
            output_path: Path to save manifest.yaml
        """
        import yaml
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict for YAML serialization
        manifest_dict = manifest.model_dump(mode='json', exclude_none=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# manifest.yaml - GENERATED FROM ADRs, DO NOT EDIT\n")
            f.write("# This file is automatically generated by 'adr generate-manifest'\n")
            f.write("# To update: modify ADRs, then regenerate manifest\n\n")
            yaml.dump(manifest_dict, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
