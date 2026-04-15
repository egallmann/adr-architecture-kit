"""Structured ADR input scaffolds for authoring workflows."""

from __future__ import annotations

from copy import deepcopy
from typing import Literal

import yaml

from ._yaml_support import ADRYamlDumper


ScaffoldType = Literal["logical", "physical-system", "physical-component"]


class ScaffoldGenerator:
    """Produce draft-oriented structured inputs for ADR authoring."""

    _SCAFFOLDS: dict[ScaffoldType, dict] = {
        "logical": {
            "schema_version": "1.0",
            "adr_type": "logical",
            "id": "ADR-L-0000",
            "title": "Draft Logical ADR",
            "status": "proposed",
            "created_date": "2026-01-01",
            "authors": ["adr-architecture-kit"],
            "domains": ["architecture"],
            "context": "Describe the architectural context and drivers.",
            "decisions": [
                {
                    "id": "DEC-0001",
                    "summary": "Describe the core decision.",
                    "rationale": "Explain why this decision is being made.",
                }
            ],
            "capabilities": [],
            "architectural_boundaries": [],
            "interaction_contracts": [],
            "constraints": [],
            "invariants": [],
            "non_functional_requirements": [],
            "gaps": [],
        },
        "physical-system": {
            "schema_version": "1.0",
            "adr_type": "physical-system",
            "id": "ADR-PS-0000",
            "title": "Draft Physical-System ADR",
            "status": "proposed",
            "created_date": "2026-01-01",
            "authors": ["adr-architecture-kit"],
            "domains": ["architecture"],
            "implements_logical": ["ADR-L-0000"],
            "technologies": ["replace-me"],
            "context": "Describe the system-level implementation context.",
            "technology_stack": [],
            "system_boundaries": [],
            "component_topology": {"components": [], "relationships": []},
            "integration_patterns": [],
            "data_flows": [],
            "deployment_model": {
                "hosting": "cloud",
                "orchestration": "replace-me",
                "scaling_strategy": "Describe how the system scales.",
            },
            "scalability_strategy": {
                "horizontal_scaling": "Describe horizontal scaling expectations.",
                "bottlenecks": [],
            },
            "failure_modes": [],
            "operational_requirements": {
                "monitoring": "Describe monitoring expectations.",
                "logging": "Describe logging expectations.",
                "security": "Describe security expectations.",
            },
            "gaps": [],
        },
        "physical-component": {
            "schema_version": "1.0",
            "adr_type": "physical-component",
            "id": "ADR-PC-0000",
            "title": "Draft Physical-Component ADR",
            "status": "proposed",
            "created_date": "2026-01-01",
            "authors": ["adr-architecture-kit"],
            "domains": ["architecture"],
            "implements_system": ["ADR-PS-0000"],
            "implements_logical": ["ADR-L-0000"],
            "technologies": ["replace-me"],
            "context": "Describe the component-level implementation context.",
            "technology_stack": [],
            "component_specifications": [
                {
                    "id": "COMP-0001",
                    "name": "Replace Me",
                    "type": "service",
                    "responsibilities": "Describe the component responsibilities.",
                    "generation_context": {
                        "purpose": "Describe the component purpose.",
                        "key_responsibilities": [],
                    },
                    "interfaces": [],
                    "implementation_identifiers": {
                        "module_path": "src/replace_me",
                    },
                    "implementation_requirements": {
                        "error_handling": {"strategy": "Describe error handling."},
                        "observability": {
                            "logging": {"level": "info", "structured": False},
                            "metrics": [],
                        },
                        "testing_requirements": {"unit_test_coverage": ">= 0%"},
                    },
                }
            ],
            "gaps": [],
        },
    }

    _OPTIONAL_FIELDS: dict[ScaffoldType, dict] = {
        "logical": {
            "tags": [],
            "related_adrs": [],
            "supersedes": [],
        },
        "physical-system": {
            "tags": [],
            "references_components": [],
        },
        "physical-component": {
            "tags": [],
            "data_architecture": [],
            "deployment_model": {
                "hosting": "cloud",
                "orchestration": "replace-me",
                "scaling_strategy": "Describe deployment scaling.",
            },
            "operational_requirements": {
                "monitoring": "Describe monitoring expectations.",
                "logging": "Describe logging expectations.",
                "security": "Describe security expectations.",
            },
        },
    }

    def scaffold(
        self,
        adr_type: ScaffoldType,
        *,
        adr_id: str | None = None,
        title: str | None = None,
        include_optional: bool = False,
    ) -> dict:
        """Return a deterministic structured ADR input scaffold."""
        scaffold = deepcopy(self._SCAFFOLDS[adr_type])
        if include_optional:
            scaffold.update(deepcopy(self._OPTIONAL_FIELDS[adr_type]))
        if adr_id is not None:
            scaffold["id"] = adr_id
        if title is not None:
            scaffold["title"] = title
        return scaffold

    def scaffold_yaml(
        self,
        adr_type: ScaffoldType,
        *,
        adr_id: str | None = None,
        title: str | None = None,
        include_optional: bool = False,
    ) -> str:
        """Render a scaffold as deterministic YAML."""
        return yaml.dump(
            self.scaffold(
                adr_type,
                adr_id=adr_id,
                title=title,
                include_optional=include_optional,
            ),
            Dumper=ADRYamlDumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
        )
