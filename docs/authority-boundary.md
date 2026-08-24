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

ADR-Kit also owns the language-neutral Consumer Binding Contract 1.0. The official
TypeScript package is a read-only binding over this authority; it does not own ADR
semantics, canonical identity, graph admission, or repository writes.

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

Browser consumers use only browser-safe ESM entry points. Node filesystem access and
embodiment linkage are explicit Node binding capabilities, not browser authority.

ADR Kit is also the sole repair authority for collisions among repository-local
canonical entity IDs. It detects collisions, preserves one deterministic keeper,
allocates replacements above the historical prefix high-water mark, never reuses
retired or remapped IDs, rewrites resolvable typed references, validates, and
regenerates its projections. Runtime does not repair local identity. A runtime
consumer may only assemble the repository namespace and local ID as structured
`namespace:id` identity.

V1.2 bindings preserve the same boundary: ADR Kit owns the authored binding record,
while the provider namespace owns the referenced substrate, rule, or entity. An
evidence expectation remains authored intent; observed evidence remains runtime-owned
state under `.ste-workspace/`.

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
