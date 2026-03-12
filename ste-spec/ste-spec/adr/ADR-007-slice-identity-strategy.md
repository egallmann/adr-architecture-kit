# ADR-007: Slice Identity Strategy

## Status

Accepted

## Context

Every slice requires a unique, stable identifier within its domain and type. This identifier must:

1. **Uniquely identify** the architectural element across versions
2. **Remain stable** when code is refactored but semantic meaning is unchanged
3. **Change appropriately** when semantic meaning changes (e.g., endpoint path changes)
4. **Be deterministic** given the same input artifact
5. **Be human-readable** for debugging and querying

The identity strategy is critical because it determines:

- Whether a slice is "new" or an "update" to an existing slice
- How queries resolve to slices
- How environment diffs detect changes
- How point-in-time queries retrieve historical state

### The Problem

Consider these refactoring scenarios:

**Scenario 1: Function Rename**
```python
# Before
def list_users():
    return User.query.all()

# After (refactor)
def get_all_users():
    return User.query.all()
```

Should this create a new slice or update an existing slice? The function name changed, but the endpoint path (`/api/users`) did not.

**Scenario 2: Endpoint Path Change**
```python
# Before
@app.route('/api/v1/users')
def list_users():
    return User.query.all()

# After (breaking change)
@app.route('/api/v2/users')
def list_users():
    return User.query.all()
```

This **should** create a new slice because the API contract changed.

**Scenario 3: Entity Rename**
```python
# Before
class User:
    id: int
    email: str

# After (refactor)
class UserAccount:
    id: int
    email: str
```

Should this create a new entity slice or update the existing one? The class name changed, but the database table name (`users`) might not have.

### Requirements

The identity strategy must:

- **Prioritize semantic stability** over syntactic stability
- **Use observable attributes** (endpoint paths, table names, module paths) over implementation details (function names, class names)
- **Be explicit about what drives identity** so extractors can apply consistently
- **Handle edge cases** (multiple endpoints with same path but different methods, shadowed imports, etc.)

## Decision

AI-DOC Fabric uses **domain-specific identity derivation** with the following rules:

### API Domain Identity

**For Endpoints** (`api/endpoint`):

Identity derived from: `{HTTP_METHOD}:{NORMALIZED_PATH}`

**Example**:
- `GET /api/v1/users` → `get-api-v1-users`
- `POST /api/v1/users` → `post-api-v1-users`
- `GET /api/v1/users/{id}` → `get-api-v1-users-id`

**Rationale**: The API contract (method + path) is what clients depend on. Function names are implementation details. If the path changes, it's a new API.

**Refactor Behavior**:
- Function rename: Identity unchanged (update)
- Path change: New identity (new slice)
- Method change on same path: New identity (new slice)

---

### Data Domain Identity

**For Entities** (`data/entity`):

Identity derived from: `{CANONICAL_NAME}`

Where canonical name is:
1. Database table name if declared in ORM mapping
2. Class name normalized to snake_case if no table name
3. Schema name + table name for explicit schemas

**Example**:
```python
class UserAccount:
    __tablename__ = 'users'  # Canonical name: users
```
- Identity: `users-entity`

**Rationale**: Database consumers depend on table names, not class names. If the table name remains stable, the entity identity should too.

**Refactor Behavior**:
- Class rename (same table): Identity unchanged (update)
- Table rename: New identity (new slice, old slice remains for history)

---

### Graph Domain Identity

**For Modules** (`graph/module`):

Identity derived from: `{MODULE_PATH}`

**Example**:
- `src/api/users.py` → `src-api-users`
- `src/services/auth.py` → `src-services-auth`

**Rationale**: Module paths are how code references other code. If a module moves, it's a new module even if content is similar.

**Refactor Behavior**:
- File rename/move: New identity (new slice)
- Content change within file: Identity unchanged (update)

---

### Integration Domain Identity

**For Clients** (`integration/client`):

Identity derived from: `{BASE_URL_OR_SERVICE_NAME}`

**Example**:
- Stripe API client → `stripe-client`
- Internal auth service → `auth-service-client`

**Rationale**: External integrations are identified by the service they connect to, not the variable name or class name in code.

**Refactor Behavior**:
- Variable rename: Identity unchanged (update)
- Target service change: New identity (new slice)

---

### Config Domain Identity

**For Settings** (`config/setting`):

Identity derived from: `{CONFIG_KEY}`

**Example**:
- `DATABASE_URL` → `database-url`
- `API_TIMEOUT_SECONDS` → `api-timeout-seconds`

**Rationale**: Configuration keys are how code references settings. If the key changes, consumers must update.

**Refactor Behavior**:
- Key rename: New identity (new slice)
- Value change: Identity unchanged (update)

---

### Normalization Rules

Identities are normalized using these rules:

1. **Lowercase**: All identities are lowercase
2. **Hyphenation**: Replace non-alphanumeric characters with hyphens
3. **No consecutive hyphens**: `foo--bar` becomes `foo-bar`
4. **No leading/trailing hyphens**: Strip hyphens from ends
5. **Path segments preserved**: `/api/v1/users` → `api-v1-users` (not `api-users`)

