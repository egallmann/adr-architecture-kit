# ADR-027: Scope Semantics and Versioning

**Status:** Accepted  
**Date:** 2025-12-29  
**Closes Gap:** GAP-1 (Scope Semantics Definition / Blocker 1.4)

---

## Context

The STE-System specification references "scope" as a critical dimension for authority verification (§6.2.1 Trust Registry, §8.1.2 PREREQ-6), artifact partitioning (ADR-018 Relationship Artifacts), and execution eligibility (§8.1.3 CEM Envelope). However, the specification does not define what "scope" means structurally, how scope identifiers are formed, or how scope matching is performed.

This ambiguity creates critical correctness risks:

1. **Authority Verification Failure:** PREREQ-6 requires "The signing identity's authority scope (from trust registry) MUST encompass the claimed scope in the Context Bundle" (§8.1.2). Without defining "encompass," implementers cannot verify authority deterministically. Does scope `project:myapp` encompass `project:myapp-backend`? What about `project:myapp:backend`?

2. **Non-Deterministic Enforcement:** §8.1.4 STEP 6 requires Gateway to verify scope match during eligibility evaluation. If scope matching logic is implementation-defined, different Gateway implementations could produce different eligibility decisions for identical inputs, violating determinism guarantees.

3. **Implementation Invention Risk:** Without normative scope structure, every implementation must invent:
   - Scope syntax (flat strings, hierarchical paths, URIs?)
   - Matching algorithm (exact match, prefix match, wildcard, regex?)
   - Authority resolution rules (if multiple authorities match, which wins?)
   - Conflict handling (what if two authorities at equal depth both match?)

4. **Interoperability Breakdown:** Trust Registry entries specify scope for each identity (§6.2.1). If two organizations interpret scope differently, trust registry entries become non-portable, breaking interoperability.

5. **Eligibility Bypass Risk:** If scope can be inferred, defaulted, or interpreted loosely, an attacker could craft Context Bundles claiming narrow scope (e.g., `project:myapp-backend`) while using broad authority (e.g., `project:*`), bypassing intended authority boundaries.

Scope is not metadata. Scope is a **canonical dimension** that participates in:
- Authority verification (PREREQ-6: who can sign what)
- Artifact partitioning (which artifacts belong to which organizational unit)
- Execution eligibility (what code is authorized to execute)
- Trust boundaries (what identities have authority over which resources)

Treating scope as optional, inferred, or subject to interpretation would compromise the correctness guarantees that define the STE-System.

## Problem Statement

The specification must answer the following questions to enable deterministic, verifiable enforcement:

1. **What is scope structure?** Is it a flat string, hierarchical path, JSON object, or URI?

2. **What are valid scope identifiers?** What characters are allowed? What is maximum length?

3. **Is scope hierarchical?** Does `project:myapp` encompass `project:myapp:backend`?

4. **What is the scope matching algorithm?** Exact match? Prefix match? Wildcard? Regex?

5. **How is authority resolved?** If multiple trust registry entries match a claimed scope, which one is authoritative?

6. **What happens on conflicts?** If two identities at equal hierarchy depth both match, is this allowed or an error?

7. **Can scope be inferred?** If Context Bundle omits scope, can Gateway infer it from artifact metadata?

8. **Can scope use wildcards?** Can authority scope `project:*` match any project scope?

9. **How does scope relate to environment?** Are they independent dimensions or combined?

10. **Can scope structure evolve?** If organizations need hierarchical matching after deploying with exact matching, how is this supported?

These questions have **no implementation-neutral answers** in the current specification. GAP-1 exists because every implementer must invent scope semantics, breaking determinism and interoperability.

## Decision

**Scope is a first-class canonical dimension with explicit, versioned semantics.**

### Baseline Approach

Scope semantics are **versioned** to enable evolution while preserving backwards compatibility:

- **Version 1 (v1):** Exact string matching (baseline workaround established December 29, 2025)
- **Version 2 (v2):** Hierarchical matching on segment boundaries (defined in this ADR)

Version selection is **explicit** via `scope_semantics_version` field in Trust Registry entries and Context Bundles. No inference, no defaults beyond v1 for omitted version, no implicit upgrades.

Gateway enforces scope matching according to the declared version. No interpretation, no policy flags, no delegation toggles. Scope semantics are **mechanical and deterministic**.

This decision intentionally provides two versions: v1 as the minimal correctness-preserving baseline, and v2 as the intended hierarchical model. Organizations can adopt v1 immediately and migrate to v2 identity-by-identity without breaking existing artifacts.

## Normative Definition

### Scope Structure

**Scope** is a hierarchical, colon-delimited string identifier that:

