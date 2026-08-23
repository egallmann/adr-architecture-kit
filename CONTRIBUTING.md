# Contributing to adr-architecture-kit

Thank you for your interest in contributing. This document covers how to set up your environment, the development methodology, and the process for submitting changes.

## Table of Contents

- [Development Setup](#development-setup)
  - [Repository maintenance notes](#repository-maintenance-notes)
- [Development Methodology](#development-methodology)
- [Running Tests](#running-tests)
- [Schema Parity](#schema-parity)
- [Governance Checks](#governance-checks)
  - [System overview and unified compile](#system-overview-and-unified-compile)
- [Pre-push Hook](#pre-push-hook)
- [Submitting Changes](#submitting-changes)
- [Publishing to PyPI (maintainers)](#publishing-to-pypi-maintainers)
- [Publishing to npm (maintainers)](#publishing-to-npm-maintainers)
- [ADR Authority](#adr-authority)

---

## Development Setup

**Requirements:** Python 3.11–3.14

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

### Repository maintenance notes

- [`README.md`](README.md) at the repository root is maintained manually.
- [`SYSTEM-OVERVIEW.md`](SYSTEM-OVERVIEW.md) is **generated**; edit its template/generator in `src/adr_kit/` rather than hand-editing the committed artifact.
- This repository is expected to work as a **standalone checkout**. The public Architecture IR schema is mirrored at [`contracts/architecture-ir/architecture-ir.schema.json`](contracts/architecture-ir/architecture-ir.schema.json) (see [`contracts/architecture-ir/MIRROR.md`](contracts/architecture-ir/MIRROR.md)); some tests additionally compare against a sibling `ste-spec` checkout when present.
- If **`git ls-files -v`** shows **`H`** for paths you have edited locally, **`assume-unchanged`** is enabled. Git may omit those paths from **`git status`** until you run **`git update-index --no-assume-unchanged -- <paths>`**. That hides real drift (for example **`schema/`** vs **`src/adr_kit/schema/`** parity) against a fresh clone or CI — clear it before you commit schema or generated-artifact fixes. Avoid blanket-setting assume-unchanged on the whole repository when doing release work (`tests/test_package_schema_parity.py` helps catch bundled drift).

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
| Test suite | `python -m pytest` |
| Coverage (≥80%) | `python -m pytest --cov=adr_kit --cov-report=term-missing --cov-fail-under=80` |
| Compatibility | `python scripts/check_compatibility_snapshots.py` |
| Version consistency | `python scripts/check_version_consistency.py` |
| Public SDK | `python -m pytest tests/test_public_sdk_contract.py tests/test_public_sdk_operations.py -q` |
| Quality debt | `python scripts/check_quality_ratchets.py` |
| Governance | `adr governance-checks` |
| Schema parity | see below |

CI enforces every row above, source-installed tests on Python 3.11–3.14,
dependency audit, build-once release artifacts, retained-wheel smoke tests on all
four Python versions, fixed-epoch reproducibility, and benchmark determinism.

---

## Running Tests

```bash
# Full test suite
pytest

# With coverage report
python -m pytest --cov=adr_kit --cov-report=term-missing --cov-fail-under=80

# Specific test file
pytest tests/test_schema_validation.py -v
```

---

## Schema Parity

JSON Schemas exist in two locations that must stay in sync:

- `schema/v1.0/`, family-first `schema/authoring/`, `schema/architecture-discovery/`, `schema/normalized-model/`, `schema/governance/`, and `schema/evidence-attribution/` — canonical schema sources
- `src/adr_kit/schema/v1_0/` through `v1_6/` and `v2_0/` — bundled copies shipped with the package

Mirrors are **manual**: copy canonical JSON into the package tree and run `tests/test_package_schema_parity.py`. Do not use `scripts/generate_repository_schemas.py` for these package mirrors (that script is kernel-facing).

**Implementation attribution evidence:** 1.0/1.2 live in `schema/evidence-attribution/v1.1/implementation-attribution-evidence.schema.json`; canonical 1.5 and provisional preferred-producer 1.6 live in their corresponding `schema/evidence-attribution/` directories with packaged `v1_5` and `v1_6` mirrors. **`ste-spec`** only carries draft hand-off prose under `contracts/implementation-attribution-evidence/` until promotion—there is no JSON mirror to sync there yet (unlike Architecture IR).

CI verifies byte-level parity (`tests/test_package_schema_parity.py` and **`Check package schema parity`** in **`.github/workflows/adr-governance.yml`**).

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

When touching implementation linkage or attribution evidence pipelines, smoke-check representative files with **`adr attribution check`** (optional `adr attribution coverage` for corpus-vs-evidence summaries); see README **Implementation linkage** for flags and evidence path defaults.

**Attribution retrofit closure workflow** (multi-repo STE workspace):

1. From **`ste-runtime`**, refresh derived evidence into the workspace-root
   `.ste-workspace/` directory. The runtime must never write into this repository.
2. Evidence path: `.ste-workspace/state/adr-architecture-kit/attribution/implementation-attribution-evidence.yaml`
3. From **`adr-architecture-kit`**: `adr attribution check --scope . --evidence <path above>`
4. Contract guards: `pytest tests/test_retrofit_contract_guards.py tests/test_attribution_evidence_sync.py -q`
5. Negative-space sign-off: [`docs/attribution-negative-space.md`](docs/attribution-negative-space.md)

Pre-push runs contract guards always; **`adr attribution check`** runs when workspace evidence exists (otherwise skipped with a message).

### System overview and unified compile

```bash
adr validate-system-overview

adr compile --mode normal
```

`adr compile` is an authoring-time and repository-discovery path. Runtime-owned machine artifacts belong in `ste-runtime`; see [`AUTHORING-SYSTEM.md`](AUTHORING-SYSTEM.md).

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

That bundle validates generated-docs integrity and runs a **subset** of `pytest`, including **`tests/test_package_schema_parity.py`** — explicit fixture mappings must byte-match canonical `schema/...` artifacts to their `src/adr_kit/schema/v*_*` mirrors (same check as **`Check package schema parity`** in **`.github/workflows/adr-governance.yml`**). It also runs **`tests/test_retrofit_contract_guards.py`**, **`tests/test_attribution_evidence_sync.py`**, README attribution-doc consistency, and the v1.5 semantic-attribution invariant tests (vocabulary/matrix parity, shim parity, 1.0/1.2 normalization, UUID resolution, decorator separation, dual-encode guard, and `next_id()` alias allocation). When workspace RECON evidence is present under **`.ste-workspace/state/adr-architecture-kit/`**, the script passes that file to **`adr attribution check --evidence`**; the CLI does not search `.ste-workspace` on its own.


---

## Submitting Changes

This repository uses a controlled feature → develop → release → main flow:

1. Branch from current `develop` for normal feature work
   (`feature/<short-name>`).
2. Follow the TDD methodology — write tests before implementation.
3. Ensure all quality gates pass locally.
4. Update `CHANGELOG.md` under `[Unreleased]`.
5. Open a feature pull request against `develop`. The PR template will prompt
   you for the required checklist.
6. Release branches are cut from admitted `develop`, prepare package version /
   changelog only, and open a release PR against `main`.
7. `main` is publication/release admission. Create the release tag only after
   the release PR is admitted to `main`.

For non-trivial changes, consider opening an issue first to discuss the approach.

---

## Publishing to PyPI (maintainers)

Releases are published with **Trusted Publishing** (OpenID Connect): GitHub proves the workflow run to PyPI; you do **not** store a PyPI password or API token in repository secrets.

Official background: [Publishing package distribution releases using GitHub Actions](https://packaging.python.org/en/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/) (Python Packaging User Guide).

### One-time linking: PyPI ↔ GitHub

1. **PyPI account** — Enable **2FA** on [pypi.org](https://pypi.org) (required to upload).
2. **Trusted publisher on PyPI** — While logged into PyPI:
   - Open **Account settings** → **Publishing** (or your project’s publishing settings after the first upload).
   - **Add a new pending publisher** → **GitHub** as the provider.
   - **PyPI project name:** `adr-architecture-kit` (must match `[project].name` in [`pyproject.toml`](pyproject.toml), *not* `adr-kit` or the import name `adr_kit`).
   - **Owner:** `egallmann` (or your GitHub user/org).
   - **Repository name:** `adr-architecture-kit`.
   - **Workflow name:** `publish-pypi.yml` (must match [`.github/workflows/publish-pypi.yml`](.github/workflows/publish-pypi.yml) — not `workflow.yml`).
   - **Environment name:** `pypi` (must match the workflow job’s `environment:` and a GitHub **Environment** you create below).
3. **GitHub Environment** — In the repo on GitHub: **Settings** → **Environments** → **New environment** → name **`pypi`**. You can leave protection rules empty at first, or add required reviewers for extra safety.
4. **Save** the pending publisher on PyPI (after the workflow and environment exist on the default branch, or the first publish may be rejected).

The **link** is that PyPI trusts *that GitHub repo + that workflow file* to upload the **distribution name** `adr-architecture-kit`. You do not paste a PyPI token into GitHub for this flow.

### Ship a version

1. Cut a `release/<version>` branch from admitted `develop`.
2. Bump **`version`** only in [`pyproject.toml`](pyproject.toml). Runtime, CLI, and SDK
   versions resolve from distribution metadata; do not add another version literal.
3. Convert [`CHANGELOG.md`](CHANGELOG.md) `[Unreleased]` into a dated section for that
   version and restore an empty `[Unreleased]` heading.
4. Open a release pull request against `main`. After admission, **wait for the successful
   ADR Governance `push` run on that `main` commit** (release-eligible qualification).
5. Only then create the exact tag `v<project-version>` (for example, `v0.4.0`) on that
   admitted `main` commit while the qualifying `release-bundle` artifact is still retained.
6. The tag workflow is promotion-only: it resolves the successful **main `push`** ADR
   Governance run for the tagged SHA, downloads that exact retained bundle, verifies
   source commit / package version / tag / hashes, and publishes without rebuilding or
   re-running pytest, coverage, governance, OS matrices, or the retained-wheel matrix.
   PR and develop qualification runs are **not** release-eligible, even for the same SHA.

Qualification evidence axes on a release-eligible `main` push:

- Ubuntu 3.12 complete suite + coverage
- Ubuntu 3.11–3.14 focused source/SDK compatibility
- Windows/macOS 3.12 complete suite (behavior/OS portability)
- Exact retained wheel on Ubuntu 3.11–3.14 and on Windows/macOS 3.12

The workflow does not publish on a branch push or manual dispatch. The first
successful tagged upload creates the PyPI project if it does not exist.

### After publish

In a clean virtual environment:

```bash
pip install adr-architecture-kit
adr --help
```

### Optional: TestPyPI first

To practice uploads, configure a second workflow or `repository-url` for TestPyPI as in [Using TestPyPI](https://packaging.python.org/en/guides/using-testpypi/); not required for production once you trust the flow.

## Publishing to npm (maintainers)

The scoped package `@system-of-thought/adr-kit` is published by
`.github/workflows/publish-npm.yml` only for an exact `v*` tag. The workflow
resolves the successful `main` push run of `adr-governance.yml`, downloads its
retained `node-dist` tarball, verifies its package name/version and contents,
and publishes that tarball without rebuilding. The npm version is checked
against `pyproject.toml`; feature and `develop` runs never publish.

Before the first release, configure npm Trusted Publishing for package
`@system-of-thought/adr-kit` with GitHub owner `egallmann`, repository
`adr-architecture-kit`, workflow `publish-npm.yml`, and GitHub environment
`npm`. The package must be available for public scoped publication. The
workflow uses GitHub OIDC (`id-token: write`) and stores no npm token.

---

## ADR Authority

Architecture decisions are encoded in YAML ADRs under `adrs/`. Before making structural changes to the library, check whether a relevant ADR or invariant governs the area:

```bash
# List ADRs as entities from the discovery bundle
adr entities list --type adr

# View a specific entity (e.g. an ADR record) by ID
adr entities get ADR-L-0001
```

If your change requires a new architectural decision, author a Logical ADR (`ADR-L`) first (structured input YAML → generated artifact under `adrs/logical/`):

```bash
adr generate-logical --input path/to/logical-spec.yaml --output adrs/logical/ADR-L-xxxx-my-decision.yaml
```

See [`docs/contributors/logical-adr-guide.md`](docs/contributors/logical-adr-guide.md) for authoring guidance.
