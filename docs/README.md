# Documentation

The root [README](https://github.com/egallmann/adr-architecture-kit#readme) is
the distribution-neutral product introduction. This directory contains current
task guidance, specialist policy, and contributor controls.

## Use ADR-Kit

- [Python SDK](public-sdk.md) — validate repositories, discover capabilities,
  inspect normalized models, and use semantic contracts.
- [Node package README](../packages/node/README.md) — use the peer
  TypeScript/Node binding and its browser-safe entry points.
- [Authority boundary](authority-boundary.md) — ownership across ADR-Kit and
  the surrounding STE repositories.
- [Public surface and stability](public-surface-and-stability.md) — current
  compatibility categories and consumption rules.

## Author architecture

- [ADR type model](adr-type-model.md) — logical, physical-system, and
  physical-component roles.
- [Schema taxonomy](../schema/README.md) — canonical schema families and
  their authority boundaries.
- [Authoring contracts](../schema/authoring/README.md) — family-scoped
  authoring resources and their relationship to ADC discovery.

Exact structure belongs in the canonical schemas, contracts, compatibility
files, and capability discovery. ADC discovery describes supported contracts;
it does not construct or mutate architecture.

## Contribute and release

- [Contributor guides](contributors/README.md) — authoring, placement, and
  release controls.
- [Promotion provider](promotion-provider.md) — the supported local promotion
  and prepared-handoff boundary.
- [CONTRIBUTING.md](../CONTRIBUTING.md) — setup, validation, governance, and
  pull-request policy.
- [SYSTEM-OVERVIEW.md](../SYSTEM-OVERVIEW.md) — generated repository
  orientation; do not hand-edit it.
- [SECURITY.md](../SECURITY.md) — vulnerability reporting and release trust.

Design Journals, prepared Promotion Contracts, and review handoffs are local
ignored convergence state. They are not a first-use path or a replacement for
accepted ADRs, governed contracts, schemas, capabilities, or generated views.
