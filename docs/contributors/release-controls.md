# Release and quality controls (contributor)

Durable release-quality controls live in this repository's Git history. The public
`docs/` spine no longer indexes phase closeout logs.

## Durable controls

- Quality, wheel, coverage, and release-manifest gates: [`../production-hardening/developer-and-release-controls.md`](../production-hardening/developer-and-release-controls.md)
- Frozen Python/CLI compatibility inventory: [`../production-hardening/public-surface-inventory.md`](../production-hardening/public-surface-inventory.md)
- Compatibility snapshots: `contracts/compatibility/`
- Local pre-push bundle: `python scripts/run_local_pre_push_checks.py`

## Historical execution records

Completed phase baselines, closeouts, and one-time benchmark captures are preserved
in Git history rather than the active documentation tree. Current controls and the
compatibility inventory above are the maintained references.

Semantic attribution remains a separate evidence line and does not authorize
unrelated graph or transactional-authoring capability. Consult accepted ADRs and
current issue/PR discussions for active planning.
