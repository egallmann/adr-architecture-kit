# Authority Boundary

## STE Layer Boundaries

### `ste-handbook`

Owns explanatory model, theory, and teaching material.

### `ste-spec`

Owns normative contracts, schemas, and the public cross-repo Architecture IR contract.

### `adr-architecture-kit`

Owns the canonical ADR encoding model, authoring validation, authoring-time normalization, projections, Python repository boundary, and adapter/compiler logic that turns ADR authority into IR-compatible outputs.

### `ste-runtime`

Owns runtime observation, evidence extraction, and composition. It does not own architecture doctrine.

### `ste-kernel`

Owns admission and governance decisions over compiled inputs.

## Practical Meaning

- If the question is about normative cross-repo contract shape, `ste-spec` wins.
- If the question is about ADR encoding, authoring validation, or repository discovery outputs, `adr-architecture-kit` wins.
- If the question is about observed runtime evidence, `ste-runtime` wins.
- If the question is about governance or admission, `ste-kernel` wins.

## Why This Boundary Exists

Without an explicit authority split, the same architecture meaning would be redefined in multiple places:

- doctrine in one repo
- schemas in another
- runtime interpretation in a third
- governance semantics in a fourth

STE keeps those responsibilities separate so external consumers can tell which surface is explanatory, normative, authoring-focused, observational, or decisioning-focused.

## Architecture IR Boundary

For Architecture IR specifically:

- `ste-spec` owns the normative public schema
- `adr-architecture-kit` emits ADR-derived records that conform to that schema
- `adr-architecture-kit` also owns repository-normalized discovery outputs, which are not the same thing as the public IR

## Related

- [architecture-ir-overview.md](architecture-ir-overview.md)
- [public-surface-and-stability.md](public-surface-and-stability.md)
