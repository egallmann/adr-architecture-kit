<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 2
hash_algorithm: sha256
source_hash: bc2463b15b8765b2256b910ae66c073efb6553a142bacead2ca33135957b13ae
rendered_hash: 8e3c98b063e9ca30aa574294202dd712a5e43eafca6592e1aa5cc63615b0f55d
-->

# ADR-L-0003: Quality Assurance and Testing Strategy

**Status:** accepted  
**Created:** 2026-03-08  
**Modified:** 2026-08-05  
**Authors:** adr-architecture-kit  
**Domains:** quality-assurance, testing, governance, reliability  
**Tags:** testing, quality, ci-cd, validation, coverage  
**Alias name:** quality-assurance-and-testing-strategy  

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


## Relationship graph

```mermaid
flowchart LR
  n_019fee89_e615_701c_8e3e_d463d56f89ce["INV-0075"]
  n_019fee89_e615_70a5_861b_b2dde147e5af["ADR-L-0001"]
  n_019fee89_e615_713f_a73d_10442c1dc6b9["DEC-0081"]
  n_019fee89_e615_722d_bf3a_9ed33338beaf["CAP-0029"]
  n_019fee89_e615_7235_8135_9a274f82afc8["INV-0083"]
  n_019fee89_e615_729d_873d_f2bf925d1846["INV-0022"]
  n_019fee89_e615_73a3_8d31_7a4721affae9["ADR-L-0005"]
  n_019fee89_e615_7402_b43f_a03be950d0b3["CAP-0046"]
  n_019fee89_e615_7498_9825_b465a8830d8a["CAP-0020"]
  n_019fee89_e615_74af_a113_f1a7a9e5d49e["INV-0072"]
  n_019fee89_e615_74c8_a813_5f18ee19f9a8["INV-0021"]
  n_019fee89_e615_74f0_9826_fcaa4052cfdc["INV-0095"]
  n_019fee89_e615_7519_972f_504bac832107["INV-0073"]
  n_019fee89_e615_7577_8d37_dd0df031bec9["ADR-L-0004"]
  n_019fee89_e615_758b_a31f_a0dcb8d9d09a["INV-0023"]
  n_019fee89_e615_75e2_a33f_645d3f0970a1["INV-0025"]
  n_019fee89_e615_760b_a43f_b3fe08e0d6ef["DEC-0033"]
  n_019fee89_e615_77f6_9b1f_695732d25443["ADR-L-0003"]
  n_019fee89_e615_7871_b719_23a5128874ae["INV-0024"]
  n_019fee89_e615_78ee_a53f_99d85ea925a3["DEC-0022"]
  n_019fee89_e615_792a_aa3e_a9f0f34c1b93["INV-0096"]
  n_019fee89_e615_7958_822b_bbd40f3a5ebc["CAP-0023"]
  n_019fee89_e615_79a1_be3d_03af8c291326["DEC-0008"]
  n_019fee89_e615_7a08_8b0f_d2b2ed57eacb["INV-0026"]
  n_019fee89_e615_7b9c_8e3f_32ceeda01491["ADR-L-0007"]
  n_019fee89_e615_7c97_a633_fbfd69ffa030["INV-0020"]
  n_019fee89_e615_7d1d_a33d_ca62fdaad0be["DEC-0015"]
  n_019fee89_e615_7d32_8d01_f61b4d7aae40["CAP-0026"]
  n_019fee89_e615_7e36_8e3f_c0e37def8629["DEC-0078"]
  n_019fee89_e615_7e99_8137_8ac8d0972e1b["DEC-0029"]
  n_019fee89_e615_7f19_810b_c7b33a9d9e0d["ADR-L-0002"]
  n_019fee89_e616_7066_8d2f_3acc7f469f72["ADR-L-0008"]
  n_019fee89_e617_7f4d_811d_4862645a55c5["ADR-L-0018"]
  n_019fee89_e618_742f_951d_d29401d56c19["ADR-P-0003"]
  n_019fee89_e618_79ed_9d2d_cc35c63bc99a["ADR-P-0001"]
  n_019fee89_e615_701c_8e3e_d463d56f89ce -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_713f_a73d_10442c1dc6b9 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_722d_bf3a_9ed33338beaf -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7235_8135_9a274f82afc8 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_729d_873d_f2bf925d1846 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7402_b43f_a03be950d0b3 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7498_9825_b465a8830d8a -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_74af_a113_f1a7a9e5d49e -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_74c8_a813_5f18ee19f9a8 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_74f0_9826_fcaa4052cfdc -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7519_972f_504bac832107 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_758b_a31f_a0dcb8d9d09a -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_75e2_a33f_645d3f0970a1 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_760b_a43f_b3fe08e0d6ef -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7871_b719_23a5128874ae -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_78ee_a53f_99d85ea925a3 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_792a_aa3e_a9f0f34c1b93 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7958_822b_bbd40f3a5ebc -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_79a1_be3d_03af8c291326 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7a08_8b0f_d2b2ed57eacb -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7c97_a633_fbfd69ffa030 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7d1d_a33d_ca62fdaad0be -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7d32_8d01_f61b4d7aae40 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7e36_8e3f_c0e37def8629 -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7e99_8137_8ac8d0972e1b -->|"declared_in"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_73a3_8d31_7a4721affae9 -->|"references"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7577_8d37_dd0df031bec9 -->|"references"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_77f6_9b1f_695732d25443 -->|"references"| n_019fee89_e615_70a5_861b_b2dde147e5af
  n_019fee89_e615_77f6_9b1f_695732d25443 -->|"references"| n_019fee89_e615_7f19_810b_c7b33a9d9e0d
  n_019fee89_e615_77f6_9b1f_695732d25443 -->|"references"| n_019fee89_e618_742f_951d_d29401d56c19
  n_019fee89_e615_77f6_9b1f_695732d25443 -->|"references"| n_019fee89_e618_79ed_9d2d_cc35c63bc99a
  n_019fee89_e615_7b9c_8e3f_32ceeda01491 -->|"references"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e616_7066_8d2f_3acc7f469f72 -->|"references"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e617_7f4d_811d_4862645a55c5 -->|"references"| n_019fee89_e615_77f6_9b1f_695732d25443
```

