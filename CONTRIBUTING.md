# Contributing to adr-architecture-kit

Thank you for your interest in contributing. This document covers how to set up your environment, the development methodology, and the process for submitting changes.

## Table of Contents

- [Development Setup](#development-setup)
- [Development Methodology](#development-methodology)
- [Running Tests](#running-tests)
- [Schema Parity](#schema-parity)
- [Governance Checks](#governance-checks)
- [Pre-push Hook](#pre-push-hook)
- [Submitting Changes](#submitting-changes)
- [ADR Authority](#adr-authority)

---

## Development Setup

**Requirements:** Python 3.11+

```bash
# Clone the repository
git clone https://github.com/egallmann/adr-architecture-kit.git
cd adr-architecture-kit

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# Install the package with dev extras
pip install -e ".[dev]"
```

The `adr` CLI is registered automatically:

```bash
adr --help
```

---

## Development Methodology

This project uses **Test-Driven Development (TDD)** as declared project authority in [`PROJECT.yaml`](PROJECT.yaml) (authority: `ADR-L-0003`).

The workflow is **Red → Green → Refactor**:

1. Write a failing test that specifies the desired behavior.
2. Write the minimum implementation to make it pass.
3. Refactor without changing external behavior.

See [`docs/contributors/tdd-workflow.md`](docs/contributors/tdd-workflow.md) for detailed guidance and rationale.

**Quality gates** (all must pass before merging):

| Gate | Command |
|------|---------|
| Test suite | `pytest` |
| Coverage (≥80%) | `pytest --cov=adr_kit --cov-report=term-missing` |
| Lint | `ruff check src/ tests/` |
| Type check | `mypy src/` |
| Format | `black --check src/ tests/` |
| Governance | `adr governance-checks` |
| Schema parity | see below |

---

## Running Tests

```bash
# Full test suite
pytest

# With coverage report
pytest --cov=adr_kit --cov-report=term-missing

# Specific test file
pytest tests/test_schema_validation.py -v
```

---

## Schema Parity

JSON Schemas exist in two locations that must stay in sync:

- `schema/v1.0/` and `schema/v1.1/` — canonical schema sources
- `src/adr_kit/schema/v1_0/` and `src/adr_kit/schema/v1_1/` — bundled copies shipped with the package

CI verifies byte-level parity. If you update schemas, regenerate the bundled copies:

```bash
python scripts/generate_repository_schemas.py
```

Then verify:

```bash
pytest tests/test_kernel_schema_fixture_sync.py -v
```

---

## Governance Checks

The project includes self-governing validation:

```bash
# Full governance check (ADR cross-references, generated docs, system overview)
adr governance-checks

# Validate generated documentation integrity
adr validate-generated-docs

# Validate PROJECT.yaml project metadata
adr validate-project-metadata

# Runtime hygiene (dependency audit, deprecations)
python scripts/check_runtime_hygiene.py
```

---

## Pre-push Hook

A pre-push hook runs the core local checks automatically:

```bash
python scripts/install_pre_push_hook.py
```

Or run the checks manually before pushing:

```bash
python scripts/run_local_pre_push_checks.py
```

---

## Submitting Changes

1. Fork the repository and create a branch from `main`.
2. Follow the TDD methodology — write tests before implementation.
3. Ensure all quality gates pass locally.
4. Update `CHANGELOG.md` under `[Unreleased]`.
5. Open a pull request against `main`. The PR template will prompt you for the required checklist.

For non-trivial changes, consider opening an issue first to discuss the approach.

---

## ADR Authority

Architecture decisions are encoded in YAML ADRs under `adrs/`. Before making structural changes to the library, check whether a relevant ADR or invariant governs the area:

```bash
# List all ADRs
adr list

# View a specific ADR
adr show ADR-L-0001
```

If your change requires a new architectural decision, author a Logical ADR (`ADR-L`) first:

```bash
adr new --type logical "My Decision Title"
```

See [`docs/contributors/logical-adr-guide.md`](docs/contributors/logical-adr-guide.md) for authoring guidance.
