# ADR Architecture Kit

**STE-compliant Python toolkit for machine-verifiable Architecture Decision Records**

## Overview

ADR Architecture Kit implements the **Documentation-State Layer (Layer 5)** of the System of Thought Engineering (STE) framework, providing structured, schema-validated architecture documentation that AI systems can reason over deterministically.

**Authoring vs compilation:** This repository is the **authoring system** (schema, validation, contributor workflows). **ste-runtime** is the **compiler of record** for machine-consumable architecture state (registries, architecture index, manifest, and evidence consumed by ste-kernel). See [AUTHORING-SYSTEM.md](AUTHORING-SYSTEM.md). Do not emit or rely on a **second authoritative** machine graph or registry compiler path here once the ste-runtime migration completes; legacy Python compilation may remain temporarily for golden parity only.

The in-repo ADR discovery/output path uses an explicit **authoring-time** compiler pipeline: canonical ADR files are parsed once, normalized into `ArchModel`, transformed through deterministic compiler passes, and emitted as registries, manifest, and rendered ADR markdown. **Runtime-facing** compilation authority migrates to ste-runtime per [AUTHORING-SYSTEM.md](AUTHORING-SYSTEM.md).
For in-process consumers, use the Architecture Repository Boundary: `ArchitectureRepository` loads compiled bundles and returns a `NormalizedArchitectureModel`. `ArchModel` remains compiler-internal.

For fastest repo orientation, start with [SYSTEM-OVERVIEW.md](/c:/Users/Erik/Documents/Projects/adr-architecture-kit/SYSTEM-OVERVIEW.md).
`SYSTEM-OVERVIEW.md` is a generated artifact. Update it with `adr generate-system-overview` and validate it with `adr validate-system-overview`.
Rendered ADR markdown and the manifest are also generated artifacts. Refresh them with `adr generate-rendered-docs` and `adr generate-manifest`, then verify projections with `adr validate-generated-docs`.
`README.md` is a manual workflow/orientation document. Update it when contributor-facing workflows change; it is not part of `adr validate-generated-docs`.

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

Supported runtime: Python 3.11+.

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

### Validate Generated Documentation

```bash
adr generate-manifest
adr generate-rendered-docs
adr generate-system-overview
adr validate-generated-docs
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

**Vision ADRs** (`ADR-V-XXXX`) - Future-state logical direction:
- A special category of logical ADR focused on target evolution and planned capability
- Defines future-state architecture and capability intent the system should grow toward
- Helps ensure implementation evolves toward the intended meta-system vision
- Not treated as current implemented authority in the same way as accepted foundational ADR-L artifacts

**Physical ADRs** (`ADR-P-XXXX`) - Legacy broad implementation specifications:
- Technology stack and architecture patterns
- Component specifications with interfaces
- Deployment model and data architecture
- Implementation decisions and operational requirements

**Physical-System ADRs** (`ADR-PS-XXXX`) - System architecture / high-level design:
- High-level design with major components, boundaries, and relationships
- System topology, integration patterns, and data flows
- Broad technology and deployment claims at system scope
- The "component boxes and relationships" view of the implementation design
- Steelman acceptance bar: a coherent design for the abstraction layer it supports

**Physical-Component ADRs** (`ADR-PC-XXXX`) - Executable architecture:
- Complete component-level implementation specification
- All detail required for AI-assisted implementation without further human clarification
- Interface, algorithm, operational, compatibility, and testing requirements
- Steelman acceptance bar: sufficient precision for implementation-ready execution

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
ADR-V-0001  Vision ADR
ADR-P-0001  Physical ADR
ADR-PS-0001 Physical-System ADR
ADR-PC-0001 Physical-Component ADR
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

## Multi-Scope Support

**Authority**: ADR-L-0002 - Multi-Scope ADR Architecture

ADR Kit supports **multi-scope operation** - sub-modules can maintain independent ADR directories:

```bash
# Auto-detect scope from current directory
adr generate-manifest
adr validate

# Work with specific scope
adr validate --scope ste-runtime

