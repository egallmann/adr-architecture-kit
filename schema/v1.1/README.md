# ADR Kit Schema v1.1

**Schema Governance**: Provisional Alpha Revision

This directory contains v1.1 schema extensions that support full STE architecture lifecycle traceability.

## Schema Files

### entity-registry.schema.json

Canonical registry of all architecture entities across ADRs.

**Purpose**: Track lifecycle and relationships for existing entity types (CAP-XXXX, COMP-XXXX, BOUND-XXXX, etc.) without creating a parallel model.

**Key Features**:
- Reuses existing entity IDs from v1.0
- Tracks entity lifecycle (proposed, active, deprecated, superseded)
- Forward-only relationship authorship (inverse edges automatically derived)
- Generated from ADR content, never manually edited

**Entity Types**:
- capability, boundary, contract, constraint, nfr, decision, gap (from Logical ADRs)
- component, interface, integration, implementation_decision (from Physical ADRs)
- invariant (standalone or embedded)

**Storage**: `<scope-root>/adrs/entities/registry.yaml`

### requirements-snapshot.schema.json

Captures requirements interrogation state at a point in time.

**Purpose**: Formalize REQ interrogation results that feed Decision Ledgers.

**Key Features**:
- Snapshot-local identifiers (RQCAP-XXXX, RQCONST-XXXX, RQINV-XXXX, RQNFR-XXXX)
- No circular dependencies with ADR-defined canonical entities
- Immutable after reference by Decision Ledger
- Technology signals for rule activation

**Storage**: `<scope-root>/adrs/requirements/snapshots/REQ-XXXX-snapshot.yaml`

### decision-ledger.schema.json

Bounds design space and constrains ADR creation.

**Purpose**: Formalize the design constraint contract that bounds the Logical ADR design space.

**Key Features**:
- Ledger-local decision IDs (LDEC-XXXX) separate from ADR decision IDs (DEC-XXXX)
- References exact requirements snapshot version
- Versioned (ledger version increments for scope changes)
- Allows controlled discovery during implementation

**Storage**: `<scope-root>/adrs/decisions/ledgers/LEDGER-XXXX-ledger.yaml`

## Governance Model

**Provisional Alpha Revision**:
- v1.0 and v1.1 are internal schema lines under single-author control
- In-place revision of v1.0 files allowed for architectural clarity
- Compatibility guarantees deferred until publication stabilization

**Schema Authority**:
- **ste-spec** remains the normative architectural doctrine and governance source
- **adr-architecture-kit** is the authoritative implementation source for ADR schemas
- **ste-runtime** and **ste-rules-library** consume artifact/schema outputs

## Integration with v1.0

v1.1 extends v1.0 schemas:

**Extended v1.0 Files**:
- `adr-common.schema.json`: Added entity lifecycle fields (introduces_entities, modifies_entities, realizes_entities, related_ledgers)
- `adr-physical.schema.json`: Added plural relationship fields to components (implements_capabilities, realizes_entities)
- `manifest.schema.json`: Added entities, requirements_snapshots, decision_ledgers sections

**New v1.1 Files**:
- `entity-registry.schema.json`
- `requirements-snapshot.schema.json`
- `decision-ledger.schema.json`
- `objection-override.schema.json`
- `implementation-attribution-evidence.schema.json`

## Architecture Flow

```
Requirements Snapshot (REQ-XXXX)
  ↓ feeds
Decision Ledger (LEDGER-XXXX)
  ↓ constrains
Logical ADR (ADR-L-XXXX)
  ↓ introduces entities (CAP, BOUND, CONTRACT)
  ↓ implements
Physical ADR (ADR-P-XXXX)
  ↓ introduces entities (COMP, IFACE, INTEG)
  ↓ components reference entities
Entity Registry
  ↓ aggregated in
Manifest
  ↓ mapped to code/infra
ste-runtime Graph
```

## Scope-Aware Placement

All new artifacts are scope-aware:
- Each scope (workspace, submodule) maintains its own entity registry, requirements snapshots, decision ledgers, and manifest
- Artifacts placed within `<scope-root>/adrs/` directory
- Recursive operations aggregate across scopes

## Future Stabilization

When the architecture reaches publication readiness:
- v1.0 will be frozen as the first stable schema release
- Subsequent schema evolution will follow semantic versioning
- Migration tooling will be introduced if breaking changes occur

Until that milestone, schema evolution remains flexible.
