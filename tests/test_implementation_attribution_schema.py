from __future__ import annotations

import pytest

from src.adr_kit.parser import ADRParser, ADRSchemaValidationError


def test_parser_accepts_valid_implementation_attribution_evidence(tmp_path):
    evidence_path = tmp_path / "implementation-attribution.yaml"
    evidence_path.write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "type: implementation_attribution_evidence",
                "records:",
                "  - implementation_entity_id: function.process_claim_event",
                "    implementation_entity_type: function",
                "    attributed_adrs:",
                "      - ADR-L-0001",
                "      - ADR-PC-0001",
                "    enforced_invariants:",
                "      - INV-0001",
                "    provenance:",
                "      source_file: src/claims/consumer.py",
                "      extractor: python-function-extractor",
                "      commit: deadbeef",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    evidence = ADRParser().parse_implementation_attribution_evidence(evidence_path)

    assert evidence.type == "implementation_attribution_evidence"
    assert evidence.records[0].implementation_entity_type == "function"
    assert evidence.records[0].attributed_adrs == ["ADR-L-0001", "ADR-PC-0001"]


def test_parser_rejects_unknown_implementation_entity_type(tmp_path):
    evidence_path = tmp_path / "implementation-attribution.yaml"
    evidence_path.write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "type: implementation_attribution_evidence",
                "records:",
                "  - implementation_entity_id: function.process_claim_event",
                "    implementation_entity_type: lambda",
                "    attributed_adrs:",
                "      - ADR-L-0001",
                "    enforced_invariants: []",
                "    provenance:",
                "      source_file: src/claims/consumer.py",
                "      extractor: python-function-extractor",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ADRSchemaValidationError):
        ADRParser().parse_implementation_attribution_evidence(evidence_path)
