# 2026 production-hardening decision journal

Status: Phase 0 implementation authorized  
Authority baseline: `48221bdd13ab35c01f6c5cbaae6dc3bcebd71873`

## Problem

The kit has meaningful tests and a usable wheel, but its production claims are not
yet backed by a coherent artifact-promotion chain. Source-tree import leakage makes
coverage and packaging evidence ambiguous; existing style and typing debt cannot be
made immediately clean without broadening scope; publishing rebuilds instead of
promoting the artifact that was tested; and the documentation mixes ADR schema
versioning with package compatibility language.

## Evidence considered

- 353 passing tests and 6 skips establish behavior worth preserving.
- Canonical namespace coverage is 83%; the 3% result was a namespace artifact.
- The existing Ruff, mypy, and Black debt is measurable and predates this branch.
- A baseline wheel works for documented imports, CLI, schemas, templates, validation,
  and compilation, but the evidence is manual and not matrixed.
- Current publishing builds again inside the privileged publish job.
- The five authority ADRs describe testing, compiler, repository, and system
  boundaries but do not yet require the Phase 0 production controls.

## Objections and disposition

| Objection | Decision |
| --- | --- |
| “Production hardening should wait for package 1.0.” | Rejected. Engineering quality and a SemVer compatibility declaration are independent. |
| “Make all legacy lint/type/format debt green now.” | Rejected for Phase 0. Truthful no-regression ratchets prevent new debt without turning hardening into a repository-wide rewrite. |
| “Expose a cleaner facade while inventorying the API.” | Deferred. A new facade, result type, root export, or SDK is Phase 1+. |
| “Resolve the `ArchModel` export contradiction by removing it.” | Rejected for Phase 0 compatibility. Preserve the import, classify it honestly, and keep new consumers on the repository boundary. |
| “Build again immediately before publishing for safety.” | Rejected. Rebuilding breaks artifact identity. Verify and promote the exact retained bundle instead. |
| “Use benchmark timing thresholds in CI.” | Rejected for the first baseline. Environment-sensitive timing remains evidence; CI checks function and determinism only. |

## Decisions

1. Amend canonical ADR authority before implementation or derived-output refresh.
2. Install the project before tests and prohibit `src.adr_kit` imports in tracked
   tests and maintenance scripts.
3. Enforce canonical `adr_kit` coverage at 80%, preserving margin below the truthful
   83% baseline.
4. Store normalized Ruff and mypy finding identities plus the Black unformatted-file
   set. Permit removals; reject additions and count increases. New Phase 0 Python
   files must be clean under all three tools.
5. Preserve runtime `__version__ == "0.1.0"` while checking it against project
   metadata, installed metadata, and the CLI. Defer `importlib.metadata` as the
   runtime source of truth to Phase 1.
6. Build one wheel and one sdist, create a manifest containing commit, version,
   filenames, sizes, and SHA-256 hashes, and make strict re-verification the boundary
   before publishing.
7. Test the selected wheel from a clean venv with source-path leakage removed.
8. Claim Python 3.11–3.14 only when both source-installed and retained-wheel jobs pass.
9. Make reproducibility a separate fixed-epoch check; do not rebuild during release
   promotion.
10. Add deterministic benchmark scaffolding without performance gates.

## Authority review

- `ADR-L-0003` owns release-artifact testing, supported-version CI, coverage, and
  quality no-regression controls.
- `ADR-L-0013` keeps `ArchitectureRepository` and `NormalizedArchitectureModel` as
  the current consumer seam, keeps `ArchModel` internal, and defers a narrow facade.
- `ADR-PC-0003` describes compiler implementation as internal while preserving CLI
  compatibility.
- `ADR-PC-0004` records the future facade direction without creating it or changing
  the normalized model.
- `ADR-PS-0002` is an authoring/compiler system and explicitly excludes Assembler,
  runtime extraction, rules, substrate, admission, MCP, and LLM responsibilities.

No new ADR is required: the change tightens existing accepted or proposed boundaries
without creating a new architectural capability.

## Explicit deferrals

Graph bundles, assertion identity, entity or schema expansion, topology identity,
bindings, transactional authoring, SDK/API facade work, replacement compilation
results, Assembler behavior, MCP, LLM integration, runtime observation, rules,
substrate, and admission remain outside Phase 0.

## Phase 1 disposition

Phase 1 subsequently authorized and implemented the narrow `adr_kit.api` facade and
metadata-first runtime version authority. The other deferrals remain in force. See
[the Phase 1 design journal](2026-phase-1-public-sdk.md) and
The phase closeout is preserved in Git history rather than as a current active-tree
document.

## Lock readiness

The decision set is ready to lock when the five ADR amendments validate with cross
references and their generated projections reproduce byte-for-byte on a second run.
Implementation is ready to close when every final-validation command passes, the
release workflow promotes without rebuilding, quality measurements remain truthful,
and a diff audit finds no deferred capability.

## Closeout criteria

The implementation closeout must enumerate changed files and amended ADRs, controls
added, baseline and final measurements, exact validation commands and results,
remaining gaps, explicit non-goal confirmation, and a Phase 1 readiness recommendation.
