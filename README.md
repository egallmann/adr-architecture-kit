# ADR Architecture Kit

`adr-architecture-kit` is the canonical ADR encoding and Architecture IR adapter layer for System of Thought Engineering (STE).

It owns the ADR frontmatter model, ADR schemas, authoring-time validation, repository-normalized discovery outputs, and the adapter/compiler logic that turns ADR authority into records that conform to the public Architecture IR contract. It does not own the normative cross-repo IR schema itself. That authority belongs to `ste-spec`.

## What This Repository Owns

- ADR schemas and frontmatter rules for canonical ADR artifacts
- Pydantic models, parsing, and validation for ADR and invariant sources
- Authoring-time normalization and deterministic repository discovery outputs
- Python consumer boundary over compiled repository bundles
- ADR-to-Architecture-IR adapter logic for the public `ste-spec` contract

## What This Repository Does Not Own

- `ste-handbook`: explanatory model, theory, and teaching material
- `ste-spec`: normative contracts, schemas, and the public cross-repo Architecture IR contract
- `ste-runtime`: runtime evidence extraction, observation, and composition
- `ste-kernel`: admission, governance, and decisioning over compiled inputs

See [authority-boundary.md](docs/authority-boundary.md) for the full authority split.

## Three Layers You Must Not Confuse

### 1. ADR Source Model

Canonical ADR YAML and invariant artifacts under `adrs/` are the authoring source of truth for this repository.

### 2. Repository-Normalized Discovery Bundle

This repository compiles canonical ADR inputs into a deterministic repository-facing bundle:

- `adrs/index/architecture-index.yaml`
- `adrs/index/entity-registry.yaml`
- `adrs/index/relationship-registry.yaml`
- `adrs/index/unresolved-registry.yaml`
- `adrs/manifest.yaml`

This bundle is a stable repository discovery and consumer surface. It is not the same thing as the public cross-repo Architecture IR contract.

### 3. Public Cross-Repo Architecture IR

The public Architecture IR contract is defined normatively in `ste-spec`. This repository emits ADR-derived records that conform to that contract, but it does not redefine the contract locally.

For the distinction between these layers, see [architecture-ir-overview.md](docs/architecture-ir-overview.md).

## Public Surface

### Stable v1 public surface

- ADR v1.0 schemas under `schema/v1.0/`
- ADR type taxonomy and frontmatter model
- parser/validator flow for ADRs and invariants
- repository-normalized discovery bundle concept and its core files
- `ArchitectureRepository`
- `NormalizedArchitectureModel`
- the rule that `ArchModel` is compiler-internal
- ADR-to-Architecture-IR adapter semantics, with `ste-spec` owning the normative schema

### Draft surface

- `schema/v1.1/` lifecycle and ledger extensions
- exact evolution of normalized registry fields beyond the core bundle identity
- logical ADR IR adapter profile version details
- additive subset registries and graph artifacts

### Experimental surface

- `ADR-V-*` vision materials
- migration and canonicalization tooling in `src/adr_kit/migrators/`
- workspace boot/publication examples such as `ADR-L-9000` and `scripts/publish_architecture_ir_fragments.py`
- repo guidance that depends on sibling workspace checkouts

See [public-surface-and-stability.md](docs/public-surface-and-stability.md).

## ADR Taxonomy

### `ADR-L`

Logical architecture intent: capabilities, boundaries, contracts, constraints, invariants, and other conceptual decisions.

### `ADR-PS`

Physical-system architecture: high-level implementation/system design, major components, boundaries, and topology.

### `ADR-PC`

Physical-component architecture: implementation-ready component design with enough precision for execution.

### `ADR-P`

Legacy broad physical ADR form. Publicly retained for compatibility and reference, not the preferred forward modeling surface.

### `ADR-V`

Experimental vision material. Useful for future-state exploration, but not part of the stable public v1 contract.

See [adr-type-model.md](docs/adr-type-model.md).

## Core Workflow

```text
ADR sources and invariants
    -> parse and validate
    -> normalize into repository discovery outputs
    -> expose repository-facing semantic boundary
    -> optionally emit ADR-derived Architecture IR fragments
```

### Repository-normalized discovery flow

Use the authoring/compiler toolchain when you need repository-local discovery outputs:

```bash
adr generate-architecture-index
adr generate-manifest
adr generate-rendered-docs
```

`adrs/index/*` plus `adrs/manifest.yaml` are derived artifacts. Treat them as generated, not hand-authored.

### Architecture IR adapter flow

Use the IR fragment path when you need ADR-derived records that conform to the public `ste-spec` Architecture IR contract:

```bash
adr build-ir-fragments
```

This produces the repo's example publication artifact at `dist/architecture-ir/adr-ir-fragments.json`. The normative IR schema still lives in `ste-spec`, and this repo mirrors the current public contract at `contracts/architecture-ir/architecture-ir.schema.json` so the repository remains testable as a standalone checkout.

## Python Consumer Boundary

For Python consumers, the supported repository seam is:

- `ArchitectureRepository`
- `NormalizedArchitectureModel`

`ArchModel` is compiler-internal. It is not the public consumer contract and should not be treated as a stable cross-repo interface.

## Start Here

### For ADR authors

Read:

- [adr-type-model.md](docs/adr-type-model.md)
- [schema/v1.0/README.md](schema/v1.0/README.md)
- [walkthrough-adr-to-ir.md](docs/walkthrough-adr-to-ir.md)

### For Python consumers

Read:

- [architecture-ir-overview.md](docs/architecture-ir-overview.md)
- [authority-boundary.md](docs/authority-boundary.md)
- [`src/adr_kit/repository/architecture_repository.py`](src/adr_kit/repository/architecture_repository.py)

### For cross-repo IR consumers

Read:

- [architecture-ir-overview.md](docs/architecture-ir-overview.md)
- [authority-boundary.md](docs/authority-boundary.md)
- [walkthrough-adr-to-ir.md](docs/walkthrough-adr-to-ir.md)

## Minimal Example

A standalone public example set lives under [`examples/public-v1/`](examples/public-v1/):

- one `ADR-L`
- one `ADR-PS`
- one `ADR-PC`
- a minimal normalized discovery bundle
- an ADR-derived Architecture IR fragment file

Use the walkthrough in [walkthrough-adr-to-ir.md](docs/walkthrough-adr-to-ir.md) to understand how those example assets connect.

## Install

### Standard install

```bash
pip install adr-architecture-kit
```

Requires Python 3.11+. Installs the `adr` CLI and the `adr_kit` Python package.

### Quickstart

```bash
# Verify the install
adr --help

# Validate ADRs in the current directory
adr validate

# Generate the repository discovery index
adr generate-architecture-index
```

### Development / editable install

```bash
git clone https://github.com/egallmann/adr-architecture-kit
cd adr-architecture-kit
pip install -e .[dev]
```

## Contributor Workflow

### Installation

```bash
pip install -e .[dev]
```

Supported runtime: Python 3.11+.

### Validation

```bash
adr validate
adr validate-generated-docs
adr validate-system-overview
```

### Governance bundle

```bash
adr governance-checks
```

### Compile through the unified driver

```bash
adr compile --mode normal
```

`adr compile` remains an authoring-time and repository-discovery path. Runtime-owned machine artifacts move to `ste-runtime` per [AUTHORING-SYSTEM.md](AUTHORING-SYSTEM.md).

## Repository Notes

- `README.md` is manual and contributor-facing.
- `SYSTEM-OVERVIEW.md` is generated; edit its generator/template rather than hand-editing the artifact.
- This repository is expected to work as a standalone checkout. The public Architecture IR schema is mirrored locally at `contracts/architecture-ir/architecture-ir.schema.json`, and tests compare that mirror against a sibling `ste-spec` checkout only when one is present.

## Related Documents

- [Documentation index](docs/README.md) — curated public `docs/` set and contributor reference under `docs/contributors/`
- [architecture-ir-overview.md](docs/architecture-ir-overview.md)
- [adr-type-model.md](docs/adr-type-model.md)
- [public-surface-and-stability.md](docs/public-surface-and-stability.md)
- [authority-boundary.md](docs/authority-boundary.md)
- [walkthrough-adr-to-ir.md](docs/walkthrough-adr-to-ir.md)
- [AUTHORING-SYSTEM.md](AUTHORING-SYSTEM.md)
