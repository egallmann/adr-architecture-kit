# Evidence-attribution schema v1.6

Evidence-attribution v1.6 is the preferred producer format for new integrations. It is a
provisional evidence contract, independent from ADR authoring schema versions, the
package version, and `adr_kit.api` contract version 1.0.

It preserves the v1.5 relationship and entity vocabularies and adds optional provenance
orientation:

- `source_pointer`
- `start_line` (1-based, inclusive)
- `end_line` (1-based, inclusive and not before `start_line`)

These values can order and fingerprint evidence occurrences. They are not implementation,
architecture, relationship, semantic-linkage, or graph-admission identities.

## Confidence

| Relationship | Declared | Inferred | Heuristic |
|---|---:|---:|---:|
| `implements` | yes | yes | yes |
| `embodies` | yes | yes | yes |
| `enforces` | yes | no | no |

Decorators emit declared confidence only. Version 1.5 keeps its historical semantics.
Normalization preserves confidence exactly and rejects conversion that would violate the
target policy.

## Normalization

`adr attribution normalize-evidence` keeps v1.5 as its default target. Select v1.6
explicitly with `--target-version 1.6`. A v1.6 downgrade succeeds only when no
v1.6-only provenance would be discarded. Conversion never invents identities, claims,
types, confidence, pointers, or spans.

## Authority

A declaration is evidence of intent, not proof. The public linkage projection has
`authority_ceiling=validated_derived_evidence` and
`graph_admission_status=not_admitted`. It never writes Architecture IR or graph state.

