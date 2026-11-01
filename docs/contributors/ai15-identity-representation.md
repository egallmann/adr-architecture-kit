# Private AI 1.5 identity representations

This private Rust seam executes `literal_alias_join`, `literal_entity_uri` and
`uuidv7_unix_milliseconds_to_rfc3339_utc`. Its output is three bounded string facts
per qualified semantic unit, not a normalized entity, model or construction result.
Complete interpretation remains `Unavailable`. No public dispatch, SDK method,
WASM export, capability, current SCS, package version or promotion changes.

## Authority and original source boundary

Every binding, execution and verification requalifies the supplied NM 2.5, AI 1.5
and ACC 1.5 bundles through `candidate_authority::qualify`. Maintained canonical
inputs select the authority; caller fingerprints, flags and consistent rehashes do
not. Candidate revisions require independent qualification and a rebuilt core,
not permanent SCF constants.

`seal_sources` accepts **already-authored native source bytes**, exact schema
selectors and source references. The sources already contain their canonical
UUIDv7 values. There is no replacement UUID argument, minter, compact-input
preparer, insertion operation or synthetic source wrapper.

The original source is the authoring input, not an asserted execution receipt.
The private witness anchors these original bytes before consumers see results:

1. Resolve the actual catalog source selector and qualified Authoring 1.7 schemas.
2. Preflight and validate the complete source through the existing sealed evaluator.
3. Require the renderer's compiled schema catalog to equal selected authority.
4. Decode canonical YAML with duplicate-member rejection. Use the existing native
   renderer/sealer and require byte-for-byte equality with the original input.
5. Seal every original artifact using the governed basis serializer and digest.
   This seam never drops a child artifact or invents containment proofs.
6. Bind the actual current authority identities and independently derived context
   into a witness whose fields cannot be manufactured by its consumers.

Native ADR documents qualify only through their exact published schemas. Catalog
membership does not grant root permission. Native standalone fragments remain
fragments; missing declaring context prevents representation execution. An
already embedded child is discovered within its original parent source, not
manufactured as another root or separately returned child artifact.

This is a native-source input seam, **not an ACC 1.5 construction producer**.
ACC 1.3 construction receipts are not relabeled, adapted or used as a fallback.
Compact/composition requests require a separately qualified current producer
handoff; this entry point does not accept those requests or their receipt flags.

## Instance and rule selection

Source occurrences are found through qualified schema references, properties,
array items and applicable schema branches. The existing evaluator performs all
validation; traversal only locates occurrences. Source pointers locate evidence
and never define canonical identity. All schema-owned canonical identity claims
are accounted for, including nested children, before selecting a unique producer.

The exact AI catalog supplies semantic type, regular/proposition branch, source
selector, three destination selectors and unique producer/rule qualifications.
Regular children require an exact inherited ownership row matching parent type,
child selector and schema containment pattern. Propositions use qualified schema
containment and receive no lifecycle value or inheritance. Custom CEC and shared
descriptor qualifications are not invented.

The only executable provider here is the actual selected AI 1.3 detached-context
resource inherited by AI 1.5. Namespace, provider kind, scope and root locators are
derived from its exact constants and the verified basis. Actual inherited rule
identity/digest/SCF remains intact. The enclosing authority is current AI 1.5.
Neither source references nor scope/root locators substitute for the namespace.
The opaque URI preserves the selected namespace literally, including its colons.

Alternative provider assertions remain `Unavailable`; this implementation cannot
fabricate evidence for two distinct qualified namespaces. Identity evidence keeps
namespace and UUID separate; identical aliases never merge distinct UUIDs.

## Execution and independent replay

`execute` returns an atomic `Executed` projection. `verify` consumes the original
private source witness and selections, not a trusted success flag. It requalifies
the candidate bundle, reconstructs the basis/contracts/identities and detached
context, rediscovers applicability and independently selects the rules.

The verifier does not call the producer or its string/date-producing functions:

- Alias output is compared to an exact byte stream of the two original aliases
  separated by a colon. There is no delimiter parsing or normalization.
- URI output is compared to the fixed prefix, qualified namespace, separator and
  original UUID byte streams. No URL parser or percent encoding is involved.
- The producer converts UUID milliseconds to civil time using integer Gregorian
  eras. The verifier checks the exact 24-byte spelling, validates Gregorian fields,
  independently converts the date back to Unix milliseconds and independently
  decodes the original twelve UUID timestamp hex digits.

The valid timestamp range ends at `253402300799999`. Later valid UUIDv7 timestamps
are `Unavailable` for this representation. They are not invalid identities.
Malformed, uppercase or wrong-version/variant UUIDs are `Rejected`. No wall clock,
authored date, Git timestamp, fallback, reminting or floating-point rounding occurs.

Source-invalid aliases are rejected. Authoring 1.7 currently permits 3–96-character
lowercase kebab-case alias names; empty/Unicode/whitespace variants do not become
valid through normalization. Valid maximum-length inputs and uppercase alias IDs
are copied exactly. Other Unicode semantic source values remain byte-preserved.

## Failure and scope

Findings are deterministic with `Rejected > Unavailable`; this seam has no governed
dependency resolver and cannot manufacture `Unresolved`. Any failure clears all
representation and qualification output. Missing evidence is unavailable; known
source, identity, rule or output inconsistency is rejected. Forged/stale witness
and result mutations cannot substitute for replay.

Physical-system shared identity, unqualified custom sources, standalone declaring
context and alternative providers remain unavailable. Relationships and owner-local
values do not acquire entity recipe producers. All 215 catalog BLOCKED entries
remain unchanged, as do the 27 types, six branches, 240 definitions, 26 labels,
54 identity definitions, three operations and five required evidence checks.

Each resulting field is validated against its qualified destination fragment.
**Complete NM branch validation remains outstanding.** The recipe's full-output
verification obligations are not claimed satisfied by three valid fields.
Original semantic values remain significant at their existing destinations; no
generated copy gains a semantic owner. Replay is not whole-ledger equality.

Remaining work includes current construction/source handoffs beyond native input,
additional provider/custom/shared qualification, remaining representation recipes,
full field/context interpretation, complete NM assembly and independent complete
ledger comparison. No `semantic_equivalent`, `Constructed`, persistence or admission
is enabled by this change.