1. **Partitions authority** - Trust Registry entries specify which scope each identity has authority over
2. **Appears in artifacts** - Canonical artifacts, relationship artifacts, and attestations are scoped
3. **Appears in Context Bundles** - Every Context Bundle specifies the scope for which execution is claimed
4. **Is verified by Gateway** - Gateway compares Context Bundle scope to Trust Registry scope using versioned matching algorithm

**Hierarchical Structure:** Scope is hierarchical with segments ordered from least specific to most specific:
- `project` (1 segment)
- `project:myapp` (2 segments)
- `project:myapp:backend` (3 segments)
- `project:myapp:backend:api` (4 segments)

**Delimiter:** Colon (`:`) separates segments. No other delimiter is permitted.

**Segment Ordering:** Left-to-right from least specific to most specific. This enables ancestor-descendant relationships in v2.

### Grammar and Validation

**Scope Format (ABNF-style):**

```
scope          = segment *(":" segment)
segment        = 1*segment-char
segment-char   = ALPHA / DIGIT / "_" / "-"
ALPHA          = "A"-"Z" / "a"-"z"
DIGIT          = "0"-"9"
```

**Validation Rules:**

**R-SCOPE-1: Scope Format Validation**

Every scope identifier MUST conform to the following rules:

- **Segment Regex:** Each segment MUST match `[A-Za-z0-9_-]+`
- **No Empty Segments:** Scope MUST NOT contain empty segments (e.g., `project::backend` is invalid)
- **No Leading/Trailing Delimiter:** Scope MUST NOT start or end with `:` (e.g., `:project` or `project:` are invalid)
- **Case-Sensitive:** Scope matching is case-sensitive in all versions
- **Maximum Length:** Total scope string MUST NOT exceed 256 characters
- **Minimum Depth:** Scope MUST contain at least 1 segment
- **Maximum Depth:** Scope MUST contain at most 8 segments

**Examples (Valid):**
- `org`
- `project:myapp`
- `project:myapp-backend`
- `project:myapp:backend:api`
- `domain:aws-iam:account-123`

**Examples (Invalid):**
- Empty string (violates minimum depth)
- `project:` (trailing delimiter)
- `:project` (leading delimiter)
- `project::backend` (empty segment)
- `project/backend` (invalid delimiter)
- `project:my app` (space not allowed)
- String exceeding 256 characters (violates maximum length)
- Scope with 9+ segments (violates maximum depth)

**Rationale:** These rules ensure scope identifiers are unambiguous, portable, and safe to use in URLs, file paths, and logging systems. Maximum depth prevents pathological hierarchies.

### Scope Semantics Versioning

**R-SCOPE-2: Scope Semantics Version Declaration**

Every Trust Registry entry MUST include `scope_semantics_version` field with value `1` or `2`.

Every Context Bundle MUST include `scope_semantics_version` field in `context_bounds` with value `1` or `2`.

**Default Behavior:** If `scope_semantics_version` is omitted:
- Trust Registry entries default to version `1` (exact match)
- Context Bundles default to version `1` (exact match)

**No Implicit Upgrades:** Gateway MUST NOT upgrade version automatically. If Trust Registry entry specifies version `1`, Gateway MUST use v1 matching even if implementation supports v2.

**Version Mismatch:** If Context Bundle `scope_semantics_version` does not match Trust Registry entry `scope_semantics_version`, Gateway MUST deny with `SCOPE_VERSION_MISMATCH`.

**Rationale:** Explicit versioning enables safe evolution. Defaults to v1 ensure backwards compatibility with artifacts created before v2 was defined.

### Version 1: Exact String Matching

**R-SCOPE-3: Version 1 Matching Algorithm**

When `scope_semantics_version = 1`, Gateway MUST perform exact, case-sensitive string equality comparison.

**Algorithm:**

```
FUNCTION MatchScopeV1(authority_scope: string, claimed_scope: string) -> bool
  RETURN authority_scope == claimed_scope  // Case-sensitive exact equality
END
```

**Match Examples:**
- Authority `project:myapp` matches claimed `project:myapp` ✓
- Authority `project:myapp` matches claimed `project:myapp` (identical) ✓

**Mismatch Examples:**
- Authority `project:myapp` does NOT match claimed `project:myapp:backend` ✗
- Authority `project:myapp` does NOT match claimed `project:myapp-backend` ✗
- Authority `project:MYAPP` does NOT match claimed `project:myapp` ✗ (case-sensitive)
- Authority `project` does NOT match claimed `project:myapp` ✗

**Rationale:** Exact matching is deterministic, implementation-neutral, and falsifiable by inspection. No interpretation required. This is the baseline established December 29, 2025, and MUST NOT change.

**Authority Resolution:** In v1, only one Trust Registry entry can match (exact match is unique). No resolution logic needed.

