<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 1107add6de90fa8d9c94f1722ef8fcc275c057693b2528e4c1db7bcad3e1dc75
rendered_hash: a03512e37da2d58b56e4b4d01c0756f5bc68d3bf5fb5b0e9159e3288afa14d72
-->

# ADR-L-0003: Quality Assurance and Testing Strategy

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0003  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-08  
**Modified:** 2026-08-05  
**Authors:** adr-architecture-kit  
**Domains:** quality-assurance, testing, governance, reliability  
**Tags:** testing, quality, ci-cd, validation, coverage  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0003 |
| Status | accepted |
| Decisions | 7 |
| Capabilities | 5 |
| Invariants | 13 |


## Context

The ADR Architecture Kit is a foundational tool for machine-verifiable architecture
documentation. As such, it must maintain high quality standards to ensure reliability,
correctness, and trust in the architectural governance it provides.

Current state:
- Validator tests exist for ADR schema/business rules, generated-doc integrity,
  system overview integrity, project metadata, and kernel contract validation
- Golden regression tests exist for committed registry outputs and manifest shape
- Compiler projection and builder parity tests exist to keep the compiler migration
  output-identical to the current generator path
- Multi-scope functionality is covered by CLI, scope resolver, validator, and
  manifest tests
- The repository has a unified governance bundle via `adr governance-checks`
  plus explicit CI gates for generated docs, system overview integrity, and
  project metadata validation
- Commit-at-meaningful-boundaries is now an explicit governance invariant

The system must be trustworthy because:
1. It validates architecture decisions that govern system behavior
2. Generated manifests are used by AI systems for reasoning
3. Schema validation failures can halt development workflows
4. Multi-scope functionality affects multiple projects simultaneously
5. Errors in ADR tooling can propagate to dependent systems

STE compliance requirements:
- **SYS-2**: Deterministic cognition requires deterministic validation
- **SYS-4**: Drift prevention requires reliable detection mechanisms
- **INV-0001**: Schema validation must be provably correct

Testing must balance:
- Comprehensive coverage vs. development velocity
- Isolated unit tests vs. real-world integration tests
- Fast feedback vs. thorough validation
- Maintainability vs. exhaustive edge case coverage
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0008 | Adopt Multi-Layer Testing Strategy | — |
| DEC-0015 | Require Tests for All New Components | — |
| DEC-0022 | Test Against Real Workspace ADRs | — |
| DEC-0029 | Enforce Testing in CI/CD Pipeline | — |
| DEC-0033 | Adopt Test-Driven Development (TDD) Methodology | — |
| DEC-0078 | Require retained release-artifact testing and no-regression quality controls | — |
| DEC-0081 | Make installed distribution metadata the runtime package-version authority | — |

### DEC-0008 — Adopt Multi-Layer Testing Strategy

**Rationale**

Different types of tests serve different purposes. A layered approach provides
comprehensive coverage while maintaining fast feedback loops.

Layers:
1. **Unit tests**: Fast, isolated, test individual functions/methods
2. **Integration tests**: Test component interactions
3. **Real-world tests**: Test against actual workspace ADRs
4. **Regression tests**: Prevent reintroduction of fixed bugs

**Consequences**

Positive:
- Clear test organization and purpose
- Fast unit tests for rapid development
- Integration tests catch interaction bugs
- Real-world tests ensure practical usability
- Test suite grows with system complexity

### DEC-0015 — Require Tests for All New Components

**Rationale**

Every new component must include tests before acceptance. This ensures
quality is built in from the start, not retrofitted later.

Prevents technical debt accumulation and ensures new features are
immediately verifiable.

**Consequences**

Positive:
- Slower initial development (offset by fewer bugs)
- Higher confidence in new features
- Easier refactoring with test safety net
- Documentation via test examples

### DEC-0022 — Test Against Real Workspace ADRs

**Rationale**

The toolkit must work with actual ADRs in the workspace. Testing against
synthetic fixtures alone is insufficient - real-world ADRs expose edge
cases and integration issues.

This provides dogfooding and ensures the toolkit works on its own
documentation.

**Consequences**

Positive:
- Tests depend on workspace ADR quality
- Tests may break when ADRs change (intentional)
- Immediate feedback on ADR schema changes
- Confidence in real-world usability

### DEC-0029 — Enforce Testing in CI/CD Pipeline

**Rationale**

Automated testing in CI/CD prevents regressions and ensures all
contributors maintain quality standards. Manual testing is insufficient
for a governance tool.

