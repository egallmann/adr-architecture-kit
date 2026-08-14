# Changelog

All notable changes to ADR Architecture Kit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Semantic implementation attribution evidence line (schema v1.5): UUID-canonical
  claims, mechanical vocabulary, repository-aware 1.0/1.2 normalization, UUID
  decorators, vocabulary-driven shims, and unique-link coverage fields
  (`ADR-L-0020`, `ADR-PC-0007`).

### Changed

- Align README stability language and documentation index with the current
  public-surface contract (Stable / Provisional / Experimental), including
  schema v1.3, identity migration, and `adr attribution workspace-report`.
- Expand SECURITY.md scope to generated writes, CLI path handling, and
  release-trust surfaces while keeping enabled-tooling and human-admission
  policy from 0.4.1.
- `ArchitectureRepository.next_id` sequences v1.3 `alias_id` while preserving
  legacy patterned `id` allocation.
- Deduplicate README attribution-evidence docs; distinguish project-local CLI
  default lookup from workspace-root `.ste-workspace` RECON evidence.
- Include v1.5 semantic-attribution invariant tests in the local pre-push subset.
- Move production-hardening phase logs out of the public docs index; durable
  release controls are pointed from contributor docs.

## [0.4.1] — 2026-08-12

### Changed

- Qualify a source commit once across orthogonal CI evidence axes (canonical
  Ubuntu 3.12 coverage suite, Ubuntu Python source/SDK compatibility,
  Windows/macOS behavior portability, and exact retained-wheel Python + OS
  cells); tag publication promotes that retained `release-bundle` fail-closed
  without rebuild or requalification (`ADR-L-0003`)
- Document release-eligible evidence as successful `main` push only; PR and
  `develop` qualification runs are not publication admission
- Strengthen public-repo security posture: Dependabot alerts, secret scanning
  with push protection, private vulnerability reporting, CodeQL workflow, and
  a human-admitted finding triage policy in `SECURITY.md`

### Fixed

- Normalize macOS `/private`-prefixed fixture paths in CLI compatibility
  snapshots so OS-portability suites match Linux goldens
- Keep the system-overview promote prepare/check/apply entry intact in the
  markdown task table (avoid raw `|` alternatives that split table columns)

## [0.4.0] — 2026-08-11

### Added

- Provisional ADR schema v1.3 canonical UUIDv7 entity identity
- `alias_id` / `alias_name` human recognition model
- v1.3 migration planning, sealing, apply, recovery/check semantics
- Normalized architecture model 2.0
- `ProviderRegistry` / `open_provider_registry`
- Design Journal Promotion Contract provider
- `prepare_promotion` / `check_promotion` / `apply_promotion`
- Promotion contract DTOs and evidence descriptors
- Human ADR projection with typed layout, relationship graph, and peer
  context/navigation
- Provider/profile-driven system overview model where appropriate

### Changed

- ADR Kit dogfood corpus migrated uniformly to v1.3
- Local relationships now normalize to canonical UUID identity
- Normalized model 2.0 emitted for all-v1.3 scopes
- Mixed legacy/v1.3 scope handling is fail-closed
- Generated human ADR documentation moved from `adrs/rendered/` to
  `adrs/adr-projection/{type}/{alias_id}-{slug}.md`
- Human projection exposes compiler-derived relationship semantics rather
  than reconstructing an independent graph
- System overview derives through explicit projection sources / provider
  profile surfaces
- Public SDK inventory expanded additively while API contract remains `1.0`

### Fixed

- Bundle the Design Journal Promotion Contract schema into the installed
  package so non-editable wheel/site-packages installs can validate
  promotion contracts without a repository checkout

### Compatibility / Migration

- ADR schema v1.0 remains frozen/readable
- ADR schema v1.2 remains readable and migratable
- ADR schema v1.3 is provisional
- Normalized model 2.0 is provisional
- API contract remains `1.0`
- `generate-rendered-docs` remains a compatibility alias for
  `generate-adr-projection`
- Markdown SDK artifact group remains `markdown`
- Logical markdown artifact IDs remain stable independent of slug/path
- Human projection relative paths intentionally changed; see
  `docs/adr-projection-path-migration.md`

## [0.3.1] — 2026-08-08

### Fixed