### Version 2: Hierarchical Matching

**R-SCOPE-4: Version 2 Matching Algorithm**

When `scope_semantics_version = 2`, Gateway MUST perform hierarchical prefix matching on segment boundaries.

**Algorithm:**

```
FUNCTION MatchScopeV2(authority_scope: string, claimed_scope: string) -> bool
  authority_segments = Split(authority_scope, ":")
  claimed_segments = Split(claimed_scope, ":")
  
  // Authority must be prefix of claimed (ancestor or equal)
  IF Length(authority_segments) > Length(claimed_segments) THEN
    RETURN false  // Authority is deeper than claimed (not an ancestor)
  END
  
  // Compare segment-by-segment
  FOR i = 0 TO Length(authority_segments) - 1 DO
    IF authority_segments[i] != claimed_segments[i] THEN
      RETURN false  // Segments don't match exactly (case-sensitive)
    END
  END
  
  RETURN true  // Authority is ancestor or equal to claimed
END
```

**Match Examples:**
- Authority `project:myapp` matches claimed `project:myapp` ✓ (equal)
- Authority `project:myapp` matches claimed `project:myapp:backend` ✓ (ancestor)
- Authority `project:myapp` matches claimed `project:myapp:backend:api` ✓ (ancestor)
- Authority `project` matches claimed `project:myapp` ✓ (ancestor)
- Authority `project` matches claimed `project:myapp:backend` ✓ (ancestor)

**Mismatch Examples:**
- Authority `project:myapp:backend` does NOT match claimed `project:myapp` ✗ (descendant, not ancestor)
- Authority `project:myapp` does NOT match claimed `project:other` ✗ (different branches)
- Authority `project:myapp-backend` does NOT match claimed `project:myapp:backend` ✗ (segment boundary matters)
- Authority `project:MYAPP` does NOT match claimed `project:myapp` ✗ (case-sensitive)

**Rationale:** Hierarchical matching enables parent authorities to cover child scopes without explicit enumeration. Segment-boundary matching prevents unintended matches (e.g., `project:myapp-backend` does not match `project:myapp` scope).

**R-SCOPE-5: Authority Resolution in Version 2**

When multiple Trust Registry entries match a claimed scope in v2 (via delegation chains or multiple authorities), Gateway MUST resolve as follows:

1. **Filter to Matching Entries:** Identify all Trust Registry entries where `MatchScopeV2(entry.Scope, claimed_scope) = true`

2. **Select Most Specific:** Among matching entries, select the one with the greatest segment depth (most segments)

3. **Example:**
   - Claimed scope: `project:myapp:backend:api`
   - Matching entries:
     - Identity A: `project` (1 segment)
     - Identity B: `project:myapp` (2 segments)
     - Identity C: `project:myapp:backend` (3 segments)
   - **Selected:** Identity C (most specific)

4. **Precedence:** More specific (deeper) authority wins. This implements principle of least privilege: narrower authority takes precedence over broader authority.

**R-SCOPE-6: Conflict Handling (Equal Depth)**

If multiple Trust Registry entries match at **equal segment depth**, Gateway MUST deny eligibility with `SCOPE_CONFLICT`.

**Conflict Example:**
- Claimed scope: `project:myapp:backend`
- Trust Registry entries:
  - Identity A: `project:myapp:backend` (3 segments)
  - Identity B: `project:myapp:backend` (3 segments)
- **Result:** DENY with `SCOPE_CONFLICT` (ambiguous authority)

**Rationale:** Equal-depth conflicts indicate misconfiguration. Two identities claiming identical scope authority is ambiguous and unsafe. Fail-closed enforcement requires explicit conflict detection and denial.

**Non-Conflict Example (Different Depths):**
- Claimed scope: `project:myapp:backend`
- Trust Registry entries:
  - Identity A: `project:myapp` (2 segments)
  - Identity B: `project:myapp:backend` (3 segments)
- **Result:** Identity B wins (more specific, no conflict)

### Environment Orthogonality

**R-SCOPE-7: Scope and Environment Are Independent Dimensions**

Scope and environment are **orthogonal** dimensions:

- **Scope** partitions authority and artifacts by organizational structure (projects, domains, services)
- **Environment** partitions canonical state by deployment context (prod, staging, dev)

**Prohibition:** Scope identifiers MUST NOT embed environment segments.

**Invalid (Environment in Scope):**
- `project:myapp:prod` (mixing scope and environment)
- `env:prod:project:myapp` (environment as scope segment)

**Valid (Separate Dimensions):**
- Scope: `project:myapp`, Environment: `prod`
- Scope: `project:myapp:backend`, Environment: `staging`

