"""Entity Registry Generator - creates entity registry from ADRs."""

from pathlib import Path
from typing import Dict, List

from ..models import (
    Entity,
    EntityRegistry,
    EntityRelationships,
    EntityType,
    LifecycleStage,
    LogicalADR,
    PhysicalADR,
)
from ..parser import ADRParser


class EntityRegistryGenerator:
    """Generate entity registry from ADRs."""
    
    def __init__(self, parser: ADRParser = None):
        """Initialize generator.
        
        Args:
            parser: ADR parser (creates new one if not provided)
        """
        self.parser = parser or ADRParser()
    
    def generate_from_directory(self, adr_dir: Path) -> EntityRegistry:
        """Generate entity registry from ADR directory.
        
        Args:
            adr_dir: Path to adrs/ directory
            
        Returns:
            Generated EntityRegistry model
        """
        adr_dir = Path(adr_dir)
        
        if not adr_dir.exists():
            raise ValueError(f"ADR directory not found: {adr_dir}")
        
        # Discover all ADR files
        logical_files = list((adr_dir / "logical").glob("*.yaml")) if (adr_dir / "logical").exists() else []
        physical_files = list((adr_dir / "physical").glob("*.yaml")) if (adr_dir / "physical").exists() else []
        
        # Parse all ADRs
        logical_adrs: List[LogicalADR] = []
        physical_adrs: List[PhysicalADR] = []
        
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
        
        # Extract entities
        entities: Dict[str, Entity] = {}
        
        # Extract from Logical ADRs
        for adr in logical_adrs:
            lifecycle = self._map_status_to_lifecycle(adr.status)
            
            for cap in adr.capabilities:
                if cap.id not in entities:
                    entities[cap.id] = Entity(
                        entity_id=cap.id,
                        entity_type=EntityType.CAPABILITY,
                        name=cap.name,
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        domains=adr.domains,
                    )
            
            for bound in adr.architectural_boundaries:
                if bound.id not in entities:
                    entities[bound.id] = Entity(
                        entity_id=bound.id,
                        entity_type=EntityType.BOUNDARY,
                        name=bound.name,
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        domains=adr.domains,
                    )
            
            for contract in adr.interaction_contracts:
                if contract.id not in entities:
                    entities[contract.id] = Entity(
                        entity_id=contract.id,
                        entity_type=EntityType.CONTRACT,
                        name=contract.participants[0] if contract.participants else "Unknown",
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        domains=adr.domains,
                    )
            
            for const in adr.constraints:
                if const.id not in entities:
                    entities[const.id] = Entity(
                        entity_id=const.id,
                        entity_type=EntityType.CONSTRAINT,
                        name=const.type,
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        domains=adr.domains,
                    )
            
            for nfr in adr.non_functional_requirements:
                if nfr.id not in entities:
                    entities[nfr.id] = Entity(
                        entity_id=nfr.id,
                        entity_type=EntityType.NFR,
                        name=nfr.category,
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        domains=adr.domains,
                    )
            
            for dec in adr.decisions:
                if dec.id not in entities:
                    entities[dec.id] = Entity(
                        entity_id=dec.id,
                        entity_type=EntityType.DECISION,
                        name=dec.summary,
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        domains=adr.domains,
                    )
            
            for gap in adr.gaps:
                if gap.id not in entities:
                    entities[gap.id] = Entity(
                        entity_id=gap.id,
                        entity_type=EntityType.GAP,
                        name=gap.question[:50],
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        domains=adr.domains,
                    )
        
        # Extract from Physical ADRs
        for adr in physical_adrs:
            lifecycle = self._map_status_to_lifecycle(adr.status)
            
            for comp in adr.component_specifications:
                if comp.id not in entities:
                    # Extract relationships from component
                    relationships = EntityRelationships(
                        depends_on=comp.dependencies,
                        implements=getattr(comp, 'implements_capabilities', []),
                        consumes=[],
                    )
                    
                    entities[comp.id] = Entity(
                        entity_id=comp.id,
                        entity_type=EntityType.COMPONENT,
                        name=comp.name,
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        domains=adr.domains,
                        relationships=relationships,
                    )
                
                for iface in comp.interfaces:
                    if iface.id not in entities:
                        entities[iface.id] = Entity(
                            entity_id=iface.id,
                            entity_type=EntityType.INTERFACE,
                            name=f"{comp.name} {iface.type}",
                            introduced_by=adr.id,
                            lifecycle_stage=lifecycle,
                            domains=adr.domains,
                        )
            
            for integ in adr.integration_points:
                if integ.id not in entities:
                    entities[integ.id] = Entity(
                        entity_id=integ.id,
                        entity_type=EntityType.INTEGRATION,
                        name=" → ".join(integ.systems),
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        domains=adr.domains,
                    )
            
            for impl_dec in adr.implementation_decisions:
                if impl_dec.id not in entities:
                    entities[impl_dec.id] = Entity(
                        entity_id=impl_dec.id,
                        entity_type=EntityType.IMPLEMENTATION_DECISION,
                        name=impl_dec.summary,
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        domains=adr.domains,
                    )
        
        return EntityRegistry(
            schema_version="1.1",
            type="entity_registry",
            entities=list(entities.values()),
        )
    
    def _map_status_to_lifecycle(self, status) -> LifecycleStage:
        """Map ADR status to entity lifecycle stage."""
        status_str = status.value if hasattr(status, 'value') else str(status)
        
        mapping = {
            "proposed": LifecycleStage.PROPOSED,
            "accepted": LifecycleStage.ACTIVE,
            "deprecated": LifecycleStage.DEPRECATED,
            "superseded": LifecycleStage.SUPERSEDED,
        }
        
        return mapping.get(status_str, LifecycleStage.ACTIVE)
