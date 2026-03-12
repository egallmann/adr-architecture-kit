# Documentation Projection Architecture

## Authoritative Model

- Canonical architectural authority remains source artifacts plus generator/template implementation.
- Covered canonical inputs are structured architecture artifacts and explicit projection code/templates.
- Covered generated documentation artifacts are derived projections only. They are committed for convenience, but they are never authoritative inputs back into the architecture system.
- Integrity metadata proves consistency with canonical inputs and the declared generator contract. It does not prove authorship and does not confer authority.
- Covered generated artifacts are committed, derived, reproducible, and disposable because they can be regenerated deterministically.

## Current Generator Architecture

Canonical artifacts:

- `adrs/logical/` and `adrs/physical/` ADR YAML
- `adrs/invariants/` invariant YAML
- `PROJECT.yaml` only where a generator explicitly consumes it
- generator code under `src/adr_kit/generators/`
- templates under `src/adr_kit/templates/`

Generated artifacts:

- `adrs/manifest.yaml` from `ManifestGenerator`
- `adrs/rendered/*.md` from `MarkdownGenerator`
- `SYSTEM-OVERVIEW.md` from `SystemOverviewGenerator`

Current formalization gap now closed by this subsystem:

- rendered ADR markdown already existed as generated output, but previously lacked a first-class CLI workflow and integrity validation

Current v1.1 status:

- parser/model/schema/manifest support exists for requirements snapshots and decision ledgers
- those source directories are not populated in the top-level workspace today

## ADR Taxonomy

- `ADR-L-XXXX`: conceptual logical architecture, including capabilities, boundaries, contracts, constraints, invariants, and non-functional requirements
- `ADR-V-XXXX`: vision-oriented logical ADRs that describe future-state direction and planned capabilities the system should evolve toward
- `ADR-P-XXXX`: legacy broad physical implementation specifications
- `ADR-PS-XXXX`: Physical-System ADRs that describe high-level system design, major component boxes, relationships, integration patterns, broad technology claims, and a coherent design for the abstraction layer they support
- `ADR-PC-XXXX`: Physical-Component ADRs that define executable architecture with enough detail for implementation-ready AI or human execution

## Decision Ledger Model

- The current authoritative decision ledger for this workspace is ADR YAML, specifically logical ADR `decisions` blocks.
- Standalone v1.1 `DecisionLedger` artifacts are supported by schema/parser/manifest/test code but are not active top-level canonical inputs in this workspace today.
- ADR decisions render into `adrs/rendered/*.md`.
- ADR-derived decision metadata contributes to `adrs/manifest.yaml`.
- `SYSTEM-OVERVIEW.md` does not directly consume ADR decision data in v1.
- `SYSTEM-OVERVIEW.md` input basis is limited to explicitly declared generator/template inputs.

## Projection Pipeline

```text
canonical architecture artifacts
        ->
generators and templates
        ->
rendered documentation
        ->
integrity validation
```

## Integrity Header Schema

Required fields, fixed order:

1. `integrity_schema_version`
2. `generated`
3. `artifact_kind`
4. `generator_id`
5. `generator_version`
6. `hash_algorithm`
7. `source_hash`
8. `rendered_hash`

Rules:

- `integrity_schema_version` is fixed to `1`
- `generated` is the literal marker `deterministic_projection_v1`
- field names are fixed and case-sensitive
- field order is fixed and deterministic
- unknown fields are rejected in v1
- header bytes are excluded from both `source_hash` and `rendered_hash`

Markdown example:

```html
<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: <sha256>
rendered_hash: <sha256>
-->
```

YAML example:

```yaml
# integrity_schema_version: 1
# generated: deterministic_projection_v1
# artifact_kind: manifest
# generator_id: adr-manifest
# generator_version: 1
# hash_algorithm: sha256
# source_hash: <sha256>
# rendered_hash: <sha256>
```

## Validation Semantics

Statuses:

- `valid`
- `stale_generated_output`
- `tampered_generated_output`
- `missing_or_malformed_integrity_header`
- `unsupported_artifact_kind`

Definitions:

- `stale_generated_output`: canonical inputs changed and the committed artifact no longer matches the current source basis
- `tampered_generated_output`: committed artifact body no longer matches its declared generated form
- `missing_or_malformed_integrity_header`: deterministic verification cannot be performed
- `unsupported_artifact_kind`: discovered file declares an unknown `artifact_kind`

## Developer Workflow

Regenerate, then validate:

```bash
adr generate-manifest
adr generate-rendered-docs
adr generate-system-overview
adr validate-generated-docs
```

Repository policy:

- contributors edit canonical sources, not covered generated artifacts
- contributors do not hand-edit `adrs/manifest.yaml`, `adrs/rendered/*.md`, or `SYSTEM-OVERVIEW.md`
- CI verifies committed generated projections remain consistent with canonical inputs and declared generator contracts
