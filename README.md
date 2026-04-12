# ADR Architecture Kit

**ADR Architecture Kit** (`adr-architecture-kit`) is a Python toolkit for teams and integrators who maintain **Architecture Decision Records** as structured YAML. It parses and validates those sources, normalizes them into deterministic machine-queryable **repository discovery** outputs (indexes, registries, manifest), and can emit **ADR-derived Architecture IR** fragments that match the public contract defined in **`ste-spec`**.

Prose ADRs often go stale once written. Structured YAML keeps architecture as a **first-class maintained artifact**: explicit shapes and links preserve higher-fidelity intent for human review and for AI-assisted engineering, slowing drift and informal lossiness when decisions live only in narrative. Machine-readable discovery outputs and **Architecture IR** supply shared, queryable context for review and automation—grounding work in repository facts rather than inferring structure from incomplete prose; that reduces (it does not remove) the risk of speculative reasoning when assistants and engineers reason about the system at scale. Derived indexes, registries, and rendered documentation keep those views reproducible as the codebase matures. For how contracts split across related repositories, see [Who Owns What](#who-owns-what) below.

## Authoring boundary and AI orientation

`adr-architecture-kit` does not turn freeform conversation into architectural decisions by itself. It expects intent already expressed in **structured** inputs (canonical ADR YAML and related artifacts), then **validates** and **materializes** them into repository-native outputs—deterministic discovery bundles, rendered views, and ADR-derived Architecture IR aligned with **`ste-spec`**.

There is a deliberate **generation gap** between informal reasoning (including model-assisted chat) and **schema-conformant, placement-correct** STE ADRs. This repository mitigates that gap in two ways: structured drafts are checked by parsers and validators; and **[`SYSTEM-OVERVIEW.md`](SYSTEM-OVERVIEW.md)**—a **generated, AI-first orientation** artifact—gives assistants a canonical discovery path (authority order, scope rules, CLI and generator entry points, placement conventions) before they author or change ADRs. **`SYSTEM-OVERVIEW.md`** does not replace **`ste-spec`** doctrine; it orients work **in this repository** (regenerate with `adr generate-system-overview`; do not hand-edit the committed file).

**AI-assisted IDEs and coding agents** can be **guided with repository instructions and examples** to **draft** structured ADR inputs; this kit remains the **schema, validation, and materialization** boundary between accepted structured intent and committed canonical artifacts.

## Quick Start

Requires **Python 3.11+**. Installs the `adr` CLI and the `adr_kit` package.

```bash
pip install adr-architecture-kit

adr --help
```

`adr --help` works from any directory after install. `adr validate` and `adr generate-architecture-index` are project-scoped commands: they require a resolvable project tree with `adrs/` and the expected project markers, or an explicit `--scope PATH`.

For a first end-to-end run, use a repository checkout with `adrs/` populated and follow [walkthrough-adr-to-ir.md](docs/walkthrough-adr-to-ir.md). The public example under [`examples/public-v1/`](examples/public-v1/) is included in that walkthrough.

## Minimal Example

A standalone public example lives under [`examples/public-v1/`](examples/public-v1/): one `ADR-L`, one `ADR-PS`, one `ADR-PC`, a minimal normalized discovery bundle, and an ADR-derived Architecture IR fragment file. The walkthrough links each asset.

Representative logical ADR source (trimmed from the public example):

```yaml
# adrs/logical/ADR-L-0001-public-example-logical.yaml (excerpt)
schema_version: "1.0"
adr_type: logical
id: ADR-L-0001
title: "Public Example Logical ADR"
status: accepted
capabilities:
  - id: CAP-0001
    name: Public Repository Onboarding
    description: Explain the minimal public ADR to IR flow.
```

From a checkout with `adrs/` populated, `adr generate-architecture-index` (with other generators as needed) materializes discovery outputs such as `adrs/index/architecture-index.yaml` and companion registries under `adrs/index/`.

## What It Does

- ADR schemas and frontmatter rules for canonical ADR artifacts
- Pydantic models, parsing, and validation for ADR and invariant sources
- Authoring-time normalization and deterministic repository discovery outputs
- Python API over compiled repository bundles (`ArchitectureRepository`, `NormalizedArchitectureModel`)
- ADR-to-Architecture-IR adapter logic for the public **`ste-spec`** contract

## Core Workflow

```text
ADR sources and invariants
    -> parse and validate
    -> normalize into repository discovery outputs
    -> expose repository-facing semantic boundary
    -> optionally emit ADR-derived Architecture IR fragments
```

```bash
# Repository-local discovery outputs (derived; do not hand-edit adrs/index/* or manifest)
adr generate-architecture-index
adr generate-manifest
adr generate-rendered-docs

# Example publication path for ADR-derived IR fragments (schema: ste-spec; test mirror under contracts/)
adr build-ir-fragments
```

## Key Concepts

**Three data layers** — each has a distinct role:

1. **ADR source model** — Canonical YAML and invariants under `adrs/` are the authoring source of truth for this repository.
2. **Repository-normalized discovery bundle** — Deterministic outputs such as `adrs/index/*.yaml` and `adrs/manifest.yaml` for repo-local discovery; separate from the cross-repo Architecture IR contract. For the supported Python API, use `ArchitectureRepository` and `NormalizedArchitectureModel` (`ArchModel` is internal to the compiler, not a stable public interface).
3. **Public Architecture IR** — Defined in **`ste-spec`**; this kit emits conforming ADR-derived records without redefining that schema.

More detail: [architecture-ir-overview.md](docs/architecture-ir-overview.md).

**ADR taxonomy (quick reference)**

| Prefix | Role | Stability |
|--------|------|-------------|
| **ADR-L** | Conceptual architecture: capabilities, boundaries, contracts, invariants, decisions | Stable public v1 |
| **ADR-PS** | Physical-system: topology, integration patterns, high-level technology posture | Stable public v1 |
| **ADR-PC** | Physical-component: implementation-ready design, interfaces, identifiers | Stable public v1 |
| **ADR-P** | Legacy broad physical ADR | Compatibility; not preferred for new work |
| **ADR-V** | Vision / future-state exploration | Experimental; not stable v1 contract |

Full model: [adr-type-model.md](docs/adr-type-model.md).

## Who Owns What

- **`ste-handbook`** — Explanatory model, theory, teaching.
- **`ste-spec`** — Contracts, schemas, and the public cross-repo Architecture IR contract.
- **`adr-architecture-kit`** (this repo) — ADR encoding, authoring validation, repository discovery outputs, and IR adapter logic into **`ste-spec`**.
- **`ste-runtime`** — Runtime observation, evidence extraction, composition.
- **`ste-kernel`** — Admission and governance over compiled inputs.

Full split: [authority-boundary.md](docs/authority-boundary.md).

## Stability

This project is **pre-1.0 (Alpha)** on PyPI; surfaces may evolve until a **1.0** commitment. Trove classifiers match that posture.

- **Stable v1** — ADR v1.0 schemas, parser/validator behavior, discovery bundle role, supported Python API, IR adapter semantics with **`ste-spec`** owning the Architecture IR schema contract.
- **Draft** — v1.1 and evolving registry/IR adapter details; consume with care.
- **Experimental** — Vision ADRs, migrators, workspace boot examples; not a basis for long-term external dependencies.

Full breakdown: [public-surface-and-stability.md](docs/public-surface-and-stability.md).

## Documentation

### Public documentation

| Document | Description |
|----------|-------------|
| [authority-boundary.md](docs/authority-boundary.md) | Who owns what across `ste-handbook`, `ste-spec`, this kit, `ste-runtime`, and `ste-kernel` |
| [adr-type-model.md](docs/adr-type-model.md) | ADR taxonomy: `ADR-L`, `ADR-PS`, `ADR-PC`, legacy `ADR-P`, experimental `ADR-V` |
| [architecture-ir-overview.md](docs/architecture-ir-overview.md) | Three layers: ADR sources, repository discovery bundle, public Architecture IR |
| [public-surface-and-stability.md](docs/public-surface-and-stability.md) | Stable v1 vs draft vs experimental surfaces |
| [walkthrough-adr-to-ir.md](docs/walkthrough-adr-to-ir.md) | End-to-end flow with [`examples/public-v1/`](examples/public-v1/) |

### Contributor guides

| Document | Description |
|----------|-------------|
| [SYSTEM-OVERVIEW.md](SYSTEM-OVERVIEW.md) | Generated AI-first repo orientation (authority, workflows, CLI, generators); read before large changes |
| [contributors/tdd-workflow.md](docs/contributors/tdd-workflow.md) | TDD workflow for this codebase |
| [contributors/logical-adr-guide.md](docs/contributors/logical-adr-guide.md) | Writing logical ADRs |
| [contributors/physical-adr-guide.md](docs/contributors/physical-adr-guide.md) | Physical ADR families (`ADR-PS`, `ADR-PC`, legacy `ADR-P`) |
| [contributors/schema-guide.md](docs/contributors/schema-guide.md) | Long-form schema and validation notes |
| [contributors/placement-convention.md](docs/contributors/placement-convention.md) | Placement rules for ADRs, manifest, and index paths |

Also [CONTRIBUTING.md](CONTRIBUTING.md) and [schema/v1.0/README.md](schema/v1.0/README.md). **Where to start:** ADR authors — [adr-type-model.md](docs/adr-type-model.md), [schema/v1.0/README.md](schema/v1.0/README.md), [walkthrough-adr-to-ir.md](docs/walkthrough-adr-to-ir.md). Python or cross-repo IR consumers — [architecture-ir-overview.md](docs/architecture-ir-overview.md), [authority-boundary.md](docs/authority-boundary.md); code entry point [`architecture_repository.py`](src/adr_kit/repository/architecture_repository.py).

## Contributing

Contributions use **Test-Driven Development** (see [`PROJECT.yaml`](PROJECT.yaml), `ADR-L-0003`). Setup, quality gates, schema parity, governance, and PR flow are in [CONTRIBUTING.md](CONTRIBUTING.md). Authoring and placement guides live under [docs/contributors/](docs/contributors/). For authoring-time vs runtime artifact boundaries, see [AUTHORING-SYSTEM.md](AUTHORING-SYSTEM.md).
