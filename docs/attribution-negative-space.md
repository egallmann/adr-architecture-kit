# Attribution negative space (permanent)

**Status:** Signed off (Phase 3 closure)  
**Date:** 2026-05-30  
**Triage authority:** [`blog-posts/evidence/adr-kit-retrofit-triage-matrix.md`](../../blog-posts/evidence/adr-kit-retrofit-triage-matrix.md)  
**Purpose:** Explicit zones where **no** implementation attribution claims are expected in RECON-derived `implementation-attribution-evidence.yaml`. Prevents false “coverage gap” alarms during retrofit and governance reviews.

---

## Manifest ADRs with zero evidence (signed off)

| ADR | Title | Classification | Reason |
|-----|-------|----------------|--------|
| **ADR-L-0003** | Quality Assurance and Testing Strategy | **Process** | QA embodied in pytest/golden harness — no single decorated export |
| **ADR-L-0005** | ADR-to-Prompt Translation | **Out of scope** | Prompt translation lives outside adr-kit Python API |
| **ADR-L-0006** | Rule Library Sub-Module | **Sibling repo** | Cooperative signals with ste-rules-library — no kit embodiment |
| **ADR-L-0008** | Validation Modes for Draft and Complete ADRs | **Policy** | Mode semantics distributed across validators — no one owner symbol |
| **ADR-L-0012** | Federation Authority and Qualified Identity | **Deferred** | No dedicated kit runtime API in current scope |
| **ADR-L-0014** | Brownfield Onboarding and Canonicalization | **Workflow** | Onboarding policy — not a decorated public function |
| **ADR-P-0001** | Python Toolkit Implementation | **Physical posture** | Repo-wide implementation — collective, not one symbol |
| **ADR-P-0002** | JSON Schema Validation with YAML | **Cross-cutting** | Parser/validator stack — no single export |
| **ADR-P-0003** | Multi-Scope Python Implementation | **Subsumed** | Covered by ADR-L-0002 multi-scope CLI surface |
| **ADR-P-0004** | Prompt Translator Implementation | **Out of scope** | See ADR-L-0005 |
| **ADR-PC-0004** | Repository Boundary (physical) | **Logical owner** | ADR-L-0013 owns repository boundary claims |
| **ADR-PC-0006** | Brownfield Onboarding (physical) | **Logical owner** | Mirror of ADR-L-0014 deferral |
| **ADR-PS-0001** | Discovery and Indexing System | **Physical posture** | Discovery covered under ADR-L-0009 / ADR-PC-0001 |
| **ADR-PS-0002** | Compiler and Validation Runtime | **Physical posture** | Compiler covered under ADR-L-0009 / ADR-PC-0003 |

These **16** ADRs are intentionally absent from attribution evidence. Zero rows is correct, not a retrofit gap.

---

## ADRs with partial coverage (accepted)

| ADR | Gap | Resolution |
|-----|-----|------------|
| **ADR-L-0016** | Corpus query / orientation APIs implemented but CLI cites ADR-L-0002/0013 not 0016 | Documented: `ArchitectureRepository` + `corpus-summary` / `next-id` carry scope/repo claims |
| **ADR-L-0017** | `ScaffoldGenerator` and `adr scaffold` exist without ADR-L-0017 id on decorators | Documented: forward authoring ergonomics attributed via multi-scope CLI cluster |

---

## Code surfaces without dedicated ADR claims (permanent negative space)

| Surface | Location | Authority / reason |
|---------|----------|-------------------|
| Golden snapshot harness | `tests/golden/` | Test infrastructure — not public API |
| Undecorated click helpers | `src/adr_kit/cli/main.py` (internal wiring) | Orchestration; decorated commands carry ADR-L-0002/0013 |
| Legacy ADR-P parsing paths | Validators/parser | Retained for brownfield; excluded from new creation ergonomics per ADR-L-0017 |

---

## Review policy

1. **Do not** decorate negative-space surfaces solely to improve coverage metrics.
2. **Do not** decorate without an ADR-amended owner list or explicit triage marking `needs_decoration`.
3. **Do** add claims when an ADR amend or new ADR explicitly assigns ownership.
4. **Re-run** `recon:workspace` from ste-runtime after any retrofit; diff evidence against this table and the triage matrix.
5. **Validate** with `adr attribution check --scope . --evidence <workspace-state-path>`.

---

## Retrofit closure (Phase 3)

- **14 / 30** manifest ADRs have evidence rows.
- **16 / 30** have zero rows by signed-off negative space.
- Phase 3B optional decoration: **skipped** (no HIGH-confidence `needs_decoration` in triage).

See [`blog-posts/evidence/adr-kit-retrofit-completion-evidence.md`](../../blog-posts/evidence/adr-kit-retrofit-completion-evidence.md) for final gate results.