**Rationale:** Scope and environment serve different purposes. Scope determines *who* has authority; environment determines *where* canonical state applies. Mixing these dimensions creates confusion and breaks orthogonality established in ADR-025.

**Context Bundle Structure (Correct):**

```yaml
context_bounds:
  scope: project:myapp:backend
  scope_semantics_version: 2
  environment: prod  # Separate field, not part of scope
```

**Trust Registry Entry (Correct):**

```yaml
Identity: alice-project-key
Scope: project:myapp
ScopeSemanticsVersion: 2
Environment: null  # Trust Registry entries are environment-agnostic
```

**Attestation Scope (Correct):**

Attestations specify both scope and environment as independent fields:
- Scope: `project:myapp` (authority boundary)
- Environment: `prod` (canonical state partition)

Attestation in v2 with scope `project:myapp` covers execution in any descendant scope (`project:myapp:backend`, `project:myapp:frontend`) within the same environment.

## Component Responsibilities

### ADF (AI-DOC Fabric Publication Service)

**Responsibilities:**
- Assign scope identifier to every canonical artifact published
- Scope assignment determined by organizational governance policy (e.g., derived from repository path, CI/CD metadata)
- Publish attestations with explicit scope field
- Scope version determined by organizational policy (can publish v1 and v2 attestations for different scopes)

**Prohibited:**
- Inferring scope from git branch names
- Defaulting scope to wildcard or "all scopes"
- Publishing canonical artifacts without explicit scope
- Mixing environment into scope identifiers

**No New Authority:** ADF already has ORG authority to sign canonical artifacts (§6.1.1). Scope partitioning does not introduce new authority; it partitions existing authority.

### STE-Gateway

**Responsibilities:**
- Extract claimed scope and `scope_semantics_version` from Context Bundle
- Extract authority scope and `scope_semantics_version` from Trust Registry entry for signing identity
- Verify versions match; deny on version mismatch
- Execute v1 or v2 matching algorithm according to version
- Resolve authority conflicts per R-SCOPE-5 and R-SCOPE-6
- Deny eligibility on scope mismatch or conflict
- Log scope in audit trail for each eligibility decision

**Prohibited:**
- Interpreting scope semantics beyond versioned matching algorithms
- Performing case-insensitive, wildcard, or regex matching
- Inferring scope from Context Bundle metadata if scope field is missing
- Upgrading scope version implicitly
- Merging authorities from multiple scopes

**No New Authority:** Gateway already has Enforcement Authority (ADR-019). Scope matching is part of eligibility evaluation (PREREQ-6), not a new enforcement scope.

### STE-Runtime

**Responsibilities:**
- Include scope identifier in Context Bundle as provided by user, deployment configuration, or organizational policy
- Include `scope_semantics_version` in Context Bundle `context_bounds`
- Propagate scope from task metadata or execution context

**Prohibited:**
- Inferring scope if not provided (MUST fail if scope is missing)
- Defaulting scope to parent scope or wildcard
- Validating scope against Trust Registry (Gateway responsibility)

**No New Authority:** Runtime already has PROJECT authority to sign Context Bundles (§6.1.3). Scope is part of the Context Bundle claim, not a new authority grant.

### Trust Registry

**Schema Extension:** Trust Registry entries MUST include:
- `Scope`: hierarchical scope identifier
- `ScopeSemanticsVersion`: `1` or `2`

**Population:** Organizational authority service populates Trust Registry with scope assignments. Scope version determined by organizational policy (can assign different identities to different versions).

**No Changes to Authority Model:** Scope is an attribute of existing Trust Registry entries, not a new authority class.

## Versioning Strategy: v1 and v2 Coexistence

### Explicit Version Declaration

**Version Selection:**
- Trust Registry entries specify `ScopeSemanticsVersion` per identity
- Context Bundles specify `scope_semantics_version` per execution request
- Gateway verifies versions match and executes corresponding algorithm

**No Automatic Migration:**
- v1 artifacts remain v1 indefinitely unless explicitly migrated
- v2 adoption requires explicit Trust Registry updates
- No silent version upgrades

### Migration Path

Organizations can migrate from v1 to v2 identity-by-identity:

1. **Phase 1: v1 Baseline**
   - All Trust Registry entries use `ScopeSemanticsVersion: 1`
   - All Context Bundles use `scope_semantics_version: 1`
   - Exact matching enforced

2. **Phase 2: Incremental v2 Adoption**
   - Update Trust Registry entries for selected identities to `ScopeSemanticsVersion: 2`
   - Updated identities can now sign Context Bundles with `scope_semantics_version: 2`
   - v1 identities continue using exact matching
   - Both versions coexist

3. **Phase 3: Full v2 (Optional)**
   - All Trust Registry entries migrated to `ScopeSemanticsVersion: 2`
   - All Context Bundles use `scope_semantics_version: 2`
   - Hierarchical matching enforced globally

