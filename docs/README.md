# Documentation (`docs/`)

Public, OSS-oriented documentation for **ADR Architecture Kit**. These pages are written for external engineers discovering the repository and for integrators who need a clear authority and stability story.

Contributor-oriented guides (TDD, authoring, placement) live under [`contributors/`](contributors/) so they stay separate from the short public spine below.

## Index (public)

| Document | Description |
|----------|-------------|
| [authority-boundary.md](authority-boundary.md) | Who owns what across `ste-handbook`, `ste-spec`, this kit, `ste-runtime`, and `ste-kernel` |
| [adr-type-model.md](adr-type-model.md) | ADR taxonomy: `ADR-L`, `ADR-PS`, `ADR-PC`, legacy `ADR-P`, experimental `ADR-V` |
| [architecture-ir-overview.md](architecture-ir-overview.md) | Three layers: ADR sources, repository discovery bundle, public Architecture IR |
| [public-surface-and-stability.md](public-surface-and-stability.md) | Stable v1 vs draft vs experimental surfaces |
| [walkthrough-adr-to-ir.md](walkthrough-adr-to-ir.md) | End-to-end flow with the [`examples/public-v1/`](../examples/public-v1/) example |

## Contributor reference

| Document | Description |
|----------|-------------|
| [contributors/tdd-workflow.md](contributors/tdd-workflow.md) | Test-driven development workflow for this codebase |
| [contributors/logical-adr-guide.md](contributors/logical-adr-guide.md) | Writing logical ADRs |
| [contributors/physical-adr-guide.md](contributors/physical-adr-guide.md) | Physical ADR families (`ADR-PS`, `ADR-PC`, legacy `ADR-P`) |
| [contributors/schema-guide.md](contributors/schema-guide.md) | Long-form schema and validation notes |
| [contributors/placement-convention.md](contributors/placement-convention.md) | Placement rules for ADRs, manifest, and index paths |

Also see [CONTRIBUTING.md](../CONTRIBUTING.md) and [schema/v1.0/README.md](../schema/v1.0/README.md).

## Documentation history (disposition)

Earlier drafts lived in a flat `docs/` tree and a temporary `_docs/` reference folder. The **public** set above replaces that for external readers. The disposition table below records what happened to common legacy filenames (no links to removed paths).

### Carried into public `docs/` (synthesized)

| Legacy source (informal) | Current location |
|--------------------------|-------------------|
| `authority-boundary.md` | [authority-boundary.md](authority-boundary.md) |
| `adr-type-model.md` | [adr-type-model.md](adr-type-model.md) |
| `architecture-ir-overview.md` | [architecture-ir-overview.md](architecture-ir-overview.md) |
| `public-surface-and-stability.md` | [public-surface-and-stability.md](public-surface-and-stability.md) |
| `walkthrough-adr-to-ir.md` | [walkthrough-adr-to-ir.md](walkthrough-adr-to-ir.md) |
| `three-level-architecture.md` | Folded into [walkthrough-adr-to-ir.md](walkthrough-adr-to-ir.md); cross-linked from [adr-type-model.md](adr-type-model.md) |
| `graph-integration.md` | Downstream section in [walkthrough-adr-to-ir.md](walkthrough-adr-to-ir.md) |

### Contributor or specialist material

| Legacy source (informal) | Current / notes |
|--------------------------|-----------------|
| `tdd-workflow.md` | [contributors/tdd-workflow.md](contributors/tdd-workflow.md) when present |
| `logical-adr-guide.md` | [contributors/logical-adr-guide.md](contributors/logical-adr-guide.md) when present |
| `physical-adr-guide.md` | [contributors/physical-adr-guide.md](contributors/physical-adr-guide.md) (also in contributor reference above) |
| `schema-guide.md` | [contributors/schema-guide.md](contributors/schema-guide.md); normative schema overview remains [schema/v1.0/README.md](../schema/v1.0/README.md) |

| `placement-convention.md` | [contributors/placement-convention.md](contributors/placement-convention.md) when present |
| `multi-scope-guide.md`, `v1.1-integration-guide.md` | Optional under `contributors/`; stability story in [public-surface-and-stability.md](public-surface-and-stability.md) |
| Internal design write-ups (traceability, projection, methodology) | Optional under `contributors/` or drop if obsolete |

For STE-wide narrative and theory, use **`ste-handbook`**; for normative contracts, use **`ste-spec`**.
