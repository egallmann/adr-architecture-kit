# AI 1.5 identity representation authority

This publication implements accepted ADR-L-0039 (DEC-9017–9022,
INV-0309–0314), inheriting ADR-L-0019 identity semantics and ADR-L-0038
required-output accounting. It publishes authority, not instance execution.

## Exact inventory and closure

The computed AI 1.5 SCF is
`scf:v1:sha256:e3d52d9e863cfb6008f55bbff5c7ea4e676ac6a021d9eb52126284636d0329af`.

The sorted manifest has 69 resources: AI 1.4's exact 60-resource closure,
the AI 1.4 definition, the NM 2.5 definition, and these seven successor keys
under `architecture-interpretation/1.5/`:

- `rules`
- `required-output-derivations`
- `required-output-derivations.schema`
- `identity-representation-recipes`
- `identity-representation-recipes.schema`
- `conformance`
- `conformance.schema`

The canonical resources, definition and Python package mirrors are generated
together. Existing Node packaging copies the exact published definition and
resource assets. No selected-set registration is performed.

## Qualified delta

All 27 types, six branches, 186 existing producer definitions, 26 literal-copy
label rules, nested requirements, contextual rules and authored destinations
are retained. The catalog replaces exactly 18 definitions for each of
`/alias_ref`, `/uri` and `/created_at`: 240 QUALIFIED, 215 BLOCKED.
All instance applicability remains Unknown. No root or declaring owner is
authorized merely by catalog membership.

The closed successor producer schema extends the seven inherited kinds with:

- `literal_alias_join`: exact authored `alias_id + ":" + alias_name`.
- `literal_entity_uri`: exact `"adr://" + architecture_namespace + "/entities/" + uuid`.
- `uuidv7_unix_milliseconds_to_rfc3339_utc`: first 48 UUIDv7 bits as unsigned
  Unix milliseconds, integer Gregorian UTC conversion, exact
  `YYYY-MM-DDTHH:mm:ss.SSSZ`. Maximum timestamp: `253402300799999`.

Each type-scoped producer selects one shared recipe by exact key, digest and
selector. Source fields, canonical UUID and provider context require independent
qualification. Aliases remain recognition-only; representations have no extra
semantic ownership. There is no formatting, URI normalization, fallback,
wall-clock input, reminting, or lifecycle conversion. Malformed canonical
identity is Rejected; a valid timestamp outside the selected year range or
unavailable provider is Unavailable.

Inherited rules keep their actual identities. The catalog explicitly binds
local literal-copy operations to the AI 1.4 catalog/SCF. URI context retains
the actual AI 1.3 detached-context resource, digest and SCF. Neither is
relabeled as an AI 1.5 rule.

## Independent qualification

Generate only this successor:

```sh
python scripts/generate_semantic_contract_assets.py --publish-ai15-only
python scripts/qualify_ai15_publication.py
```

The independent qualifier does not import generator builders. It qualifies
historical authority as itself, compares every inherited declaration, checks
accepted recipe lineage, resolves source/destination schemas, verifies exact
dependency edges/roles/digests, and validates the complete closure through the
shared SCF implementation. A newly recalculated SCF cannot authorize changed
recipe semantics. Full companion-schema validation uses a sealed in-memory
registry; canonical relative references resolve only to supplied resources.
Evaluation identifiers are internal and do not modify published schema bytes.

The 132 new AI15 authority-only cases cover the 18 eligible types, nine
excluded types, recipes, provider/alias/time boundaries, evidence failures and
preservation. The 85 inherited AI14 cases are separately qualified by their
actual identities. Historical publication-state snapshots remain historical
snapshots, not permanent successor-absence requirements. These cases do not
claim end-to-end runtime conformance.

Permanent tests pin exact bytes, fingerprints, closure, mirrors and semantic
obligations. PR-specific preservation uses explicit revisions:

```sh
python scripts/qualify_ai15_boundary.py --base <actual-base> --head <actual-head>
```

There is no permanent Git baseline or forever-unselected assertion. Negative
mutations exercise missing/competing authority, source selectors, rule operations,
provider substitutions, timestamp precision/range, forged receipts, schema and
dependency corruption, and validly recomputed unauthorized fingerprints.

## Remaining obligations

The 215 blocked entries retain these 11 categories: `fingerprint_preimage`,
`source_envelope_recipe`, `completeness_recipe`, `custom_lifecycle`,
`declaring_context`, `shared_identity`, `relationship_branch`,
`relationship_envelope`, `nonselected_output`, `owner_local_context`,
`custom_qualification`.

Definitions are not successful instance values. Complete interpretation remains
Unavailable. This slice changes no Rust, WASM, protocol, execution API,
capability, current SCS, historical authority, lifecycle ownership, or ACC
construction behavior. It enables neither semantic equivalence nor Constructed.
ACC 1.5 publication is a subsequent separately authorized slice after human
acceptance of this authority.