**Coexistence Safety:**
- v1 and v2 Context Bundles can coexist in same environment
- Gateway handles each according to declared version
- No cross-version confusion (versions are explicit)

**Version Mismatch Handling:**
- If Context Bundle specifies v2 but signing identity is v1: DENY with `SCOPE_VERSION_MISMATCH`
- If Context Bundle specifies v1 but signing identity is v2: DENY with `SCOPE_VERSION_MISMATCH`
- Versions MUST match exactly (no implicit compatibility)

## Relationship to Fabric Attestations

**Attestation Scope Field:** Attestations include scope as explicit field:

```yaml
attestation:
  scope: project:myapp
  scope_semantics_version: 2
  environment: prod
  timestamp: 2025-12-29T10:00:00Z
  invariants: [...]
```

**v1 Attestations:**
- Cover single exact scope only
- Context Bundle scope MUST match attestation scope exactly
- Example: Attestation with scope `project:myapp` authorizes Context Bundle with scope `project:myapp` ONLY

**v2 Attestations:**
- Cover claimed scope and all descendant scopes
- Context Bundle scope can be equal to or descendant of attestation scope
- Example: Attestation with scope `project:myapp` authorizes Context Bundles with scopes:
  - `project:myapp` ✓
  - `project:myapp:backend` ✓
  - `project:myapp:frontend` ✓
  - `project:other` ✗ (different branch)

**No Wildcards in v2:** v2 hierarchical matching covers descendants implicitly. No wildcard syntax needed or permitted.

**Authority Resolution:** If multiple attestations match (v2 only), most specific (deepest) attestation wins per R-SCOPE-5.

## Relationship Artifacts

**Scoping:** Relationship artifacts (ADR-018) are scoped:

```yaml
relationship:
  from: {domain: service, type: api-endpoint, id: GET-/users}
  to: {domain: data, type: database-table, id: users}
  scope: project:myapp:backend
  scope_semantics_version: 2
  relationship_type: reads
```

**Cross-Scope Relationships Permitted:**

Relationship artifacts MAY reference elements from different scopes:

```yaml
relationship:
  from: {domain: service, type: lambda, id: order-processor, scope: project:orders}
  to: {domain: service, type: sqs-queue, id: payment-queue, scope: project:payments}
  scope: project:orders  # Relationship artifact's own scope
  relationship_type: publishes_to
```

**Rationale:** Scope is a **provenance dimension** (who asserted this relationship), not a **containment constraint** (what elements can be related). Cross-scope edges are valid and necessary for modeling distributed systems.

**Authority Verification:** Relationship artifact signature is verified against Trust Registry entry for the artifact's own scope, not the scopes of referenced elements.

**Scope Does NOT:**
- Constrain which elements can be endpoints of a relationship
- Partition the semantic graph (graph is global; scope is provenance)
- Prevent queries across scope boundaries

**Scope DOES:**
- Determine which identity can sign relationship artifact
- Partition authority over relationship assertions
- Enable provenance tracking (who claimed this edge exists)

## Threat Model Implications

### Attacks This Prevents

**1. Scope Escalation via Parent Authority**

**Attack (v1):** Attacker with authority over `project:myapp` attempts to execute in scope `project:myapp:backend`, expecting hierarchical inheritance.

**Prevention (v1):** v1 uses exact matching. `project:myapp` ≠ `project:myapp:backend`. Eligibility denied.

**Attack (v2):** Attacker with authority over `project:myapp:backend` attempts to execute in parent scope `project:myapp`.

**Prevention (v2):** v2 requires authority to be ancestor or equal. `project:myapp:backend` is descendant of `project:myapp`, not ancestor. Match fails, eligibility denied.

**2. Scope Substitution in Context Bundle**

**Attack:** Attacker modifies Context Bundle scope from `project:myapp:backend` to `project:myapp` after signing, attempting to bypass scope verification.

**Prevention:** Scope is part of signed Context Bundle. Signature verification fails when scope is modified.

**3. Version Confusion Attack**

**Attack:** Attacker with v1 authority (exact match) crafts v2 Context Bundle, expecting hierarchical matching to grant broader access.

**Prevention:** Gateway enforces version match. Context Bundle v2 with Trust Registry v1 results in `SCOPE_VERSION_MISMATCH` denial.

**4. Equal-Depth Ambiguity Exploitation**

**Attack (v2):** Organization mistakenly creates two Trust Registry entries with identical scope. Attacker exploits ambiguity to bypass controls.

**Prevention:** R-SCOPE-6 requires DENY on equal-depth conflicts. Gateway detects ambiguity and fails closed.

