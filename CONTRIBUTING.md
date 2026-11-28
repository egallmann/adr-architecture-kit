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

**Requirements:** Python 3.14+ (`requires-python >=3.14`; currently qualified 3.14.x; reference interpreter 3.14.7)

Node package work additionally requires Node 20+; use the peer binding guide in
[`packages/node/README.md`](packages/node/README.md) for its local commands and
qualification gates.

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

Keep the TDD loop repository-specific: write the smallest failing contract or
behavior test, implement the change, then run the relevant assurance gates.
Generic TDD tutorials are intentionally not maintained in this repository.

**Quality gates** (all must pass before merging):

| Gate | Command |
|------|---------|
| Test suite | `python -m pytest` |
| Coverage (≥80%) | `python -m pytest --cov=adr_kit --cov-report=term-missing --cov-fail-under=80` |
| Compatibility | `python scripts/check_compatibility_snapshots.py` |
| Version consistency | `python scripts/check_version_consistency.py` |
| Public SDK | `python -m pytest tests/test_public_sdk_contract.py tests/test_public_sdk_operations.py -q` |
| Quality debt | `python scripts/check_quality_ratchets.py` |
| Repository naming | `python scripts/check_repository_naming.py` |
| Governance | `adr governance-checks` |
| Schema parity | see below |

CI stratifies these checks by lifecycle. Pull requests run the explicit
developer/TDD fast suite, the broader semantic and SDK contract collection,
Rust source qualification, Node/TypeScript checks, governance, and quality
ratchets in **`.github/workflows/pr-feedback.yml`**. Native Rust tests and
WASM production check out the same exact commit and run independently. Host
jobs can start once the source-built WASM matches both tracked copies. Overall
assurance requires successful native tests, WASM production, and the required
consumer checks. The Windows developer bootstrap remains unqualified. Pushes to
`develop` run **`.github/workflows/develop-assurance.yml`**: the non-governance
behavioral/integration/cross-host Python suite with canonical coverage, plus the
governance-marked pytest assertions in the governance job. Together these lanes
exercise the complete Python assertion inventory; repository-state governance
commands, Python/Node parity, dependency, and quality assurance also remain
required. Full Windows/macOS source suites run weekly against the resolved
`develop` commit or on demand through
**`.github/workflows/portability-assurance.yml`**, and again during release
certification. Pushes to `main` run
**`.github/workflows/release-certification.yml`**, which also qualifies the exact
retained Python/npm bundle, packaged WASM identity, retained-wheel smoke tests,
fixed-epoch reproducibility, and benchmark determinism. Release qualification
therefore retains cross-platform evidence without spending the full OS-suite cost
on every ordinary develop push.
Tag publishers admit the retained bundle only after the exact-source main-push
certification and the durable authority-promotion evidence required by ADR-L-0040.

---

## Running Tests

```bash
# Developer/TDD fast suite (isolated behavior and contract tests)
python -m pytest -m fast --durations=10

# Focus one file or case
python -m pytest tests/test_schema_validation.py -q
python -m pytest -k "scope" -q

# Full source suite
python -m pytest --durations=30

# Full suite with canonical coverage gate
python -m pytest --durations=30 --cov=adr_kit --cov-report=term-missing --cov-fail-under=80

# PR fast/TDD plus semantic/source collections
python -m pytest -m fast --durations=10
python scripts/run_pr_feedback.py

# Governance pytest assertions and repository-state checks
python -m pytest -m governance --durations=30
adr governance-checks --skip-tests
```

Pytest registers `fast`, `integration`, `governance`, `crosshost`, and
`benchmark` assurance layers. Tests without an explicit layer remain in the
complete suite as `integration`; accidental multiple-layer classification fails
collection. Use `-m fast` only for the TDD loop, not as a replacement for the
complete suite or lifecycle gates. PR Feedback reports the fast suite's count,
slowest tests, and duration separately. CI reports test counts and slowest tests;
workflow job durations provide the lane-level timing record.

---

## Schema Parity

JSON Schemas exist in two locations that must stay in sync:

