# ADR Architecture Kit

**ADR Architecture Kit** (`adr-architecture-kit`) is the authoring-time STE toolkit for teams and integrators who maintain **Architecture Decision Records** as structured YAML. The Python implementation provides parsing, validation, CLI authoring workflows, deterministic **repository discovery** outputs (indexes, registries, manifest), and **ADR-derived Architecture IR** fragments that match the public contract defined in **`ste-spec`**. The same release lineage also publishes the official read-only TypeScript consumer binding [`@system-of-thought/adr-kit`](https://www.npmjs.com/package/@system-of-thought/adr-kit) (ADR-L-0024).

Semantic authority is language-neutral: accepted ADRs, canonical schemas, and promoted contracts define ADR-Kit meaning; Python and TypeScript implementations project that authority and do not own it independently.

```text
accepted ADRs + canonical schemas + promoted contracts
    -> language-neutral ADR-Kit semantic authority
    -> Python implementation
    -> TypeScript consumer binding
```

Prose ADRs often go stale once written. Structured YAML keeps architecture as a **first-class maintained artifact**: explicit shapes and links preserve higher-fidelity intent for human review and for AI-assisted engineering, slowing drift and informal lossiness when decisions live only in narrative. Machine-readable discovery outputs and **Architecture IR** supply shared, queryable context for review and automation—grounding work in repository facts rather than inferring structure from incomplete prose; that reduces (it does not remove) the risk of speculative reasoning when assistants and engineers reason about the system at scale. Derived indexes, registries, and rendered documentation keep those views reproducible as the codebase matures. For how contracts split across related repositories, see [Who Owns What](#who-owns-what) below.

## Authoring boundary and AI orientation

`adr-architecture-kit` does not turn freeform conversation into architectural decisions by itself. It expects intent already expressed in **structured** inputs (canonical ADR YAML and related artifacts), then **validates** and **materializes** them into repository-native outputs—deterministic discovery bundles, rendered views, and ADR-derived Architecture IR aligned with **`ste-spec`**.

There is a deliberate **generation gap** between informal reasoning (including model-assisted chat) and **schema-conformant, placement-correct** STE ADRs. This repository mitigates that gap in two ways: structured drafts are checked by parsers and validators; and **[`SYSTEM-OVERVIEW.md`](https://github.com/egallmann/adr-architecture-kit/blob/main/SYSTEM-OVERVIEW.md)**—a **generated, AI-first orientation** artifact—gives assistants a canonical discovery path (authority order, scope rules, CLI and generator entry points, placement conventions) before they author or change ADRs. **`SYSTEM-OVERVIEW.md`** does not replace **`ste-spec`** doctrine; it orients work **in this repository** (regenerate with `adr generate-system-overview`; do not hand-edit the committed file).

**AI-assisted IDEs and coding agents** can be **guided with repository instructions and examples** to **draft** structured ADR inputs; this kit remains the **schema, validation, and materialization** boundary between accepted structured intent and committed canonical artifacts.

## Quick Start

Minimum supported Python is **3.14** (`requires-python >=3.14`). Currently qualified released minor line: **3.14.x**. Reference development interpreter: **3.14.7**. Installs the `adr` CLI and the `adr_kit` package.

```bash
pip install adr-architecture-kit

adr --help
```

`adr --help` works from any directory after install. `adr validate` and `adr generate-architecture-index` are project-scoped commands: they require a resolvable project tree with `adrs/` and the expected project markers, or an explicit `--scope PATH`.

New Python integrations should use the narrow supported facade:

```python
from pathlib import Path
from adr_kit.api import ValidationRequest, capabilities, validate_architecture

print(capabilities().as_dict())
result = validate_architecture(ValidationRequest(Path("/absolute/project/root")))
print(result.success, result.diagnostics)
```

See the [public SDK guide](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/public-sdk.md) for preview/write compilation,
repository queries, diagnostics, and the exact supported inventory.

TypeScript / Node consumers should start with the official binding docs:

- [`packages/node/README.md`](https://github.com/egallmann/adr-architecture-kit/blob/main/packages/node/README.md)
- [`docs/typescript-consumer-binding.md`](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/typescript-consumer-binding.md)

For a first end-to-end run, use a repository checkout with `adrs/` populated and follow [walkthrough-adr-to-ir.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/walkthrough-adr-to-ir.md). The public example under [`examples/public-v1/`](https://github.com/egallmann/adr-architecture-kit/tree/main/examples/public-v1/) is included in that walkthrough.

## Minimal Example

A standalone public example lives under [`examples/public-v1/`](https://github.com/egallmann/adr-architecture-kit/tree/main/examples/public-v1/): one `ADR-L`, one `ADR-PS`, one `ADR-PC`, a minimal normalized discovery bundle, and an ADR-derived Architecture IR fragment file. The walkthrough links each asset.

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
- Narrow installed-package SDK (`adr_kit.api`) over validation, authoring compilation,
  `ArchitectureRepository`, and `NormalizedArchitectureModel`
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
adr generate-adr-projection
# compatibility alias:
# adr generate-rendered-docs

# Example publication path for ADR-derived IR fragments (schema: ste-spec; test mirror under contracts/)
adr build-ir-fragments
```

## Key Concepts

**Three data layers** — each has a distinct role:

1. **ADR source model** — Canonical YAML and invariants under `adrs/` are the authoring source of truth for this repository.
2. **Repository-normalized discovery bundle** — Deterministic outputs such as `adrs/index/*.yaml` and `adrs/manifest.yaml` for repo-local discovery; separate from the cross-repo Architecture IR contract. For the supported Python API, use `ArchitectureRepository` and `NormalizedArchitectureModel` (`ArchModel` is internal to the compiler, not a stable public interface).
3. **Public Architecture IR** — Defined in **`ste-spec`**; this kit emits conforming ADR-derived records without redefining that schema.

More detail: [architecture-ir-overview.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/architecture-ir-overview.md).

**ADR taxonomy (quick reference)**

| Prefix | Role | Stability |
|--------|------|-------------|
| **ADR-L** | Conceptual architecture: capabilities, boundaries, contracts, invariants, decisions | Stable public v1 |
| **ADR-PS** | Physical-system: topology, integration patterns, high-level technology posture | Stable public v1 |
| **ADR-PC** | Physical-component: implementation-ready design, interfaces, identifiers | Stable public v1 |
| **ADR-P** | Legacy broad physical ADR | Compatibility; not preferred for new work |
| **ADR-V** | Vision / future-state exploration | Experimental; not stable v1 contract |

Full model: [adr-type-model.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/adr-type-model.md).

## Who Owns What

- **`ste-handbook`** — Explanatory model, theory, teaching.
- **`ste-spec`** — Contracts, schemas, and the public cross-repo Architecture IR contract.
- **`adr-architecture-kit`** (this repo) — ADR encoding, authoring validation, repository discovery outputs, IR adapter logic into **`ste-spec`**, and the official TypeScript consumer binding `@system-of-thought/adr-kit` (ADR-L-0024).
- **`ste-runtime`** — Runtime observation, evidence extraction, composition.
- **`ste-kernel`** — Admission and governance over compiled inputs.

Full split: [authority-boundary.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/authority-boundary.md).

## Stability

This project is **pre-1.0 (Alpha)** on PyPI (`adr-architecture-kit`) and npm (`@system-of-thought/adr-kit`); surfaces may evolve until a **1.0** commitment. Trove classifiers match that posture. Shared release lineage keeps Python and TypeScript distributions version-aligned.

- **Stable** — ADR v1.0 encoding, the repository/model consumer seam (`ArchitectureRepository` and `NormalizedArchitectureModel`), traceability decorators, and the documented discovery-bundle role. See [public surface and stability](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/public-surface-and-stability.md).
- **Provisional** — ADR authoring v1.1–v1.3, normalized models 1.1 and 2.0, discovery/ledger/lifecycle extensions, implementation-attribution evidence v1.5/v1.6, and the TypeScript consumer binding. v1.6 is preferred for new evidence producers but remains provisional.
- **Experimental** — Vision ADRs, migrators, workspace boot examples; not a basis for long-term external dependencies.

Full breakdown: [public-surface-and-stability.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/public-surface-and-stability.md).

## Documentation

### Public documentation

| Document | Description |
|----------|-------------|
| [authority-boundary.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/authority-boundary.md) | Who owns what across `ste-handbook`, `ste-spec`, this kit, `ste-runtime`, and `ste-kernel` |
| [public-sdk.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/public-sdk.md) | Supported `adr_kit.api` installation and consumer contract |
| [packages/node/README.md](https://github.com/egallmann/adr-architecture-kit/blob/main/packages/node/README.md) | Official TypeScript/Node consumer binding (`@system-of-thought/adr-kit`) |
| [typescript-consumer-binding.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/typescript-consumer-binding.md) | TypeScript consumer binding contract and distribution notes |
| [schema-v1.2.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/schema-v1.2.md) | Additive v1.2 authoring and normalized semantics |
| [schema-v1.3.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/schema-v1.3.md) | UUID identity authoring schema and model 2.0 linkage |
| [schema-v1.5.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/schema-v1.5.md) | Semantic implementation attribution evidence (UUID claims) |
| [schema-v1.6.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/schema-v1.6.md) | Preferred producer evidence, provenance spans, confidence, and lossless conversion |
| [ste-runtime-semantic-linkage-handoff.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/ste-runtime-semantic-linkage-handoff.md) | Downstream extraction contract for ste-runtime |
| [identity-v13-migration.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/identity-v13-migration.md) | Sealed UUID identity migration lifecycle |
| [external-bindings.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/external-bindings.md) | External authority binding without ownership absorption |
| [topology-identity-migration.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/topology-identity-migration.md) | Stable physical topology identity migration |
| [adr-type-model.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/adr-type-model.md) | ADR taxonomy: `ADR-L`, `ADR-PS`, `ADR-PC`, legacy `ADR-P`, experimental `ADR-V` |
| [architecture-ir-overview.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/architecture-ir-overview.md) | Three layers: ADR sources, repository discovery bundle, public Architecture IR |
| [public-surface-and-stability.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/public-surface-and-stability.md) | Stable v1 vs draft vs experimental surfaces |
| [walkthrough-adr-to-ir.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/walkthrough-adr-to-ir.md) | End-to-end flow with [`examples/public-v1/`](https://github.com/egallmann/adr-architecture-kit/tree/main/examples/public-v1/) |

### Contributor guides

| Document | Description |
|----------|-------------|
| [SYSTEM-OVERVIEW.md](https://github.com/egallmann/adr-architecture-kit/blob/main/SYSTEM-OVERVIEW.md) | Generated AI-first repo orientation (authority, workflows, CLI, generators); read before large changes |
| [contributors/tdd-workflow.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/contributors/tdd-workflow.md) | TDD workflow for this codebase |
| [contributors/logical-adr-guide.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/contributors/logical-adr-guide.md) | Writing logical ADRs |
| [contributors/physical-adr-guide.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/contributors/physical-adr-guide.md) | Physical ADR families (`ADR-PS`, `ADR-PC`, legacy `ADR-P`) |
| [contributors/schema-guide.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/contributors/schema-guide.md) | Long-form schema and validation notes |
| [contributors/placement-convention.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/contributors/placement-convention.md) | Placement rules for ADRs, manifest, and index paths |

Also [CONTRIBUTING.md](https://github.com/egallmann/adr-architecture-kit/blob/main/CONTRIBUTING.md) and [schema/v1.0/README.md](https://github.com/egallmann/adr-architecture-kit/blob/main/schema/v1.0/README.md). **Where to start:** ADR authors — [adr-type-model.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/adr-type-model.md), [schema/v1.0/README.md](https://github.com/egallmann/adr-architecture-kit/blob/main/schema/v1.0/README.md), [walkthrough-adr-to-ir.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/walkthrough-adr-to-ir.md). Python or cross-repo IR consumers — [architecture-ir-overview.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/architecture-ir-overview.md), [authority-boundary.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/authority-boundary.md); code entry point [`architecture_repository.py`](https://github.com/egallmann/adr-architecture-kit/blob/main/src/adr_kit/repository/architecture_repository.py). Curated doc index: [docs/README.md](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/README.md).

## Implementation linkage

Python APIs and CLI entry points declare **architecture implementation intent** beside code using no-op decorators in [`src/adr_kit/decorators.py`](https://github.com/egallmann/adr-architecture-kit/blob/main/src/adr_kit/decorators.py):

- `@implements_adr("ADR-L-…", …)` / `@implements_adrs(["ADR-L-…", …])` — legacy alias metadata (`__implements_adrs__`)
- `@enforces_invariant("INV-…", …)` / `@enforces_invariants(["INV-…", …])` — legacy alias metadata (`__enforces_invariants__`)
- `@implements("<uuid>")` / `@enforces("<uuid>")` / `@embodies("<uuid>")` — UUID-canonical claims (`__architecture_attribution_claims__`, `confidence: declared`)

Normative rationale: [ADR-L-0004](https://github.com/egallmann/adr-architecture-kit/blob/main/adrs/logical/ADR-L-0004-adr-to-code-traceability-via-decorators.yaml) and [ADR-L-0020](https://github.com/egallmann/adr-architecture-kit/blob/main/adrs/logical/ADR-L-0020-semantic-implementation-attribution.yaml). These decorators only attach metadata; they do not change control flow. A declaration is evidence of intent, not proof.

**ste-runtime** RECON can parse the decorator calls from the AST and emit derived evidence under the workspace-root `.ste-workspace/` state directory, outside every repository. That output is **declared linkage**, not proof of correctness: canonical architecture remains the ADR corpus and contracts in **`ste-spec`**. Pass a RECON/workspace file to the CLI with **`--evidence`**; `check` / `coverage` do not search `.ste-workspace` automatically. ste-runtime’s independently governed Python extraction substrate is out of scope for this package’s Python floor.

TypeScript linkage shims are generated with `adr attribution generate-shim --language typescript` and consumed through `@system-of-thought/adr-kit` Node linkage entry points; see [`packages/node/README.md`](https://github.com/egallmann/adr-architecture-kit/blob/main/packages/node/README.md).

**CLI (`adr attribution`)** validates and inspects attribution evidence YAML (RECON-derived, synthetic, or project-local) against your repository’s canonical ADRs:

- **`adr attribution check`** — Schema + corpus validation (`--profile greenfield|brownfield|migration`, default **greenfield**). Use `--scope PATH` as the project root (default: current directory) and optional `--evidence PATH` for the YAML file.
- **`adr attribution coverage`** — Prints an informational YAML report of ADRs cited by evidence versus the corpus (same `--scope` / `--evidence`), plus unique-link counts distinct from evidence occurrence.
- **`adr attribution workspace-report`** — Builds a workspace federation index of qualified ADR ids across registered repos.
- **`adr attribution generate-shim --language python|typescript`** — Writes linkage decorator shims (`-o`/ stdout).
- **`adr attribution normalize-evidence --scope PATH --input FILE --target-version 1.5|1.6`** — Selects a lossless canonical target; v1.5 remains the default.
- **`adr attribution linkage-report --scope PATH --evidence FILE`** — Builds the deterministic non-authoritative projection, with optional implementation, intent, and relationship filters.

If `--evidence` is omitted, `check` and `coverage` resolve the first existing **project-local** file under `--scope` (not the workspace-root `.ste-workspace` tree):

1. `{scope}/state/attribution/implementation-attribution-evidence.yaml`
2. `{scope}/.ste/state/attribution/implementation-attribution-evidence.yaml`

Local pre-push (`scripts/run_local_pre_push_checks.py`) looks up workspace-derived RECON evidence at `{workspace}/.ste-workspace/state/adr-architecture-kit/attribution/implementation-attribution-evidence.yaml` and passes that path via `--evidence`.

v1.5 and v1.6 are **semantic implementation-attribution evidence**, not ADR authoring schemas; in particular, v1.5 is not ADR authoring schema 1.5. 1.0/1.2 remain under `schema/evidence-attribution/v1.1/implementation-attribution-evidence.schema.json`. Canonical 1.5 lives under `schema/evidence-attribution/v1.5/`, while preferred-producer 1.6 lives under `schema/evidence-attribution/v1.6/`. v1.5 retains historical semantics; v1.6 adds optional source pointers/spans and declared-only enforcement confidence. `adr_kit.api.build_embodiment_linkage` consumes an explicitly supplied evidence path—even outside the repository—and returns immutable valid links plus rejected claims without writing evidence, Architecture IR, or graph state. Its authority ceiling is validated derived evidence and its graph admission status is not admitted.

## Contributing

Contributions use **Test-Driven Development** (see [`PROJECT.yaml`](https://github.com/egallmann/adr-architecture-kit/blob/main/PROJECT.yaml), `ADR-L-0003`). Setup, quality gates, schema parity, governance, and PR flow are in [CONTRIBUTING.md](https://github.com/egallmann/adr-architecture-kit/blob/main/CONTRIBUTING.md). Authoring and placement guides live under [docs/contributors/](https://github.com/egallmann/adr-architecture-kit/tree/main/docs/contributors/). For authoring-time vs runtime artifact boundaries, see [AUTHORING-SYSTEM.md](https://github.com/egallmann/adr-architecture-kit/blob/main/AUTHORING-SYSTEM.md).
