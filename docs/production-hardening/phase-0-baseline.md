# Phase 0 production-hardening baseline

Date: 2026-08-05  
Baseline commit: `48221bdd13ab35c01f6c5cbaae6dc3bcebd71873`  
Branch: `feature/adr-kit-production-hardening`  
Package version: `0.1.0`

This document freezes the evidence accepted by the Phase 0 production-hardening
plan. A failing condition listed here is pre-existing debt or a known release gap;
it is not permission to ignore a new regression. Phase 0 controls must preserve the
measurement, allow debt reduction, and fail on new findings or count increases.

## Verified baseline

| Area | Baseline evidence | Classification |
| --- | --- | --- |
| Full test suite | 353 passed, 6 skipped; approximately 5m19s | Passing baseline |
| Canonical package coverage | 83% when measured with `--cov=adr_kit` after canonical namespace loading | Truthful passing baseline |
| Documented coverage command | `--cov=adr_kit` reported 3% while tests mixed `src.adr_kit` and `adr_kit` | Misleading check; must be replaced |
| Pre-push bundle | 60 passed plus generated-artifact and attribution checks; approximately 43s | Passing baseline |
| Ruff 0.15.15 | 68 findings | Pre-existing debt; ratchet required |
| strict mypy 2.1.0 | 370 errors | Pre-existing debt; ratchet required |
| Black 26.5.1 | 105 unformatted tracked Python files | Pre-existing debt; ratchet required |
| Dependency audit | No known project dependency vulnerabilities | Passing baseline |
| Clean wheel | Install, documented imports, CLI, schemas, templates, and ADR validation succeeded | Passing but not automated across supported versions |
| ADR validation | No errors; two warnings | Pre-existing warnings, not regressions |

The release artifacts produced from the baseline were:

| Artifact | SHA-256 |
| --- | --- |
| Wheel | `728A52DEA40B8E41E98B61BEEC190DB2844D39115BF4D57DA885EC7F0FA8104A` |
| Sdist | `2658FDCA33CF1E96C854E5CD194EF86A16E658F1A91998DBDDBE6F197EB8656D` |

Those hashes identify the baseline build only. Phase 0 must not alter a future
baseline merely to conceal a reproducibility or release-promotion failure.

## Source and packaging observations

- The checkout is clean and `HEAD`, `develop`, and `origin/develop` all resolve to
  the baseline commit.
- Thirty-six tracked test or maintenance-script files import `src.adr_kit`, so a
  source checkout can bypass installed-package behavior.
- `adr_kit.__version__`, `[project].version`, installed package metadata, and
  `adr --version` all currently report `0.1.0`, but no drift guard exists.
- `pyproject.toml` claims Python 3.11 and 3.12 only. Python 3.13 and 3.14 cannot be
  claimed until source and retained-wheel jobs pass for all four versions.
- CI builds a distribution in its artifact-smoke job, while the publishing workflow
  separately rebuilds on `main`. There is no retained-artifact manifest or promotion
  verification.
- `twine` is not part of the development tool set, so package metadata validation is
  not a standard gate.

## Known contradictions

- Documentation calls surfaces “stable public v1” while the distribution is a
  pre-1.0 Alpha at `0.1.0`. ADR schema v1.0 stability and package SemVer stability
  are separate promises and must be described separately.
- `ArchModel` is documented as compiler-internal but is exported from
  `adr_kit.compiler`. Phase 0 preserves that import for compatibility while
  classifying it as de facto public/internal-deprecated-for-dependency use.
- The version exists as literals in project metadata and runtime code. Runtime
  behavior remains unchanged in Phase 0; metadata-derived runtime versioning is
  deferred to Phase 1.
- Physical ADR wording calls the authoring-time implementation a “runtime,” which
  blurs its boundary with `ste-runtime`. Phase 0 corrects the responsibility wording
  without renaming CLI commands or adding runtime capability.
- Tests executed from the source tree can pass with `src.adr_kit` imports even when
  an installed wheel is incomplete. Phase 0 makes `adr_kit` the only allowed import
  namespace and adds an isolated installed-consumer harness.

## Release gaps Phase 0 must close

- supported-version source and retained-wheel matrices;
- truthful source-namespace coverage at 80% or greater;
- Ruff, strict-mypy, and Black no-regression ratchets;
- build-once wheel/sdist manifest creation and strict verification;
- tag/package-version/source-commit equality checks;
- metadata checking with Twine;
- installed-wheel imports, CLI, external validation/compilation, schemas, and templates;
- reproducibility checks with a fixed `SOURCE_DATE_EPOCH`;
- deterministic benchmark smoke coverage;
- publish workflow contract tests proving that promotion never rebuilds.

## Scope boundary

Phase 0 is production engineering around the existing authoring/compiler package.
It does not authorize an SDK facade, new root exports, schema promotion, graph or
normalized-model redesign, transactional authoring, Assembler implementation, MCP,
runtime extraction, rules, substrate, admission, or any other Phase 1+ capability.
