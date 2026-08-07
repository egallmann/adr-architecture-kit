# Authority boundary

This document defines how **ADR Architecture Kit** (`adr-architecture-kit`) fits into the broader System of Thought Engineering (STE) platform: which repository owns which concerns, and how to resolve conflicts.

## STE layer boundaries

### `ste-handbook`

Owns explanatory model, theory, and teaching material.

### `ste-spec`

Owns normative contracts, schemas, and the public cross-repo Architecture IR contract.

### `adr-architecture-kit`

Owns the canonical ADR encoding model, authoring validation, authoring-time normalization,
repository projections, the narrow `adr_kit.api` authoring SDK, the Python repository
boundary, and adapter/compiler logic that turns ADR authority into IR-compatible outputs.

### `ste-runtime`

Owns runtime observation, evidence extraction, and composition. Its derived state
is written beneath the workspace-root `.ste-workspace/` directory, outside every
repository. It may read supported ADR Kit contracts but must never write into the
ADR Kit repository. It does not own architecture doctrine.

### `ste-kernel`

Owns admission and governance decisions over compiled inputs.

## Practical meaning

- If the question is about **normative cross-repo contract shape**, `ste-spec` wins.
- If the question is about **ADR encoding**, **authoring validation**, or **repository discovery outputs**, `adr-architecture-kit` wins.
- If the question is about **observed runtime evidence**, `ste-runtime` wins.
- If the question is about **governance or admission**, `ste-kernel` wins.

## Repository write boundary

Each repository is the sole writer of its own canonical and repository-local
derived artifacts. In particular, only ADR Kit tooling may create or modify files
inside `adr-architecture-kit`.

Workspace and runtime projections are not repository artifacts. They belong under:

```text
<workspace-root>/.ste-workspace/
```

External tools may consume repository contracts read-only. A runtime or workspace
command that resolves an output path inside a repository violates this boundary;
its output must not be accepted, committed, or used to refresh compatibility
baselines.

The SDK compilation groups (`registries`, `manifest`, and `markdown`) remain ADR Kit
authoring projections. They do not authorize runtime graph or evidence emission into
this repository.

## Why this boundary exists

Without an explicit authority split, the same architecture meaning would be redefined in multiple places:

- doctrine in one repo
- schemas in another
- runtime interpretation in a third
- governance semantics in a fourth

STE keeps those responsibilities separate so external consumers can tell which surface is explanatory, normative, authoring-focused, observational, or decisioning-focused.

## Architecture IR boundary

For Architecture IR specifically:

- `ste-spec` owns the normative public schema
- `adr-architecture-kit` emits ADR-derived records that conform to that schema
- `adr-architecture-kit` also owns **repository-normalized discovery outputs**, which are **not** the same thing as the public IR

## Related

- [architecture-ir-overview.md](architecture-ir-overview.md) — three data layers (source, discovery bundle, public IR)
- [public-surface-and-stability.md](public-surface-and-stability.md) — what is stable vs draft vs experimental
