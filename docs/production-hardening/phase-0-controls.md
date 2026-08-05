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
clean.

## Local release validation

```bash
python -m build --outdir python-dist
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
SHA-256 hashes, source commit, package version, and tag. Release publishing downloads
and re-verifies that retained bundle. The privileged job never rebuilds it.

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
requires deterministic repeated fingerprints.
