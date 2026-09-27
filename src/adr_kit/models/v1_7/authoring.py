"""Minimal typed boundary for authoring v1.7 documents.

The canonical JSON Schemas remain the complete admission authority. These
models intentionally preserve the versioned document envelope and leave the
schema-owned semantic payload open so new accepted entities remain lossless.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _AuthoringADRv17(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: Literal["1.7"]
    id: str
    alias_id: str
    alias_name: str
    title: str
    status: str
    created_date: str
    modified_date: str | None = None
    authors: list[str]
    domains: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    related_adrs: list[str] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: str | None = None
    projection_signals: list[str] = Field(default_factory=list)
    ownership: dict[str, Any] | None = None
    governance: dict[str, Any] | None = None


class LogicalADRv17(_AuthoringADRv17):
    adr_type: Literal["logical"]
    context: str
    decisions: list[dict[str, Any]] = Field(..., min_length=1)


class PhysicalSystemADRv17(_AuthoringADRv17):
    adr_type: Literal["physical-system"]
    implements_logical: list[str] = Field(..., min_length=1)
    context: str
    technology_stack: list[dict[str, Any]] = Field(..., min_length=1)
    system: dict[str, Any]


class PhysicalComponentADRv17(_AuthoringADRv17):
    adr_type: Literal["physical-component"]
    implements_logical: list[str] = Field(..., min_length=1)
    implements_system: list[str] = Field(..., min_length=1)
    context: str
    technology_stack: list[dict[str, Any]] = Field(..., min_length=1)
    component_specifications: list[dict[str, Any]] = Field(..., min_length=1)