- Made the package README PyPI-portable by replacing repository-relative Markdown
  links with absolute GitHub `main` blob/tree URLs (observed on published `0.3.0`:
  relative targets such as `docs/public-sdk.md` resolved under the PyPI project page
  and 404'd). Added deterministic README portability validation (`INV-0083`) wired
  into local pre-push checks and covered by release quality pytest.

## [0.3.0] — 2026-08-07

Cumulative public delta since `0.1.0`: Phase 0 production hardening, Phase 1 public SDK,
and Phase 2 schema v1.2 / normalized semantic foundation. Unpublished intermediate
`0.2.0` was intentionally skipped; this release ships the admitted Phase 2 capability
tier as `0.3.0`.

### Changed

- Added the narrow supported `adr_kit.api` facade (API contract `1.0`) for capability
  discovery, validation, preview/write authoring compilation, and eager repository
  opening without exposing compiler internals.
- Delegated `adr validate` and `adr compile` through shared private application
  services while preserving the frozen CLI surface, output, exit codes, warnings, and
  generated bytes across a 16-case behavior snapshot.
- Made installed distribution metadata the runtime package-version authority, with a
  validated direct-source `pyproject.toml` fallback and `0+unknown` sentinel.
- Extended source, editable, retained-wheel, quality-ratchet, and benchmark controls
  to exercise the public SDK on Python 3.11–3.14.
- Reaffirmed that only ADR Kit writes inside this repository; all runtime/workspace
  derived state belongs under the workspace-root `.ste-workspace/`.
- Phase 0 production hardening now installs through the canonical `adr_kit`
  namespace, snapshots Python/CLI compatibility, enforces version and quality
  ratchets, supports Python 3.11–3.14, tests the retained wheel, and promotes a
  manifested wheel/sdist bundle without rebuilding in the PyPI job.
- Reframed as STE authoring subsystem. Package description, README, `__init__.py`,
  and ADR-L-0001 now consistently present ADR Kit as the authoring-time layer for
  canonical ADR encoding and validation, subordinate to ste-spec, ste-runtime, and
  ste-kernel.
- Moved `click` to default runtime dependencies. The `adr` CLI entrypoint is always
  registered; a default install now satisfies it without requiring `[cli]` extras.
- Added package-data declarations for bundled schemas and templates. Installing from
  a wheel now correctly locates `schema/v1.0/` and `schema/v1.1/` JSON Schemas and
  Jinja2 templates via `importlib.resources`.
- Fixed `yaml_parser.py` schema path resolution. Replaced the four-level
  `Path(__file__).parent...` chain (which broke in installed wheels) with
  `importlib.resources.files("adr_kit.schema.v1.0")`.
- Renamed `validate_kernel_contract_bundle` → `validate_adr_contract_bundle` in
  `contract_validation.py`. The old name implied kernel contract authority; a
  backward-compat alias is retained for the pre-1.0 transition period.
- Renamed `kernel_contract.py` → `repository_schema_generator.py`. The old module
  is retained as a compatibility shim.
- Renamed `scripts/generate_kernel_contract_schemas.py` →
  `scripts/generate_repository_schemas.py`. The old script delegates to the new one.
- Added `schema/kernel/README.md` documenting the kernel-compatibility scope and
  authority boundary of the generated schemas in that directory.
- Added `contracts/architecture-ir/MIRROR.md` documenting the provenance and sync
  rules for the mirrored ste-spec Architecture IR schema.
- Added `src/adr_kit/schema/v1.0/PROVENANCE.md` and `v1.1/PROVENANCE.md` marking
  the package-bundled schema copies as derived from the repo-root canonical source.
- Improved `pyproject.toml` metadata: classifiers, project URLs, keywords,
  maintainer field, `build` added to dev extras.
- Demoted `adr build-ir-fragments` to a clearly-labelled repository self-publication
  example; help text now directs generic consumers to `compile-ir-fragments`.
- Refreshed README: added standard `pip install` quickstart, updated contributor
  install instructions to use `pip install -e .[dev]`.
- Fixed `PROJECT.yaml` `package_name` field to match published package name
  (`adr-architecture-kit`, not `adr-kit`); added `import_name: adr_kit` field.
- README: **Authoring boundary and AI orientation** (generation gap, role of
  generated `SYSTEM-OVERVIEW.md`, AI-assisted drafting vs kit validation);
  **Stability** pre-1.0 Alpha note for PyPI; contributor table links for
  `SYSTEM-OVERVIEW.md`, physical ADR guide, and schema guide.
- `pyproject.toml` `description` sharpened for PyPI listing (structured ADR in,
  discovery / IR out; Alpha).
- PR template checklist: **CI vs local** note linking to CONTRIBUTING.

### Added

- Provisional additive ADR authoring schema v1.2, explicit parser negotiation, and
  byte-identical installed-package schema resources while preserving frozen v1.0.
- Normalized model 1.1 promotion for `boundary`, `contract`, `interface`, and
  `implementation_decision`, including repository query methods and deterministic
  projection.
- Source-sensitive `assertion_id` on relationship records while preserving historical
  endpoint-based `relationship_id` compatibility.
- Bind-only substrate, rule, and evidence-expectation contracts with explicit
  cross-repository qualification and no external authority or runtime evidence
  ingestion.
- Dry-run-first `adr migrate-topology-ids` with first-free stable IDs, unique name
  rewrites, candidate validation, atomic writes, and fail-closed ambiguity handling.
- ADR Kit-owned monotonic canonical-ID collision repair, permanent non-reuse ledgers,
  CI/pre-push allocation validation, and runtime read-only `namespace:id` assembly.
- Installed-wheel and benchmark proof for Phase 2 schemas, semantic projection,
  bindings, assertion identity, and topology migration.
- Logical invariants: optional `supersedes` list on invariant entities; compiler
  derives invariant-to-invariant `supersedes` / `superseded_by` relationships and
  includes `supersedes` in extracted invariant metadata. JSON Schema for logical
  ADRs updated accordingly.
- `SystemOverviewGenerator` resolves project metadata from the current working
  directory and `PROJECT.yaml`, with configurable system purpose and optional
  workspace highlights in the Jinja2 template.
- CI job for retained release-artifact validation: builds wheel and sdist, installs
  into a clean environment, and runs smoke tests to prove wheel install without
  editable-install workarounds.
- CI step for schema parity check: validates that `src/adr_kit/schema/v*/` copies
  match the repo-root `schema/v*/` canonical files byte-for-byte.
- Advisory CI step for Architecture IR mirror check against sibling `ste-spec`
  checkout (skips gracefully when sibling is absent).
- GitHub Actions workflow `publish-pypi.yml`: publish to PyPI on push of a `v*` tag
  matching the package version, using **Trusted Publishing** (OIDC; no PyPI token in
  secrets). Does not publish on branch push or manual dispatch.
- Maintainer instructions in `CONTRIBUTING.md` for linking PyPI to this repository.
- `pyproject.toml` `[tool.setuptools] license-files` so `LICENSE` is included in
  the source distribution.
- `adr attribution check`, **`coverage`**, and **`generate-shim`** CLI commands for validating
  RECON-derived `implementation-attribution-evidence.yaml`, reporting citation coverage,
  and emitting Python/TypeScript linkage shims.
- **`implementation-attribution-evidence`** schema **`1.2`** extensions (`confidence`,
  `attributed_capabilities`, `attribution_source_language`) aligned with **ste-runtime** emission.
- Normalized **entity registry**: `lifecycle_stage` on each `NormalizedEntity`, derived from ADR status
  and persisted in emitted `entity-registry.yaml`; refreshed **kernel** JSON Schema in `schema/kernel/`.
- Canonical **`schema/v1.1/implementation-attribution-evidence.schema.json`** synced with the bundled
  package copy so CI schema parity (`schema/` vs `src/adr_kit/schema/`) passes.
- **`tests/test_package_schema_parity.py`**: asserts canonical vs bundled authoring schemas stay byte-identical (mirrors `.github/workflows/adr-governance.yml`); included in **`scripts/run_local_pre_push_checks.py`**.
- Explicitly recorded bundled **`normalized-entity-registry.schema.json`** at **`src/adr_kit/schema/v1_1/`** matching **`schema/v1.1/`** for clean-checkout CI parity (`assume-unchanged` in local workspaces can suppress staging otherwise — see **`CONTRIBUTING.md`**).

## [0.1.0]

### Added

**Schema v1.0:**
- JSON Schema definitions for logical ADRs, physical ADRs, invariants, PROJECT.yaml, and manifest
- Type-prefixed IDs (ADR-L-XXXX, ADR-P-XXXX) to prevent collision
- Rich frontmatter as authoritative metadata
- Explicit relationship fields for graph extraction
- Policy integration fields (policy_reference, enforcement_level, compliance_frameworks)
- Implementation identifiers for EDR matching and correction agents

**Python Package:**
- Pydantic models matching JSON Schemas
- YAML parser with JSON Schema validation
- RefResolver for local schema references
- Manifest generator (SYS-14: Index Currency)
- Markdown view generator with Jinja2 templates
- Full `adr` CLI with validate, compile, generate, governance, entity query, and audit commands

**Dogfooding:**
- ADR-L-0001: STE authoring subsystem design (founding ADR)
- ADR-P-0001: Python toolkit implementation
- ADR-P-0002: JSON Schema + YAML format choice
- INV-0001: Schema validation required
- PROJECT.yaml: Project metadata for adr-architecture-kit

**Testing:**
- pytest test suite covering schema validation, manifest generation, compiler pipeline,
  contract validation, and CLI integration

**CI/CD:**
- GitHub Actions workflow for ADR governance
- Schema validation enforcement
- Manifest freshness validation
- PROJECT.yaml validation

**Documentation:**
- README with authority boundary, public surface, ADR taxonomy, and workflow
- authority-boundary.md, public-surface-and-stability.md
- architecture-ir-overview.md, adr-type-model.md, walkthrough-adr-to-ir.md
- Schema v1.0 documentation

**STE Integration:**
- ADR-to-Architecture-IR adapter with ste-spec normative contract as authority
- Repository-normalized discovery bundle (architecture index, entity registry,
  relationship registry, unresolved registry, manifest)

### Design Decisions

- YAML with embedded markdown (not markdown with YAML frontmatter) — DEC-0001
- Separate logical and physical ADRs with distinct schemas — DEC-0002
- Rich frontmatter as authoritative metadata, manifest as derived view — DEC-0003
- Type-prefixed IDs (ADR-L-XXXX, ADR-P-XXXX) — DEC-0004
- PROJECT.yaml for project-level metadata — DEC-0005
- Dogfooding strategy — DEC-0006
