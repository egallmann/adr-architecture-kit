# Changelog

All notable changes to ADR Architecture Kit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — Public Release Readiness Pass

### Changed

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

### Added

- CI job `release-artifact-validation`: builds wheel and sdist, installs into a
  clean environment, and runs `adr --help` smoke tests to prove the wheel install
  works without editable-install workarounds.
- CI step for schema parity check: validates that `src/adr_kit/schema/v*/` copies
  match the repo-root `schema/v*/` canonical files byte-for-byte.
- Advisory CI step for Architecture IR mirror check against sibling `ste-spec`
  checkout (skips gracefully when sibling is absent).

## [0.1.0] — 2026-03-07

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
