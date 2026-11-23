# Release and quality controls

Release qualification validates the retained artifacts that were produced from
the exact source commit. Publishing promotes that retained bundle; it must not
rebuild a different bundle at tag or publish time.

## Required controls

Release qualification covers compatibility, version, quality, package,
governance, retained-wheel installation, platform portability, deterministic
generation, and package-description link portability. README links intended for
PyPI or npm must be absolute or otherwise valid outside GitHub
repository-relative rendering.

The release manifest must contain exactly one wheel and one source distribution
and verify filenames, sizes, hashes, source commit, project version, and tag.
Do not refresh a compatibility or quality baseline merely to hide a regression.
Change canonical inputs first, regenerate derived artifacts with owned tooling,
and require a deterministic second run before promotion.

## Local checks

```bash
python scripts/run_local_pre_push_checks.py
python scripts/check_compatibility_snapshots.py
python scripts/check_version_consistency.py
python scripts/check_quality_ratchets.py
adr governance-checks
```

The pre-push bundle is a fast local subset. Develop and release assurance remain
authoritative for the full Python suite, coverage, platform qualification,
retained artifacts, and publication gates.

## Authority-cohort promotion enforcement

Accepted ADR-L-0040 requires a deterministic inventory of every authority actually packaged,
including embedded WASM and resource-qualified dependencies, followed by an external
human promotion attestation for precisely that finalized cohort. A mismatch requires
a newly qualified source/bundle; retained artifacts cannot be stripped or edited.
The proposal preserves main-push qualification and build-once promotion-only
publication. See [the specification](semantic-contract-lifecycle.md).

PR A supplied the closed specification. The operational checkpoint now scans the
actual package/WASM payloads and independently enforces the exact retained cohort
and external human promotion evidence in both publishers. See the
[approval, durable-evidence and publisher procedure](authority-promotion-enforcement.md).
This implementation does not itself approve or promote any authority.

## v0.13.0 consolidation boundary

The owner-selected v0.13.0 release scope is the lifecycle-governed consolidation
path established by accepted ADR-L-0042. A package release number does not certify
Forward Semantic Execution Completion. That separate milestone retains the all-27
type objective, its 455 destination obligations (including all 215 currently
BLOCKED destinations), successor authority qualification/promotion, public protocol
conformance, approved current SCS, and independent end-to-end qualification.

The v0.13 distribution and certified promotion cohort must include released
semantic authority only. AI 1.2–1.5, ACC 1.1–1.5, and NM 2.5 remain canonical
development candidates in `contracts/` and are excluded from wheel, sdist, npm,
and publisher inventory. Release
Certification must scan the actual built archives and produce a fresh exact cohort;
REL-3b rehearsal counts and hashes are not certification evidence. The first real
promotion remains gated by the protected human approval and durable evidence PR in
[the promotion procedure](authority-promotion-enforcement.md).
