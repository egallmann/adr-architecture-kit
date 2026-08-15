"""Architecture-aware UUID resolution for v1.5 attribution evidence."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from adr_kit.models.implementation_attribution import SemanticAttributionClaim
from adr_kit.parser import ADRParser
from adr_kit.repository import ArchitectureRepository


def test_alias_is_rejected_as_v15_target_entity_id() -> None:
    with pytest.raises(ValidationError):
        SemanticAttributionClaim(
            relationship="implements",
            target_entity_id="ADR-L-0004",
            confidence="declared",
        )


def test_parser_negotiates_15_versus_12() -> None:
    parser = ADRParser()
    v12 = parser.parse_implementation_attribution_evidence_from_data("""
schema_version: "1.2"
type: implementation_attribution_evidence
records: []
""")
    assert v12.schema_version == "1.2"
    v15 = parser.parse_implementation_attribution_evidence_from_data("""
schema_version: "1.5"
type: implementation_attribution_evidence
records: []
""")
    assert v15.schema_version == "1.5"


def test_repository_resolves_live_adr_uuid() -> None:
    repo = ArchitectureRepository(project_root=".")
    entity = repo.find_entity_by_uuid("019fee89-e615-7577-8d37-dd0df031bec9")
    assert entity is not None
    assert entity.alias_id == "ADR-L-0004"
    assert entity.entity_type == "adr"
