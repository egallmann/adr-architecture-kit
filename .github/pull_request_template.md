## Summary

Brief description of what this PR changes and why.

Closes #<!-- issue number, if applicable -->

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor / internal improvement
- [ ] Documentation
- [ ] Schema / model change
- [ ] Other:

## Checklist

- [ ] Tests written (TDD: tests added before or alongside implementation — `ADR-L-0003`)
- [ ] `pytest` passes locally
- [ ] Coverage does not decrease below 80%
- [ ] `ruff check src/ tests/` passes
- [ ] `mypy src/` passes
- [ ] `black --check src/ tests/` passes
- [ ] `adr governance-checks` passes
- [ ] Schema parity maintained (`schema/` and `src/adr_kit/schema/` are in sync)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`

**CI note:** GitHub Actions enforces ADR validation, `adr governance-checks` (including `pytest`), generated-docs checks, system overview validation, runtime hygiene, and schema parity. Coverage, `ruff`, `mypy`, and `black` are **strongly recommended locally** but are not separate CI jobs—see [CONTRIBUTING.md](CONTRIBUTING.md#development-methodology).

## ADR Traceability

If this PR implements or modifies behavior governed by an ADR or invariant, list them here (e.g. `ADR-L-0002 INV-0015`). If a new architectural decision is required, note whether an ADR has been authored or is planned.

## Notes for Reviewers

Any areas of particular interest, open questions, or known limitations.
