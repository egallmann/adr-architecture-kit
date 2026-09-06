# ADR-Kit Consumer Binding Contract 1.0 conformance corpus

This corpus is verification evidence for the language-neutral consumer binding
contract. It is not semantic authority; accepted ADRs and canonical files under
`schema/` remain authoritative.

Each fixture records the canonical input, the observable semantic result expected
from a binding, the authority references, and the capability/contract version under
test. Tests read the checked-in expected values and never regenerate them. A fixture
maintenance command, when added, must be explicit and separate from ordinary tests.

Consumer Binding Contract 1.0 qualifies overlapping capabilities at five distinct
levels:

- structural schema acceptance and rejection;
- semantic preservation of identity, relationships, extensions, unresolved state,
  and provenance;
- behavioral operation outcomes;
- diagnostic classification and stable codes where available;
- serialization equivalence only where a portable canonical serialization is
  explicitly declared.

Python and TypeScript binding-local fingerprints are intentionally not compared.

The initial corpus covers normalized model 2.1, evidence attribution 1.5/1.6,
qualified extensions, canonical and compatibility relationships, unresolved records,
unsupported versions, duplicate claims, target mismatch, and the v1.6 `enforces`
confidence restriction. It also covers the promoted ADC 1.0 discovery contract:
contract description, complete and kind-filtered type listing, representative
descriptors, exact case-sensitive lookup, deterministic errors, and explicit
non-equivalence of discovery serialization bytes.

The ADC fixture is expected evidence only. `contracts/authoring-domain/v1.0/contract.json`
is the semantic authority, and ordinary qualification must not regenerate the
checked-in expected results.
