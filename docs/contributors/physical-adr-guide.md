# Physical ADR guide

Physical ADRs describe how accepted logical architecture is realized. Use the
two current physical roles instead of the retired broad `ADR-P` authoring form:

- `ADR-PS` (physical-system) captures system topology, integrations, and
  high-level technology posture.
- `ADR-PC` (physical-component) captures implementation-ready component
  responsibilities, interfaces, identifiers, and operational requirements.

Legacy `ADR-P` files remain readable for compatibility only. Do not create a new
generic `ADR-P` when the system/component split expresses the architecture.

## Current workflow

1. Discover the exact authoring contract through capability discovery or the
   canonical resources under `contracts/authoring-domain/` and
   `schema/authoring/`.
2. Place physical-system sources under `adrs/physical-system/` and
   physical-component sources under `adrs/physical-component/`.
3. Link each physical record to its logical authority as required by the
   discovered contract.
4. Validate the scope and generated projections:

   ```bash
   adr validate --scope . --mode complete
   adr validate-generated-docs --scope .
   ```

The schemas and capability manifest define exact fields, identity, topology,
and version rules. This guide does not reproduce those machine contracts or a
legacy `ADR-P` example.
