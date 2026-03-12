# ADR-008: Correctness and Consistency Contract

## Status

Accepted

## Context

AI-DOC Fabric stores architectural state extracted from deployment artifacts. Users query this state with the expectation that results are accurate and trustworthy. However, the system operates in a distributed environment where partial failures, concurrent updates, and replication lag are inevitable.

The system must define explicit guarantees about:

1. **Correctness**: What does it mean for extracted data to be "correct"?
2. **Consistency**: What consistency model do queries observe?
3. **Partial Failures**: How does the system behave when extraction partially fails?
4. **Replication**: How does multi-region replication impact query results?
5. **Reconciliation Overlap**: What happens when multiple recon jobs target overlapping scopes?

Without explicit guarantees, users cannot trust results or reason about system behavior during failures.

### The Problem

**Scenario 1: Partial Extraction Failure**

A repository has 50 files. Extraction succeeds for 48 files but fails for 2 files (syntax errors, unsupported constructs). What should queries return?

- **Option A**: Return 48 slices, mark repository as "partially extracted" with unknowns
- **Option B**: Fail entire extraction, return nothing
- **Option C**: Return 48 slices, silently ignore 2 failures

**Scenario 2: Concurrent Reconciliations**

Two recon jobs target overlapping scopes:
- Job 1: Recon-incremental for commit `abc123`
- Job 2: Recon-full for same repository

Job 2 starts before Job 1 completes. Which slices should queries return while both jobs are running?

**Scenario 3: Multi-Region Replication Lag**

A slice is updated in us-east-1. Replication to eu-west-1 takes 2 seconds. A query in eu-west-1 during replication lag returns stale data. Is this acceptable?

**Scenario 4: Extract vs. Asserted Conflicts**

An extractor finds `service-a` depends on `database-x`. A manual assertion claims `service-a` depends on `database-y`. Both cannot be fully correct. Which is returned in queries?

### Requirements

The system must:

- **Define correctness explicitly**: What does "correct" mean for extracted slices?
- **Provide consistency guarantees**: What can users rely on?
- **Handle partial failures gracefully**: Users need partial data more than no data
- **Distinguish extracted from asserted facts**: Provenance matters
- **Document limitations**: Where guarantees do not hold

## Decision

AI-DOC Fabric provides the following guarantees:

### Correctness Definition

**A slice is correct if it accurately reflects the source artifact at the specified version.**

Correctness is validated through:

1. **Deterministic extraction**: Same artifact + same extractor version → same slice
2. **Provenance tracking**: Every slice records source file, line number, extractor version
3. **Spot-check validation**: Quarterly manual review of random sample (50 slices)

**Not Guaranteed**:
- Runtime behavior matching extracted state (system captures deployment-time state, not runtime state)
- Completeness of extraction (extractors may miss edge cases in complex code)

**Implication**: Users trust slices to reflect source artifacts but understand extraction may be incomplete for complex constructs.

---

### Consistency Model

**Eventual consistency with version-scoped reads.**

**Guarantees**:

1. **Version-Scoped Consistency**: Queries specifying a version (commit SHA, timestamp) see a consistent snapshot of that version once extraction completes.

2. **Environment-Scoped Consistency**: Queries for an environment see slices from the most recently completed extraction for that environment.

3. **Cross-Region Eventual Consistency**: Multi-region deployments use DynamoDB Global Tables (eventual consistency, last-writer-wins). Queries may observe replication lag (<2 seconds typical, <10 seconds maximum).

4. **No Read-Your-Writes Guarantee**: After triggering extraction, queries may not immediately see new slices. Users must wait for `fabric.recon.completed` event before querying.

**Not Guaranteed**:
- Strong consistency across regions (eventual consistency model)
- Immediate visibility after extraction trigger (async processing)
- Transactional updates across multiple slices (slices updated individually)

**Implication**: Users design query workflows to wait for completion events. Dashboards refresh periodically rather than expecting real-time updates.

---

### Partial Failure Handling

**Partial extraction succeeds; failures are marked explicitly.**

**Behavior**:

1. **Per-File Granularity**: Extraction failures are isolated to individual files. If file X fails, files Y and Z still produce slices.

2. **Unknown Markers**: Failed extractions emit slices with `extraction_status: partial` and `unknowns` listing what could not be extracted.

