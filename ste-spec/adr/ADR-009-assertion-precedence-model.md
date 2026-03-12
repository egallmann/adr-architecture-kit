# ADR-009: Assertion Precedence Model

## Status

Accepted

## Context

AI-DOC Fabric generates architectural documentation through two mechanisms:

1. **Automated Extraction**: Extractors analyze deployment artifacts and generate slices
2. **Manual Assertions**: Humans declare relationships that exist outside extractable code

Both mechanisms can describe the same architectural elements or relationships, leading to potential conflicts:

- Extractor finds service A depends on database X
- Human asserts service A depends on database Y
- Both cannot be fully correct

The system must define clear rules for:

1. **When assertions supplement extraction** (adding information)
2. **When assertions conflict with extraction** (contradictory information)
3. **How queries resolve conflicts** (which fact to return)
4. **How assertions expire** (time-based validity)
5. **How governance works** (who can assert, what evidence is required)

Without explicit precedence rules, users cannot trust query results or reason about correctness.

### The Problem

**Scenario 1: Supplemental Assertion**

Extractor cannot detect that service A calls third-party Stripe API (payment processing happens in Stripe's SaaS, not in code). Human asserts:

```yaml
assertion:
  source: service-a
  target: stripe-api
  relationship: depends_on
  evidence: https://docs.company.com/stripe-integration
```

This supplements extraction (adds information). No conflict.

---

**Scenario 2: Corrective Assertion**

Extractor incorrectly infers service A depends on database X (false positive from commented-out code). Human asserts:

```yaml
assertion:
  source: service-a
  target: database-x
  relationship: does_not_depend_on
  evidence: https://jira.company.com/TICKET-1234
```

This contradicts extraction. Which is correct?

---

**Scenario 3: Runtime Configuration**

Extractor finds service A hardcoded to connect to database X in source code. Human asserts service A actually connects to database Y (environment variable overrides hardcoded value in production). Both are correct in different contexts.

---

**Scenario 4: Time-Bound Assertion**

Human asserts service A depends on legacy-system-z because migration is in progress. Migration completes two weeks later. Extractor finds no reference to legacy-system-z. Assertion is now stale.

---

### Requirements

The precedence model must:

- **Preserve extracted facts**: Do not silently discard extraction results
- **Honor human knowledge**: Humans may have information extractors cannot capture
- **Track provenance**: Users must see source of each fact (extracted vs. asserted)
- **Handle temporal validity**: Assertions should expire when no longer relevant
- **Require evidence**: All assertions must provide supporting documentation
- **Enable governance**: System must audit who asserted what and when

## Decision

AI-DOC Fabric implements **coexistence with explicit conflict detection** governed by the following rules:

### Rule 1: Extracted and Asserted Facts Coexist

**Both extracted slices and manual assertions are stored with full provenance.**

- Extractors produce slices with `provenance.source: extracted`
- Humans submit assertions stored as slices with `provenance.source: asserted`
- Neither automatically overrides the other

**Rationale**: Preserving both enables users to make informed judgments. Automatic precedence rules cannot account for all scenarios.

---

### Rule 2: Queries Return Both With Provenance

**By default, queries return both extracted and asserted facts, tagged with provenance.**

Query response format:

```yaml
query: "What does service-a depend on?"
results:
  - id: database-x
    domain: data
    type: table
    provenance:
      source: extracted
      evidence:
        file: src/service_a/db.py
        line: 15
        extractor: python-ast
        extractor_version: 1.2.0
        extracted_at: 2025-12-18T10:30:00Z
  - id: stripe-api
    domain: integration
    type: client
    provenance:
      source: asserted
      evidence:
        assertion_id: assert-001
        asserting_party: alice@example.com
        asserted_at: 2025-12-15T14:00:00Z
        evidence_url: https://docs.company.com/stripe
        scope: prod
```

**Users decide which facts to trust based on provenance.**

---

### Rule 3: Conflicts Are Detected and Surfaced

**When extracted and asserted facts contradict, queries include a `conflicts` section.**

Conflict triggers:

1. **Dependency Conflict**: Extracted says "A depends on X", asserted says "A depends on Y"
2. **Negation Conflict**: Extracted says "A depends on X", asserted says "A does not depend on X"
3. **Attribute Conflict**: Extracted says endpoint is `GET /api/users`, asserted says it is `GET /api/v2/users`

**Conflict Response Format**:

```yaml
conflicts:
  - type: dependency_conflict
    element: service-a
    extracted:
      dependency: database-x
      evidence:
        file: src/service_a/db.py
        line: 15
    asserted:
      dependency: database-y
      evidence:
        assertion_id: assert-002
        asserting_party: bob@example.com
        evidence_url: https://jira.company.com/TICKET-1234
    recommendation: "Verify source code matches deployment configuration. If database-y is correct, update source code or investigate runtime config override."
```

**Rationale**: Conflicts indicate either extractor bugs, stale assertions, or complex runtime behavior. Users must investigate.

---

### Rule 4: Assertions Require Evidence

**Every manual assertion must provide evidence.**

Required assertion fields:

- `relationship`: What is being asserted (depends_on, exposes_endpoint, stores_in, etc.)
- `source`: Source element (service, module, etc.)
- `target`: Target element (database, API, etc.)
- `evidence_url`: Link to ticket, design doc, contract, or other supporting documentation
- `asserting_party`: Who made the assertion (email or user ID)
- `scope`: Environment and validity (prod, non-prod, all)
- `valid_until` (optional): Expiration date for time-bound assertions

**Assertions without evidence are rejected at submission.**

---

### Rule 5: Assertions Can Expire

**Time-bound assertions include `valid_until` timestamp.**

Behavior:

1. **Active Assertions**: `valid_until` is null or in the future → Included in query results
2. **Expired Assertions**: `valid_until` is in the past → Excluded from query results by default
3. **Query for Expired**: Users can query expired assertions via `include_expired=true` parameter

**Use Case**: Temporary dependencies during migration, pilot integrations, time-limited SaaS trials.

**Example**:

```yaml
assertion:
  relationship: depends_on
  source: service-a
  target: legacy-system-z
  evidence_url: https://jira.company.com/MIGRATION-PLAN
  valid_until: 2025-06-30T23:59:59Z  # Migration completes by this date
```

---

### Rule 6: Negation Assertions Suppress Extraction

**Assertions can explicitly negate extracted facts.**

Use case: Extractor false positives (commented-out code, dead imports, test fixtures mistaken for production code).

**Negation Assertion Format**:

```yaml
assertion:
  relationship: does_not_depend_on
  source: service-a
  target: database-x
  evidence_url: https://jira.company.com/FALSE-POSITIVE
  reason: "Import is in commented-out legacy code. Service does not actually use database-x."
```

**Behavior**:

- Queries by default exclude edges negated by assertions
- Users can query with `include_negated=true` to see both extracted and negated facts
- Negated facts remain in storage for auditability

**Rationale**: Enables correction of extractor false positives without modifying extraction logic or source code.

---

### Rule 7: Assertion Governance and Audit

**All assertions are auditable with full provenance.**

Stored metadata:

- `assertion_id`: Unique identifier (UUID)
- `asserting_party`: Who made the assertion (authenticated user)
- `asserted_at`: Timestamp
- `evidence_url`: Required supporting documentation
- `scope`: Environment (prod, non-prod, all)
- `review_status`: Optional (pending, approved, rejected)
- `reviewed_by`: Optional (if governance workflow exists)

**Audit Queries**:

- "Show all assertions made by user X"
- "Show all assertions without approval"
- "Show all expired assertions"
- "Show all assertions for service Y"

**Rationale**: Governance and compliance teams need visibility into who asserted what and why.

---

### Rule 8: Extracted Facts Cannot Be Deleted, Only Supplemented

**Extraction results are immutable.**

- Humans cannot delete slices produced by extractors
- Humans can negate extraction via `does_not_depend_on` assertions
- Humans can supplement extraction with additional facts

**Rationale**: Preserves auditability. If extraction produced wrong results, root cause is extractor bug or source code issue, not missing assertion.

---

## Consequences

### Positive

**No Information Loss**: Both extracted and asserted facts are preserved. Users make informed decisions.

**Conflict Transparency**: System explicitly surfaces conflicts rather than silently choosing one source over the other.

**Auditability**: Full provenance tracking enables debugging and compliance reporting.

**Temporal Validity**: Time-bound assertions handle transient dependencies without polluting long-term state.

**Negation Capability**: Users can correct false positives without modifying extractors or source code.

**Governance Enabled**: Assertion metadata supports approval workflows and audit trails.

### Negative

**User Responsibility**: Users must interpret conflicts and decide which facts to trust. System does not automatically resolve.

**Complexity in Queries**: Query responses include provenance and conflict sections, increasing payload size and parsing complexity.

**Assertion Maintenance**: Humans must update or expire assertions when reality changes. Stale assertions can mislead.

**Governance Overhead**: If organizations implement approval workflows, assertion submission becomes slower.

### Neutral

**Provenance-First Design**: Queries always include provenance. Cannot disable (intentional design choice).

**Negation as Assertion**: Negating extracted facts requires explicit assertion (cannot implicitly delete extraction results).

## Alternatives Considered

### Alternative 1: Assertions Always Override Extraction

**Approach**: When assertion conflicts with extraction, assertion wins. Extracted fact is hidden.

**Rejected Because**:
- Silently discards extraction results (reduces auditability)
- Assumes humans are always correct (they are not)
- Removes ability to detect conflicts and investigate root cause

### Alternative 2: Extraction Always Overrides Assertions

**Approach**: Extraction is truth. Assertions are ignored when conflicts arise.

**Rejected Because**:
- Extractors cannot capture runtime configuration, SaaS dependencies, or organizational policies
- Removes value of manual assertions (users cannot supplement extraction)

### Alternative 3: Automatic Conflict Resolution Based on Recency

**Approach**: Most recent fact (extracted or asserted) wins.

**Rejected Because**:
- Recency is not a proxy for correctness
- Extraction may run daily; assertion may be weeks old but still correct
- Users lose visibility into conflicting information

### Alternative 4: Approval Workflow for All Assertions

**Approach**: All assertions require approval from designated approvers before appearing in queries.

**Rejected Because**:
- Adds latency and overhead for all assertions (even low-risk supplemental ones)
- Organizations vary in governance needs; some do not require approval
- Can be implemented as optional layer (not enforced by core system)

**Future Option**: Organizations can build approval workflows on top of core assertion API. Assertions marked `review_status: pending` can be filtered out until approved.

## Related Decisions

- [ADR-006: Explicit Unknowns](./ADR-006-explicit-unknowns.md) - Unknowns are distinct from assertions
- [ADR-008: Correctness and Consistency Contract](./ADR-008-correctness-consistency-contract.md) - Consistency model for extracted and asserted facts
- [Governance Architecture](../03-cross-cutting-concerns/governance-architecture.md) - Assertion governance details

## Implementation Notes

### Assertion API Requirements

Ingestion API must:

- Validate required fields (relationship, source, target, evidence_url, asserting_party)
- Reject assertions without evidence
- Authenticate asserting party (SSO or IAM)
- Store assertions with full metadata
- Emit `fabric.assertion.created` event

### Query API Requirements

Intelligence API must:

- Return both extracted and asserted facts by default
- Tag each result with provenance
- Detect conflicts and include `conflicts` section in response
- Support filtering: `source=extracted`, `source=asserted`, `include_expired=true`, `include_negated=true`
- Log all queries for audit

### Storage Requirements

Assertions stored as slices with:

- `provenance.source: asserted`
- `provenance.assertion_id`: UUID
- `provenance.asserting_party`: User ID
- `provenance.asserted_at`: Timestamp
- `provenance.evidence_url`: Required
- `provenance.valid_until`: Optional
- `provenance.scope`: Environment

### Event Schema Requirements

`fabric.assertion.created` event includes:

- `assertion_id`
- `asserting_party`
- `relationship`
- `source` and `target`
- `evidence_url`
- `scope`

## Traceability

- **Requirements**: [BR-006: Provenance and Auditability](../01-context/business-requirements.md#br-006)
- **Stakeholders**: Development Teams, Security/Compliance Teams, Enterprise Architects
- **Depth-6 Concern**: #4 - Manual Assertions Governance
- **Related Views**: [Governance Architecture](../03-cross-cutting-concerns/governance-architecture.md), [Intelligence API](../05-interface-specifications/intelligence-api.md)

---

**Decision Date**: 2025-12-19  
**Last Updated**: 2025-12-19  
**Status**: Accepted





