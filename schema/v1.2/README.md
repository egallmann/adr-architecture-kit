# ADR Kit Schema v1.2

`schema/v1.2/` is the provisional additive ADR authoring line introduced by Phase 2.
It adds bind-only external references, substrate/rule/evidence-expectation contracts,
and optional stable physical-topology IDs. It does not replace frozen v1.0 or
repurpose the provisional v1.1 discovery and ledger schemas.

External bindings record identity and authoring intent only. They do not import,
execute, or admit externally owned semantics or observed evidence.