3. **Completion Event Indicates Partial**: `fabric.recon.completed` event includes:
   - `status: partial` if any files failed
   - `failed_files: [...]` listing failures
   - `failure_reasons: [...]` providing diagnostics

4. **Query Results Include Partials**: Queries return slices from successful extractions. Users can filter by `extraction_status` to exclude partials if desired.

**Rationale**: Partial data is more useful than no data. Users need visibility into what succeeded and what failed.

**Example**:

```yaml
_slice:
  id: auth-service-module
  domain: graph
  type: module
  extraction_status: partial
  unknowns:
    - type: extraction_failure
      file: src/auth/legacy.py
      reason: "SyntaxError: invalid syntax at line 42"
      impact: "Dependencies from this file are not captured"
```

**User-Visible Guarantee**: "If extraction completes (even partially), you will get slices for everything that succeeded plus explicit unknowns for everything that failed."

---

### Reconciliation Overlap Rules

**Last-completed-wins with job lifecycle tracking.**

**Behavior**:

1. **Concurrent Jobs Allowed**: Multiple recon jobs can target overlapping scopes. No locking or serialization.

2. **Slice Versioning**: Each slice version is immutable. New extraction creates new version with new timestamp.

3. **Current Pointer Update**: The `current_pointers` table tracks the latest version per environment. Updated atomically when job completes.

4. **Last-Completed-Wins**: If two jobs complete for the same scope, the job that completes last determines the "current" version.

5. **Job Metadata Visible**: Users can query job history to see which job produced which slices.

**Rationale**: Locking is operationally complex and error-prone. Last-completed-wins is simple and predictable. In practice, concurrent jobs are rare (incremental recon is fast; full recon is scheduled or manually triggered).

**Edge Case**:
- Job 1 (full recon) starts at T=0, completes at T=10
- Job 2 (incremental recon) starts at T=5, completes at T=6

Result: Job 1's slices become "current" at T=10, overwriting Job 2's slices. Job 2's slices remain in version history.

**User-Visible Guarantee**: "Queries see slices from the most recently completed job for the environment."

---

### Extracted vs. Asserted Conflict Resolution

**Both are stored; queries distinguish by provenance.**

**Behavior**:

1. **No Automatic Precedence**: Extracted slices and manual assertions coexist. Neither automatically overrides the other.

2. **Provenance Tracking**: Every slice and edge records whether it was extracted or asserted.

3. **Query-Time Filtering**: Users can filter results by provenance:
   - `source=extracted` - Only extraction-derived facts
   - `source=asserted` - Only manual assertions
   - `source=all` (default) - Both

4. **Conflict Warnings**: When a query returns conflicting edges (extracted says X, asserted says Y), the response includes a `conflicts` section listing both with provenance.

**Example Conflict**:

```yaml
query: "What does service-a depend on?"
results:
  - id: database-x
    source: extracted
    evidence:
      file: src/service_a/db.py
      line: 15
  - id: database-y
    source: asserted
    evidence:
      ticket: JIRA-1234
      asserting_party: alice@example.com
conflicts:
  - message: "Extracted and asserted dependencies differ"
    extracted: database-x
    asserted: database-y
    recommendation: "Verify source code matches assertion. Update assertion or investigate extraction bug."
```

**Rationale**: Humans may have information extractors cannot capture (runtime config, organizational policy). Extractors may be correct when humans are wrong. System presents both; users make judgment.

**Related Decision**: [ADR-009: Assertion Precedence Model](./ADR-009-assertion-precedence-model.md) provides detailed conflict resolution guidance.

**User-Visible Guarantee**: "Queries show both extracted and asserted facts with provenance. You decide which to trust."

---

### Multi-Region Behavior

**Active-active with eventual consistency.**

**Guarantees**:

1. **Bidirectional Replication**: S3 MRAP and DynamoDB Global Tables replicate slices across regions.

2. **Replication Lag**: Typical <2 seconds, maximum <10 seconds (AWS SLA).

3. **Last-Writer-Wins**: If slices updated simultaneously in both regions, last write wins. Acceptable because slices are versioned and immutable (conflicts are rare and transient).

4. **Query Returns Regional View**: Queries in us-east-1 see us-east-1 data; queries in eu-west-1 see eu-west-1 data. During replication lag, regions may differ briefly.

