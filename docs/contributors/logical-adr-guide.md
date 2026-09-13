# Logical ADR guide

Logical ADRs record conceptual architecture authority: capabilities,
boundaries, contracts, constraints, invariants, and decisions. They explain
what must be true and why, without turning implementation choices into
logical intent.

## Use a logical ADR when

- a capability or boundary needs an accepted architectural decision;
- a contract, invariant, or constraint must become durable authority; or
- a change needs explicit rationale and traceability before implementation.

Keep technology choices, deployment details, component interfaces, and other
implementation detail in the appropriate physical-system or physical-component
ADR.

## Current workflow

1. Discover the supported authoring contract with `adr_kit.api` capability and
   authoring discovery, or inspect the canonical resources under
   `contracts/authoring-domain/` and `schema/authoring/`.
2. Place the source under `adrs/logical/` and preserve the repository's
   canonical identity and relationship rules.
3. Validate the scope with:

   ```bash
   adr validate --scope . --mode complete
   adr validate-generated-docs --scope .
   ```

4. Generate or refresh derived projections only with repository-owned commands.

The exact fields, versions, and allowed values are machine-verifiable contract
truth. This guide intentionally does not reproduce a schema or a full YAML
template.

## Boundary

Logical ADRs are source authority. Generated manifests, registries, rendered
Markdown, and normalized models are derived views. Runtime evidence and
governance/admission decisions belong to their owning repositories.
