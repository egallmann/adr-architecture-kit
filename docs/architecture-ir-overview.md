# Architecture IR overview

## Purpose

This document separates the three architecture data layers that appear in `adr-architecture-kit`:

- ADR source artifacts
- repository-normalized discovery outputs
- the public cross-repo Architecture IR contract

Those layers are related, but they are **not** interchangeable.

## Normative contract ownership

The public cross-repo Architecture IR contract is owned by **`ste-spec`**.

- Normative schema: `ste-spec/contracts/architecture-ir/architecture-ir.schema.json`
- This repository may emit ADR-derived records that conform to that schema
- This repository must not redefine that schema as a competing authority

This repo carries a **test mirror** of that schema at [`contracts/architecture-ir/architecture-ir.schema.json`](../contracts/architecture-ir/architecture-ir.schema.json); see [`contracts/architecture-ir/MIRROR.md`](../contracts/architecture-ir/MIRROR.md) for provenance.

## The three layers

### ADR source model

Canonical ADR YAML and invariant artifacts under `adrs/` are the authoring source of truth for this repository.

Examples:

- `ADR-L-*`
- `ADR-PS-*`
- `ADR-PC-*`
- standalone `INV-*`

These artifacts express architecture meaning directly in the ADR encoding model owned by this repository.

### Repository-normalized discovery bundle

This repository compiles ADR authority into a deterministic repository-facing bundle, including:

- `adrs/index/architecture-index.yaml`
- `adrs/index/entity-registry.yaml`
- `adrs/index/relationship-registry.yaml`
- `adrs/index/unresolved-registry.yaml`
- `adrs/manifest.yaml`

This bundle is the stable repository discovery surface and the primary input to the Python consumer boundary.

It is **not** the same thing as the public cross-repo Architecture IR contract. It is narrower in some ways, richer in some repository-local ways, and optimized for repository discovery and semantic loading.

### Public Architecture IR

The public Architecture IR is the cross-repo contract defined in `ste-spec`.

`adr-architecture-kit` contributes to that layer by compiling ADR authority into IR-compatible records. In this repository, the concrete adapter path today is the logical ADR IR fragment compiler and its conventional publication example.

## Compiler-internal IR vs public IR

[`ArchModel`](../src/adr_kit/compiler/ir/arch_model.py) is **compiler-internal**.

It exists to support authoring-time compilation, pass orchestration, and deterministic projection. It is not:

- the repository consumer boundary
- the public Architecture IR contract
- a stable cross-repo data model

The stable Python consumer seam is instead:

- [`ArchitectureRepository`](../src/adr_kit/repository/architecture_repository.py)
- [`NormalizedArchitectureModel`](../src/adr_kit/models/normalized_architecture_model.py)

## How this repository emits IR

Current public IR adapter behavior:

- **source:** selected `ADR-L-*` inputs
- **adapter/compiler:** logical ADR IR fragment compiler
- **output:** deterministic JSON fragment array
- **contract target:** `ste-spec` Architecture IR schema

The output is an adapter surface into the public IR contract, not a replacement for the full compiled document assembly performed elsewhere in the STE stack.

## Practical rules

- Treat ADR YAML and invariants as canonical source authority for this repository.
- Treat `adrs/index/*` and `adrs/manifest.yaml` as repository-generated discovery outputs.
- Treat `ste-spec` as the only normative owner of the public Architecture IR schema.
- Treat `ArchModel` as internal only.
- Treat `ArchitectureRepository` and `NormalizedArchitectureModel` as the supported Python consumer seam.

## Related

- [authority-boundary.md](authority-boundary.md)
- [public-surface-and-stability.md](public-surface-and-stability.md)
- [walkthrough-adr-to-ir.md](walkthrough-adr-to-ir.md)
