"""Backward-compatibility shim for adr_kit.schema.kernel_contract.

This module was renamed to repository_schema_generator in the pre-1.0
public-release cleanup pass. The canonical module is now:
    adr_kit.schema.repository_schema_generator

Imports from this module continue to work via re-export.
"""

from adr_kit.schema.repository_schema_generator import (  # noqa: F401
    KERNEL_SCHEMA_MODELS,
    REPOSITORY_SCHEMA_MODELS,
    generate_kernel_schema_documents,
    generate_repository_schema_documents,
    normalize_json_data,
    write_kernel_schema_documents,
    write_repository_schema_documents,
)