- `schema/v1.0/`, family-first `schema/authoring/`, `schema/architecture-discovery/`, `schema/normalized-model/`, `schema/governance/`, and `schema/evidence-attribution/` — canonical schema sources
- `src/adr_kit/schema/v1_0/` through `v1_6/` and `v2_0/` — bundled copies shipped with the package

Mirrors are **manual**: copy canonical JSON into the package tree and run `tests/test_package_schema_parity.py`. Do not use `scripts/generate_repository_schemas.py` for these package mirrors (that script is kernel-facing).

**Implementation attribution evidence:** 1.0/1.2 live in `schema/evidence-attribution/v1.1/implementation-attribution-evidence.schema.json`; canonical 1.5 and provisional preferred-producer 1.6 live in their corresponding `schema/evidence-attribution/` directories with packaged `v1_5` and `v1_6` mirrors. **`ste-spec`** only carries draft hand-off prose under `contracts/implementation-attribution-evidence/` until promotion—there is no JSON mirror to sync there yet (unlike Architecture IR).

CI verifies byte-level parity (`tests/test_package_schema_parity.py` and the
governance jobs in **`.github/workflows/pr-feedback.yml`** and
**`.github/workflows/integration-assurance.yml`**).

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
5. Review attribution scope without fabricating claims to increase coverage;
   evidence remains derived linkage, not architecture authority.

Pre-push runs contract guards always; **`adr attribution check`** runs when workspace evidence exists (otherwise skipped with a message).

Durable filenames, module names, contract identifiers, fixtures, and tests must
describe their domain capability, responsibility, or behavior. Delivery
sequencing belongs in issues, branches, PRs, and planning prose—not durable
implementation names. The naming policy rejects delivery labels such as
`slice_a`, `slice-c`, `hsg14`, `tranche-15`, `phase0`, `phase_2`, `phase-a`,
and `wave_3` in active paths and identifiers; the exact historical design
journals are allowlisted for provenance.

### System overview and unified compile

```bash
adr validate-system-overview

adr compile --mode normal
```

`adr compile` is an authoring-time and repository-discovery path. Runtime-owned machine artifacts belong in `ste-runtime`; see [`AUTHORING-SYSTEM.md`](AUTHORING-SYSTEM.md).

---

## Pre-push Hook

A pre-push hook runs a fast local safety check automatically:

```bash
python scripts/install_pre_push_hook.py
```

The fast hook checks repository naming, canonical-ID allocation, and byte
identity across the tracked semantic-core WASM artifacts. Generated-document
integrity and test suites remain in the full local bundle and PR CI.
The full local assurance bundle remains available when explicitly requested:

```bash
python scripts/run_local_pre_push_checks.py
```

That bundle validates generated-docs integrity and runs a **subset** of `pytest`, including **`tests/test_package_schema_parity.py`** — explicit fixture mappings must byte-match canonical `schema/...` artifacts to their `src/adr_kit/schema/v*_*` mirrors (the same contract enforced by the PR and integration governance workflows). It also runs **`tests/test_retrofit_contract_guards.py`**, **`tests/test_attribution_evidence_sync.py`**, README attribution-doc consistency, and the v1.5 semantic-attribution invariant tests (vocabulary/matrix parity, shim parity, 1.0/1.2 normalization, UUID resolution, decorator separation, dual-encode guard, and `next_id()` alias allocation). When workspace RECON evidence is present under **`.ste-workspace/state/adr-architecture-kit/`**, the script passes that file to **`adr attribution check --evidence`**; the CLI does not search `.ste-workspace` on its own.


---

## Submitting Changes

This repository uses a controlled feature → develop → release → main flow:

1. Branch from current `develop` for normal feature work
   (`feature/<short-name>`).
2. Follow the TDD methodology — write tests before implementation.
3. Ensure all quality gates pass locally.
4. Update `CHANGELOG.md` under `[Unreleased]`.
5. Open a feature pull request against `develop`. The fast PR gate is an early
   semantic/source signal; it does not replace develop integration assurance.
   The PR template will prompt you for the required checklist.
6. Release branches are cut from admitted `develop`, prepare package version /
   changelog only, and open a release PR against `main`.
7. `main` is publication/release admission. Create the annotated release tag only
   after exact-source Release Certification, authorized cohort promotion, and the
   durable evidence PR are complete; follow the ordered procedure below.
