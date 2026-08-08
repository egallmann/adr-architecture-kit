# Topology identity migration

ADR schema v1.2 supports optional stable IDs for physical-system topology
components. IDs match `TOPO-[A-Z0-9][A-Z0-9-]*`; the migrator allocates
reviewable `TOPO-0001` style IDs.

## Legacy and migrated forms

Legacy name-keyed topology:

```yaml
schema_version: '1.0'
component_topology:
  components:
  - name: gateway
    type: gateway
    purpose: Accept requests.
  relationships:
  - from: gateway
    to: worker
    type: calls
data_flows:
- id: FLOW-0001
  name: Request flow
  description: Gateway to worker.
  path: [gateway, worker]
```

Migrated v1.2 topology retains display names and rewrites endpoints:

```yaml
schema_version: '1.2'
component_topology:
  components:
  - id: TOPO-0001
    name: gateway
    type: gateway
    purpose: Accept requests.
  relationships:
  - from: TOPO-0001
    to: TOPO-0002
    type: calls
data_flows:
- id: FLOW-0001
  name: Request flow
  description: Gateway to worker.
  path: [TOPO-0001, TOPO-0002]
```

## Command

Preview is the default and never writes:

```powershell
adr migrate-topology-ids --scope .
```

Apply only after reviewing every structural-pointer change:

```powershell
adr migrate-topology-ids --scope . --apply
adr validate --scope . --mode complete
```

The migrator preserves existing IDs, scans files and component lists in
canonical order, and allocates the first free sequential topology ID across the
scope. It rewrites relationship endpoints and data-flow paths only when a name
resolves exactly once, validates the complete v1.2 candidate, then writes all
changed documents atomically. A second run is idempotent.

Duplicate IDs, ambiguous names, and dangling names or IDs are blocking
diagnostics. The migrator does not guess and does not use an LLM.
