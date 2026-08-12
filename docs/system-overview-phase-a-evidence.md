# Phase A Evidence Note — SYSTEM-OVERVIEW Provider Refactor

**Branch:** `feature/adr-v1.3-identity`  
**Date:** 2026-08-11  
**Status:** PROPOSED_CASE_B (evidence-neutral determination)

## A1 Kit baseline

- `pytest tests/test_system_overview_generator.py` — 4 passed
- `adr validate-system-overview` — valid
- Generator identity: `adr-system-overview` version **1**
- Content class: documentation-state toolkit / CLI-first / First Discovery Order

## A2 ste-runtime (current behavior)

- Emission: success; validation: success
- Runtime purpose language present (`implements STE runtime workflows`)
- Workspace highlights for ADR-L-0009 / ADR-L-0010 / INV-0014 when manifest present
- **Also** still includes kit-centric leftover sections (`## First Discovery Order`, `src/adr_kit/` paths)

## A3 Generic `overview-consumer-fixture` (current behavior)

- Emission: **success**; validation: **success**
- Content class: same as kit-default (documentation-state toolkit, First Discovery Order, `src/adr_kit/`)
- Project name appears in metadata; no fail-closed today

## A4 Authority / compatibility inspection

| Artifact | Current status | Role |
|----------|----------------|------|
| ADR-L-0007 | **accepted** | Owns SYSTEM-OVERVIEW / deterministic documentation projection — primary amend target |
| ADR-PC-0005 | **proposed** | Physical integrity embodiment — review/traceability only; not locked accepted authority |
| ADR-L-0002 | **proposed** | Multi-scope — context only |
| ADR-L-0013 | accepted | Repository / normalized model boundary (reference) |
| ADR-L-0016 | accepted | Corpus/orientation APIs — not overview projection owner |
| CLI `generate-system-overview` | de facto public | `docs/production-hardening/public-surface-inventory.md`: preserve **success/failure behavior** |
| Integrity | optional-by-absence | Validates SYSTEM-OVERVIEW only if file exists |

No compatibility snapshot freezes overview body content for arbitrary project names.  
No accepted ADR requires SYSTEM-OVERVIEW generation for every ADR-managed repo.  
CLI generation command currently succeeds for non-kit / non-runtime project names (characterized).

## Case determination

**PROPOSED_CASE_B**

### Evidence rule (not preference)

1. Observable current behavior: generic project generation **succeeds** and validates.
2. Documented CLI generation contract: preserve success/failure behavior for `generate-system-overview`.
3. Case A fail-closed would change that success/failure behavior → classified as **compatibility-impacting intentional behavior change** relative to current de facto CLI posture.
4. Per plan: if Case A would violate current compatibility policy → select bounded Case B or STOP.
5. Bounded Case B can preserve emission success without kit-provider framing and without designing future generic consumer product.

### Case A break classification (if Case A were chosen anyway)

Would be: **intentional breaking change** to CLI success/failure for non-profiled projects (or “unsupported behavior removal” only if authority explicitly denied support — it does not today).  
Would require compatibility review / release notes under `docs/public-surface-and-stability.md`.  
**Not selected** because Case B preserves the existing success path safely.

### Case B constraints to authorize in ADR-L-0007

- Legacy generic path is compatibility-only
- Must not inherit ADR Kit provider semantics / provider IA
- Must not be the future generic-consumer design
- Kit + ste-runtime remain explicit profiles
- Richer generic assembly remains deferred
- Absence of SYSTEM-OVERVIEW remains valid (integrity skips missing file)

## Contradictions / stop risks

- None requiring STOP: L-0007 still owns the concern; Case B does not require designing future generic consumer architecture.
- PC-0005 remains proposed — L-0007 accepted invariants for generated docs + existing integrity machinery suffice for this embodiment.
