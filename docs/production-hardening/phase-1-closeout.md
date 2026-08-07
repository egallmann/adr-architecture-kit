# Phase 1 closeout

Phase 1 implements the ADR-authorized narrow `adr_kit.api` facade while preserving
Phase 0 compatibility and repository ownership boundaries.

## Delivered

- Exact 17-symbol `adr_kit.api` inventory and API contract version `1.0`.
- Immutable request, result, artifact, diagnostic, capability, and exception contracts.
- Validation, preview/write compilation, and eager repository opening.
- Shared normalized-bundle assembly with preview/repository fingerprint parity.
- Compiler-type containment in annotations and runtime result graphs.
- Private CLI application-service delegation with an unchanged 16-case behavior and
  generated-byte snapshot.
- Metadata-first runtime version authority with direct-source fallback and
  `0+unknown` non-release sentinel.
- Source, editable, and retained-wheel consumer controls on Python 3.11–3.14 CI.
- Additive deterministic SDK benchmark sidecars and explicit Phase 1 zero-debt files.

## Authority boundary resolution

Only ADR Kit writes inside this repository. Runtime and workspace projections belong
under the workspace-root `.ste-workspace/`, outside every repository. No
`ste-runtime` source or output was changed or used to refresh ADR Kit files. The
obsolete plan step that targeted runtime output at this repository was intentionally
not executed.

## Focused commit evidence

- `5552f8a` — design alternatives and contract
- `a034265` — ADR authority for facade and version metadata
- `373fc6c` — initial ADR-derived regeneration
- `520ecfa` — workspace-external runtime-state authority correction
- `e4405bb` — corrected authority projection regeneration
- `9425288` — public SDK RED contracts
- `a8cc81e` — narrow facade GREEN
- `c27f0c8` — CLI behavior baseline and delegation RED
- `3b58c2a` — CLI delegation GREEN
- `e738c65` — version authority RED
- `f26276b` — metadata-first version GREEN
- `c28fb5b` — distribution/CI/quality/benchmark RED
- `ec1fb6f` — distribution/CI/quality/benchmark GREEN

Two intervening commits (`14d217e`, `d268ba2`) preserve the audit trail of the
runtime-write conflict before the user renewed the correct authority boundary.

## Final validation evidence

Validated on 2026-08-06 with Python 3.12:

- Phase 1 focused suites: 16 SDK, 4 CLI delegation, 5 version-authority, and 8
  release/quality/benchmark tests passed.
- Compatibility snapshots: Python surface, CLI surface, and 16-case CLI behavior
  snapshots matched.
- Version parity: `pyproject.toml`, installed metadata, `adr_kit.__version__`,
  `adr --version`, SDK capabilities, and SDK results reported `0.1.0`.
- ADR validation: 30 files, 0 errors, 2 pre-existing warnings; cross-references valid.
- Generated documentation, system overview, compiler check mode, goldens, and package
  schema parity passed.
- Quality ratchets passed at Ruff 63, mypy 352, and Black 103; each is at or below
  its Phase 0 no-regression baseline, and new Phase 1 files are zero-debt targets.
- Local pre-push passed 60 focused tests and validated compliant read-only attribution
  evidence from workspace `.ste-workspace` (72 records, 0 errors, 0 warnings).
- Greenfield and brownfield governance profiles were compliant with 238 complete
  entities and no sentinel or non-complete entities.
- Full suite: 390 passed, 6 skipped.
- Coverage suite: 390 passed, 6 skipped, 85.70% total coverage (80% required).
- Dependency audit: no known vulnerabilities.
- Fresh wheel/sdist: build and `twine check` passed; the retained-wheel harness passed
  in an external clean virtual environment with SDK, resource, CLI, and source-isolation
  probes.
- Descriptive benchmark: original and SDK evidence deterministic for repository,
  examples, and synthetic 10/100/500-ADR corpora.
- Frozen CLI surface remains byte-identical to `origin/develop`.

The documented Python 3.11–3.14 matrix is enforced in CI. This local closeout used
Python 3.12; no claim is made that the other matrix jobs ran locally.

## Release recommendation

Keep the feature branch at `0.1.0`. After merge to `develop`, a separate reviewed
release-only decision may authorize `0.2.0`. Phase 1 does not authorize `1.0.0`,
runtime graph ownership, Architecture IR promotion, transactional authoring, or any
Phase 2 capability.
