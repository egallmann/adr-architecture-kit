# Release and quality controls (contributor)

Durable release-quality controls live in this repository's Git history. The public
`docs/` spine no longer indexes phase closeout logs.

## Durable controls

- Quality, wheel, coverage, and release-manifest gates: [`../production-hardening/phase-0-controls.md`](../production-hardening/phase-0-controls.md)
- Frozen Python/CLI compatibility inventory: [`../production-hardening/public-surface-inventory.md`](../production-hardening/public-surface-inventory.md)
- Compatibility snapshots: `contracts/compatibility/`
- Local pre-push bundle: `python scripts/run_local_pre_push_checks.py`

## Phase logs (not public spine)

These files remain in Git for history and are not linked from the public docs index:

- `docs/production-hardening/phase-0-baseline.md`
- `docs/production-hardening/phase-1-*.md`
- `docs/production-hardening/phase-2-*.md`
- `docs/production-hardening/benchmark-baseline.md`

v1.5 semantic attribution does not reopen Phase 3 GraphProjectionBundle. See [`../../ROADMAP.md`](../../ROADMAP.md).
