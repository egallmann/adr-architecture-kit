# ADR Kit JSON Schema v1.0

This directory contains the JSON Schema definitions for ADR Architecture Kit v1.0.

## Schema Files

### Core Schemas

- **`types.schema.json`** - Shared type definitions (IDs, dates, enums)
- **`adr-common.schema.json`** - Common frontmatter for all ADR types
- **`adr-logical.schema.json`** - Logical ADR schema (conceptual design)
- **`adr-physical.schema.json`** - Physical ADR schema (implementation specs)
- **`project-metadata.schema.json`** - PROJECT.yaml schema (project-level metadata)
- **`invariant.schema.json`** - Standalone invariant schema
- **`manifest.schema.json`** - Generated manifest schema

## Schema Principles

### STE Compliance

All schemas follow STE invariants:

- **PRIME-1: No Implicit Assumptions** - All fields explicit, no defaults
- **PRIME-2: No Undeclared State** - All metadata in frontmatter
- **SYS-2: Deterministic Cognition** - Schema validation before use
- **SYS-4: Drift Prevention** - Schema violations = divergence
- **SYS-5: Documentation-State Precedence** - ADRs are authoritative
- **SYS-13: Graph Completeness** - Explicit relationships for graph extraction
- **SYS-14: Index Currency** - Manifest generated from ADRs

### Design Decisions

1. **Type-Prefixed IDs** - `ADR-L-XXXX`, `ADR-P-XXXX`, `ADR-D-XXXX` prevent collisions
2. **Rich Frontmatter** - All discovery metadata in frontmatter (single source of truth)
3. **Explicit Relationships** - Array fields for graph edges (`implements_logical`, `related_adrs`)
4. **Markdown in YAML** - Structured data with rich prose where needed
5. **Enforcement Levels** - RFC 2119 levels (must, should, may) for policy validation
6. **Implementation Identifiers** - Enable EDR matching and correction agent location

## ID Patterns

```
ADR-L-0001  Logical ADR
ADR-P-0001  Physical ADR
ADR-D-0001  Decision ADR (autonomous agent decisions)
INV-0001    Invariant
CAP-0001    Capability
COMP-0001   Component
IFACE-0001  Interface
DEC-0001    Decision (logical)
IMPL-0001   Implementation Decision (physical)
CONST-0001  Constraint
GAP-0001    Gap
BOUND-0001  Architectural Boundary
CONTRACT-0001  Interaction Contract
INTEG-0001  Integration Point
NFR-0001    Non-Functional Requirement
```

## Schema Evolution

### Backward Compatibility

Schemas support evolution through optional fields:

```yaml
# v1.0 (minimal)
owned_by: "team-api"

# v1.1 (expanded - backward compatible)
ownership:
  team: "team-api"
  tech_lead: "@alice"
```

### Version Signaling

All artifacts include `schema_version: "1.0"` to enable:
- Tool adaptation based on version
- Breaking changes in major versions (v2.0, v3.0)
- Gradual migration support

## Validation

### Schema Validation Order

1. **Structural validation** - JSON Schema compliance
2. **ID format validation** - Pattern matching
3. **Reference validation** - Referenced IDs exist
4. **Bidirectional validation** - Relationships are consistent
5. **Completeness validation** - Required fields present

### Divergence Mapping

Schema violations map to STE Divergence Taxonomy:

- Missing required field → `Doc-Missing-Inventory`
- Invalid ID format → `Doc-Identifier-Collision` risk
- Broken reference → `Doc-Reference-Unresolvable`
- Missing bidirectional link → `Doc-Bidirectional-Inconsistency`
- ADR not in manifest → `Doc-Orphaned-Item`

## Graph Extraction

### RECON Compatibility

Schemas are designed for ste-runtime RECON extraction:

**Graph Nodes:**
- ADRs (Logical, Physical, Decision)
- Capabilities, Components, Invariants
- Decisions, Constraints, Gaps

**Graph Edges:**
- `implements_logical` → Physical implements Logical
- `related_adrs` → ADR relates to ADR
- `enforced_by` → Invariant enforced by Physical ADR
- `dependencies` → Component depends on Component
- `supersedes` → ADR supersedes ADR

### Slice Metadata

While not in the YAML source, RECON will generate `_slice` metadata:

```yaml
_slice:
  domain: "architecture"
  type: "logical-adr"
  id: "adr-l-0001"
  dependencies: [...]
  dependents: [...]
  tags: [...]
```

## Usage

### Validate ADR Against Schema

```python
import jsonschema
import yaml

# Load schema
with open("schema/v1.0/adr-logical.schema.json") as f:
    schema = json.load(f)

# Load ADR
with open("adrs/logical/ADR-L-0001.yaml") as f:
    adr = yaml.safe_load(f)

# Validate
jsonschema.validate(adr, schema)
```

### Generate Manifest

```python
from adr_kit.generators import ManifestGenerator

generator = ManifestGenerator()
manifest = generator.generate_from_directory("adrs/")
```

## Future Enhancements

Schema v1.0 is designed to support future use cases without breaking changes:

- **Decision ADRs** - Autonomous agent reasoning persistence
- **Policy validation** - Rules & Signal Service integration
- **Drift detection** - Compare declared vs. actual state
- **Blast radius analysis** - Graph traversal for impact assessment
- **Embodiment scoring** - Quantify architectural coverage
- **Correction agents** - Automated remediation with safety boundaries

All future fields can be added as optional, maintaining backward compatibility.
