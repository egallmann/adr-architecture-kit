# Projection v3 — Authority Substrate Promoted

**Disposition:** `AUTHORITY_SUBSTRATE_PROMOTED`  
**Branch:** `fix/documentation-projection-defects`  
**Baseline develop SHA:** `589432cc0e2a360e12de43179235af7917d38557`  
**Promotion date:** 2026-08-28

## Minted authority identities

| Alias | Document UUID |
|-------|---------------|
| ADR-L-0025 | `01a048d8-454a-7464-bcaa-718e58dfb9c2` |
| ADR-PC-0008 | `01a048d8-454a-7464-bcaa-718fa77bed6a` |

## Gate evidence

| Gate | Result | Evidence |
|------|--------|----------|
| **A** — Supported-version logical ADRs | PASS | `adr validate`: 30 files OK; 6 v1.5 PS/PC expected failures only |
| **B** — v1.5 authority documents | PASS | `tests/test_authoring_v15_contract.py` (13 passed) including promoted PS/PC sources |
| **C** — v2.2 contract | PASS | v2.2 shape fixtures in `tests/test_authoring_v15_contract.py` |
| **D** — Production parser gap | OPEN | `adr validate` rejects `schema_version: "1.5"` — implementation plan scope |

## Reference closure (canonical sources)

- Zero `ADR-P-000[1-4]` and zero retired P document UUIDs in `adrs/logical`, `adrs/physical-system`, `adrs/physical-component`, `PROJECT.yaml` (historical retirement-map prose excepted).
- `adrs/physical/` generic ADR-P sources removed (4 files).
- `PROJECT.yaml` methodology authority: `ADR-L-0003 DEC-0033`.

## Stale derived state (intentionally deferred)

Non-authoritative generated corpus not regenerated during substrate promotion:

- `adrs/index/**`
- `adrs/manifest.yaml`
- `adrs/adr-projection/**`
- `tests/golden/expected/**`

## Checkpoint posture

`AUTHORITY_SUBSTRATE_PROMOTED` is recorded on a feature branch. **Do not merge** to governance-green admission until Gate D closes in the implementation tranche.
