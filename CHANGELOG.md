# Changelog

All notable changes to ADR Architecture Kit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-07

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

**Dogfooding:**
- ADR-L-0001: STE-compliant ADR system conception (constitutional document)
- ADR-P-0001: Python toolkit implementation
- ADR-P-0002: JSON Schema + YAML format choice
- INV-0001: Schema validation required
- PROJECT.yaml: Project metadata for adr-architecture-kit

**Testing:**
- 17 pytest tests covering schema validation, manifest generation, markdown generation
- Test fixtures (valid and invalid ADRs)
- Comprehensive test coverage

**CI/CD:**
- GitHub Actions workflow for ADR governance
- Schema validation enforcement
- Manifest freshness validation
- PROJECT.yaml validation

**Documentation:**
- README.md with quick start guide
- Logical ADR guide
- Physical ADR guide
- Schema guide
- Graph integration guide
- Schema v1.0 documentation

**STE Integration:**
- ste-spec submodule (normative specification)
- ste-runtime submodule (semantic graph)
- STE-compliant schema design (PRIME-1, PRIME-2, SYS-2, SYS-4, SYS-5, SYS-6, SYS-13, SYS-14)

### Design Decisions

- YAML with embedded markdown (not markdown with YAML frontmatter) - DEC-0001
- Separate logical and physical ADRs with distinct schemas - DEC-0002
- Rich frontmatter as authoritative metadata, manifest as derived view - DEC-0003
- Type-prefixed IDs (ADR-L-XXXX, ADR-P-XXXX) - DEC-0004
- PROJECT.yaml for project-level metadata - DEC-0005
- Dogfooding strategy - DEC-0006

### Known Limitations

- Decision ADRs (ADR-D-XXXX) schema defined but not implemented
- ste-runtime RECON ADR parser not yet implemented (future work)
- CLI tooling not implemented (future work)
- EDR comparison not implemented (future work)
- Policy engine integration not implemented (future work)

## [Unreleased]

### Planned for v0.2.0

- CLI commands (adr new, adr validate, adr generate-manifest, adr render)
- Advanced validators (convergence, conflicts, traceability)
- HTML/PDF view generators
- ste-runtime RECON ADR parser implementation
- Graph extraction validation

### Planned for v1.0.0

- EDR comparison and validation loop
- Patch system integration
- Policy engine integration
- Complete STE compliance validation
- Production-ready CLI