### Collision Handling

When two elements map to the same identity (rare but possible):

1. **Log warning** during extraction
2. **Append disambiguation suffix** based on source location
3. **Example**: Two `GET /api/users` endpoints in different files → `get-api-users` and `get-api-users-2`

Extractors should detect collisions and emit warnings for manual review.

### Identity Stability Guarantees

**Guaranteed Stable**:
- Function/class renamed, observable attribute (path, table, module) unchanged → Identity unchanged

**Guaranteed Changed**:
- Observable attribute changed (endpoint path, table name, module path) → New identity

**Ambiguous Cases**:
- Entity with no explicit table name, class renamed → Identity changes (class name is observable)
- File moved to new directory → Identity changes (module path is observable)

## Consequences

### Positive

**Semantic Refactoring Transparency**: Renaming functions or classes does not create spurious "new" slices when the underlying contract is unchanged.

**Deterministic Identity**: Same input artifacts always produce same identities. Extraction is reproducible.

**Query Stability**: Queries referencing identities remain valid across refactors that preserve semantic meaning.

**Environment Diffs Work**: Comparing non-prod to prod correctly identifies real changes, not refactor artifacts.

**Human-Readable**: Identities like `get-api-v1-users` are debuggable and understandable.

### Negative

**Extractors Must Implement Domain Logic**: Each extractor must understand identity derivation rules for its language. Increased extractor complexity.

**Edge Cases Require Judgment**: When canonical name is ambiguous (entity with no table name, multiple possible paths), extractors must make choices. Increases extractor testing burden.

**Identity Changes on Observable Refactors**: Moving a module or renaming a table creates new slices. Historical queries must account for identity changes.

**Collision Detection Required**: Extractors must detect and handle identity collisions. Adds validation logic.

### Neutral

**Versioning Orthogonal to Identity**: Slice identity is separate from slice version. Same identity can have multiple versions over time.

**Manual Assertion Identity**: Manual assertions follow the same identity derivation rules. Humans must use correct identities when asserting relationships.

## Alternatives Considered

### Alternative 1: Content-Based Identity (Hash of Slice Content)

**Approach**: Derive identity from SHA-256 hash of slice content.

**Rejected Because**:
- Not stable across refactors (any content change creates new identity)
- Not human-readable (debugging requires hash lookup)
- Environment diffs become meaningless (every change looks new)

### Alternative 2: User-Specified Identity

**Approach**: Allow teams to annotate code with explicit slice IDs (e.g., `@slice_id("get-users")`).

**Rejected Because**:
- Requires code modification (increases adoption friction)
- Inconsistent across teams (no enforcement of conventions)
- Manual maintenance burden (defeats automation goal)
- Legacy code without annotations falls back to automatic derivation (two systems)

### Alternative 3: Function/Class Name as Identity

**Approach**: Use function or class name directly as identity.

**Rejected Because**:
- Refactoring function names creates spurious changes
- Multiple endpoints in one function (common in some frameworks) cannot be distinguished
- Not semantically meaningful for consumers (clients care about `/api/users`, not `list_users`)

### Alternative 4: UUID Generation

**Approach**: Generate UUID on first extraction, store mapping persistently.

**Rejected Because**:
- Not deterministic (different runs produce different IDs)
- Requires persistent mapping storage (increases state management complexity)
- Not human-readable (debugging requires UUID lookup)
- Breaks environment diffs (same code in non-prod and prod has different UUIDs)

## Related Decisions

- [ADR-008: Correctness and Consistency Contract](./ADR-008-correctness-consistency-contract.md) - Identity stability impacts consistency guarantees

## Implementation Notes

### Extractor Requirements

Each extractor must:

1. **Implement domain-specific derivation** per rules above
2. **Detect collisions** and emit warnings
3. **Normalize consistently** using normalization rules
4. **Test edge cases** (shadowed imports, multiple definitions, ambiguous names)

### Testing Strategy

Identity derivation must be tested with:

- **Refactor scenarios**: Ensure identity stability across renames
- **Breaking change scenarios**: Ensure identity changes when semantics change
- **Collision scenarios**: Ensure extractors detect and handle collisions
- **Normalization edge cases**: Test special characters, empty strings, long paths

### Migration Path

When identity derivation rules change (future ADR updates):

1. **New extractor version** implements new rules
2. **Recon-full** triggered for all repositories
3. **Migration tool** maps old identities to new identities
4. **Historical queries** updated to use new identities

## Traceability

- **Requirements**: [BR-001: Accurate Documentation](../01-context/business-requirements.md#br-001)
- **Stakeholders**: Extractor Developers, Development Teams, Intelligence Consumers
- **Depth-6 Concern**: #2 - Slice Identity Invariants
- **Related Views**: [Slice Schema](../05-interface-specifications/slice-schema.md), [Data View](../02-architecture-views/data-view.md)

---

**Decision Date**: 2025-12-19  
**Last Updated**: 2025-12-19  
**Status**: Accepted





