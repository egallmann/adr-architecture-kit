"""Repository access for architecture discovery artifacts."""

from .architecture_repository import (
    ArchitectureRegistryError,
    ArchitectureRepository,
    ContractBundleView,
    EntityAliasRecord,
)
from .provider_registry import ProviderBinding, ProviderRegistry

__all__ = [
    "ArchitectureRegistryError",
    "ArchitectureRepository",
    "ContractBundleView",
    "EntityAliasRecord",
    "ProviderBinding",
    "ProviderRegistry",
]