**Not Guaranteed**:
- Strong consistency across regions
- Conflict-free updates (rare conflicts possible, resolved via last-writer-wins)

**Implication**: Queries during replication lag may return stale data. Acceptable trade-off for active-active availability.

**User-Visible Guarantee**: "Multi-region deployments provide high availability but may show slight replication lag (<10 seconds)."

---

## Consequences

### Positive

**Explicit Guarantees Build Trust**: Users know what to expect. No surprises about consistency or failure handling.

**Partial Failures Do Not Block Progress**: Teams get value from partial extraction. Unknown markers guide investigation.

**Provenance Enables Debugging**: When results are unexpected, users trace to source artifacts or assertions.

**Graceful Degradation**: System remains useful during partial failures, replication lag, or concurrent updates.

**Multi-Region Without Complexity**: Eventual consistency is acceptable trade-off for active-active availability.

### Negative

**Not Strongly Consistent**: Users cannot rely on read-your-writes or cross-region consistency. Workflows must account for eventual consistency.

**Conflict Resolution Manual**: When extracted and asserted facts conflict, users must investigate. System does not automatically resolve.

**Replication Lag Visible**: Queries during replication lag may return stale results. Users see transient inconsistencies.

**Concurrent Job Behavior Non-Intuitive**: Last-completed-wins can overwrite more recent incremental recon with older full recon. Requires job lifecycle understanding.

### Neutral

**Consistency Model Matches AWS Primitives**: DynamoDB Global Tables and S3 MRAP both use eventual consistency. No impedance mismatch.

**Version History Provides Auditability**: Even when current pointers update, old versions remain for debugging.

## Alternatives Considered

### Alternative 1: Strong Consistency (Fail on Partial Extraction)

**Approach**: Extraction must fully succeed or fully fail. No partial results.

**Rejected Because**:
- Users lose value from partial data
- One broken file blocks entire repository extraction
- Operational burden increases (must fix all syntax errors before any slices appear)

### Alternative 2: Extracted Facts Always Override Assertions

**Approach**: When extracted and asserted facts conflict, extraction wins automatically.

**Rejected Because**:
- Humans may have information extractors cannot capture (runtime config, organizational policy)
- Extractors may have bugs; humans may be correct
- Removes ability to supplement extraction with domain knowledge

### Alternative 3: Strong Consistency Across Regions (Single-Region Writes)

**Approach**: All writes go to primary region; secondaries are read-only replicas.

**Rejected Because**:
- Eliminates active-active availability
- Write latency increases for non-primary regions
- Failover requires promoting secondary to primary (operational complexity)
- Eventual consistency acceptable for documentation use case (not financial transactions)

### Alternative 4: Locking for Concurrent Reconciliations

**Approach**: Serialize reconciliation jobs with distributed locks.

**Rejected Because**:
- Distributed locking is operationally complex (lock expiration, deadlock detection, failure recovery)
- Concurrent jobs are rare in practice (incremental recon is fast)
- Last-completed-wins is simpler and sufficient

## Related Decisions

- [ADR-007: Slice Identity Strategy](./ADR-007-slice-identity-strategy.md) - Identity stability impacts consistency
- [ADR-009: Assertion Precedence Model](./ADR-009-assertion-precedence-model.md) - Detailed conflict resolution guidance

## Implementation Notes

### Extractor Requirements

Extractors must:
- Isolate failures to individual files (do not fail entire job on single file failure)
- Emit unknown markers for extraction failures with diagnostic details
- Record extraction status (`complete`, `partial`) in slice metadata

### Query API Requirements

Intelligence API must:
- Support provenance filtering (`source=extracted`, `source=asserted`, `source=all`)
- Return conflict warnings when extracted and asserted facts differ
- Include extraction status in slice metadata responses

### Event Schema Requirements

`fabric.recon.completed` events must include:
- `status: complete | partial`
- `failed_files: [...]` if partial
- `failure_reasons: [...]` if partial
- `slice_count: N` (successful extractions)

## Traceability

This architectural decision is fully specified within the STE specification. Applied examples and historical artifacts are intentionally excluded from this publication.

- **Stakeholders**: Development Teams, Intelligence Consumers, Operations Teams
- **Depth-6 Concern**: #1 - Truth Model and Consistency

---

**Decision Date**: 2025-12-19  
**Last Updated**: 2025-12-19  
**Status**: Accepted





