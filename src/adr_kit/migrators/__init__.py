"""Migration utilities for converting other ADR formats to ADR Kit schema."""

from .e_adr_parser import EADRParser, EADRMetadata, EADRContent
from .markdown_to_yaml import MarkdownToYAMLMigrator
from .topology_identity import TopologyIdentityMigrator
from .identity_v13 import IdentityV13Migrator, compare_semantic_parity
from .consumer_alias_allocation import (
    AliasAllocationDiagnostic,
    ConsumerAllocationReport,
    build_candidate_inventory,
    collision_report,
    dry_run_consumer_allocation,
    verify_sealed_map,
    validate_consumer_alias_allocations,
)

__all__ = [
    "EADRParser",
    "EADRMetadata",
    "EADRContent",
    "MarkdownToYAMLMigrator",
    "TopologyIdentityMigrator",
    "IdentityV13Migrator",
    "compare_semantic_parity",
    "AliasAllocationDiagnostic",
    "ConsumerAllocationReport",
    "build_candidate_inventory",
    "collision_report",
    "dry_run_consumer_allocation",
    "verify_sealed_map",
    "validate_consumer_alias_allocations",
]
