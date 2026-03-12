# ADR-006: Explicit Unknowns Over Inference

## Status

**Accepted** — 2025-12-19

## Context

Extractors encounter code patterns they cannot fully understand:

- Third-party SaaS integrations (Stripe, Twilio, Salesforce)
- Dynamic imports using runtime strings
- Reflection and metaprogramming
- Legacy systems in unsupported languages
- Configuration-based behaviors outside code

When extraction cannot determine a relationship or property, we must decide:

1. **Infer**: Make best guess based on heuristics
2. **Omit**: Skip the element entirely
3. **Record Unknown**: Explicitly mark gaps in knowledge

## Decision

AI-DOC Fabric will **explicitly track unknowns** with the same rigor as known elements.

**Concrete Implementation**:

1. **Unknowns in Slice Schema**
   ```yaml
   unknowns:
     - category: opaque_boundary
       description: "Stripe API internal implementation not observable"
       recorded_at: "2025-12-19T15:30:00Z"
   ```

2. **Unknown Categories**
   - `opaque_boundary`: External service without observable internals
   - `unsupported_language`: Code in language without extractor
   - `incomplete_extraction`: Extractor limitation for supported language
   - `manual_assertion_needed`: Relationship exists but not extractable

3. **Query Interface for Unknowns**
   - `GET /v1/unknowns?environment=prod` — Returns all slices with unknowns
   - Filter by category, domain, type
   - Prioritize extractor development based on unknown frequency

4. **Event Stream**
   - SNS topic `fabric.meta.unknowns` emits when unknowns detected
   - Enables gap tracking and reporting

## Consequences

### Positive

**Honesty**:
- Users know what system doesn't know
- No false confidence from inferred guesses
- Query results trustworthy (unknowns explicitly flagged)

**Gap Visibility**:
- Prioritize extractor development based on real gaps
- Identify which services have most unknowns
- Measure extraction coverage over time

**Manual Assertion Target**:
- Unknowns guide what to assert manually
- Evidence requirement higher for unknowns (know where gaps are)

**Debugging Aid**:
- Missing dependencies explained ("unknown because X")
- Not "dependency missing" but "dependency unknown because opaque boundary"

### Negative

**Incomplete Graph**:
- Graph has explicit holes
- Traversal may not reach all dependents if edges unknown
- Users must understand and accept incompleteness

**Query Ambiguity**:
- "What depends on Stripe?" may return incomplete results
- Users need to check unknowns to verify completeness

**Perception Risk**:
- May be seen as "system doesn't work"
- Requires user education: Explicit unknowns better than silent guesses

### Neutral

**Transparency Trade-off**:
- Chose transparency over completeness
- Acceptable for enterprise systems
- Users can supplement with manual assertions

## Alternatives Considered

### Alternative 1: Heuristic Inference

**Approach**: When cannot extract definitively, infer based on naming conventions, file locations, common patterns.

**Rejected Because**:
- False positives pollute graph
- User cannot distinguish extracted vs inferred
- Confidence in results erodes
- Debugging false inferences difficult

**Example**: File named `stripe_client.py` doesn't mean it uses Stripe (could be mock, could be misnamed).

### Alternative 2: Omit Unknown Elements

**Approach**: If cannot extract completely, don't create slice at all.

**Rejected Because**:
- Loses partial information (can extract client exists, just not its internals)
- No visibility into gaps
- Cannot prioritize extractor development
- Manual assertions have nowhere to attach

### Alternative 3: Mark Entire Slice as "Low Confidence"

**Approach**: Create slice, flag as "low confidence" rather than specific unknowns.

**Rejected Because**:
- Vague: What specifically is unknown?
- Cannot query for specific gap types
- Doesn't guide manual assertions
- Binary confidence insufficient (may know 90% of slice)

## Related Decisions

- **ADR-001: Deterministic Extraction** — When deterministic fails, record unknown
- **ADR-009: Assertion Precedence** — Manual assertions can fill unknowns

## Implementation Notes

### Unknown Detection

Extractors detect unknowns during processing:

```python
def extract_integration_clients(ast: AST) -> List[ClientElement]:
    clients = []
    for node in ast.find_all(CallExpression):
        if is_external_client_instantiation(node):
            client = extract_client_metadata(node)
            
            # Can't determine authentication method
            if not can_extract_auth_config(node):
                client.unknowns.append({
                    'category': 'incomplete_extraction',
                    'description': 'Authentication configuration not statically determinable',
                    'context': { 'line': node.lineno }
                })
            
            clients.append(client)
    return clients
```

### Unknown Reporting

```json
{
  "event_type": "fabric.meta.unknowns",
  "payload": {
    "unknowns": [
      {
        "category": "opaque_boundary",
        "slice_id": "integration/client/stripe-client",
        "description": "Stripe API internal implementation not observable",
        "recommendation": "Consider manual assertion for critical dependencies"
      }
    ]
  }
}
```

## Traceability

This architectural decision is fully specified within the STE specification. Applied examples and historical artifacts are intentionally excluded from this publication.

**Stakeholders**: Architects, Development Teams, Quality Assurance





