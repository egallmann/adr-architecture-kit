# READY_FOR_SYSTEM_OVERVIEW_AUTHORITY_LOCK

**Hard stop.** Do not begin Phases B–J (target RED/GREEN / v2 realization) until a human approves this package.

## Phase A disposition

- Evidence note: [`docs/system-overview-phase-a-evidence.md`](../docs/system-overview-phase-a-evidence.md)
- Characterization tests: [`tests/test_system_overview_characterization.py`](../tests/test_system_overview_characterization.py) (3 passed)
- **PROPOSED_CASE_B** (legacy generic compatibility path; no kit-provider framing; no future generic product)

## A. OLD AUTHORITY (pre-amendment ADR-L-0007)

Retained unchanged (accepted history preserved):

| Alias | Summary |
|-------|---------|
| DEC-0012 | Treat human-readable architecture documentation as deterministic derived state |
| DEC-0019 | Prohibit manual edits to generated documentation |
| DEC-0026 | Require generator, validator, test, and CI enforcement |
| DEC-0108 | Emit ADR human projections under typed adr-projection paths |
| DEC-0109 | Human ADR projections render compiler-derived relationship semantics only |
| INV-0037 | INV-DOC-001 generated from structured/projection source |
| INV-0038 | INV-DOC-002 deterministic given identical inputs |
| INV-0039 | INV-DOC-003 never edit rendered docs manually |

## B. PROPOSED AUTHORITY DELTA (additive)

| Alias | UUID | Summary |
|-------|------|---------|
| DEC-0110 | `019ff22a-bb5f-7bfc-851d-938bffc81281` | Classify projection inputs as derived facts or authored orientation |
| DEC-0111 | `019ff22a-bb5f-7214-8818-40820f8c553e` | Allow deterministic semantic intermediate model (semantic basis ≠ sole integrity basis) |
| DEC-0112 | `019ff22a-bb5f-7d9e-973f-b9008898a8c9` | Require projection-source closure (semantic + projection-rule) |
| DEC-0113 | `019ff22a-bb5f-76eb-8a31-546eeba55dcb` | Projections reflect supported boundaries without redefining them |
| DEC-0114 | `019ff22a-bb5f-77ed-a63f-98f0455fdd1e` | Isolate repository-specific orientation by scope |
| DEC-0115 | `019ff22a-bb5f-7926-a33c-b66f72343219` | Preserve legacy generic SYSTEM-OVERVIEW generation as compatibility-only (Case B) |
| INV-0099 | `019ff22a-bb5f-7c77-a223-1dab5e8c814d` | INV-DOC-004 no authored duplicate of owning machine-verifiable facts |
| INV-0100 | `019ff22a-bb5f-7779-912f-040cdf1b54b8` | INV-DOC-005 authored orientation non-authoritative |
| INV-0101 | `019ff22a-bb5f-7b93-a600-f587022aeffd` | INV-DOC-006 projection-source closure / no whole-repo hashing |
| INV-0102 | `019ff22a-bb5f-7fca-b021-b3cbc68ddde2` | INV-DOC-007 no provider-orientation leak across scopes |

Related ADR references added (by UUID): ADR-L-0013, ADR-PC-0005.

## Related authority review

| ADR | Status | Disposition |
|-----|--------|-------------|
| ADR-PC-0005 | **proposed** | Not treated as accepted. L-0007 accepted invariants + existing integrity machinery suffice for embodiment. **No PC-0005 amend.** |
| ADR-L-0002 | **proposed** | Context only |
| ADR-L-0013 | accepted | Referenced; not amended |
| ADR-L-0016 | accepted | Unchanged |

## C. EFFECT ON IMPLEMENTATION (post-approval)

| Authority | Implementation consequence | Planned evidence |
|-----------|----------------------------|------------------|
| DEC-0110 / INV-0099 | Provider facts from `capabilities()`; no version literals in profile/generator/tests | Phase D consistency guards |
| DEC-0110 / INV-0100 | Kit + ste-runtime authored profiles as orientation only | Phase C profile tests |
| DEC-0111 | `SystemOverviewModel` as complete semantic basis | Phase C model tests |
| DEC-0112 / INV-0101 | Semantic snapshot + projection-rule HashInputs; generator v2 | Phase E/F hash sensitivity tests |
| DEC-0113 | Overview routes to existing SDK/CLI/boundaries; does not invent them | Phase B/G orientation tests |
| DEC-0114 / INV-0102 | Kit / ste-runtime / Case B routing; anti-provider-leak | Phase I |
| DEC-0115 | Case B legacy generic path (compat-only, no provider IA) | Phase I generic regression |

## Generated artifact deltas

```text
OLD generated overview
    ↓
pre-lock current-contract regeneration
    (manifest hash change after ADR amend; pre-refactor generator v1 only)
    ↓
proposed v2 implementation consequences after approval
    (NOT embodied yet)
```

Also regenerated via current-contract pipelines: registries, manifest, adr-projection markdown (incl. L-0007), architecture-graph, golden expected snapshots.

## Validation evidence

- `adr validate --cross-references` — pass
- `adr validate-system-overview` — pass (after current-contract regen)
- `tests/test_system_overview_characterization.py` — 3 passed
- `tests/test_system_overview_generator.py` — 4 passed
- `tests/golden/test_current_outputs.py` — pass after golden refresh
- `tests/test_generated_docs_integrity.py::test_repo_generated_artifacts_validate` — pass after graph emit

## Human decision required

**APPROVED** (2026-08-11) — Phases B–J authorized and realized on `feature/adr-v1.3-identity`.

**Do not treat plan greenlight as this authority-lock approval.** (Historical note: lock was granted explicitly after this package.)
