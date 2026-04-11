# Walkthrough: ADR to IR

## Goal

This walkthrough shows the end-to-end **public** story for `adr-architecture-kit`:

1. Author ADR source artifacts (canonical YAML under `adrs/`).
2. Normalize them into the **repository-normalized discovery bundle** (indexes and manifest).
3. Optionally emit **ADR-derived Architecture IR fragments** that conform to the contract owned by `ste-spec`.

A minimal worked example lives under [`examples/public-v1/`](../examples/public-v1/).

## Three authoring levels (conceptual)

ADR Kit models architecture at three levels (see [adr-type-model.md](adr-type-model.md) for the full taxonomy):

| Level | Prefix | Question it answers |
|-------|--------|---------------------|
| Logical | `ADR-L-*` | **What** must be true — capabilities, boundaries, contracts, invariants |
| Physical system | `ADR-PS-*` | **How** at system scale — topology, integration patterns, major components |
| Physical component | `ADR-PC-*` | **How** at execution scale — interfaces, responsibilities, implementation identifiers |

Typical refinement flow:

```text
ADR-L (intent)
    -> ADR-PS (system realization)
        -> ADR-PC (implementation-ready components)
```

Relationships between artifacts are expressed in ADR frontmatter and compiled into registries; the example set includes one file of each kind.

## Example inputs

The [`examples/public-v1/`](../examples/public-v1/) tree includes:

- one logical ADR: `ADR-L-0001`
- one physical-system ADR: `ADR-PS-0001`
- one physical-component ADR: `ADR-PC-0001`

Those YAML files are the **canonical source** artifacts for the example. Everything under `examples/public-v1/output/` is **derived**.

## Step 1: ADR source meaning

### Logical ADR (`ADR-L-*`)

Defines conceptual architecture intent: capabilities, boundaries, interaction contracts, constraints, invariants, and decisions — without locking implementation technology.

### Physical-system ADR (`ADR-PS-*`)

Defines the high-level system shape that realizes logical intent: major components, topology, integration posture, and system-level boundaries.

### Physical-component ADR (`ADR-PC-*`)

Defines implementation-ready component design: interfaces, operational requirements, testing expectations, and **implementation identifiers** (where the component lives in code and deployment).

## Step 2: Normalize into repository discovery outputs

The compiler / generator pipeline turns ADR authority into a **deterministic, repository-local** bundle for discovery and tooling.

Core outputs include:

- `architecture-index.yaml` — bootstrap pointer into the bundle
- `entity-registry.yaml` — normalized entity records
- `relationship-registry.yaml` — explicit edges
- `unresolved-registry.yaml` — gaps and deferred items as first-class signals
- `manifest.yaml` — summary index (derived; not semantic authority on its own)

In the public example, compiled outputs appear under:

- [`examples/public-v1/output/index/`](../examples/public-v1/output/index/)
- [`examples/public-v1/output/manifest.yaml`](../examples/public-v1/output/manifest.yaml)

**Important:** this bundle is the repository-owned **discovery surface**. It is **not** the normative cross-repo Architecture IR contract (that remains `ste-spec`).

### Example commands (typical repo)

```bash
adr generate-architecture-index
adr generate-manifest
```

Use `--scope <path>` when working in a subdirectory; use `--recursive` to refresh multiple scopes (see project CLI help).

## Step 3: Emit Architecture IR fragments

Selected logical ADR inputs can be adapted into JSON records shaped for the **public Architecture IR** schema.

In the example, output is at:

- [`examples/public-v1/output/architecture-ir/adr-ir-fragments.json`](../examples/public-v1/output/architecture-ir/adr-ir-fragments.json)

That file is an **adapter output**: it must validate against the schema mirrored at [`contracts/architecture-ir/architecture-ir.schema.json`](../contracts/architecture-ir/architecture-ir.schema.json), whose normative home is **`ste-spec`**.

### Example commands

```bash
# Parameterized / generic path (see `adr compile-ir-fragments --help`)
adr compile-ir-fragments

# Conventional in-repo self-publication example (this repository)
adr build-ir-fragments
```

`build-ir-fragments` is explicitly a **repository self-publication** example; prefer `compile-ir-fragments` for parameterized use.

## Downstream consumption (runtime and kernel)

### Graph and runtime (`ste-runtime`)

`ste-runtime` owns **runtime observation**, evidence extraction, and graph composition. It should **consume** upstream architecture surfaces (discovery bundle and/or public IR) — not redefine ADR encoding or the normative IR schema.

**Practical posture for integrators:**

- Prefer the repository-normalized bundle (`adrs/index/*`, `adrs/manifest.yaml`) for **repository-local** discovery and semantic loading.
- Use **`ste-spec`** for the normative **Architecture IR** schema and cross-repo semantics.
- Do not treat downstream graph projections as a new source of architecture authority.

### Kernel (`ste-kernel`)

`ste-kernel` owns **admission and governance** over compiled inputs. It does not own the Architecture IR schema.

## End-to-end mapping

```text
ADR source artifacts (adrs/**/*.yaml, invariants)
    -> parse / validate (schema/v1.0)
    -> repository-normalized discovery outputs (adrs/index/*, manifest)
    -> Python consumer boundary (ArchitectureRepository, NormalizedArchitectureModel)
    -> optional: ADR-derived Architecture IR fragments (JSON)
    -> normative contract: ste-spec Architecture IR schema
```

## Related

- [architecture-ir-overview.md](architecture-ir-overview.md) — layers vs `ArchModel` vs public seam
- [adr-type-model.md](adr-type-model.md) — ADR-L / PS / PC / P / V
- [authority-boundary.md](authority-boundary.md) — STE stack ownership
- [public-surface-and-stability.md](public-surface-and-stability.md) — what to depend on externally