## Related ADRs

### ADR-L-0001 — STE-Compliant Machine-Verifiable Architecture Decision Record System

**Relationships:**
- this ADR -[:references]-> 019fee89-e615-70a5-861b-b2dde147e5af

**Context:** # ADR Architecture Kit — STE Authoring Subsystem

[Open projection](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
### ADR-L-0002 — Multi-Scope ADR Architecture for Sub-Module Development

**Relationships:**
- this ADR -[:references]-> 019fee89-e615-7f19-810b-c7b33a9d9e0d

**Context:** The adr-architecture-kit is being actively developed in a single workspace alongside
multiple sub-modules (ste-runtime, future services) that will eventually become
independent services. Each sub-module needs to leverage the ADR system for its own
architectural documentation while being developed in parallel within the monorepo.

[Open projection](ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)
### ADR-L-0004 — ADR-to-Implementation Traceability via Decorators and Metadata Attribution

**Relationships:**
- 019fee89-e615-7577-8d37-dd0df031bec9 -[:references]-> this ADR

**Context:** Architecture Decision Records document why implementation artifacts exist, but
the repo still lacks a universal, machine-verifiable way to trace code,
infrastructure, configuration, schemas, pipelines, and scripts back to the
ADRs that justify them.

[Open projection](ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)
### ADR-L-0005 — ADR-to-Prompt Translation for AI Implementation

**Relationships:**
- 019fee89-e615-73a3-8d31-7a4721affae9 -[:references]-> this ADR

**Context:** The ADR Architecture Kit encodes architectural decisions in machine-readable YAML
format with explicit invariants, capabilities, and component specifications. These
structured ADRs contain all the information needed to guide AI implementation:

[Open projection](ADR-L-0005-adr-to-prompt-translation-for-ai-implementation.md)
### ADR-L-0007 — Deterministic Documentation Projection

**Relationships:**
- 019fee89-e615-7b9c-8e3f-32ceeda01491 -[:references]-> this ADR

**Context:** The repository already treats several human-readable artifacts as derived state:
ADR human projections under adrs/adr-projection/, manifest summaries, and the AI-first SYSTEM-OVERVIEW
are generated from structured or code-defined sources. That behavior now needs
explicit architectural authority so future contributors do not reintroduce
manually maintained documentation that drifts from canonical artifacts.

[Open projection](ADR-L-0007-deterministic-documentation-projection.md)
### ADR-L-0008 — Validation Modes for Draft and Complete ADRs

**Relationships:**
- 019fee89-e616-7066-8d2f-3acc7f469f72 -[:references]-> this ADR

**Context:** The ADR Architecture Kit currently couples schema validation to completeness for
several ADR types. That behavior is useful for acceptance gates, but it is too
strict for the actual design workflow used in this workspace.

[Open projection](ADR-L-0008-validation-modes-for-draft-and-complete-adrs.md)
### ADR-L-0018 — Schema v1.2 and Normalized Semantic Foundation

**Relationships:**
- 019fee89-e617-7f4d-811d-4862645a55c5 -[:references]-> this ADR

**Context:** Phase 1 established a narrow supported authoring SDK while explicitly deferring
schema expansion, normalized-model expansion, assertion identity, bindings, and
topology identity. The repository now needs those contracts as an additive
semantic foundation for future consumers, without implementing the Phase 3 graph
bundle or absorbing authority owned by runtime, rules, substrate, or admission
systems.

[Open projection](ADR-L-0018-schema-v1-2-and-normalized-semantic-foundation.md)
### ADR-P-0001 — Python Toolkit Implementation for ADR Kit

**Relationships:**
- this ADR -[:references]-> 019fee89-e618-79ed-9d2d-cc35c63bc99a

**Context:** This ADR specifies the implementation of ADR Kit using Python ecosystem and modern
Python tooling. The implementation must support schema validation, YAML parsing,
Pydantic models, and view generation.

[Open projection](../physical/ADR-P-0001-python-toolkit-implementation-for-adr-kit.md)
### ADR-P-0003 — Multi-Scope Python Implementation for ADR Toolkit

**Relationships:**
- this ADR -[:references]-> 019fee89-e618-742f-951d-d29401d56c19

**Context:** ADR-L-0002 defines the logical architecture for multi-scope ADR support.
This Physical ADR specifies the concrete Python implementation including
module structure, API design, and CLI interface.

[Open projection](../physical/ADR-P-0003-multi-scope-python-implementation-for-adr-toolkit.md)

## Capabilities

### CAP-0020: Automated Quality Gates

CI/CD pipeline automatically runs test suite on every commit and PR.
Prevents merging code that fails tests or reduces coverage.


### CAP-0023: Test-Driven Development Support

Test infrastructure supports TDD workflow - write failing test, implement
feature, test passes. Fast test execution enables rapid iteration.


### CAP-0026: Regression Prevention

Once a bug is fixed, a test is added to prevent reintroduction. Test
suite grows to cover discovered edge cases.


### CAP-0029: Documentation via Tests

Tests serve as executable documentation showing how to use components.
Examples in tests demonstrate API usage patterns.


### CAP-0046: Verified Build-Once Release Promotion

Build one release bundle, verify its metadata and identity, exercise the
retained wheel across the supported Python matrix, and publish that exact
bundle without a second build.






## Invariants

### INV-0020

**Statement:** Every component with public API MUST have unit tests covering:
- Happy path (valid inputs)
- Error cases (invalid inputs)
- Edge cases (boundary conditions)
- Backward compatibility (when applicable)
  
**Scope:** global  
**Enforcement:** must (test)  
**Verification:** automated

**Rationale:**
Public APIs are contracts. Tests document expected behavior and prevent
breaking changes.




### INV-0021

**Statement:** Schema validators MUST have tests proving correctness against:
- Valid ADRs (should pass)
- Invalid ADRs (should fail with clear errors)
- Edge cases (empty fields, special characters, etc.)
  
**Scope:** global  
**Enforcement:** must (test)  
**Verification:** automated

**Rationale:**
Schema validation is the foundation of machine-verifiable architecture.
Incorrect validation undermines the entire system.




### INV-0022

**Statement:** Multi-scope functionality MUST have tests covering:
- Single scope (backward compatibility)
- Multiple scopes (recursive operations)
- Scope boundary enforcement (security)
- Parent-child relationships
  
**Scope:** global  
**Enforcement:** must (test)  
**Verification:** automated

**Rationale:**
Multi-scope is complex and affects multiple projects. Comprehensive
testing prevents cross-project contamination and security issues.




### INV-0023

**Statement:** Test suite MUST complete in under 30 seconds for fast feedback
  
**Scope:** global  
**Enforcement:** should (test)  
**Verification:** automated

**Rationale:**
Slow tests discourage running them frequently. Fast feedback enables
test-driven development and rapid iteration.




### INV-0024

**Statement:** Tests MUST be deterministic - same input always produces same output
  
**Scope:** global  
**Enforcement:** must (test)  
**Verification:** automated

**Rationale:**
Non-deterministic tests (flaky tests) erode trust and waste time.
Aligns with SYS-2 (deterministic cognition).




### INV-0025

**Statement:** Breaking changes to public APIs MUST be detected by tests
  
**Scope:** global  
**Enforcement:** must (test)  
**Verification:** automated

**Rationale:**
Backward compatibility is critical for existing users. Tests should
fail when APIs change incompatibly.




### INV-0026

**Statement:** Test coverage SHOULD be measured and tracked, with minimum 80% coverage
for critical components (parsers, validators, generators)
  
**Scope:** global  
**Enforcement:** should (test)  
**Verification:** automated

**Rationale:**
Coverage metrics identify untested code paths. 80% is pragmatic balance
between thoroughness and diminishing returns.




### INV-0072

**Statement:** Pull-request and release validation MUST install the project before tests,
MUST measure canonical `adr_kit` namespace coverage at no less than 80%,
and MUST exercise both a source installation and the exact retained wheel
on every claimed Python version.
  
**Scope:** global  
**Enforcement:** must (test)  
**Verification:** automated

**Rationale:**
Source-package leakage and namespace aliases can produce misleading
coverage and allow incomplete wheels to pass repository-local tests.




### INV-0073

**Statement:** Release publication MUST promote exactly one previously tested wheel and
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
**Enforcement:** must (test)  
**Verification:** automated

**Rationale:**
Artifact identity and truthful quality measurements are required for a
trustworthy release chain while pre-existing debt is retired incrementally.




### INV-0075

**Statement:** Source, editable-install, and clean retained-wheel consumers MUST exercise
the supported SDK and MUST agree on package, CLI, SDK result, capability,
and installed-distribution versions wherever distribution metadata exists.
Direct-source fallback MUST occur only when metadata is absent and MUST NOT
hide invalid installed metadata or package-resource failures.
  
**Scope:** global  
**Enforcement:** must (test)  
**Verification:** automated

**Rationale:**
A supported SDK and release chain require equivalent behavior from the
checkout, editable installation, and the exact artifact selected for
promotion.




### INV-0083

**Statement:** The PyPI-facing package description (the file declared as `project.readme`)
MUST contain only Markdown link and image targets that resolve independently
of GitHub repository-relative rendering: same-document anchors, absolute
`https://` URLs (optional fragment), and `mailto:` URIs. Repository-relative
file or directory targets and `http://` URLs MUST be rejected by automated
release qualification before merge or publication.
  
**Scope:** global  
**Enforcement:** must (test)  
**Verification:** automated

**Rationale:**
Observed on the published `0.3.0` long description: GitHub-valid relative
README links became invalid PyPI package-description URLs. `twine check`
validates metadata renderability but not cross-surface link portability.




### INV-0095

**Statement:** adr_kit MUST not ship deprecated runtime API usage, and its direct dependencies MUST be audited for vulnerabilities and upgrade freshness  
**Scope:** global  
**Enforcement:** must (policy)  
**Verification:** automated

**Rationale:**
adr_kit is a governance and architecture-authority tool. If it relies on
deprecated modules, stale runtimes, or vulnerable packages, it undermines
its own authority. CI hooks include `scripts/check_runtime_hygiene.py` and
`adr audit-runtime`.




### INV-0096

**Statement:** Repository changes must be committed at meaningful verified boundaries rather than accumulated indefinitely.  
**Scope:** global  
**Enforcement:** must (policy)  
**Verification:** audit

**Rationale:**
Small, verified commits reduce review ambiguity and preserve architectural
intent. A meaningful boundary requires a coherent slice, relevant tests and
validation, and a reviewable repository state.






## Decisions

### DEC-0008: Adopt Multi-Layer Testing Strategy

**Rationale:**
Different types of tests serve different purposes. A layered approach provides
comprehensive coverage while maintaining fast feedback loops.

Layers:
1. **Unit tests**: Fast, isolated, test individual functions/methods
2. **Integration tests**: Test component interactions
3. **Real-world tests**: Test against actual workspace ADRs
4. **Regression tests**: Prevent reintroduction of fixed bugs



**Consequences:**

**Positive:**
- Clear test organization and purpose
- Fast unit tests for rapid development
- Integration tests catch interaction bugs
- Real-world tests ensure practical usability
- Test suite grows with system complexity



### DEC-0015: Require Tests for All New Components

**Rationale:**
Every new component must include tests before acceptance. This ensures
quality is built in from the start, not retrofitted later.

Prevents technical debt accumulation and ensures new features are
immediately verifiable.



**Consequences:**

**Positive:**
- Slower initial development (offset by fewer bugs)
- Higher confidence in new features
- Easier refactoring with test safety net
- Documentation via test examples



### DEC-0022: Test Against Real Workspace ADRs

**Rationale:**
The toolkit must work with actual ADRs in the workspace. Testing against
synthetic fixtures alone is insufficient - real-world ADRs expose edge
cases and integration issues.

This provides dogfooding and ensures the toolkit works on its own
documentation.



**Consequences:**

**Positive:**
- Tests depend on workspace ADR quality
- Tests may break when ADRs change (intentional)
- Immediate feedback on ADR schema changes
- Confidence in real-world usability



### DEC-0029: Enforce Testing in CI/CD Pipeline

**Rationale:**
Automated testing in CI/CD prevents regressions and ensures all
contributors maintain quality standards. Manual testing is insufficient
for a governance tool.



**Consequences:**

**Positive:**
- PRs cannot merge without passing tests
- Consistent quality across contributions
- Automated regression detection
- Slower PR merge (acceptable trade-off)



### DEC-0033: Adopt Test-Driven Development (TDD) Methodology

**Rationale:**
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



**Consequences:**

**Positive:**
- Development workflow changes: test-first, not test-after
- Initial development may feel slower (pays off in debugging time)
- Forces thinking about behavior before implementation
- Creates comprehensive test suite organically
- Reduces debugging time (tests isolate issues)
- Higher confidence in correctness
- Better API design (testability constraint)



### DEC-0078: Require retained release-artifact testing and no-regression quality controls

**Rationale:**
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



**Consequences:**

**Positive:**
- Installed-package behavior becomes release evidence rather than an assumption
- Published artifacts are byte-identical to the tested release bundle
- Existing quality debt can only stay level or decrease
- Supported Python claims are backed by source and wheel execution
- PyPI package-description links remain valid independently of GitHub rendering
- Tag publication promotes previously qualified artifacts without requalifying



### DEC-0081: Make installed distribution metadata the runtime package-version authority

**Rationale:**
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



**Consequences:**

**Positive:**
- Package, CLI, SDK, and installed-distribution version reports share one authority
- Direct-source execution remains supported without masking packaging defects
- Release evidence detects drift instead of synchronizing duplicate literals





---

*Generated from ADR-L-0003 by ADR Architecture Kit*