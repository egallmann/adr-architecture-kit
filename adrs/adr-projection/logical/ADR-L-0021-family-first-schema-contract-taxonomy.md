<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: d30d344e4b1fb7ffb477a57aa25a3747c1bff8dd4e8ee5721dd27c3608ad2ee0
rendered_hash: d859865805c98e115357b80169cd03ffbe00c13c0577cdb9c31059cefc472b2a
-->

# ADR-L-0021: Family-First Schema Contract Taxonomy and Authority

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0021  
**Authoring contract:** authoring v1.5  
**Created:** 2026-08-15  
**Authors:** adr-architecture-kit  
**Domains:** architecture, schema  
**Tags:** schema-taxonomy, authority, compatibility  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0021 |
| Status | accepted |
| Decisions | 3 |
| Invariants | 2 |


## Context

Canonical JSON schemas currently use version-only root directories while
the accepted architecture distinguishes authoring, normalized-model,
governance, architecture-discovery, and evidence-attribution contracts.
This ADR establishes a family-first repository taxonomy without changing
schema semantics, JSON bytes, package resources, runtime behavior, or the
installed package namespace. Semantic attribution evidence v1.5 is not an
ADR authoring schema v1.5 and is not a normalized model version.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0125 | Canonical schema placement is family-first with family-scoped versions | — |
| DEC-0126 | Canonical repository schemas are the single schema authority | — |
| DEC-0127 | Taxonomy relocation is semantic and runtime neutral | — |

### DEC-0125 — Canonical schema placement is family-first with family-scoped versions

**Rationale**

Place authoring, architecture-discovery, normalized-model, governance,
and evidence-attribution contracts beneath their family roots. Preserve
schema/v1.0 as the sole stable bare numeric compatibility exception, and
retain kernel/ and migrations/ as special families.

### DEC-0126 — Canonical repository schemas are the single schema authority

**Rationale**

The accepted ADR governs family and version policy; schema/... owns the
actual contract bytes; README files orient humans. Installed package
mirrors under src/adr_kit/schema/v*_* are compatibility resources and
remain independently named. The test inventory fixture is a derived,
non-authoritative verification snapshot only.

### DEC-0127 — Taxonomy relocation is semantic and runtime neutral

**Rationale**

Relocation must preserve schema JSON bytes, $id and $ref semantics,
parser/runtime behavior, SDK and CLI behavior, wheel behavior, package
version, and ADR corpus. Any production behavior change is outside this
ADR and is a stop condition.





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0128 | Canonical schema membership and SHA-256 fingerprints are unchanged by taxonomy relocation. | MUST / test | automated |
| INV-0129 | Every canonical schema artifact has one authoritative repository path and at most one explicit package mirror mapping. | MUST / test | automated |

### INV-0128

**Statement**

Canonical schema membership and SHA-256 fingerprints are unchanged by taxonomy relocation.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Byte-preserving relocation is required for semantic neutrality.

### INV-0129

**Statement**

Every canonical schema artifact has one authoritative repository path and at most one explicit package mirror mapping.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Authority must not be duplicated by topology or by the verification fixture.





## Constraints

### CONST-0021 — technical

Schema/v1.0 remains at its existing path as the stable compatibility exception.

**Rationale**

Existing authoring consumers rely on the stable v1.0 path.

### CONST-0022 — technical

Package resources remain under src/adr_kit/schema/v*_* and are not relocated.

**Rationale**

Installed resource namespaces are an independent compatibility surface.

### CONST-0023 — technical

No new bare root version directory may be introduced.

**Rationale**

Family-first placement prevents version-only taxonomy ambiguity.

### CONST-0024 — regulatory

The taxonomy inventory fixture is verification data, never semantic authority.

**Rationale**

Canonical schema bytes and the accepted ADR retain authority.








---

*Generated from ADR-L-0021 by ADR Architecture Kit (projection v3)*