<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: f5e5d4f77353d9ada66412468850d17ada669c55eb2458551738692aae3a3e68
rendered_hash: 8160ed8039723400d12602372f59988448a74b30b214bd9a108035f49cb85f25
-->

# ADR-L-0002: Multi-Scope ADR Architecture for Sub-Module Development

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0002  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-08  
**Modified:** 2026-03-08  
**Authors:** erik.gallmann  
**Domains:** adr, architecture, governance, multi-project  
**Tags:** adr, scope-resolution, multi-project, sub-modules, monorepo  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0002 |
| Status | accepted |
| Decisions | 1 |
| Capabilities | 4 |
| Invariants | 7 |
| Physical realizations | [ADR-PS-0001](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md), [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md), [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md), [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md), [ADR-PC-0003](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md), [ADR-PC-0008](../physical-component/ADR-PC-0008-project-scope-resolution.md) |


## Context

The adr-architecture-kit is being actively developed in a single workspace alongside
multiple sub-modules (ste-runtime, future services) that will eventually become
independent services. Each sub-module needs to leverage the ADR system for its own
architectural documentation while being developed in parallel within the monorepo.

Current challenges:
1. ADR generators/validators are hardcoded to work at a single project scope
2. Sub-modules cannot maintain their own ADR directories independently
3. No mechanism to discover and validate ADRs at different project levels
4. Tooling assumes a single adrs/ directory at the workspace root

The ste-runtime already implements a sophisticated project scope resolution mechanism
(see src/config/index.ts) that:
- Auto-detects project boundaries via markers (package.json, pyproject.toml, etc.)
- Supports both self-analysis and external project modes
- Enforces workspace boundaries to prevent scanning outside intended scope
- Uses ste.config.json as authoritative project marker

We need similar scope resolution for ADR generation and validation to support:
- Workspace root ADRs (adr-architecture-kit itself)
- Sub-module ADRs (ste-runtime/adrs/, future-service/adrs/)
- Independent service ADRs (when modules are extracted)
- Parallel development with isolated documentation
## Architectural Decisions

### DEC-0007 — Adopt Scope-Aware ADR Architecture

**Rationale**

ADR generators and validators must support multiple project scopes to enable
sub-modules to maintain independent architectural documentation while being
developed in a shared workspace.

This mirrors the ste-runtime's project scope resolution pattern, providing
consistent behavior across the STE ecosystem.

**Consequences**

Positive:
- ADR tools can work at any project level (workspace, sub-module, service)
- Sub-modules can maintain independent ADR directories
- Tooling auto-detects project boundaries using standard markers
- Manifest generation scoped to specific project context
- Validation can be run at different scopes independently


## Capabilities

### CAP-0019 — Automatic Project Scope Detection

Auto-detect project boundaries by searching for markers:
- ste.config.json (authoritative)
- PROJECT.yaml (ADR-specific marker)
- package.json, pyproject.toml (language markers)
- .git directory (repository root)

**Acceptance criteria**
- Detects workspace root when run from any subdirectory
- Detects sub-module root when run from sub-module
- Respects explicit --scope parameter
- Fails gracefully with clear error if no project found

### CAP-0022 — Scoped Manifest Generation

Generate manifest.yaml scoped to specific project, including only ADRs
within that project's adrs/ directory

**Acceptance criteria**
- Manifest includes only ADRs from detected scope
- File paths in manifest are relative to project root
- Cross-scope references are validated but not included
- Generated manifest includes scope metadata

### CAP-0025 — Scoped Validation

Validate ADRs within specific project scope, with optional recursive
validation of sub-modules

**Acceptance criteria**
- Validates ADRs in detected scope
- Validates cross-references within scope
- Warns on cross-scope references without validation
- Recursive mode validates all sub-scopes

### CAP-0028 — Multi-Scope CLI Interface

Provide CLI commands that work at any scope level with consistent behavior

