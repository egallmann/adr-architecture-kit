# Documentation

Use this page to choose a task. The root [README](https://github.com/egallmann/adr-architecture-kit#readme)
is the distribution-neutral product introduction; these pages add recipes,
contract precision, migration guidance, and contributor controls.

## I want to use ADR-Kit

- [Python SDK](public-sdk.md) — install, validate a repository, discover supported authoring contracts, inspect a normalized repository, and use semantic contracts.
- [Node package README](../packages/node/README.md) — install the peer TypeScript/Node binding, validate a repository, discover capabilities, and understand browser-safe entry points.
- [TypeScript consumer binding](typescript-consumer-binding.md) — host qualification, entry-point rules, and distribution behavior.
- [Authority boundary](authority-boundary.md) — concise ownership map across ADR-Kit and the surrounding STE repositories.

## I want to author architecture

- [ADR type model](adr-type-model.md) — the small conceptual taxonomy for logical, physical-system, and physical-component records.
- [Schema taxonomy](../schema/README.md) — stable v1.0 compatibility, family-scoped authoring contracts, discovery, normalized models, and evidence attribution.
- [Authoring schemas](../schema/authoring/README.md) — the exact family-scoped authoring line and its relationship to ADC discovery.
- [Walkthrough](walkthrough-adr-to-ir.md) — a deeper source-to-discovery-to-IR explanation using the retained v1.0 compatibility example.

Authoring discovery is available through the Python and browser-safe TypeScript
public APIs. It describes contracts and types; it does not construct or mutate
architecture.

## I need exact semantic or contract reference

- [Public surface and stability](public-surface-and-stability.md) — compatibility categories and the supported public boundaries.
- [Architecture IR overview](architecture-ir-overview.md) — repository discovery versus the cross-repository IR contract.
- [Schema v1.6](schema-v1.6.md) — evidence-attribution details for the current preferred producer line.
- [Semantic linkage handoff](ste-runtime-semantic-linkage-handoff.md) — downstream evidence-consumption details.
- [Promotion provider](promotion-provider.md) — the specialist Design Journal promotion contract.
- [Production hardening](production-hardening/public-surface-inventory.md) — frozen compatibility evidence for maintainers.

Use `capabilities()` in the installed host to discover current versions and
operations. The compatibility contracts and checked-in schema families remain
the precise reference when an integration needs exact bytes or shapes.

## I am upgrading or migrating

- [Identity v1.3 migration](identity-v13-migration.md)
- [Topology identity migration](topology-identity-migration.md)
- [External bindings](external-bindings.md)
- [Public stability policy](public-surface-and-stability.md)

## I am contributing to ADR-Kit

- [CONTRIBUTING.md](../CONTRIBUTING.md) — setup, TDD, quality gates, schema parity, governance, and PR flow.
- [Contributor guides](contributors/README.md) — authoring, placement, schema, release, and TDD specialist guidance.
- [SYSTEM-OVERVIEW.md](../SYSTEM-OVERVIEW.md) — generated AI-first orientation for modifying this repository; do not hand-edit it.
- [SECURITY.md](../SECURITY.md) — vulnerability reporting and release-trust controls.

The `docs/design-journal/` material records historical or local design context;
it is not a first-use documentation path or a replacement for accepted ADRs,
contracts, or generated contributor orientation.
