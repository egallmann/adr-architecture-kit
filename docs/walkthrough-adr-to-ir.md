# Walkthrough: ADR To IR

## Goal

This walkthrough shows the end-to-end public story for `adr-architecture-kit`:

1. author ADR source artifacts
2. normalize them into the repository discovery bundle
3. emit ADR-derived Architecture IR fragments

The example assets live under [`examples/public-v1/`](../examples/public-v1/).

## Example Inputs

The example source set contains:

- one logical ADR: `ADR-L-0001`
- one physical-system ADR: `ADR-PS-0001`
- one physical-component ADR: `ADR-PC-0001`

Those files are the canonical source artifacts for the example.

## Step 1: ADR Source Meaning

### Logical ADR

The logical ADR defines conceptual architecture intent:

- one capability
- one invariant
- one decision

### Physical-System ADR

The physical-system ADR defines the high-level system shape that realizes the logical intent.

### Physical-Component ADR

The physical-component ADR defines the implementation-ready component responsible for the concrete realization.

## Step 2: Normalize Into Repository Discovery Outputs

The repository compiler/generator flow turns ADR authority into a deterministic repository-facing bundle.

Core outputs:

- `architecture-index.yaml`
- `entity-registry.yaml`
- `relationship-registry.yaml`
- `unresolved-registry.yaml`
- `manifest.yaml`

In the example, these live under:

- `examples/public-v1/output/index/`
- `examples/public-v1/output/manifest.yaml`

This layer is meant for repository discovery and semantic loading. It is not the public cross-repo Architecture IR contract.

## Step 3: Emit Architecture IR Fragments

Selected ADR inputs can also be adapted into public Architecture IR records.

In the example, the fragment output lives at:

- `examples/public-v1/output/architecture-ir/adr-ir-fragments.json`

That file is an ADR-derived IR adapter output. It is shaped to conform to the public Architecture IR contract owned by `ste-spec`.

## What Runtime And Kernel Consume

### Runtime

`ste-runtime` consumes architecture information as part of runtime observation and evidence composition. It does not become the normative owner of ADR encoding or public IR contracts.

### Kernel

`ste-kernel` consumes compiled inputs and applies governance/admission logic. It does not redefine the Architecture IR schema.

## Example Commands

Repository discovery outputs:

```bash
adr generate-architecture-index
adr generate-manifest
```

IR fragment publication example:

```bash
adr build-ir-fragments
```

## Mapping Summary

```text
ADR source artifacts
    -> repository-normalized discovery outputs
    -> Python consumer boundary
    -> ADR-derived Architecture IR fragments
    -> ste-spec Architecture IR contract
```

## Related

- [architecture-ir-overview.md](architecture-ir-overview.md)
- [adr-type-model.md](adr-type-model.md)