### Attacks This Does NOT Prevent

**1. Authorized Execution in Wrong Scope**

**Scenario:** Attacker with valid authority over `project:myapp` executes in scope `project:myapp` but references artifacts outside their intended scope.

**Not Prevented:** Scope matching verifies authority boundary, not artifact content. Attacker's authority is valid; execution succeeds.

**Mitigation (Out of Scope):** Artifact-level access controls, least-privilege scope assignment. Scope semantics verify authority, not artifact ownership.

**2. Approved Bypass via Valid Authority**

**Scenario:** Attacker obtains valid Trust Registry entry for broad scope (e.g., `project`) and exploits hierarchical matching in v2 to access all descendant scopes.

**Not Prevented:** Broad scope authority is valid. Gateway correctly permits descendant scope access per v2 semantics.

**Mitigation (Out of Scope):** Organizational policy limits broad scope grants. Scope semantics enforce declared authority, not organizational intent.

**3. Cross-Scope Data Leakage**

**Scenario:** Attestation for scope `project:myapp` includes invariants that reference elements in scope `project:other`. Attacker infers information across scopes.

**Not Prevented:** Scope does not constrain attestation content. Cross-scope references in attestations are permitted (necessary for modeling dependencies).

**Mitigation (Out of Scope):** Attestation content validation, organizational policy on cross-scope references. Scope semantics partition authority, not data visibility.

## Consequences

### Positive

**1. Deterministic Scope Matching**

Given identical Trust Registry entry (scope, version) and Context Bundle (scope, version), all compliant Gateway implementations produce identical PREREQ-6 verification outcomes.

**Falsifiable:** Replay scope matching on different Gateway instances; outcomes must match.

**2. Explicit Authority Boundaries**

Scope version and structure are explicit. No hidden interpretation, no inference, no policy flags.

**Falsifiable:** Inspect Trust Registry entry and Context Bundle; authority boundaries are immediately visible.

**3. Safe v1/v2 Coexistence**

v1 and v2 can coexist without ambiguity. Version mismatch results in denial, preventing confusion.

**Falsifiable:** Submit v1 Context Bundle with v2 Trust Registry entry; Gateway must deny.

**4. No Wildcards Required**

v2 hierarchical matching provides parent coverage without wildcard syntax, reducing complexity and ambiguity.

**5. Mechanical Authority Resolution**

R-SCOPE-5 provides deterministic resolution when multiple authorities match (most specific wins). R-SCOPE-6 fails closed on conflicts.

**Falsifiable:** Create conflict scenario (equal depth); Gateway must deny.

**6. Environment Independence**

Scope and environment remain orthogonal (R-SCOPE-7), preserving ADR-025 semantics.

### Negative

**1. No Tolerance for Scope Naming Inconsistencies**

If organization uses `project:myapp`, `project:my-app`, and `project:my_app` inconsistently, exact matching (v1) and segment matching (v2) cause denials.

**Mitigation:** Organizational governance establishes canonical scope naming conventions.

**2. v2 Parent Authority Grants Broad Access**

In v2, authority over `project` grants authority over all descendant scopes (`project:myapp`, `project:other`, etc.). Broad scopes have broad authority.

**Mitigation:** Organizational policy limits broad scope grants. Prefer narrow scopes (principle of least privilege).

**3. Migration Requires Explicit Updates**

Migrating from v1 to v2 requires updating Trust Registry entries and Context Bundles. No automatic migration.

**Mitigation:** Migration can be incremental (identity-by-identity). v1 and v2 coexist safely.

**4. Segment Depth Limit (8 Segments)**

Maximum depth of 8 segments may be insufficient for very deep organizational hierarchies.

**Mitigation:** 8 segments typically sufficient (e.g., `org:division:department:team:project:service:component:subcomponent`). Limit prevents pathological hierarchies.

**5. No Wildcard Syntax**

v2 covers descendants implicitly but does not support pattern matching (e.g., `project:myapp-*`). Sibling scopes require separate authorities.

**Mitigation:** Hierarchical structure typically sufficient. Wildcard patterns deferred to future work if needed.

### Neutral

**1. Scope Naming Is Organizational Concern**

Specification defines structure and matching, not naming conventions. Organizations define scope identifiers.

**Implication:** Interoperability requires organizations to document scope hierarchies. No universal registry exists.

**2. Scope Version Selection Is Policy Decision**

Specification provides v1 and v2; organizations choose which to adopt and when.

**Implication:** v2 provides more flexibility but requires careful authority design. v1 is simpler but less expressive.

## Alternatives Considered

