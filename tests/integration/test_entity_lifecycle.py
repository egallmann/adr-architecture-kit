"""Integration tests for entity lifecycle workflow."""

import shutil
from datetime import date
from pathlib import Path
import uuid

import pytest
import yaml

from adr_kit.generators import EntityRegistryGenerator, ManifestGenerator
from adr_kit.models import (
    DecisionLedger,
    EntityRegistry,
    LedgerDecision,
    RequirementsSnapshot,
    RequiredCapability,
    TechnologySignals,
)
from adr_kit.parser import ADRParser
from adr_kit.validators import EntityValidator


@pytest.fixture
def temp_adr_dir():
    """Create temporary ADR directory structure."""
    base_dir = Path(__file__).resolve().parents[1] / ".tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    root_dir = base_dir / f"entity-lifecycle-{uuid.uuid4().hex[:8]}"
    adr_dir = root_dir / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "logical").mkdir()
    (adr_dir / "physical").mkdir()
    (adr_dir / "requirements" / "snapshots").mkdir(parents=True)
    (adr_dir / "decisions" / "ledgers").mkdir(parents=True)
    (adr_dir / "entities").mkdir()

    try:
        yield adr_dir
    finally:
        shutil.rmtree(root_dir, ignore_errors=True)


def test_requirements_to_ledger_to_adr_workflow(temp_adr_dir):
    """Test complete workflow: REQ → Ledger → Logical ADR → Physical ADR → Entity Registry."""
    
    # Step 1: Create Requirements Snapshot
    req_snapshot = RequirementsSnapshot(
        schema_version="1.1",
        type="requirements_snapshot",
        snapshot_id="REQ-0001",
        created_date=date(2026, 3, 10),
        required_capabilities=[
            RequiredCapability(
                req_item_id="RQCAP-0001",
                name="AI Request Routing",
                description="Route AI requests to appropriate LLM providers"
            )
        ],
        domains=["ai_platform"],
        technology_signals=TechnologySignals(
            language="python",
            infrastructure="aws",
            architecture_pattern="serverless"
        ),
        feeds_logical_adr="ADR-L-0001"
    )
    
    req_file = temp_adr_dir / "requirements" / "snapshots" / "REQ-0001-snapshot.yaml"
    with open(req_file, 'w') as f:
        yaml.dump(req_snapshot.model_dump(mode='json', exclude_none=True), f)
    
    # Step 2: Create Decision Ledger
    ledger = DecisionLedger(
        schema_version="1.1",
        type="decision_ledger",
        ledger_id="LEDGER-0001",
        version="1.0",
        created_date=date(2026, 3, 10),
        source_requirements_snapshot="REQ-0001",
        target_logical_adr="ADR-L-0001",
        required_decisions=[
            LedgerDecision(
                ledger_decision_id="LDEC-0001",
                question="What architecture pattern should the AI gateway use?",
                alternatives=["serverless", "containerized", "hybrid"],
                related_snapshot_items=["RQCAP-0001"]
            )
        ]
    )
    
    ledger_file = temp_adr_dir / "decisions" / "ledgers" / "LEDGER-0001-ledger.yaml"
    with open(ledger_file, 'w') as f:
        yaml.dump(ledger.model_dump(mode='json', exclude_none=True), f)
    
    # Step 3: Create Logical ADR
    logical_adr_data = {
        "schema_version": "1.0",
        "adr_type": "logical",
        "id": "ADR-L-0001",
        "title": "AI Gateway Architecture",
        "status": "accepted",
        "created_date": "2026-03-10",
        "authors": ["test-author"],
        "domains": ["ai_platform"],
        "introduces_entities": ["CAP-0001"],
        "related_ledgers": ["LEDGER-0001"],
        "context": "Design AI request routing capability",
        "capabilities": [
            {
                "id": "CAP-0001",
                "name": "AI Request Routing",
                "description": "Route AI requests to appropriate LLM providers",
                "rationale": "Enable multi-provider AI support"
            }
        ],
        "architectural_boundaries": [],
        "interaction_contracts": [],
        "constraints": [],
        "non_functional_requirements": [],
        "invariants": [],
        "decisions": [
            {
                "id": "DEC-0001",
                "summary": "Use a routed gateway for AI requests",
                "rationale": "Supports multi-provider request handling."
            }
        ],
        "gaps": []
    }
    
    logical_file = temp_adr_dir / "logical" / "ADR-L-0001-ai-gateway.yaml"
    with open(logical_file, 'w') as f:
        yaml.dump(logical_adr_data, f)
    
    # Step 4: Create Physical ADR
    physical_adr_data = {
        "schema_version": "1.0",
        "adr_type": "physical",
        "id": "ADR-P-0001",
        "title": "AI Gateway Implementation",
        "status": "accepted",
        "created_date": "2026-03-10",
        "authors": ["test-author"],
        "domains": ["ai_platform"],
        "implements_logical": ["ADR-L-0001"],
        "realizes_entities": ["CAP-0001"],
        "related_ledgers": ["LEDGER-0001"],
        "introduces_entities": ["COMP-0001"],
        "technologies": ["python", "aws-lambda"],
        "context": "Implement AI gateway using serverless",
        "technology_stack": [
            {
                "category": "language",
                "name": "Python",
                "version": "3.11",
                "rationale": "Team expertise"
            }
        ],
        "architecture_patterns": [],
        "component_specifications": [
            {
                "id": "COMP-0001",
                "name": "AI Gateway Lambda",
                "type": "gateway",
                "responsibilities": "Route AI requests",
                "implements_capabilities": ["CAP-0001"],
                "realizes_entities": [],
                "interfaces": [],
                "dependencies": [],
                "upstream_services": [],
                "downstream_services": []
            }
        ],
        "deployment_model": {},
        "data_architecture": [],
        "implementation_decisions": [],
        "integration_points": [],
        "operational_requirements": {},
        "gaps": []
    }
    
    physical_file = temp_adr_dir / "physical" / "ADR-P-0001-ai-gateway-impl.yaml"
    with open(physical_file, 'w') as f:
        yaml.dump(physical_adr_data, f)
    
    # Step 5: Parse and validate
    parser = ADRParser()
    
    parsed_req = parser.parse_requirements_snapshot(req_file)
    assert parsed_req.snapshot_id == "REQ-0001"
    
    parsed_ledger = parser.parse_decision_ledger(ledger_file)
    assert parsed_ledger.ledger_id == "LEDGER-0001"
    
    parsed_logical = parser.parse_logical_adr(logical_file)
    assert parsed_logical.id == "ADR-L-0001"
    assert "CAP-0001" in parsed_logical.introduces_entities
    
    parsed_physical = parser.parse_physical_adr(physical_file)
    assert parsed_physical.id == "ADR-P-0001"
    assert "CAP-0001" in parsed_physical.realizes_entities
    
    # Step 6: Generate Entity Registry
    registry_gen = EntityRegistryGenerator(parser)
    entity_registry = registry_gen.generate_from_directory(temp_adr_dir)
    
    assert len(entity_registry.entities) >= 2  # CAP-0001, COMP-0001
    entity_ids = {e.entity_id for e in entity_registry.entities}
    assert "CAP-0001" in entity_ids
    assert "COMP-0001" in entity_ids
    
    # Step 7: Validate entity references
    validator = EntityValidator()
    errors = validator.validate_entity_references(
        entity_registry,
        [parsed_logical],
        [parsed_physical]
    )
    assert len(errors) == 0, f"Validation errors: {errors}"
    
    # Step 8: Validate decision ledger traceability
    errors = validator.validate_decision_ledger_traceability(
        parsed_ledger,
        parsed_req,
        parsed_logical
    )
    assert len(errors) == 0, f"Traceability errors: {errors}"
    
    # Step 9: Generate Manifest
    manifest_gen = ManifestGenerator(parser)
    manifest = manifest_gen.generate_from_directory(temp_adr_dir)
    
    assert manifest.statistics.total_adrs == 2
    assert manifest.statistics.logical_adrs == 1
    assert manifest.statistics.physical_adrs == 1
    assert manifest.statistics.total_entities >= 2
    assert manifest.statistics.total_requirements_snapshots == 1
    assert manifest.statistics.total_decision_ledgers == 1
    
    assert len(manifest.entities) >= 2
    assert len(manifest.requirements_snapshots) == 1
    assert len(manifest.decision_ledgers) == 1


