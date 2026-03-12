# ADR-001: Deterministic Extraction Over ML-Based Inference

## Status

**Accepted** — 2025-12-19

## Context

AI-DOC Fabric needs to extract architectural elements from source code. Two primary approaches exist:

1. **Deterministic extraction** using language-native AST parsers and framework-specific patterns
2. **ML-based inference** using embedding models, LLMs, or probabilistic classifiers

The choice impacts:
- Reproducibility of extraction results
- Auditability of system outputs
- Operational complexity and cost
- Confidence in query results
- Ability to explain "why" something was extracted

Enterprise documentation systems require high confidence in their outputs. When a query returns "Service X depends on Database Y," stakeholders need assurance that this reflects actual code, not probabilistic inference.

## Decision

AI-DOC Fabric will use **deterministic extraction** exclusively for generating slices from source code. Extractors will parse code using language-native AST tools (Python's `ast` module, TypeScript Compiler API, etc.) and detect framework patterns through explicit rules.

**Concrete Implementation**:

1. **Extractors use AST parsing**
   - Python: `ast.parse()`
   - JavaScript/TypeScript: TypeScript Compiler API
   - Java: JavaParser or Eclipse JDT
   - Go: `go/parser`

2. **Framework detection via explicit patterns**
   - FastAPI routes: Detect `@app.get()`, `@app.post()` decorators
   - Express routes: Detect `app.get()`, `app.post()` calls
   - Spring Boot: Detect `@GetMapping`, `@PostMapping` annotations

3. **No probabilistic matching**
   - No embeddings for code similarity
   - No LLM inference for relationships
   - No ML classifiers for element types

4. **Optional NL query translation**
   - Intelligence Service MAY use LLM to translate natural language to structured queries
   - LLM sees only the query, not the results
   - One-way translation: LLM input → structured query output
   - Falls back to structured query if translation fails

## Consequences

### Positive

**Reproducibility**: Given the same source code and extractor version, output is identical. This enables:
- Regression testing of extractors
- Auditable extraction process
- Confident reprocessing (recon-full) when extractor logic improves

**Explainability**: Every slice traces to specific source file, line number, and extractor logic. Users can:
- Understand why something was extracted
- Debug unexpected extraction results
- Trust that results reflect actual code

**No Model Drift**: Extraction logic doesn't degrade over time. No need for:
- Model retraining
- Embedding model versioning
- ML model deployment infrastructure
- Drift detection and mitigation

**Lower Operational Cost**:
- No GPU instances required
- Smaller compute footprint
- Faster extraction (no inference latency)
- Lower AWS costs

**Predictable Behavior**: Extraction behavior is deterministic and testable. Teams can:
- Write unit tests for extractors
- Verify extraction logic through code review
- Debug extraction issues with traditional tools

### Negative

**Limited to Observable Patterns**: Cannot infer relationships that aren't explicitly in code:
- Dynamic module loading (e.g., Python `importlib.import_module(computed_string)`)
- Runtime plugin discovery
- Reflection-based dependencies
- Convention-over-configuration patterns where convention isn't codified

**Extractor Development Burden**: Each language and framework requires custom extractor logic:
- Development effort to support new languages
- Maintenance as frameworks evolve
- Testing burden for edge cases

**No "Smart" Guessing**: When code is ambiguous, system records unknown rather than inferring:
- May result in incomplete graph for dynamically-constructed systems
- Requires manual assertions for gaps

**Framework Coverage Gaps**: Extractors work best for mainstream frameworks:
- Custom frameworks require custom extractors
- Niche frameworks may not be supported
- Legacy frameworks may lack sufficient structure for extraction

### Neutral

**Coverage Taxonomy**: System explicitly tracks what it can and cannot extract. This is neither good nor bad, but a requirement:
- Gap visibility drives extractor prioritization
- Manual assertions supplement coverage
- Unknowns are tracked with same rigor as knowns

## Alternatives Considered

### Alternative 1: LLM-Based Code Understanding

**Approach**: Use large language models (GPT-4, Claude, etc.) to "understand" code and extract relationships.

**Rejected Because**:
- Non-deterministic: Same code produces different results across runs
- Hallucination risk: LLMs may infer non-existent dependencies
- Cost: API costs for processing large codebases prohibitive
- Latency: Inference time significantly slower than parsing
- Auditability: Cannot explain why LLM made a specific extraction
- Trust: Enterprise stakeholders unwilling to trust probabilistic outputs for critical architecture documentation

**When It Might Work**: Small codebases with high tolerance for uncertainty, non-critical use cases

### Alternative 2: Embedding-Based Similarity

**Approach**: Generate embeddings for code segments, cluster similar elements, infer relationships through proximity.

**Rejected Because**:
- Similarity ≠ Dependency: Similarity doesn't imply architectural relationship
- False positives: Similar code from unrelated modules incorrectly linked
- Requires threshold tuning: Threshold changes based on codebase size and style
- Cannot explain: "These are similar" doesn't explain why or if they're related

**When It Might Work**: Code search and discovery tools (not dependency tracking)

### Alternative 3: Hybrid Approach (AST + ML for Ambiguity)

**Approach**: Use deterministic extraction as primary, fall back to ML for ambiguous cases.

**Rejected Because**:
- Complexity: Two systems to maintain and reason about
- Inconsistency: Some slices deterministic, some probabilistic (confusing)
- Where to draw the line: Ambiguity definition becomes arbitrary
- Still requires explicit unknowns: Better to record unknown than infer incorrectly

**When It Might Work**: Research prototypes exploring extraction boundaries

### Alternative 4: Static Analysis Tools (SonarQube, CodeQL, etc.)

**Approach**: Leverage existing static analysis tools for dependency extraction.

**Rejected Because**:
- Not designed for architecture extraction: Focus on bugs, vulnerabilities, code smells
- Insufficient metadata: Don't capture domain/type taxonomy needed for slices
- Tool diversity: Each language needs different tool, inconsistent outputs
- Licensing: Enterprise tools expensive and restrictive

**Partial Adoption**: May use static analysis as input to custom extractors, but not as primary extraction mechanism.

## Related Decisions

- **ADR-006: Explicit Unknowns** — When deterministic extraction can't reach, record unknown
- **ADR-007: Slice Identity Strategy** — Deterministic IDs derived from deterministic extraction
- **ADR-008: Correctness Consistency Contract** — Deterministic extraction enables truth model

## Implementation Notes

### Extractor Requirements

Each extractor must:

1. Parse source code using language-native tools
2. Implement pattern detection through explicit rules
3. Produce identical output for identical input
4. Document framework patterns supported
5. Report coverage taxonomy
6. Record unknowns when patterns not detectable

### Testing Strategy

Extractors require:

- Unit tests with sample code snippets
- Regression tests ensuring consistent output across versions
- Edge case tests for complex framework patterns
- Coverage tests verifying taxonomy accuracy

### Performance Expectations

Deterministic extraction is fast:
- Target: < 100ms per file for files < 1MB
- No network calls (unlike LLM APIs)
- Parallelizable across files

## Review Criteria

This decision should be revisited if:

1. **Deterministic extraction proves insufficient** for majority of codebases
2. **LLM technology advances** to provide deterministic, explainable outputs
3. **Enterprise tolerance for probabilistic systems increases** significantly
4. **Operational costs** of deterministic extraction exceed ML-based approaches

## Traceability

This architectural decision is fully specified within the STE specification. Applied examples and historical artifacts are intentionally excluded from this publication.

**Stakeholders**: Architects, Quality Assurance, Compliance, Development Teams