| Alternative | Pros | Cons | Rejection Rationale |
|-------------|------|------|---------------------|
| **Flat String Scopes (v1 Only)** | Simplest; no hierarchy; exact match only | Cannot model organizational hierarchies; requires explicit enumeration of all scopes; no parent coverage | Insufficient for real-world organizational structures. Parent teams need authority over descendant projects without explicit enumeration. |
| **Wildcard Matching** (`project:myapp-*`, `project:*`) | Flexible pattern matching; can match siblings | Introduces ambiguity (greedy vs. non-greedy); precedence unclear; wildcard semantics vary (glob vs. regex) | Deferred to future work. Wildcards introduce interpretation. Hierarchical matching covers most use cases without wildcards. |
| **Regex-Based Matching** | Maximum flexibility; can express complex patterns | Non-deterministic (backtracking); performance varies; regex semantics vary by engine; unsafe (ReDoS attacks) | Rejected. Regex matching is not deterministic, not falsifiable by inspection, and introduces security risks. |
| **URI-Based Scopes** (`urn:project:myapp`, `https://org.com/projects/myapp`) | Standards-compliant; interoperable with web technologies | Complex parsing; URI semantics introduce ambiguity (relative vs. absolute, query strings, fragments); overkill for internal identifiers | Rejected. Scope is internal identifier, not web resource. URI complexity unnecessary. |
| **Implicit Hierarchy (Slash-Delimited)** (`project/myapp/backend`) | Familiar (file path-like) | Conflicts with file paths in artifact references; slash requires URL encoding in some contexts | Rejected. Colon is unambiguous, does not conflict with file paths, and does not require encoding. |
| **JSON Object Scopes** (`{"org": "acme", "project": "myapp"}`) | Structured; supports multiple dimensions | Complex serialization; order-dependent hashing for signatures; difficult to use in URLs and logs | Rejected. String-based scope is simpler, more portable, and sufficient for hierarchical modeling. |
| **Implicit Version Upgrade** (v1 artifacts auto-upgrade to v2) | No explicit migration; smoother transition | Non-deterministic (when does upgrade occur?); breaks v1 semantics retroactively; cannot distinguish v1 and v2 artifacts | Rejected. Implicit upgrades violate determinism. Explicit versioning required for safe coexistence. |
| **Hierarchical Matching Only (No v1)** | Simpler (single version); no version management | Breaks December 29 v1 baseline; requires immediate migration; no backwards compatibility | Rejected. v1 is established baseline and must not change. v2 is optional evolution. |

**Decision:** Hierarchical colon-delimited scopes with explicit v1/v2 versioning. Trades flexibility (no wildcards) for determinism and simplicity.

## Future Work (Explicitly Deferred)

The following features are **intentionally omitted** and deferred to future ADRs:

### 1. Wildcard Scope Matching

**Deferred Capability:** Authority scope `project:myapp-*` matches `project:myapp-backend`, `project:myapp-frontend`, etc.

**Why Deferred:** Wildcards introduce pattern matching (glob vs. regex), precedence (specific vs. wildcard), and ambiguity (overlapping patterns). v2 hierarchical matching covers most use cases.

**Future ADR Required:** Define wildcard syntax, matching algorithm, and precedence rules. Ensure determinism preserved.

### 2. Multi-Version Compatibility

**Deferred Capability:** Context Bundle v2 can execute against Trust Registry v1 entry with automatic compatibility translation.

**Why Deferred:** Introduces implicit behavior and version confusion. Explicit version matching required for v1.

**Future ADR Required:** Define compatibility matrix and translation rules if needed.

### 3. Scope Aliases

**Deferred Capability:** Trust Registry defines `project:my-app` as alias for `project:myapp`; Gateway treats as equivalent.

**Why Deferred:** Aliases require centralized registry, canonical name selection, and update propagation. Introduces indirection.

**Future ADR Required:** Define alias registry, canonical name semantics, and Gateway resolution logic.

### 4. Dynamic Scope Resolution

**Deferred Capability:** Gateway resolves scope at execution time based on Context Bundle metadata (e.g., git branch, deployment target).

**Why Deferred:** Dynamic resolution introduces non-determinism, hidden logic, and dependency on external state.

**Future ADR Required:** Define resolution algorithm, determinism guarantees, and caching semantics.

### 5. Cross-Scope Authority Delegation

**Deferred Capability:** Authority over `project:myapp` can explicitly delegate subset of authority to `project:other` (cross-branch delegation).

**Why Deferred:** Introduces complex delegation chains across hierarchy boundaries. Unclear precedence and revocation semantics.

**Future ADR Required:** Define delegation model, verification algorithm, and revocation mechanism.

### 6. Scope Depth Beyond 8 Segments

**Deferred Capability:** Support scopes with 9+ segments for very deep organizational hierarchies.

**Why Deferred:** 8 segments sufficient for most organizations. Limit prevents pathological hierarchies and complexity.

