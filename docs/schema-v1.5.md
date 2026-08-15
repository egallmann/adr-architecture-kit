# Implementation attribution evidence schema v1.5

v1.5 is a **semantic attribution evidence** line. It is not ADR authoring schema 1.5 and it does not introduce normalized model 3.0.

## Authority

- Canonical JSON: [`schema/v1.5/implementation-attribution-evidence.schema.json`](../schema/v1.5/implementation-attribution-evidence.schema.json)
- Mechanical vocabulary: [`schema/v1.5/semantic-attribution-vocabulary.json`](../schema/v1.5/semantic-attribution-vocabulary.json)
- Package mirrors: `src/adr_kit/schema/v1_5/` (byte-identical; see `tests/test_package_schema_parity.py`)
- Architecture authority remains authored ADR YAML and model 2.0
- Extracted YAML and decorators are untrusted declarations, not proof

Do not add `1.5` to `supported_adr_schema_versions`. Attribution 1.0/1.2 remains readable under [`schema/v1.1/implementation-attribution-evidence.schema.json`](../schema/v1.1/implementation-attribution-evidence.schema.json).

## Evidence locations

These paths are not interchangeable:

- **Workspace-derived RECON evidence** may live under the workspace-root `.ste-workspace/` tree, outside the repository. Pass that file to `adr attribution check` / `coverage` with `--evidence`. The CLI does not search `.ste-workspace` automatically.
- **Project-local default lookup** (when `--evidence` is omitted) checks only under `--scope`:
  1. `{scope}/state/attribution/implementation-attribution-evidence.yaml`
  2. `{scope}/.ste/state/attribution/implementation-attribution-evidence.yaml`
- **Local pre-push** (`scripts/run_local_pre_push_checks.py`) knows the ADR Kit workspace evidence path and supplies it via `--evidence`.

## Raw claim shape

Each claim requires:

- `relationship`: `implements` | `enforces` | `embodies`
- `target_entity_id`: lowercase UUIDv7
- `confidence`: `declared` | `inferred` | `heuristic`

Records also require `implementation_entity_id`, `implementation_entity_type`, and `provenance` (`source_file`, `extractor`, optional `commit`).

Raw evidence **must not** require `target_entity_type`. Optional `asserted_target_entity_type` is redundant; if present, architecture-aware validation compares it to the repository-resolved type and fails on mismatch.

Decorator-generated claims always use `confidence: declared`. `inferred` and `heuristic` are for extractors.

## Resolved type and matrix

After `ArchitectureRepository.find_entity_by_uuid` (model 2.0), validation derives `resolved_target_entity_type` on results and coverage reports:

| Relationship | Admitted resolved types |
|--------------|-------------------------|
| `implements` | `adr`, `decision`, `capability`, `contract`, `interface`, `implementation_decision` |
| `enforces` | `invariant` |
| `embodies` | `system`, `component`, `boundary` |

Unresolved UUID, alias-as-canonical, illegal pair, or asserted-type mismatch fails closed. `superseded` / `deprecated` targets warn.

These evidence verbs are **not** `RelationshipRecordV2` values and must not be written into architecture relationship registries.

## Legacy 1.0/1.2 translation

`normalize_attribution_evidence(doc, repository_or_model)` requires architecture state. Aliases resolve through governed `alias_id` lookup; UUID values resolve directly; unresolved or ambiguous aliases fail closed. Canonical output is sorted and idempotent.

CLI (stdout by default; `--output` writes only that path):

```bash
adr attribution normalize-evidence --scope . --input evidence.yaml
```

## Coverage

`adr attribution coverage` keeps:

- `scope_root`
- `evidence_schema_version`
- `adrs_with_attribution_claims`
- `adr_corpus_total`
- `catalog_adrs_not_cited_by_evidence`

For v1.5 input, ADR keys fill from claims whose resolved type is `adr`. Additive fields distinguish unique semantic links from evidence occurrence:

- `semantic_unique_claim_counts_by_relationship`
- `semantic_unique_claim_counts_by_resolved_target_entity_type`
- `semantic_evidence_occurrence_counts_by_relationship`

Neither metric proves correctness.

## Decorators

Legacy `@implements_adr` / `@enforces_invariant` set `__implements_adrs__` / `__enforces_invariants__` only. They do not load architecture state or synthesize UUID claims.

UUID `@implements` / `@enforces` / `@embodies` compose `__architecture_attribution_claims__` with `confidence: declared`. Sequence forms `*_uuids([...])` exist for list-literal extractor parity.

Python and TypeScript shims are generated from the vocabulary (`adr attribution generate-shim`).