**Consequences**

Positive:
- PRs cannot merge without passing tests
- Consistent quality across contributions
- Automated regression detection
- Slower PR merge (acceptable trade-off)

### DEC-0033 — Adopt Test-Driven Development (TDD) Methodology

**Rationale**

TDD (Red-Green-Refactor) is architecturally aligned with STE principles:

**Alignment with STE**:
- SYS-2 (Deterministic Cognition): Tests enforce deterministic behavior
- SYS-4 (Drift Prevention): Tests detect drift immediately  
- PRIME-1 (No Implicit Assumptions): Tests make behavior explicit
- INV-0001 (Schema Validation): Tests prove validation correctness

**Why TDD for this system**:
1. This is a governance tool - it MUST be provably correct
2. Validation logic is complex - tests clarify expected behavior
3. Multi-scope functionality has many edge cases
4. Schema validation errors are costly (halt workflows)
5. Generated manifests are consumed by AI systems (must be reliable)

**TDD Cycle**:
1. Red: Write failing test (executable specification)
2. Green: Implement minimum code to pass (correctness proof)
3. Refactor: Improve design while maintaining tests (quality)

**Benefits for ADR Kit**:
- Tests become executable specifications of ADR behavior
- Validation logic is provably correct before deployment
- Refactoring is safe (tests prevent regressions)
- API design improves (testability forces good interfaces)
- Documentation via test examples

**Consequences**

Positive:
- Development workflow changes: test-first, not test-after
- Initial development may feel slower (pays off in debugging time)
- Forces thinking about behavior before implementation
- Creates comprehensive test suite organically
- Reduces debugging time (tests isolate issues)
- Higher confidence in correctness
- Better API design (testability constraint)

### DEC-0078 — Require retained release-artifact testing and no-regression quality controls

**Rationale**

Source-tree tests alone cannot prove that an installed distribution contains
the documented modules and package data, and rebuilding during publication
breaks the identity between tested and published artifacts. Existing Ruff,
strict-mypy, and Black debt must remain visible without permitting new debt.

CI therefore tests source installs and the exact retained wheel on every
supported Python version, measures coverage through the canonical `adr_kit`
namespace, ratchets legacy quality findings, and promotes a verified wheel
and sdist without rebuilding them in the publishing job.

Metadata renderability alone is insufficient for the PyPI-facing package
description: repository-relative README links resolve on GitHub but break
when rendered under the PyPI project page. Release qualification therefore
also requires portable link forms in the README used as `project.readme`.

Release qualification may complete for an exact source commit and its exact
retained distribution before a release tag exists, provided every required
qualification gate has already passed for that commit and artifact. Creating
`v<version>` does not, by itself, require a second independent qualification
of the same commit and artifact. Tag publication is the promotion boundary for
a previously qualified retained bundle.

**Consequences**

Positive:
- Installed-package behavior becomes release evidence rather than an assumption
- Published artifacts are byte-identical to the tested release bundle
- Existing quality debt can only stay level or decrease
- Supported Python claims are backed by source and wheel execution
- PyPI package-description links remain valid independently of GitHub rendering
- Tag publication promotes previously qualified artifacts without requalifying

### DEC-0081 — Make installed distribution metadata the runtime package-version authority

**Rationale**

A manually synchronized package literal can drift from build metadata and
from the artifact exercised by an installed consumer. Runtime package, CLI,
SDK result, and capability versions therefore resolve from installed
`adr-architecture-kit` metadata. Only `PackageNotFoundError` permits a
direct-source fallback to a name-verified `pyproject.toml`; an unavailable
or invalid source fallback returns the explicit non-release sentinel
`0+unknown`.

`pyproject.toml:[project].version` remains the sole manually edited package
version. Editable and wheel tests must prove metadata resolution rather than
silently relying on source-tree importability.

**Consequences**

Positive:
- Package, CLI, SDK, and installed-distribution version reports share one authority
- Direct-source execution remains supported without masking packaging defects
- Release evidence detects drift instead of synchronizing duplicate literals


## Capabilities

### CAP-0020 — Automated Quality Gates

CI/CD pipeline automatically runs test suite on every commit and PR.
Prevents merging code that fails tests or reduces coverage.

**Acceptance criteria**
- All tests pass before merge
- Coverage does not decrease
- Linting passes (code quality)
- Type checking passes (mypy)

### CAP-0023 — Test-Driven Development Support