**Future ADR Required:** Justify need, analyze performance implications, and define new maximum.

All deferred features require **separate ADRs** and **must preserve determinism, falsifiability, and explicit semantics**. Convenience features that introduce ambiguity or hidden logic are **permanently rejected**, not merely deferred.

## Final Validation Clause

A compliant STE-System implementation and a reasonable reader of this ADR **must not** infer or conclude that:

### Prohibited Inferences

- [ ] **Scope can be inferred** from artifact metadata, git branches, or deployment context
- [ ] **Scope can be defaulted** to wildcard or omitted from Trust Registry or Context Bundle
- [ ] **Scope is optional** or metadata rather than a canonical dimension participating in authority boundaries
- [ ] **Scope matching is case-insensitive**, wildcard-based, or subject to interpretation beyond versioned algorithms
- [ ] **Scope versions can be mixed** (v1 Context Bundle with v2 Trust Registry entry is valid)
- [ ] **Scope and environment can be combined** (environment embedded in scope segments)
- [ ] **Scope constrains graph topology** (relationships cannot cross scope boundaries)
- [ ] **Gateway interprets scope semantics** beyond mechanical matching per R-SCOPE-3 and R-SCOPE-4
- [ ] **v1 behavior can change** to support hierarchical matching without explicit v2 adoption
- [ ] **Authority resolution is ambiguous** when multiple authorities match at equal depth (must DENY per R-SCOPE-6)

### Required Behaviors

A compliant implementation **must** exhibit the following falsifiable behaviors:

1. **Validate scope format** - Reject scopes violating R-SCOPE-1 (invalid characters, empty segments, excessive depth)
2. **Enforce version declaration** - Reject Context Bundles without `scope_semantics_version` (or default to v1)
3. **Perform exact matching in v1** - `project:myapp` ≠ `project:myapp:backend`; no hierarchical inference
4. **Perform hierarchical matching in v2** - `project:myapp` matches `project:myapp:backend` (ancestor relationship)
5. **Deny on version mismatch** - Context Bundle v1 with Trust Registry v2 results in `SCOPE_VERSION_MISMATCH`
6. **Resolve to most specific authority in v2** - When multiple authorities match, select deepest (most segments)
7. **Deny on equal-depth conflicts** - Two authorities at same depth both matching claimed scope results in `SCOPE_CONFLICT`
8. **Preserve environment orthogonality** - Scope `project:myapp` applies independently in environments `prod` and `staging`
9. **Log scope in audit trail** - Every eligibility decision records claimed scope, authority scope, and version
10. **Permit cross-scope relationships** - Relationship artifact from scope A can reference elements in scope B

These behaviors are **testable, observable, and falsifiable** by inspection or replay.

## Related Decisions

- **ADR-025: Environment Semantics** - Establishes environment as orthogonal dimension to scope. This ADR ensures scope does not embed environment (R-SCOPE-7).
- **ADR-019: Gateway Authority and Signing Model** - Establishes Gateway enforces but does not attest. This ADR establishes Gateway enforces scope matching (PREREQ-6) but does not define scope semantics.
- **ADR-018: Relationship Artifacts** - Establishes relationship artifacts are scoped. This ADR clarifies scope does not constrain edge endpoints.
- **ADR-021: Gateway Trust Verification Model** - Establishes Trust Registry verification algorithm. This ADR extends Trust Registry schema with `ScopeSemanticsVersion` field.

## Traceability

**Closes Gap:** GAP-1 (Scope Semantics Definition / Blocker 1.4) from STE Specification Gap Analysis and Blocker Resolution Phases

**Requirements:**
- §8.1.2 PREREQ-6 (Authority Scope Match) - now fully algorithmically defined
- §6.2.1 Trust Registry Structure - extended with `ScopeSemanticsVersion` field
- §8.1.3 CEM Envelope - extended with `scope_semantics_version` field
- §8.1.4 Eligibility Evaluation STEP 6 - now includes explicit v1/v2 algorithms

**Views:**
- `specifications/ste-system.iso42010.md` §6.2 (Trust Registry)
- `specifications/ste-system.iso42010.md` §8.1 (Execution Eligibility Contract)
- `specifications/ste-system.iso42010.md` §9.1 (Context Bundles)

**Stakeholders:**
- ADF Implementers (must assign scope to artifacts and attestations)
- Gateway Implementers (must enforce scope matching per PREREQ-6)
- Runtime Implementers (must include scope in Context Bundles)
- Security/Compliance Teams (scope partitions authority)
- Enterprise Architects (scope models organizational structure)

---

**Last Updated:** 2025-12-29  
**Status:** Accepted  
**Next Review:** After v1 Implementation Feedback


