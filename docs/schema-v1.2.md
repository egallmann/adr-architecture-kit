# ADR authoring schema v1.2

Schema v1.2 is the provisional additive ADR authoring line introduced by
ADR-L-0018. It does not replace or modify the frozen v1.0 encoding, and it does
not repurpose the provisional v1.1 discovery and ledger schemas.

## Version posture

| Line | Purpose | Stability |
|---|---|---|
| `schema/v1.0/` | ADR authoring encoding | Stable and frozen |
| `schema/architecture-discovery/v1.1/`, `schema/governance/v1.1/`, `schema/evidence-attribution/v1.1/`, `schema/normalized-model/v1.1/` | Discovery, ledger, remediation, attribution, and normalized-model contracts | Provisional |
| `schema/authoring/v1.2/` | Additive ADR authoring encoding | Provisional |

Parsers dispatch `schema_version: '1.2'` explicitly. Unsupported future
versions fail closed rather than falling back to v1.0.

## Canonical inventory

The canonical v1.2 source directory contains:

- `adr-common.schema.json`
- `adr-logical.schema.json`
- `adr-physical-base.schema.json`
- `adr-physical.schema.json`
- `adr-physical-system.schema.json`
- `adr-physical-component.schema.json`
- `invariant.schema.json`
- `types.schema.json`

Byte-identical packaged copies live under `adr_kit.schema.v1_2` and are
available through `importlib.resources` in installed wheels.

## Additive semantics

V1.2 adds bounded external references, substrate and rule bindings, evidence
expectations, and optional stable topology component IDs. Details are in
[external bindings](external-bindings.md) and
[topology identity migration](topology-identity-migration.md).

The normalized model is version `1.1` and admits exactly ten first-class entity
types:

```text
adr, system, component, decision, capability, invariant,
boundary, contract, interface, implementation_decision
```

Constraint, NFR, gap, and integration records remain embedded. Data flow is not
promoted in Phase 2.

Relationship records preserve the historical endpoint-based `relationship_id`
and add a source-sensitive `assertion_id`. The assertion input is the compact
JSON encoding of:

```text
[relationship_type, from_entity_id, to_entity_id,
 canonical_source_ref, source_pointer_or_empty]
```

The identifier is `asrt-` followed by the lowercase SHA-256 digest. This is an
identity foundation only; Phase 2 does not implement multi-source replacement
semantics or GraphProjectionBundle.

## Validation

Use the existing validation command:

```powershell
adr validate --scope . --mode complete
```

Source/package parity is enforced by `tests/test_package_schema_parity.py` and
the local pre-push checks.