**Acceptance criteria**
- adr generate-manifest works from any directory
- adr validate works from any directory
- "--scope" parameter overrides auto-detection
- "--recursive" enables multi-scope operations




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0014 | ADR generators and validators MUST support explicit scope parameter to override auto-detection when needed | MUST / design | automated |
| INV-0015 | Project scope resolution MUST use the same marker hierarchy as ste-runtime: 1. Explicit --scope parameter (highest… | MUST / design | automated |
| INV-0016 | Each project scope MUST maintain its own adrs/ directory and manifest.yaml | MUST / design | automated |
| INV-0017 | ADR cross-references between different scopes MUST use fully-qualified identifiers (e.g., "ste-runtime:ADR-L-0001") | SHOULD / design | automated |
| INV-0018 | Scope resolution MUST NOT traverse above workspace root to prevent scanning unintended directories | MUST / design | automated |
| INV-0019 | ADR validation at workspace scope SHOULD validate all sub-module ADRs recursively when --recursive flag is provided | SHOULD / design | automated |
| INV-0098 | Recursive compilation must compile each resolved project scope independently and must not implicitly merge… | MUST / design | automated |

### INV-0014

**Statement**

ADR generators and validators MUST support explicit scope parameter to
override auto-detection when needed

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

While auto-detection handles most cases, explicit scope control is needed
for CI/CD, testing, and edge cases where auto-detection may be ambiguous

### INV-0015

**Statement**

Project scope resolution MUST use the same marker hierarchy as ste-runtime:
1. Explicit --scope parameter (highest priority)
2. ste.config.json in current or parent directories
3. Standard project markers (package.json, pyproject.toml, .git)
4. Current working directory (fallback)

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Consistent scope resolution across STE tools prevents confusion and ensures
predictable behavior

### INV-0016

**Statement**

Each project scope MUST maintain its own adrs/ directory and manifest.yaml

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Independent ADR directories enable sub-modules to document their own
architecture without interfering with parent or sibling projects

### INV-0017

**Statement**

ADR cross-references between different scopes MUST use fully-qualified
identifiers (e.g., "ste-runtime:ADR-L-0001")

**Scope:** global

**Enforcement:** SHOULD (design)
**Verification:** automated

**Rationale**

Enables linking between workspace and sub-module ADRs while maintaining
clear scope boundaries

### INV-0018

**Statement**

Scope resolution MUST NOT traverse above workspace root to prevent
scanning unintended directories

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Security and performance - prevents accidental scanning of home directory
or system directories

### INV-0019

**Statement**

ADR validation at workspace scope SHOULD validate all sub-module ADRs
recursively when --recursive flag is provided

**Scope:** global

**Enforcement:** SHOULD (design)
**Verification:** automated

**Rationale**

Enables comprehensive validation of entire workspace architecture while
maintaining ability to validate individual scopes

### INV-0098

**Statement**

Recursive compilation must compile each resolved project scope independently and must not implicitly merge architecture state across scopes.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Multi-scope support exists so each project root owns its canonical ADR state.
Recursive execution is orchestration, not authorization to collapse scopes.




## Physical Realization

**Systems**
- [ADR-PS-0001](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md)
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)

**Components**
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-PC-0003](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md)
- [ADR-PC-0008](../physical-component/ADR-PC-0008-project-scope-resolution.md)




## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0004](ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)

**References**
- [ADR-L-0004](ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)
- [ADR-L-0003](ADR-L-0003-quality-assurance-and-testing-strategy.md)
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0012](ADR-L-0012-federation-authority-and-qualified-identity-model.md)
- [ADR-L-0017](ADR-L-0017-forward-authoring-ergonomics-for-split-physical-adr-types.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-PC-0001 — Entity Registry and Discovery Index](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md) | implements this logical authority | `ADR-PC-0001 -[:implements_logical]-> ADR-L-0002` |
| [ADR-PC-0002 — Schema and Contract Validation](../physical-component/ADR-PC-0002-schema-and-contract-validation.md) | implements this logical authority | `ADR-PC-0002 -[:implements_logical]-> ADR-L-0002` |
| [ADR-PC-0003 — Compiler Pipeline and Driver](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md) | implements this logical authority | `ADR-PC-0003 -[:implements_logical]-> ADR-L-0002` |
| [ADR-PC-0008 — Project Scope Resolution](../physical-component/ADR-PC-0008-project-scope-resolution.md) | implements this logical authority | `ADR-PC-0008 -[:implements_logical]-> ADR-L-0002` |
| [ADR-PS-0001 — ADR Architecture Kit Discovery and Indexing System](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md) | implements this logical authority | `ADR-PS-0001 -[:implements_logical]-> ADR-L-0002` |
| [ADR-PS-0002 — ADR Kit Authoring Compiler and Validation System](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md) | implements this logical authority | `ADR-PS-0002 -[:implements_logical]-> ADR-L-0002` |




## Notes

Implementation should leverage existing patterns from ste-runtime/src/config/index.ts
for project root detection and boundary validation.

Consider future enhancement: ADR aggregation service that can query ADRs across
all scopes in workspace for cross-cutting architectural analysis.


---

*Generated from ADR-L-0002 by ADR Architecture Kit (projection v3)*