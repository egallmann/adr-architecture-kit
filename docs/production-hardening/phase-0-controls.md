# Phase 0 developer and release controls

Install the package before running tests so imports resolve through `adr_kit`, the same
namespace present in a wheel:

```bash
python -m pip install .[dev]
python -m pytest
python -m pytest --cov=adr_kit --cov-report=term-missing --cov-fail-under=80
```

Run the frozen compatibility, version, and debt controls with:

```bash
python scripts/check_compatibility_snapshots.py
python scripts/check_version_consistency.py
python scripts/check_quality_ratchets.py
```

Quality baselines contain normalized finding identities. Findings may be removed; new
identities or count increases fail. Do not refresh a baseline to make a regression pass.
New Phase 0 Python files are checked separately and must be Ruff, strict-mypy, and Black
clean. The baseline-defining tool versions are pinned in `pyproject.toml` (`ruff==0.15.15`,
`mypy==2.1.0`, and `black==26.5.1`) so dependency resolution cannot silently redefine
the measurements.

## Local release validation

```bash
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
python -m build --outdir python-dist
python scripts/release_manifest.py normalize-sdist \
  --sdist python-dist/adr_architecture_kit-<version>.tar.gz \
  --source-date-epoch "${SOURCE_DATE_EPOCH}"
python -m twine check python-dist/*
python scripts/release_manifest.py create \
  --dist-dir python-dist \
  --output release-manifest.json \
  --source-commit <full-commit> \
  --version <project-version>
python scripts/release_manifest.py verify \
  --dist-dir python-dist \
  --manifest release-manifest.json \
  --expected-source-commit <full-commit> \
  --expected-version <project-version> \
  --expected-tag v<project-version>
python scripts/test_installed_wheel.py --wheel <wheel-path>
```

The manifest requires exactly one wheel and one sdist and verifies filenames, sizes,
SHA-256 hashes, source commit, package version, and tag.

Release publishing downloads the retained `release-bundle` from the successful **main
`push`** ADR Governance qualification for the tagged SHA (not a tag-side rebuild; not a
PR or develop run). Python-version compatibility and OS portability are separate
evidence axes: Ubuntu owns the Python 3.11–3.14 focused compatibility and retained-wheel
Python matrix; Windows/macOS at Python 3.12 own complete-suite behavior portability and
exact retained-wheel OS portability via `scripts/test_installed_wheel.py`. The retained
wheel is not rebuilt per OS. Tag publication does not rerun platform qualification.
README/package-description portability remains part of qualification (coverage suite /
local pre-push), not publish requalification. GitHub Actions artifact retention means
tags must be cut while the qualifying artifact still exists; missing, expired, or
ambiguous bundles fail closed. Sdist normalization removes build-clock and owner
metadata using the source commit epoch before hashing. The privileged job never
rebuilds the bundle.

## 0.3.0 release finding: PyPI README link portability

**Observed failure:** GitHub-valid repository-relative README links became invalid
PyPI package-description links (for example
`https://pypi.org/project/adr-architecture-kit/0.3.0/docs/public-sdk.md`).

**Missing invariant:** Release qualification validated package metadata and artifacts
(`twine check`, retained-bundle identity) but did not validate README link portability
across rendering surfaces.

**Resulting control:** The PyPI-facing package description (`project.readme`) must
contain only link forms valid independently of GitHub repository-relative rendering
(`INV-0083`; enforced by `tests/test_readme_pypi_portability.py` in the local pre-push
bundle and the canonical qualification coverage suite).

**Future release-protocol implication:** README/package-description portability is part
of release qualification. The deferred `capture-release-protocol` contributor skill
must consume this observed invariant as evidence (skill implementation remains separate
future work; see `ROADMAP.md`).

## Benchmarks

The full baseline command is:

```bash
python benchmarks/phase0.py \
  --corpus all \
  --sizes 10,100,500 \
  --warmups 1 \
  --repeats 5 \
  --json-out <path>
```

Timing is evidence, not a Phase 0 CI threshold. CI runs a small functional smoke and
requires deterministic repeated fingerprints. Historical benchmark measurements are
retained in Git history; this document keeps the current benchmark method and release
controls without treating a phase snapshot as durable authority.
