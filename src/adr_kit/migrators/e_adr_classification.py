"""Classification mapping for E-ADRs to Logical/Physical ADRs."""

from typing import Dict, Literal, Optional


# Classification mapping based on E-ADR content analysis
EADR_CLASSIFICATION: Dict[str, Dict[str, any]] = {
    "E-ADR-001": {
        "type": "logical",
        "new_id": "ADR-L-0001",
        "title": "RECON Provisional Execution for Project-Level Semantic State",
        "rationale": "Conceptual decision about RECON execution model (what/why)",
        "domains": ["recon", "architecture", "governance"],
        "tags": ["recon", "provisional-execution", "semantic-state", "ste-compliance"],
    },
    "E-ADR-002": {
        "type": "logical",
        "new_id": "ADR-L-0002",
        "title": "RECON Self-Validation Strategy",
        "rationale": "Conceptual decision about validation approach (what/why)",
        "domains": ["recon", "validation", "governance"],
        "tags": ["recon", "validation", "self-validation", "ste-compliance"],
    },
    "E-ADR-003": {
        "type": "logical",
        "new_id": "ADR-L-0003",
        "title": "CEM Implementation Deferral",
        "rationale": "Meta-decision about implementation sequencing (what/why)",
        "domains": ["architecture", "governance", "cem"],
        "tags": ["cem", "deferral", "meta-decision", "build-order"],
    },
    "E-ADR-004": {
        "type": "physical",
        "new_id": "ADR-P-0001",
        "title": "RSS CLI Implementation for Developer-Invoked Graph Traversal",
        "rationale": "Implementation specification for RSS CLI (how)",
        "domains": ["rss", "cli", "implementation"],
        "tags": ["rss", "cli", "graph-traversal", "developer-tools"],
        "implements_logical": ["ADR-L-0002"],  # Self-validation enables RSS queries
    },
    "E-ADR-005": {
        "type": "physical",
        "new_id": "ADR-P-0002",
        "title": "JSON Data Extraction for Compliance Controls and Schemas",
        "rationale": "Implementation specification for JSON extractor (how)",
        "domains": ["extraction", "data", "implementation"],
        "tags": ["json", "extractor", "compliance", "schemas"],
        "implements_logical": ["ADR-L-0001"],  # RECON execution model
    },
    "E-ADR-006": {
        "type": "physical",
        "new_id": "ADR-P-0003",
        "title": "Angular and CSS/SCSS Semantic Extraction",
        "rationale": "Implementation specification for Angular/CSS extractors (how)",
        "domains": ["extraction", "frontend", "implementation"],
        "tags": ["angular", "css", "scss", "extractor", "frontend"],
        "implements_logical": ["ADR-L-0001"],  # RECON execution model
    },
    "E-ADR-007": {
        "type": "logical",
        "new_id": "ADR-L-0004",
        "title": "Watchdog Authoritative Mode for Workspace Boundary",
        "rationale": "Conceptual decision about watchdog operation model (what/why)",
        "domains": ["watchdog", "governance", "workspace-boundary"],
        "tags": ["watchdog", "file-watching", "workspace-boundary", "ste-compliance"],
    },
    "E-ADR-008": {
        "type": "documentation",  # Not an ADR - it's a guide
        "new_id": None,
        "title": "Extractor Development Guide",
        "rationale": "Documentation guide, not a decision record",
        "domains": ["documentation", "extractors"],
        "tags": ["guide", "extractors", "development"],
    },
    "E-ADR-009": {
        "type": "logical",
        "new_id": "ADR-L-0005",
        "title": "Self-Configuring Domain Discovery",
        "rationale": "Conceptual decision about domain discovery approach (what/why)",
        "domains": ["recon", "domain-discovery", "architecture"],
        "tags": ["domain-discovery", "self-configuring", "ai-doc"],
    },
    "E-ADR-010": {
        "type": "logical",
        "new_id": "ADR-L-0006",
        "title": "Conversational Query Interface for RSS",
        "rationale": "Conceptual decision about query interface design (what/why)",
        "domains": ["rss", "interface", "architecture"],
        "tags": ["rss", "conversational", "query-interface", "natural-language"],
    },
    "E-ADR-011": {
        "type": "physical",
        "new_id": "ADR-P-0004",
        "title": "ste-runtime MCP Server Implementation",
        "rationale": "Implementation specification for MCP server (how)",
        "domains": ["mcp", "integration", "implementation"],
        "tags": ["mcp", "server", "cursor-integration", "file-watching"],
        "implements_logical": ["ADR-L-0004", "ADR-L-0006"],  # Watchdog + Conversational interface
    },
    "E-ADR-013": {
        "type": "physical",
        "new_id": "ADR-P-0005",
        "title": "Extractor Validation Requirements",
        "rationale": "Implementation specification for validation (how)",
        "domains": ["validation", "extraction", "implementation"],
        "tags": ["validation", "extractors", "quality-assurance"],
        "implements_logical": ["ADR-L-0002"],  # Self-validation strategy
    },
}


def classify_eadr(eadr_id: str) -> Literal["logical", "physical", "documentation"]:
    """Classify E-ADR as logical, physical, or documentation.
    
    Args:
        eadr_id: E-ADR ID (e.g., "E-ADR-001")
        
    Returns:
        Classification type
    """
    if eadr_id not in EADR_CLASSIFICATION:
        raise ValueError(f"Unknown E-ADR: {eadr_id}")
    
    return EADR_CLASSIFICATION[eadr_id]["type"]


def get_new_adr_id(eadr_id: str) -> Optional[str]:
    """Get new ADR Kit ID for E-ADR.
    
    Args:
        eadr_id: E-ADR ID (e.g., "E-ADR-001")
        
    Returns:
        New ADR Kit ID (e.g., "ADR-L-0001") or None if documentation
    """
    if eadr_id not in EADR_CLASSIFICATION:
        raise ValueError(f"Unknown E-ADR: {eadr_id}")
    
    return EADR_CLASSIFICATION[eadr_id]["new_id"]


def get_classification_metadata(eadr_id: str) -> Dict:
    """Get full classification metadata for E-ADR.
    
    Args:
        eadr_id: E-ADR ID (e.g., "E-ADR-001")
        
    Returns:
        Classification metadata dict
    """
    if eadr_id not in EADR_CLASSIFICATION:
        raise ValueError(f"Unknown E-ADR: {eadr_id}")
    
    return EADR_CLASSIFICATION[eadr_id]