Test infrastructure supports TDD workflow - write failing test, implement
feature, test passes. Fast test execution enables rapid iteration.

**Acceptance criteria**
- Tests run in under 30 seconds
- Clear test output (pass/fail/error)
- Easy to run subset of tests
- Good test isolation (no shared state)

### CAP-0026 — Regression Prevention

Once a bug is fixed, a test is added to prevent reintroduction. Test
suite grows to cover discovered edge cases.

**Acceptance criteria**
- Bug fixes include regression test
- Regression tests documented with issue reference
- Tests prevent reintroduction of bug

### CAP-0029 — Documentation via Tests

Tests serve as executable documentation showing how to use components.
Examples in tests demonstrate API usage patterns.

**Acceptance criteria**
- Tests show common usage patterns
- Tests demonstrate error handling
- Tests illustrate edge cases
- Test names clearly describe behavior

### CAP-0046 — Verified Build-Once Release Promotion

Build one release bundle, verify its metadata and identity, exercise the
retained wheel across the supported Python matrix, and publish that exact
bundle without a second build.

**Acceptance criteria**
- minimum supported Python minor is 3.14 (`requires-python >=3.14`); currently qualified released minor line is 3.14; source and retained-wheel qualification execute on that line; repository reference interpreter is currently 3.14.7; new GA Python minors require explicit admission to the qualification matrix
- canonical package coverage remains at or above 80%
- Ruff, strict-mypy, and Black controls reject new debt
- the release manifest requires exactly one wheel and one sdist
- the publish job has no build step and confines OIDC and the PyPI environment to publication
- the PyPI-facing package description (`project.readme`) contains only portable link forms valid outside GitHub repository-relative rendering
- tag publication promotes a previously qualified retained bundle for the exact tagged SHA
- re-qualification is not required solely because a release tag was created
- publication fails closed when qualification evidence or the retained bundle is missing or fails identity verification
- release-eligible qualification includes OS-portability evidence on Ubuntu/Linux, Windows, and macOS as separate axes from Python-version compatibility
- Windows/macOS Python 3.14 complete-suite evidence proves source/runtime OS portability; the exact retained wheel additionally passes the installed-wheel harness on Windows/macOS Python 3.14 without rebuilding per OS
- UUIDv7 mint mechanism remains implementation-owned and is not part of ADR-L-0003 identity semantics




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0020 | Every component with public API MUST have unit tests covering: - Happy path (valid inputs) - Error cases (invalid… | MUST / test | automated |
| INV-0021 | Schema validators MUST have tests proving correctness against: - Valid ADRs (should pass) - Invalid ADRs (should… | MUST / test | automated |
| INV-0022 | Multi-scope functionality MUST have tests covering: - Single scope (backward compatibility) - Multiple scopes… | MUST / test | automated |
| INV-0023 | Test suite MUST complete in under 30 seconds for fast feedback | SHOULD / test | automated |
| INV-0024 | Tests MUST be deterministic - same input always produces same output | MUST / test | automated |
| INV-0025 | Breaking changes to public APIs MUST be detected by tests | MUST / test | automated |
| INV-0026 | Test coverage SHOULD be measured and tracked, with minimum 80% coverage for critical components (parsers,… | SHOULD / test | automated |
| INV-0072 | Pull-request and release validation MUST install the project before tests, MUST measure canonical `adr_kit`… | MUST / test | automated |
| INV-0073 | Release publication MUST promote exactly one previously tested wheel and one previously tested sdist without… | MUST / test | automated |
| INV-0075 | Source, editable-install, and clean retained-wheel consumers MUST exercise the supported SDK and MUST agree on… | MUST / test | automated |
| INV-0083 | The PyPI-facing package description (the file declared as `project.readme`) MUST contain only Markdown link and… | MUST / test | automated |
| INV-0095 | adr_kit MUST not ship deprecated runtime API usage, and its direct dependencies MUST be audited for vulnerabilities… | MUST / policy | automated |
| INV-0096 | Repository changes must be committed at meaningful verified boundaries rather than accumulated indefinitely. | MUST / policy | audit |

### INV-0020

**Statement**

Every component with public API MUST have unit tests covering:
- Happy path (valid inputs)
- Error cases (invalid inputs)
- Edge cases (boundary conditions)
- Backward compatibility (when applicable)

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Public APIs are contracts. Tests document expected behavior and prevent
breaking changes.

### INV-0021

**Statement**

Schema validators MUST have tests proving correctness against:
- Valid ADRs (should pass)
- Invalid ADRs (should fail with clear errors)
- Edge cases (empty fields, special characters, etc.)

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Schema validation is the foundation of machine-verifiable architecture.
Incorrect validation undermines the entire system.

### INV-0022

**Statement**

Multi-scope functionality MUST have tests covering:
- Single scope (backward compatibility)
- Multiple scopes (recursive operations)
- Scope boundary enforcement (security)
- Parent-child relationships

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Multi-scope is complex and affects multiple projects. Comprehensive
testing prevents cross-project contamination and security issues.

### INV-0023

**Statement**

Test suite MUST complete in under 30 seconds for fast feedback

**Scope:** global

**Enforcement:** SHOULD (test)
**Verification:** automated

**Rationale**

Slow tests discourage running them frequently. Fast feedback enables
test-driven development and rapid iteration.

### INV-0024

**Statement**

Tests MUST be deterministic - same input always produces same output

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Non-deterministic tests (flaky tests) erode trust and waste time.
Aligns with SYS-2 (deterministic cognition).

### INV-0025

**Statement**

Breaking changes to public APIs MUST be detected by tests

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Backward compatibility is critical for existing users. Tests should
fail when APIs change incompatibly.

### INV-0026

**Statement**

Test coverage SHOULD be measured and tracked, with minimum 80% coverage
for critical components (parsers, validators, generators)

**Scope:** global

**Enforcement:** SHOULD (test)
**Verification:** automated

**Rationale**

Coverage metrics identify untested code paths. 80% is pragmatic balance
between thoroughness and diminishing returns.

### INV-0072

**Statement**

Pull-request and release validation MUST install the project before tests,
MUST measure canonical `adr_kit` namespace coverage at no less than 80%,
and MUST exercise both a source installation and the exact retained wheel
on every claimed Python version.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Source-package leakage and namespace aliases can produce misleading
coverage and allow incomplete wheels to pass repository-local tests.

### INV-0073

**Statement**

Release publication MUST promote exactly one previously tested wheel and
one previously tested sdist without rebuilding. Their filenames, sizes,
SHA-256 hashes, package version, source commit, and `v<version>` tag MUST
be verified before the privileged publish step. Ruff, strict-mypy, and
Black debt MUST be guarded by committed no-regression baselines that allow
removals but reject additions or count increases.

When a successful qualification already exists for the exact tagged source
commit and its retained release bundle, the tag publication path MUST act as
a promotion and identity-verification boundary only. It MUST NOT rebuild
distributions or re-run the independent qualification suite solely because a
tag was created. Publication MUST fail closed if successful qualification
evidence or the retained bundle for that exact commit cannot be proven.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Artifact identity and truthful quality measurements are required for a
trustworthy release chain while pre-existing debt is retired incrementally.

### INV-0075

**Statement**

Source, editable-install, and clean retained-wheel consumers MUST exercise
the supported SDK and MUST agree on package, CLI, SDK result, capability,
and installed-distribution versions wherever distribution metadata exists.
Direct-source fallback MUST occur only when metadata is absent and MUST NOT
hide invalid installed metadata or package-resource failures.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

A supported SDK and release chain require equivalent behavior from the
checkout, editable installation, and the exact artifact selected for
promotion.

### INV-0083

**Statement**

The PyPI-facing package description (the file declared as `project.readme`)
MUST contain only Markdown link and image targets that resolve independently
of GitHub repository-relative rendering: same-document anchors, absolute
`https://` URLs (optional fragment), and `mailto:` URIs. Repository-relative
file or directory targets and `http://` URLs MUST be rejected by automated
release qualification before merge or publication.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Observed on the published `0.3.0` long description: GitHub-valid relative
README links became invalid PyPI package-description URLs. `twine check`
validates metadata renderability but not cross-surface link portability.

### INV-0095

**Statement**

adr_kit MUST not ship deprecated runtime API usage, and its direct dependencies MUST be audited for vulnerabilities and upgrade freshness

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

adr_kit is a governance and architecture-authority tool. If it relies on
deprecated modules, stale runtimes, or vulnerable packages, it undermines
its own authority. CI hooks include `scripts/check_runtime_hygiene.py` and
`adr audit-runtime`.

### INV-0096

**Statement**

Repository changes must be committed at meaningful verified boundaries rather than accumulated indefinitely.

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** audit

**Rationale**

Small, verified commits reduce review ambiguity and preserve architectural
intent. A meaningful boundary requires a coherent slice, relevant tests and
validation, and a reviewable repository state.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0002](ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)
- [ADR-PC-0008](../physical-component/ADR-PC-0008-project-scope-resolution.md)

**References**
- [ADR-L-0005](ADR-L-0005-adr-to-prompt-translation-for-ai-implementation.md)
- [ADR-L-0004](ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0002](ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)
- [ADR-PC-0008](../physical-component/ADR-PC-0008-project-scope-resolution.md)
- [ADR-L-0007](ADR-L-0007-deterministic-documentation-projection.md)
- [ADR-L-0008](ADR-L-0008-validation-modes-for-draft-and-complete-adrs.md)
- [ADR-L-0018](ADR-L-0018-schema-v1-2-and-normalized-semantic-foundation.md)





## Notes

Testing strategy implementation:

Test organization:
```
tests/
  test_scope_resolver.py      # Unit + integration tests for scope detection
  test_adr_validator.py        # Unit tests for validation logic
  test_multi_scope_generator.py # Integration tests for scoped generation
  test_manifest_generator.py   # Unit tests for manifest generation
  test_markdown_generator.py   # Unit tests for view generation
  test_schema_validation.py    # Schema validation correctness
```

Test execution:
```bash
# Standard local governance bundle
adr governance-checks

# Strict contract gate
adr validate-contract --contract-profile greenfield

# Ratcheted brownfield contract gate
adr validate-contract --contract-profile brownfield --max-sentinel-fields 0 --max-non-complete-entities 0

# Generated artifact integrity (manifest + rendered ADR markdown)
adr validate-generated-docs

# Generated system overview integrity
adr validate-system-overview

# PROJECT.yaml integrity
adr validate-project-metadata

# Targeted pytest usage for local development
pytest tests/ -v
pytest tests/ --cov=adr_kit --cov-report=html --cov-report=term --cov-fail-under=80
pytest tests/ -k "scope" -v
```

CI/CD integration (orthogonal evidence axes):
- Minimum supported Python minor is 3.14 (`requires-python >=3.14`); currently qualified released minor line is 3.14; reference interpreter is currently 3.14.7; new GA Python minors require explicit admission to the qualification matrix
- Canonical correctness: Ubuntu + Python 3.14 runs the complete suite with coverage (`--cov=adr_kit --cov-fail-under=80`) exactly once
- Python-version compatibility: Ubuntu runs focused source/install/SDK compatibility on the currently qualified released minor line (Python 3.14; not a second full suite on each interpreter)
- OS behavior / source-runtime portability: Windows and macOS at Python 3.14 each run the complete suite (no coverage gate); Ubuntu 3.14 suite is owned by the coverage job and is not duplicated
- Retained-wheel Python compatibility: exact retained wheel via `scripts/test_installed_wheel.py` on Ubuntu Python 3.14
- Retained-wheel OS portability: the exact same retained wheel via `scripts/test_installed_wheel.py` on Windows and macOS at Python 3.14; the wheel MUST NOT be rebuilt per OS
- UUIDv7 mint mechanism remains implementation-owned and is not part of ADR-L-0003 identity semantics
- These axes are orthogonal and MUST NOT imply that all supported Python versions execute on every OS
- Linux-only execution is insufficient evidence for an OS-agnostic package claim
- PR qualification = proposed-change evidence; develop qualification = integration evidence; only a successful completed `push` of ADR Governance on `main` for the exact tagged SHA is release-eligible; tag publication is promotion/identity verification only
- `adr governance-checks --skip-tests` must pass in CI when the complete suite is already owned by the coverage job
- `adr validate-generated-docs` must pass for manifest and rendered ADR output
- `adr validate-system-overview` must pass for `SYSTEM-OVERVIEW.md`
- `adr validate-project-metadata` must pass for `PROJECT.yaml`
- Quality gates are broader than generic `pytest` alone because they also enforce
  contract, generated-artifact, and project-metadata integrity
- Verified implementation slices must be committed at meaningful boundaries in
  alignment with `INV-0096`
- Release artifacts are built once, retained, installed in clean environments,
  manifested, re-verified, and promoted without rebuilding
- Ruff, strict-mypy, and Black legacy debt is governed by no-regression ratchets;
  new Phase 0 Python files must be clean under all three tools

Future enhancements:
- Property-based testing (hypothesis) for generators
- Mutation testing to verify test quality
- Performance benchmarks to detect regressions
- Contract testing for API stability


---

*Generated from ADR-L-0003 by ADR Architecture Kit (projection v3)*