def test_entity_lifecycle_tracking(temp_adr_dir):
    """Test entity lifecycle stages through ADR status changes."""
    
    # Create ADR with proposed status
    logical_adr_data = {
        "schema_version": "1.0",
        "adr_type": "logical",
        "id": "ADR-L-0002",
        "title": "Test Capability",
        "status": "proposed",
        "created_date": "2026-03-10",
        "authors": ["test-author"],
        "domains": ["test"],
        "introduces_entities": ["CAP-0002"],
        "context": "Test lifecycle",
        "capabilities": [
            {
                "id": "CAP-0002",
                "name": "Test Capability",
                "description": "Test",
                "rationale": "Test"
            }
        ],
        "architectural_boundaries": [],
        "interaction_contracts": [],
        "constraints": [],
        "non_functional_requirements": [],
        "invariants": [],
        "decisions": [
            {
                "id": "DEC-0002",
                "summary": "Track lifecycle through ADR status",
                "rationale": "Entity registry derives lifecycle from ADR state."
            }
        ],
        "gaps": []
    }
    
    logical_file = temp_adr_dir / "logical" / "ADR-L-0002-test.yaml"
    with open(logical_file, 'w') as f:
        yaml.dump(logical_adr_data, f)
    
    # Generate entity registry
    parser = ADRParser()
    registry_gen = EntityRegistryGenerator(parser)
    entity_registry = registry_gen.generate_from_directory(temp_adr_dir)
    
    # Find the capability entity
    cap_entity = next((e for e in entity_registry.entities if e.entity_id == "CAP-0002"), None)
    assert cap_entity is not None
    assert cap_entity.lifecycle_stage.value == "proposed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
