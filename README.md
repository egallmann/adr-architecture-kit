# ADR Architecture Kit

**STE-compliant Python toolkit for machine-verifiable Architecture Decision Records**

## Overview

ADR Architecture Kit implements the **Documentation-State Layer (Layer 5)** of the System of Thought Engineering (STE) framework, providing structured, schema-validated architecture documentation that AI systems can reason over deterministically.

### Key Features

- **Machine-Verifiable ADRs** - JSON Schema validation ensures structural integrity
- **Two-Layer Architecture** - Separate logical (conceptual) from physical (implementation) designs
- **Semantic Graph Integration** - ADRs participate in ste-runtime semantic graph via RECON
- **Derived Manifest** - Fast discovery without reading all ADRs (SYS-14 compliance)
- **Human-Readable Views** - Generate markdown from structured YAML
- **STE Compliance** - Governed by ste-spec normative specification

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Parse an ADR

```python
from pathlib import Path
from adr_kit.parser import ADRParser

parser = ADRParser()
adr = parser.parse_logical_adr(Path("adrs/logical/ADR-L-0001.yaml"))

print(f"ADR: {adr.id} - {adr.title}")
print(f"Decisions: {len(adr.decisions)}")
print(f"Invariants: {len(adr.invariants)}")
```

### Generate Manifest

```python
from pathlib import Path
from adr_kit.generators import ManifestGenerator

generator = ManifestGenerator()
manifest = generator.generate_from_directory(Path("adrs"))
generator.save_manifest(manifest, Path("adrs/manifest.yaml"))
```

### Generate Markdown Views

```python
from pathlib import Path
from adr_kit.parser import ADRParser
from adr_kit.generators.views import MarkdownGenerator

parser = ADRParser()
generator = MarkdownGenerator()

adr = parser.parse_logical_adr(Path("adrs/logical/ADR-L-0001.yaml"))
generator.render_to_file(adr, Path("adrs/rendered/ADR-L-0001.md"))
```

## Architecture

### Three-Repository Architecture

```
ste-spec (normative specification)
    ↓ governs
ADR Kit (this project - Documentation-State Layer)
    ↓ feeds
ste-runtime (semantic graph extraction via RECON)
```

- **ste-spec**: Normative ISO-42010 architectural specification (submodule)
- **adr-architecture-kit**: Schema, validators, generators for ADR artifacts (this project)
- **ste-runtime**: Semantic graph and RECON implementation (submodule)

### ADR Types

**Logical ADRs** (`ADR-L-XXXX`) - Conceptual design:
- Capabilities and architectural boundaries
- Interaction contracts and constraints
- Invariants and non-functional requirements
- NO implementation details

**Physical ADRs** (`ADR-P-XXXX`) - Implementation specifications:
- Technology stack and architecture patterns
- Component specifications with interfaces
- Deployment model and data architecture
- Implementation decisions and operational requirements

**PROJECT.yaml** - Project-level metadata:
- Ownership (team, tech lead, on-call)
- Implementation identifiers (service name, repository)
- Automation permissions (what agents can do)
- Integrations (SCM, CI, observability)

## Schema v1.0

### JSON Schemas

Located in `schema/v1.0/`:

- `types.schema.json` - Shared type definitions
- `adr-common.schema.json` - Common frontmatter
- `adr-logical.schema.json` - Logical ADR schema
- `adr-physical.schema.json` - Physical ADR schema
- `invariant.schema.json` - Standalone invariant schema
- `project-metadata.schema.json` - PROJECT.yaml schema
- `manifest.schema.json` - Generated manifest schema

### ID Patterns

```
ADR-L-0001  Logical ADR
ADR-P-0001  Physical ADR
INV-0001    Invariant
CAP-0001    Capability
COMP-0001   Component
DEC-0001    Decision (logical)
IMPL-0001   Implementation Decision (physical)
```

## STE Compliance

ADR Kit implements STE invariants:

- **PRIME-1**: No implicit assumptions (all architecture explicit)
- **PRIME-2**: No undeclared state (all metadata in frontmatter)
- **SYS-2**: Deterministic cognition through constraints (schema validation)
- **SYS-4**: Drift prevention as first-class objective (violations halt execution)
- **SYS-5**: Documentation-state as authoritative truth (ADRs precede implementation)
- **SYS-6**: RECON completion prerequisite (architecture extracted before reasoning)
- **SYS-13**: Graph completeness (bidirectional relationships)
- **SYS-14**: Index currency (manifest generated from ADRs)

## Dogfooding

This project documents its own architecture using ADR Kit:

- **ADR-L-0001**: STE-compliant ADR system conception
- **ADR-P-0001**: Python toolkit implementation
- **ADR-P-0002**: JSON Schema + YAML format choice
- **INV-0001**: Schema validation required

See `adrs/` directory for complete project documentation.

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

Test coverage includes:
- Schema validation (valid and invalid ADRs)
- ID pattern validation
- Manifest generation
- Markdown view generation
- Pydantic model parsing

## CI Governance

GitHub Actions workflow (`.github/workflows/adr-governance.yml`) enforces:

1. **Schema validation** - All ADRs must validate against JSON Schema
2. **Manifest freshness** - Manifest must be up-to-date with ADRs
3. **Test suite** - All tests must pass
4. **PROJECT.yaml validation** - Project metadata must be valid

## Documentation

- `docs/schema-guide.md` - JSON Schema reference
- `docs/logical-adr-guide.md` - Writing logical ADRs
- `docs/physical-adr-guide.md` - Writing physical ADRs
- `docs/graph-integration.md` - ste-runtime integration
- `schema/v1.0/README.md` - Schema documentation

## Future Vision

ADR Kit is the foundation for:

- **Rules & Signal Service** - Policy validation and conflict detection
- **Correction Agents** - Autonomous remediation within safety boundaries
- **Self-Healing Architecture** - Policy-driven automated governance
- **Embodied Design Records** - Compare declared vs. actual architecture
- **Policy Propagation** - Blast radius analysis via semantic graph

## License

Apache-2.0

## Author

Erik Gallmann (@egallmann)