8. After both registries report the released version, synchronize the exact
   released `main` state back into `develop` through a reviewed post-release
   synchronization PR. The synchronization is not complete until the
   resulting `develop` push has passed Develop Assurance and the ancestry
   check confirms that `main` is contained in `develop`.

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
2. Bump **`version`** only in [`pyproject.toml`](pyproject.toml). This is the single
   manually edited package-version authority; do not hand-edit a second release version.
3. Synchronize the checked-in Node package metadata and lockfile from that authority:

   ```bash
   python scripts/sync_node_package_version.py --write
   ```

   The command updates `packages/node/package.json` and the root package version fields
   in `packages/node/package-lock.json`. CI and release-artifact qualification run the
   same command in `--check` mode and fail closed on drift. Runtime, CLI, SDK, and
   generated capability versions continue to resolve from the Python distribution
   authority.
4. Convert [`CHANGELOG.md`](CHANGELOG.md) `[Unreleased]` into a dated section for that
   version and restore an empty `[Unreleased]` heading.
5. Open a release pull request against `main`. After admission, wait for successful
   Release Certification on the exact resulting `main` push SHA. Retain its exact
   `release-bundle`; PR/develop qualification is not release admission.
6. Before tagging, dispatch `.github/workflows/authority-promotion.yml` on `main`
   with that certification run ID. The workflow must be present on the default
   branch; the release PR brings it onto `main` for the first use. Confirm the
   `semantic-authority-promotion` environment has required reviewers including an
   authorized `PROJECT.yaml` approver, permits the authorized owner to approve the
   run they dispatched, and disallows administrator bypass. Review the computed
   source/cohort statement and retained inventory before approving. The workflow
   verifies the actual approval and emits an external attestation artifact.
7. After the promotion workflow succeeds, record its exact attestation bytes in
   the evidence-only PR at `.github/authority-promotions/<main-source-sha>.json`.
   Review and merge that PR to `main`; it must not alter the certified source or
   retained bundle. This durable evidence is required before publication.
8. Only after the evidence PR is merged, create and push the annotated
   `v<project-version>` tag pointing to the exact certified `main` source SHA
   (which is an ancestor of the evidence commit). The tag publishers resolve the
   successful certification run and independently verify the retained bundle,
   durable promotion evidence, source, version, tag, and hashes before publishing.
   They do not rebuild packages. PyPI and npm publication remain separate jobs with
   their existing environment/OIDC controls.
9. Verify that both publisher workflows succeeded and that the registries expose
   the intended version. A workflow dispatch or tag event alone is not proof of
   publication. If a publish attempt fails, use its supported retry path against
   the same tag and retained certified bundle; never rebuild or retarget the tag.

10. Synchronize the released state back into `develop` after publication succeeds:

    ```bash
    git fetch origin main develop
    git switch -c post-release/<version> origin/develop
    git merge --no-ff origin/main -m "chore: synchronize main after <version>"
    git push -u origin post-release/<version>
    gh pr create --base develop --head post-release/<version> \
      --title "chore: synchronize develop after <version>"
    ```

    Wait for the PR checks, merge the synchronization PR with a merge commit, and
    then wait for the successful **develop `push`** Develop Assurance run on the
    resulting merge SHA. Verify the final state with:

    ```bash
    python scripts/verify_release_branch_sync.py \
      --main-ref origin/main \
      --release-ref v<version> \
      --develop-ref origin/develop \
      --expected-version <version>
    ```

    This step is required even when the release PR itself merged cleanly: release
    metadata and release-only governance fixes must not remain stranded on `main`.

### v0.13.0 consolidation scope

The v0.13.0 release follows accepted ADR-L-0042 and the owner-selected
lifecycle-governed consolidation path. It promises only capabilities demonstrated
by its released authority, public interfaces, and exact release evidence. It does
not claim completion of **Forward Semantic Execution Completion**: all 27 semantic
types, all 455 destination obligations, the 215 currently BLOCKED destinations,
and the objective's independent execution-qualification criteria remain in force.
The distribution cohort must be selected from released lifecycle authority only;
development candidates (AI 1.2–1.5, ACC 1.1–1.5, and NM 2.5) remain in canonical
`contracts/` sources and are excluded from wheel, sdist, npm, and the
certified/promoted cohort. Recompute and review the
actual release inventory for the release source; rehearsal counts or digests are not
substitutes for certification evidence.

