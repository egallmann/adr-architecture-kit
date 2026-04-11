# ADR type model

## Purpose

This document is the canonical public explanation of ADR types in `adr-architecture-kit`.

## Quick reference

| Prefix | Role | Stability |
|--------|------|-----------|
| **ADR-L** | Conceptual architecture: capabilities, boundaries, contracts, invariants, decisions | Stable public v1 |
| **ADR-PS** | Physical-system: topology, integration patterns, high-level technology posture | Stable public v1 |
| **ADR-PC** | Physical-component: implementation-ready design, interfaces, identifiers | Stable public v1 |
| **ADR-P** | Legacy broad physical ADR | Compatibility; not preferred for new work |
| **ADR-V** | Vision / future-state exploration | Experimental; not part of stable v1 contract |

Standalone **INV-*** invariants are first-class authoring artifacts validated alongside ADRs.

## Stable types

### `ADR-L-*` Logical ADRs

Logical ADRs capture architecture intent without implementation detail.

Typical content:

- capabilities
- boundaries
- interaction contracts
- constraints
- invariants
- conceptual decisions

Logical ADRs define what the system must mean or guarantee.

### `ADR-PS-*` Physical-System ADRs

Physical-system ADRs describe high-level system design.

Typical content:

- major component boxes
- topology
- broad integration structure
- high-level technology posture
- system-level implementation boundaries

This is the preferred high-level physical modeling form for public use.

### `ADR-PC-*` Physical-Component ADRs

Physical-component ADRs describe implementation-ready component design.

Typical content:

- interfaces
- component responsibilities
- operational and compatibility requirements
- testing requirements
- implementation identifiers

This is the preferred detailed physical modeling form for public use.

## Compatibility type

### `ADR-P-*` Legacy Physical ADRs

`ADR-P-*` remains supported for compatibility and historical continuity.

Use it as:

- legacy input
- reference material
- migration bridge

Do not treat it as the preferred forward public modeling form when `ADR-PS-*` and `ADR-PC-*` can express the architecture more clearly.

## Experimental type

### `ADR-V-*` Vision ADRs

Vision ADRs are future-state or exploratory logical artifacts.

They are useful for:

- future-state exploration
- design direction
- architectural intent that is not yet part of the stable canonical model

They are not part of the stable public v1 contract for this repository.

## Relationship between types

```text
ADR-L
    -> defines conceptual architecture intent
ADR-PS
    -> describes high-level physical realization of that intent
ADR-PC
    -> describes implementation-ready component realization
ADR-P
    -> legacy broad physical form retained for compatibility
ADR-V
    -> experimental future-state material
```

A typical refinement chain is: **logical intent (L)** → **system shape (PS)** → **component specification (PC)**. Exact linking fields live in the schemas; see [schema/v1.0/README.md](../schema/v1.0/README.md).

## Source to output relationship

- ADR source artifacts define canonical authoring intent
- compiler and generators normalize that intent into repository discovery outputs
- selected ADR inputs can also be adapted into public Architecture IR records governed by `ste-spec`

## Related

- [architecture-ir-overview.md](architecture-ir-overview.md)
- [walkthrough-adr-to-ir.md](walkthrough-adr-to-ir.md)
- [public-surface-and-stability.md](public-surface-and-stability.md)
