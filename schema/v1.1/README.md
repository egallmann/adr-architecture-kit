# ADR Kit Schema v1.1

`schema/v1.1/` is a draft schema line.

It contains public-in-repo extensions that are useful for review and experimentation, but it is not part of the stable public v1 contract for `adr-architecture-kit`.

## Current status

- Stability: draft
- Intended use: evaluation, iteration, and staged adoption
- Compatibility promise: not yet locked as a stable external contract

## What lives here

Examples include:

- normalized entity registry extensions
- relationship and unresolved registry schemas
- remediation and governance-adjacent schemas
- lifecycle, ledger, and attribution-related extensions

## Authority note

Even when these schemas are useful, they do not replace the public Architecture IR contract owned by `ste-spec`.

## Practical guidance

- Review these schemas as draft design material
- Avoid taking hard external dependencies on them as if they were stable
- Use `schema/v1.0/` when you need the stable public ADR encoding surface

## Related

- [../../docs/public-surface-and-stability.md](../../docs/public-surface-and-stability.md)
- [../../docs/architecture-ir-overview.md](../../docs/architecture-ir-overview.md)