Before starting the release, the owner must verify live GitHub environment and
publisher configuration. Repository documentation cannot prove reviewer settings,
bypass protection, or PyPI/npm Trusted Publisher state. The exact promotion
environment requirements and fail-closed recovery steps are documented in
[authority-promotion enforcement](docs/contributors/authority-promotion-enforcement.md).

Qualification evidence axes on a release-eligible `main` push:

- Ubuntu 3.14 complete suite + coverage
- Ubuntu 3.14 focused source/SDK compatibility
- Windows/macOS 3.14 complete suite (behavior/OS portability)
- Exact retained wheel on Ubuntu 3.14 and on Windows/macOS 3.14

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
resolves the successful `main` push run of `release-certification.yml`, downloads its
retained `node-dist` tarball, verifies its package name/version and contents,
and publishes that tarball without rebuilding. The npm version is checked
against `pyproject.toml`; `packages/node/package.json` and
`packages/node/package-lock.json` are synchronized from that authority by
`scripts/sync_node_package_version.py`; feature and `develop` runs never publish.

### One-time npm bootstrap

The npm organization `system-of-thought` must own the scope, and the human
maintainer performing this step must have package write access and account-level
2FA enabled. The package does not currently exist on the public registry, so
the first package creation is a human-authenticated exception to the normal
tag-only publisher:

1. From the exact retained `node-dist` tarball for the first release version,
   run `npm publish <qualified-tarball> --access public` while authenticated as
   the npm scope maintainer. Do not use a long-lived automation token. Do not
   manually alter the package version; it must already match `pyproject.toml`.
2. After the package exists, configure its npm Trusted Publisher either in the
   package settings UI or with npm CLI 11.15+:

   ```bash
   npm trust github @system-of-thought/adr-kit \
     --file publish-npm.yml \
     --repository egallmann/adr-architecture-kit \
     --environment npm \
     --allow-publish
   ```

   The exact values are: GitHub owner `egallmann`, repository
   `adr-architecture-kit`, workflow filename `publish-npm.yml` (filename only,
   not `.github/workflows/publish-npm.yml`), environment `npm`, package
   `@system-of-thought/adr-kit`, and allowed action `npm publish`.
3. Do not create a tag that would cause the tag publisher to attempt a second
   upload of the manually bootstrapped version. Start the normal release flow
   with the next not-yet-published package version after the bootstrap package
   and Trusted Publisher are confirmed.

The GitHub repository must contain an `npm` environment before tagged npm
publication. In repository Settings, Environments, configure `npm` with the
repository owner as required reviewer, permit self-review, and disable
administrator bypass. ADR Kit is a single-maintainer project: a second human
reviewer or collaborator is not required. The owner retains final release approval
authority. AI-assisted review and automated qualification provide evidence but
are not GitHub reviewer identities or cryptographic human approval.

These environment protections are repository release policy, not an npm Trusted
Publishing requirement. Successful exact-source certification and durable
owner-approved authority promotion evidence remain mandatory before publication.
Explicit owner authorization is required before promotion or publication. Apply
the same owner-review/self-review/bypass policy to `pypi`; retain the existing
`semantic-authority-promotion` protections.

Independently inspect registry account settings: owner `egallmann`, repository
`adr-architecture-kit`, workflow `publish-npm.yml`, environment `npm`, package
`@system-of-thought/adr-kit`; and workflow `publish-pypi.yml`, environment `pypi`,
project `adr-architecture-kit` for PyPI. PyPI requires account 2FA. Neither platform
requires a second human reviewer. See [npm Trusted Publishing](https://docs.npmjs.com/trusted-publishers/)
and [PyPI publisher configuration](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).
The workflows use OIDC (`id-token: write`) in the publication jobs and publish
verified retained artifacts without rebuilding or long-lived registry tokens.
Workflow declarations alone do not prove registry configuration.

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