# Operate on all scopes recursively
adr generate-manifest --recursive
adr validate --recursive
```

See [Multi-Scope Guide](docs/multi-scope-guide.md) for details.

## Dogfooding

This project documents its own architecture using ADR Kit:

### Workspace ADRs
- **ADR-L-0001**: STE-compliant ADR system conception
- **ADR-L-0002**: Multi-scope ADR architecture
- **ADR-L-0003**: Quality assurance and testing strategy
- **ADR-P-0001**: Python toolkit implementation
- **ADR-P-0002**: JSON Schema + YAML format choice
- **ADR-P-0003**: Multi-scope Python implementation

### Sub-Module ADRs (ste-runtime)
- **ADR-L-0001**: RECON provisional execution
- **ADR-L-0002**: RECON self-validation strategy
- **ADR-L-0003** through **ADR-L-0006**: Additional logical ADRs
- **ADR-P-0001** through **ADR-P-0005**: Physical implementations

See `adrs/` and `ste-runtime/adrs/` directories for complete documentation.

## Testing

**Authority**: ADR-L-0003 - Quality Assurance and Testing Strategy

Run the test suite:

```bash
pytest tests/ -v
```

Validate the compiled contract bundle:

```bash
adr validate-contract --contract-profile greenfield
```

Compile the single-scope artifact bundle with an explicit success policy:

```bash
adr compile --mode strict
```

Run the ratcheted brownfield gate used in CI:

```bash
adr validate-contract --contract-profile brownfield --max-sentinel-fields 0 --max-non-complete-entities 0
```

Run the standard local governance bundle:

```bash
adr governance-checks
```

This runs the greenfield contract gate, the brownfield ratchet gate, and the full test suite.
Use `adr governance-checks --recursive` to validate all detected scopes recursively while still running the full test suite once at the root.
When you finish a coherent implementation slice, commit it after the relevant checks pass rather than accumulating unrelated changes.
Use `adr compile --mode normal|strict|lenient` when you need the unified compiler path directly:
- `normal` reports errors and returns non-zero on compile failure
- `strict` treats any compile error as non-viable
- `lenient` only tolerates the current post-emit drift and contract-validation error family
- add `--recursive` to compile each detected scope independently while preserving per-scope output locations
- add `--emit graph` to generate the additive `adrs/index/architecture-graph.yaml` navigation artifact without changing current registry contracts

The discovery compiler is the authoritative path for registry, manifest, and rendered ADR generation. Compatibility generators remain available, but compiler-backed emitters consume pipeline state rather than reading ADR files independently.
The architecture graph is an additive machine-navigation surface projected from the same compiler IR; current normalized registries remain the authoritative contract surfaces in this phase.

The compatibility wrapper still exists if you need it:

```bash
python scripts/run_governance_checks.py
```

With coverage:

```bash
pytest tests/ --cov=src/adr_kit --cov-report=html --cov-report=term
```

Test coverage includes:
- Schema validation (valid and invalid ADRs)
- Multi-scope detection and resolution
- Scoped manifest generation
- Scoped validation (single and recursive)
- ID pattern validation
- Markdown view generation
- Pydantic model parsing
- Backward compatibility

### Test-Driven Development

This project follows **Red-Green-Refactor TDD methodology** (ADR-L-0003 DEC-0005). See [TDD Workflow Guide](docs/TDD-WORKFLOW.md) for detailed practices.

## CI Governance

GitHub Actions workflow (`.github/workflows/adr-governance.yml`) enforces:

1. **ADR validation** - `adr validate --cross-references` must pass
2. **Governance bundle** - `adr governance-checks` must pass, including the full test suite and contract profile gates
   Use `adr governance-checks --recursive` when validating a multi-scope workspace locally.
3. **Generated artifact freshness** - `adr validate-generated-docs` must pass for manifest, rendered output, and any emitted architecture graph artifacts
4. **System overview integrity** - `adr validate-system-overview` must pass
5. **PROJECT.yaml validation** - `adr validate-project-metadata` must pass
6. **Runtime hygiene** - Deprecated APIs fail governance checks
7. **Dependency security** - Known vulnerable packages fail governance checks
8. **Dependency freshness** - Outdated direct dependencies are surfaced continuously

Repository practice also requires commits at meaningful verified boundaries:
- one coherent implementation slice per commit
- relevant tests and validation run first
- leave the repo in a reviewable state before continuing

Run the runtime hygiene audit locally:

```bash
python scripts/check_runtime_hygiene.py
adr audit-runtime --fail-on-outdated
```

## Documentation

### User Guides
- `docs/schema-guide.md` - JSON Schema reference
- `docs/logical-adr-guide.md` - Writing logical ADRs
- `docs/physical-adr-guide.md` - Writing physical ADRs
- `docs/multi-scope-guide.md` - Multi-scope ADR management
- `docs/graph-integration.md` - ste-runtime integration

### Developer Guides
- `docs/TDD-WORKFLOW.md` - Test-Driven Development practices
- `docs/TESTING-IMPLEMENTATION.md` - Test suite documentation
- `docs/MULTI-SCOPE-IMPLEMENTATION.md` - Multi-scope architecture details
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
