# External bindings

ADR schema v1.2 can author three binding families without importing external
authority into ADR Kit.

## Semantic boundary

```text
binding != ownership
rule binding != rule execution
evidence expectation != observed evidence
external reference != locally admitted authority
```

ADR Kit validates and projects these authored references. It does not load a
substrate body, execute a rule, ingest observed evidence, contact a provider, or
create local entities for external targets.

## External references

Cross-repository entity references are explicit objects containing:

```yaml
namespace: provider-architecture
id: CAP-0042
kind: capability
fingerprint: sha256:<64 lowercase hexadecimal characters>
```

Their consumer-facing qualification is assembled as
`provider-architecture:CAP-0042`. Bare strings remain repository-local entity
references; they never imply a cross-repository lookup.

## Binding families

`substrate_bindings` records an external artifact selection, its version and
fingerprint, its role, the local selecting entity, and optional local
configuration or supersession references.

`rule_bindings` records an external rule and one disposition: `adopted`,
`refined`, `overridden`, `exempted`, or `not_applicable`. Non-adopted
dispositions require rationale; `exempted` also requires `exception_ref`.

`evidence_expectations` names evidence architecture expects to exist later. An
expectation is projected with `observed_evidence: false`; it is never evidence
that the condition was actually observed.

## Projection

The relationship registry emits `binds_substrate`, `binds_rule`, and
`expects_evidence` from the owning ADR. External targets use qualified IDs, and
expectations use their authored `EVID-*` ID. These targets are deliberately not
materialized in the local entity registry or architecture graph.

Every local `selected_by`, `affected_entities`, or `related_entities` reference
must resolve to exactly one local entity. Validation is deterministic and
performs no network access.
