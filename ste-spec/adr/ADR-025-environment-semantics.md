# ADR-025: Environment Semantics

**Status:** Accepted  
**Date:** 2025-12-29  
**Closes Gap:** GAP-2 (Environment Definition / Blocker 5.1)

---

## Context

The STE-System specification references "environment" as a scoping dimension for canonical state (§7.1.1), relationship artifacts (ADR-018), and Fabric Attestations (§8.1.7). However, the specification does not define what "environment" means, how environment identifiers are established, or how environment semantics are enforced.

This ambiguity creates critical correctness risks:

1. **Canonical State Ambiguity:** §7.1.1 states "For any given environment and element identity, canonical state is unambiguous." Without defining environment, implementers cannot determine canonical state boundaries. Does `prod` canonical state differ from `production`? Are `dev` and `development` the same environment?

2. **Attestation Verification Failure:** Fabric Attestations (§8.1.7) include environment in their scope: "at timestamp T, for scope S, **in environment E**, the following canonical invariants were resolved...". Gateway cannot verify attestation validity if environment semantics are undefined. What constitutes a matching environment?

3. **Eligibility Bypass Risk:** If environment can be inferred, defaulted, or aliased, an attacker could craft Context Bundles claiming `prod` environment while referencing `production` attestations, bypassing enforcement if the Gateway treats these as equivalent.

4. **Determinism Violation:** §8.1.4 claims eligibility evaluation is deterministic. If environment matching logic is implementation-defined, different Gateway implementations could produce different eligibility decisions for identical inputs.

5. **Authority Partitioning Failure:** Without explicit environment semantics, canonical state from multiple environments could be conflated, undermining the authority model. ADF publishes canonical state "for environment E," but if E is ambiguous, authority boundaries dissolve.

Environment is not metadata. Environment is a **canonical dimension** that participates in:
- Identity resolution (what canonical state applies)
- Attestation verification (what invariants are authoritative)
- Eligibility enforcement (what execution is permitted)
- Authority partitioning (what state is canonical for which scope)

Treating environment as optional, inferred, or subject to interpretation would compromise the correctness guarantees that define the STE-System.

## Problem Statement

The specification must answer the following questions to enable deterministic, verifiable enforcement:

1. **What is an environment?** Is it a deployment target, a git branch, a combination, or something else?

2. **Who defines environment identifiers?** Is environment a user-supplied string, a Fabric-resolved value, or derived from artifacts?

3. **Where are environment identifiers established?** In Fabric Attestations? In Context Bundles? In organizational policy?

4. **How are environment identifiers compared?** Exact string match? Case-insensitive? Pattern matching? Hierarchy?

5. **Can environment be inferred?** If a Context Bundle omits environment, can Gateway infer it from deployment metadata, git branch, or infrastructure tags?

6. **Can environment be defaulted?** If Fabric Attestation specifies no environment, does it apply to all environments or no environments?

7. **Can environments share canonical state?** If two environments reference the same attestation, do they share authority boundaries?

8. **What happens on environment mismatch?** If Context Bundle claims environment `prod` but Fabric Attestation specifies `production`, is this a match, a mismatch, or undefined?

9. **Do environments form a hierarchy?** Can `prod` inherit invariants from `production-us-east-1`? Can wildcard matching apply (e.g., `prod-*`)?

10. **What does environment guarantee?** Does `prod` environment guarantee production-level safety, compliance, or infrastructure? Or is it merely a partitioning label?

These questions have **no implementation-neutral answers** in the current specification. GAP-2 exists because every implementer must invent environment semantics, breaking determinism and interoperability.

## Decision

**Environment is a first-class canonical dimension with explicit, Fabric-defined semantics.**

### v1 Baseline

For STE-System v1, environment is defined as:

**A mandatory, opaque string identifier established by AI-DOC Fabric governance that partitions canonical state, participates in Fabric Attestations, and is enforced by exact string matching at the Gateway.**

Environment is **not** inferred, defaulted, hierarchical, or interpretable. Environment is **not** bound to deployment topology, infrastructure, safety level, or organizational structure.

Environment semantics live in **AI-DOC Fabric governance**, not in Gateway logic, Runtime logic, or ADF extraction logic. The Fabric defines which environment identifiers exist and what scopes they partition. The Gateway enforces exact matching. No component interprets environment beyond exact string equality.

This decision intentionally restricts v1 to the minimal correctness-preserving definition. Features that introduce interpretation, inference, or hierarchy are explicitly deferred to future work.

## Normative Definition

### Environment (Canonical)

**Environment** is an opaque, case-sensitive string identifier that:

1. **Partitions canonical state** - Canonical artifacts, relationship artifacts, and Fabric Attestations are scoped to exactly one environment
2. **Appears in Fabric Attestations** - Every Fabric Attestation specifies the environment for which it attests canonical invariants
3. **Appears in Context Bundles** - Every Context Bundle specifies the environment in which execution is claimed to occur
4. **Is verified by Gateway** - Gateway compares Context Bundle environment to Fabric Attestation environment using exact string equality

**Format:** Environment identifiers are non-empty, printable ASCII strings (matching regex `[A-Za-z0-9_-]+`) with maximum length 64 characters.

**Examples (Illustrative Only):**
- `prod`
- `staging`
- `dev`
- `production-us-east-1`
- `non-prod`

These examples are **not normative**. AI-DOC Fabric governance defines which identifiers exist for each deployment. The specification imposes no semantic structure.

**Non-Examples (Invalid):**
- Empty string (violates non-empty requirement)
- `prod/staging` (violates character set)
- Strings exceeding 64 characters (violates length limit)
- Unicode or whitespace (violates ASCII printable requirement)

### Authority Over Environment Semantics

**AI-DOC Fabric (Organizational Governance):**
- Defines which environment identifiers exist
- Assigns canonical artifacts to environments
- Publishes Fabric Attestations scoped to specific environments
- Determines environment semantics (what `prod` means organizationally)

**STE-Gateway:**
- Enforces exact string matching between Context Bundle environment and Fabric Attestation environment
- Rejects eligibility when environments do not match
- Does **not** interpret, infer, or transform environment identifiers

**STE-Runtime:**
- Includes environment in Context Bundles as provided by user or deployment configuration
- Does **not** infer environment from git branch, deployment tags, or infrastructure
- Does **not** validate environment against Fabric-known identifiers (Gateway responsibility)

**ADF (AI-DOC Fabric Publication Service):**
- Publishes canonical artifacts and Fabric Attestations with explicit environment scope
- Environment is specified by organizational governance policy, not derived from artifacts

## Authoritative Rules (Normative)

The following requirements apply to all compliant STE-System implementations:

### R-ENV-1: Environment is Mandatory

Every Fabric Attestation MUST specify exactly one environment identifier.

Every Context Bundle submitted for eligibility evaluation MUST specify exactly one environment identifier.

**Rationale:** Environment is a canonical dimension. Omitting environment makes canonical state scope ambiguous, violating G-CAN-1 (§7.1.1: "For any given environment and element identity, canonical state is unambiguous").

**Prohibition:** Implementations MUST NOT provide default environment values. Implementations MUST NOT infer environment from deployment metadata, git branches, or infrastructure tags.

### R-ENV-2: Environment Matching is Exact String Equality

Gateway MUST compare environment identifiers using exact, case-sensitive string equality.

**Match:** Context Bundle environment `prod` matches Fabric Attestation environment `prod`.

**Mismatch:** Context Bundle environment `prod` does NOT match Fabric Attestation environment `production`, `PROD`, `Prod`, or `prod-us-east-1`.

**Rationale:** Exact matching is deterministic, implementation-neutral, and falsifiable by inspection. Any interpretation (case folding, hierarchy, wildcards) introduces implementation-specific logic, violating determinism.

**Prohibition:** Gateway MUST NOT perform case-insensitive matching, prefix matching, suffix matching, pattern matching, or any transformation of environment identifiers.

### R-ENV-3: Environment Mismatch Results in Denial

If Context Bundle environment does not exactly match Fabric Attestation environment, Gateway MUST deny execution eligibility.

**Denial Category:** `ENVIRONMENT_MISMATCH`

**Rationale:** Environment partitions canonical state. If Context Bundle claims environment `prod` but only `staging` attestations exist, canonical invariants cannot be resolved authoritatively for `prod`. Permitting execution would violate fail-closed enforcement (ADR-022).

**Prohibition:** Gateway MUST NOT permit execution when environment mismatches. No fallback to "best available" attestation is permitted.

### R-ENV-4: Environment Partitions Canonical State

Canonical artifacts, relationship artifacts, and Fabric Attestations for environment `E1` MUST NOT be used to authorize execution in environment `E2` where `E1 ≠ E2`.

**Rationale:** Environment is an authority boundary. Canonical state for `staging` does not authorize execution in `prod`. Conflating environments would undermine authority scarcity and provenance.

**Prohibition:** Gateway MUST NOT merge, aggregate, or cross-reference attestations from multiple environments. Each eligibility evaluation is scoped to exactly one environment.

### R-ENV-5: Environment is Cryptographically Bound

Fabric Attestations MUST include environment identifier in signed content.

**Rationale:** Environment is part of the attestation scope: "for scope S, **in environment E**, invariants I were resolved...". If environment is not signed, an attacker could substitute environment values, claiming `prod` attestation applies to `staging`.

**Prohibition:** Environment MUST NOT be transmitted as out-of-band metadata separate from signed attestation. Environment is part of the attested claim.

### R-ENV-6: No Environment Inference or Derivation

No STE-System component MUST infer, derive, or compute environment identifiers from:
- Git branch names
- Deployment target metadata (AWS account, region, VPC)
- Infrastructure tags (cost center, owner, environment tag)
- Time of day, date, or calendar
- Network location or IP address
- User identity or role

**Rationale:** Inference introduces implicit logic that varies by organization and implementation. Determinism requires explicit, verifiable environment specification.

**Prohibition:** All components MUST treat environment as an explicit input, not a computed value.

### R-ENV-7: Environment Semantics Are Not Enforceable by Gateway

Gateway MUST NOT enforce organizational semantics of environment identifiers.

**Example (Prohibited):** Gateway MUST NOT enforce that `prod` requests require elevated approval while `dev` requests do not. Such policies are organizational governance concerns, not Gateway enforcement scope.

**Rationale:** Gateway enforces structural correctness (exact matching, signature verification, canonical state boundaries). Gateway does not interpret what `prod` means organizationally. Semantic enforcement belongs in organizational policy (e.g., CI/CD pipeline controls, approval workflows).

**Permitted:** Gateway enforces that Context Bundle environment exactly matches Fabric Attestation environment. The fact that both specify `prod` is structurally verified; the meaning of `prod` is not Gateway's concern.

## What Environment Guarantees

When environment semantics are correctly implemented per this ADR, the STE-System provides:

### 1. Deterministic Eligibility Evaluation

Given identical Context Bundle (environment `E`, scope `S`, MVC references) and identical Fabric Attestation (environment `E`, scope `S`, invariants `I`), Gateway produces identical eligibility decision.

**Falsifiable:** Replay the same Context Bundle against the same attestation on different Gateway instances; outcomes must match.

### 2. Authority Partitioning

Canonical state for environment `E1` does not authorize execution in environment `E2` where `E1 ≠ E2`.

**Falsifiable:** Submit Context Bundle claiming environment `staging`, verify Gateway denies eligibility when only `prod` attestations exist.

### 3. Execution Separation

Model invocations claiming environment `prod` cannot succeed using canonical invariants from environment `staging`.

**Falsifiable:** Attempt cross-environment execution; Gateway must reject with `ENVIRONMENT_MISMATCH`.

### 4. Provenance Clarity

Every execution eligibility decision records which environment was claimed and which environment's attestations were used.

**Falsifiable:** Inspect Gateway audit logs; environment mismatch events are logged and observable.

### 5. Attestation Integrity

Environment is cryptographically bound into Fabric Attestations, preventing environment substitution attacks.

**Falsifiable:** Modify environment in attestation without re-signing; Gateway signature verification must fail.

## What Environment Explicitly Does NOT Guarantee

Environment is a **partitioning label**, not a semantic assertion. The following properties are **not** guaranteed by environment semantics:

### 1. Deployment Topology

Environment identifier `prod` does **not** guarantee that execution occurs in production infrastructure, production AWS account, or production network.

**Rationale:** Environment partitions canonical state. Whether `prod` execution actually reaches production infrastructure is determined by deployment configuration, network routing, and operational controls, not by environment identifier.

**Implication:** An attacker with access to `prod` Fabric Attestations could submit Context Bundle claiming `prod` environment to a non-production Gateway instance. Gateway enforces environment matching (canonical state boundary) but does not enforce where execution physically occurs.

### 2. Infrastructure Mapping

Environment identifier does **not** specify AWS account, region, VPC, Kubernetes cluster, or any infrastructure topology.

**Rationale:** Same environment (e.g., `prod`) may span multiple regions, accounts, or clusters. Environment is orthogonal to deployment topology.

**Implication:** `prod` attestation applies to all `prod` executions regardless of infrastructure location. Topology isolation is an operational concern, not an environment semantics concern.

### 3. Safety or Assurance Level

Environment identifier `prod` does **not** guarantee that execution is subject to production-level safety controls, approval workflows, or change management.

**Rationale:** Safety and assurance are organizational governance concerns enforced by CI/CD pipelines, approval systems, and policy engines. Gateway enforces canonical state boundaries, not approval workflows.

**Implication:** Gateway will permit execution in `prod` environment if canonical attestations exist and prerequisites are satisfied, regardless of whether organizational approval was obtained. Approval enforcement is out-of-scope.

### 4. Data Sensitivity or Compliance

Environment identifier does **not** indicate data sensitivity level, compliance requirements (SOX, PCI, HIPAA), or data classification.

**Rationale:** Sensitivity and compliance are data governance concerns, not canonical state partitioning concerns.

**Implication:** `prod` and `staging` environments may contain identical data sensitivity levels. Environment partitions canonical state, not data.

### 5. Runtime Behavior or Correctness

Environment identifier does **not** guarantee that code execution produces correct results, avoids errors, or behaves safely.

**Rationale:** Environment partitions canonical state used for eligibility evaluation. Execution correctness depends on code quality, invariant correctness, and model behavior, not environment identifier.

**Implication:** Execution in `prod` environment with canonical attestations may still produce incorrect results if invariants are incorrect or code has bugs. Environment semantics do not guarantee execution correctness.

### 6. Multi-Environment Consistency

Environment identifiers do **not** guarantee that `staging` canonical state resembles `prod` canonical state.

**Rationale:** Each environment has independent canonical state. Whether environments are synchronized is an operational concern.

**Implication:** `staging` may have entirely different invariants, artifacts, and state than `prod`. Gateway enforces environment boundaries but does not enforce cross-environment consistency.

## Alternatives Considered

| Alternative | Pros | Cons | Rejection Rationale |
|-------------|------|------|---------------------|
| **Implicit Environment** (Inferred from git branch, deployment tags, or infrastructure) | Reduces explicit configuration; "just works" in simple cases | Non-deterministic; different implementations infer differently; breaks reproducibility; introduces hidden dependencies on metadata that may change | Violates determinism (§8.1.4). Inference logic varies by organization and implementation. Gateway cannot verify inferred environment cryptographically. |
| **Environment as Metadata** (Optional field, defaults to wildcard, or omitted) | Simplifies onboarding; reduces friction for teams without environment separation | Breaks canonical state partitioning; weakens authority boundaries; introduces ambiguity in attestation scope; default values hide missing decisions | Violates G-CAN-1 (§7.1.1): "For any given environment and element identity, canonical state is unambiguous." If environment is optional, canonical state boundaries are undefined. |
| **Case-Insensitive Matching** (`prod` matches `PROD`, `Prod`, `Production`) | Reduces friction from naming inconsistencies; user-friendly | Non-deterministic across implementations (does `PROD` match `production`?); introduces hidden transformation logic; breaks exact signature verification | Introduces implementation-defined behavior. Exact matching is falsifiable and deterministic. Case folding rules vary (ASCII vs. Unicode, locale-specific). |
| **Hierarchical Environments** (`prod-us-east-1` inherits from `prod`) | Enables regional overrides; reduces attestation duplication | Introduces complex matching logic; hierarchy rules must be specified; unclear precedence (does child override parent or merge?); hierarchy semantics vary by organization | Deferred to future work. V1 requires simplest correct semantics. Hierarchy introduces interpretation, violating v1 goal of structural enforcement only. |
| **Wildcard Matching** (`prod-*` matches `prod-us-east-1`, `prod-eu-west-1`) | Enables attestation reuse across regions; reduces Fabric publication burden | Introduces pattern matching logic (glob vs. regex); unclear semantics (greedy vs. non-greedy); wildcard precedence ambiguous; breaks exact verification | Deferred to future work. Wildcards introduce interpretation and ambiguity. Exact matching is simpler, deterministic, and falsifiable. |
| **Environment Aliases** (`prod` and `production` are equivalent) | Reduces migration friction; accommodates legacy naming | Requires centralized alias registry; unclear precedence (canonical name vs. aliases); alias updates create versioning concerns; breaks exact matching | Deferred to future work. Aliases introduce indirection, making environment boundaries less explicit. V1 requires exact, unambiguous identifiers. |
| **Canonical Environment Dimension** (Explicit, mandatory, exact-match string identifier) | Deterministic; implementation-neutral; falsifiable; no hidden logic; cryptographically verifiable; simple to enforce | Requires discipline in environment naming; no tolerance for naming inconsistencies; cross-environment attestation reuse not supported | **Accepted.** Trades convenience for correctness. Explicit environment semantics enable deterministic enforcement and clear authority boundaries. |

## Component Interaction

### ADF (AI-DOC Fabric Publication Service)

**Responsibilities:**
- Assign environment identifier to every canonical artifact published
- Include environment identifier in every Fabric Attestation (signed)
- Environment assignment determined by organizational governance policy

**Prohibited:**
- Inferring environment from git branch name
- Defaulting environment to wildcard or "all environments"
- Publishing canonical artifacts without explicit environment

**No New Authority:** ADF already has ORG authority to sign canonical artifacts (§6.1.1). Environment scoping does not introduce new authority; it partitions existing authority.

### STE-Runtime

**Responsibilities:**
- Include environment identifier in Context Bundle as provided by user, deployment configuration, or CI/CD metadata
- Propagate environment from prompt metadata or execution context

**Prohibited:**
- Inferring environment from deployment infrastructure
- Defaulting environment if not provided by user
- Validating environment against Fabric-known identifiers (Gateway responsibility)

**No New Authority:** Runtime already has PROJECT authority to sign Context Bundles (§6.1.3). Environment is part of the Context Bundle claim, not a new authority grant.

### STE-Gateway

**Responsibilities:**
- Extract environment from Context Bundle
- Extract environment from Fabric Attestation
- Compare environments using exact string equality (R-ENV-2)
- Deny eligibility on environment mismatch (R-ENV-3)
- Log environment in audit trail for each eligibility decision

**Prohibited:**
- Interpreting environment semantics (e.g., treating `prod` as higher assurance than `dev`)
- Performing case-insensitive, hierarchical, or pattern matching
- Merging attestations from multiple environments
- Inferring environment from Runtime identity or network location

**No New Authority:** Gateway already has Enforcement Authority (ADR-019). Environment matching is part of eligibility evaluation, not a new enforcement scope.

### Trust Registry

**No Changes:** Trust Registry is unchanged. Environment is not a trust dimension. Identity trust (who can sign what) is orthogonal to environment scope (which canonical state applies).

**Clarification:** Trust Registry validates that ADF has ORG authority to sign Fabric Attestations. The fact that attestations are environment-scoped does not change trust validation logic.

## Threat Model Implications

### Attacks This Prevents

**1. Cross-Environment Privilege Escalation**

**Attack:** Attacker obtains `staging` Fabric Attestation, submits Context Bundle claiming `prod` environment, attempts to execute using `staging` canonical invariants.

**Prevention:** Gateway compares environment identifiers, detects mismatch (`staging` ≠ `prod`), denies eligibility with `ENVIRONMENT_MISMATCH`.

**2. Environment Substitution in Attestations**

**Attack:** Attacker intercepts Fabric Attestation for environment `staging`, modifies environment to `prod` without re-signing, submits to Gateway.

**Prevention:** Environment is cryptographically bound into signed attestation (R-ENV-5). Signature verification fails when environment is modified.

**3. Implicit Environment Assumption**

**Attack:** Attacker omits environment from Context Bundle, relies on Gateway inferring environment from infrastructure tags or git branch, bypasses explicit environment enforcement.

**Prevention:** Environment is mandatory (R-ENV-1). Gateway rejects Context Bundles without explicit environment.

**4. Case-Folding Confusion**

**Attack:** Attacker submits Context Bundle with environment `PROD`, relies on case-insensitive matching to reference `prod` attestations, bypasses environment boundary if organization treats these as distinct.

**Prevention:** Environment matching is exact, case-sensitive (R-ENV-2). `PROD` ≠ `prod`; no ambiguity.

### Attacks This Does NOT Prevent

**1. Authorized Execution in Wrong Infrastructure**

**Scenario:** Attacker with valid `prod` Fabric Attestations submits Context Bundle claiming `prod` environment to a Gateway instance running in non-production infrastructure.

**Not Prevented:** Gateway enforces environment matching (canonical state boundary) but does not enforce deployment topology. Attacker successfully obtains eligibility decision, though execution may not reach production model provider.

**Mitigation (Out of Scope):** Network segmentation, deployment controls, infrastructure-as-code enforcement. Environment semantics partition canonical state, not infrastructure.

**2. Approved Bypass via Valid Attestations**

**Scenario:** Attacker obtains valid `prod` Fabric Attestations (e.g., through compromised ADF signing key or insider access), submits legitimate Context Bundle with environment `prod`, obtains eligibility.

**Not Prevented:** Attestations are valid, environment matches, prerequisites satisfied. Gateway correctly permits execution.

**Mitigation (Out of Scope):** Key management, attestation revocation, time-bounded attestations. Environment semantics do not address compromised signing keys.

**3. Semantic Environment Confusion**

**Scenario:** Organization defines environment `production` in CI/CD but uses `prod` in Fabric Attestations. Developer submits Context Bundle with environment `production`, expects match.

**Not Prevented:** Gateway enforces exact matching. `production` ≠ `prod`; eligibility denied. This is **correct behavior** (prevents ambiguity), but causes operational friction.

**Mitigation (Out of Scope):** Organizational governance ensures consistent environment naming. Environment aliases or mapping are future work (intentionally deferred).

**4. Cross-Environment State Leakage via Shared Invariants**

**Scenario:** Fabric publishes identical invariants for `staging` and `prod` environments. Attacker infers production state by observing staging invariants.

**Not Prevented:** Environment semantics partition canonical state, but do not prevent Fabric from publishing similar state to multiple environments.

**Mitigation (Out of Scope):** Organizational policy controls what state is published to which environments. Environment semantics enforce boundaries, not content isolation.

## Consequences

### Positive

**1. Deterministic Environment Enforcement**

Eligibility evaluation is deterministic across implementations and time. Given identical Context Bundle environment and Fabric Attestation environment, all compliant Gateways produce identical decisions.

**Falsifiable:** Replay eligibility evaluation on different Gateway instances; outcomes must match.

**2. Explicit Authority Boundaries**

Canonical state for environment `E` does not authorize execution in environment `E'` where `E ≠ E'`. Authority partitioning is explicit and verifiable.

**Falsifiable:** Attempt cross-environment execution; Gateway must deny.

**3. Cryptographic Binding Prevents Substitution**

Environment is signed as part of Fabric Attestation. Modifying environment without re-signing invalidates signature, preventing environment substitution attacks.

**Falsifiable:** Modify environment in signed attestation; signature verification must fail.

**4. No Hidden Inference Logic**

All environment identifiers are explicit inputs. No component infers environment from metadata, reducing hidden dependencies and improving reproducibility.

**Falsifiable:** Inspect Context Bundle and Fabric Attestation; environment is explicitly present.

**5. Clear Specification Boundary**

Gateway enforces structural correctness (exact matching, signature verification) but does not interpret environment semantics (what `prod` means organizationally). Organizational semantics remain in governance scope, not Gateway scope.

**6. Fail-Closed on Ambiguity**

Ambiguous environment (missing, malformed, mismatched) results in denial, not best-effort execution. Correctness is prioritized over availability.

### Negative

**1. No Tolerance for Naming Inconsistencies**

If organization uses `prod`, `production`, and `PROD` inconsistently across teams or systems, exact matching causes eligibility denial.

**Mitigation:** Organizational governance establishes canonical environment names and enforces consistency. Environment aliases are future work.

**2. Cross-Environment Attestation Reuse Not Supported**

Invariants published for `staging` cannot be reused for `dev` without duplicate publication. Each environment requires independent Fabric Attestations.

**Mitigation:** Fabric publication process can automate multi-environment attestation. Hierarchical environments or wildcards are future work.

**3. Operational Friction for Multi-Region Deployments**

If organization defines separate environments per region (e.g., `prod-us-east-1`, `prod-eu-west-1`), each requires independent attestations. Regional aggregation not supported.

**Mitigation:** Organization can define single `prod` environment spanning regions, or use region-specific environments. Hierarchical environments are future work.

**4. Environment Semantics Are Opaque to Gateway**

Gateway cannot enforce organizational policies like "prod requires approval" or "dev has relaxed controls." Such policies must be enforced outside Gateway.

**Mitigation:** Organizational CI/CD pipelines, approval workflows, and policy engines enforce semantic controls. Gateway enforces canonical state boundaries only.

**5. No Cross-Environment Consistency Enforcement**

Gateway does not verify that `staging` resembles `prod`, or that environments are synchronized. Drift detection is out-of-scope.

**Mitigation:** Organizational tooling can compare environments. Environment semantics partition state; consistency is a separate concern.

### Neutral

**1. Environment Naming Is Organizational Concern**

Specification does not prescribe environment names (`prod` vs. `production`) or count (two environments vs. ten). Organizations define identifiers.

**Implication:** Interoperability requires organizations to document environment identifiers. No universal registry exists.

**2. Environment Is Not a Trust Dimension**

Trust Registry validates identity authority (who can sign), not environment scope (which canonical state applies). Environment and trust are orthogonal.

**Implication:** Environment matching is separate from signature verification. Both must succeed for eligibility.

## Future Work (Explicitly Deferred)

The following features are **intentionally omitted from v1** and deferred to future ADRs:

### 1. Hierarchical Environments

**Deferred Capability:** Environment `prod-us-east-1` inherits invariants from parent environment `prod`.

**Why Deferred:** Hierarchy introduces matching rules (prefix, longest match, precedence), inheritance semantics (override vs. merge), and organizational variation. V1 requires simplest correct semantics.

**Future ADR Required:** Define hierarchy matching algorithm, precedence rules, and inheritance model. Ensure determinism preserved.

### 2. Wildcard or Pattern Matching

**Deferred Capability:** Attestation for environment `prod-*` applies to `prod-us-east-1`, `prod-eu-west-1`, etc.

**Why Deferred:** Wildcards introduce pattern matching (glob vs. regex), precedence (specific vs. wildcard), and ambiguity (overlapping patterns).

**Future ADR Required:** Define wildcard syntax, matching algorithm, and precedence rules. Ensure falsifiability.

### 3. Environment Aliases

**Deferred Capability:** Fabric defines `production` as alias for `prod`; Gateway treats as equivalent.

**Why Deferred:** Aliases require centralized registry, canonical name selection, and update propagation. Introduces indirection and versioning concerns.

**Future ADR Required:** Define alias registry, canonical name semantics, and Gateway resolution logic.

### 4. Dynamic Environment Resolution

**Deferred Capability:** Fabric resolves environment at execution time based on Context Bundle metadata (e.g., user identity, time of day, resource tags).

**Why Deferred:** Dynamic resolution introduces non-determinism, hidden logic, and dependency on external state. V1 requires explicit, static environment.

**Future ADR Required:** Define resolution algorithm, determinism guarantees, and caching semantics.

### 5. Cross-Environment Queries

**Deferred Capability:** Gateway permits execution to reference attestations from multiple environments (e.g., query `staging` invariants while executing in `prod`).

**Why Deferred:** Cross-environment queries weaken authority boundaries and introduce complex precedence rules (which environment takes precedence?).

**Future ADR Required:** Define use cases, safety constraints, and precedence model. Ensure authority boundaries preserved.

### 6. Environment Composition

**Deferred Capability:** Context Bundle specifies multiple environments (e.g., `[prod, us-east-1]`); Gateway resolves attestations from composition.

**Why Deferred:** Composition introduces join semantics (intersection vs. union), precedence (which environment's invariants apply), and complexity.

**Future ADR Required:** Define composition semantics, matching algorithm, and use cases.

### 7. Environment Inference from Organizational Policy

**Deferred Capability:** Gateway queries organizational policy service to infer environment from deployment metadata, user identity, or git branch.

**Why Deferred:** Inference introduces external dependency, non-determinism (policy may change), and hidden logic. V1 requires explicit environment.

**Future ADR Required:** Define policy interface, caching semantics, and determinism guarantees.

All deferred features require **separate ADRs** and **must preserve determinism, falsifiability, and explicit semantics**. Convenience features that introduce ambiguity or hidden logic are **permanently rejected**, not merely deferred.

## Final Validation Clause

A compliant STE-System implementation and a reasonable reader of this ADR **must not** infer or conclude that:

### Prohibited Inferences

- [ ] **Environment can be inferred** from git branch, deployment tags, infrastructure metadata, user identity, or time of day
- [ ] **Environment can be defaulted** to wildcard, "all environments," or omitted from Context Bundle or Fabric Attestation
- [ ] **Environment is optional** or metadata rather than a canonical dimension participating in authority boundaries
- [ ] **Environment matching is case-insensitive**, hierarchical, pattern-based, or subject to interpretation
- [ ] **Environment semantics are interpreted by Gateway** beyond exact string matching and signature verification
- [ ] **Environment implies safety level, compliance requirements, or deployment topology** rather than canonical state partitioning
- [ ] **Environment guarantees execution correctness, data sensitivity, or infrastructure isolation** rather than authority boundaries
- [ ] **Two different environments can share canonical state** or attestations
- [ ] **Gateway enforces organizational semantics** of environment (e.g., approval workflows for `prod`) rather than structural correctness
- [ ] **Cross-environment attestation reuse is supported** without explicit duplicate publication

### Required Behaviors

A compliant implementation **must** exhibit the following falsifiable behaviors:

1. **Reject Context Bundle without explicit environment** - Gateway returns error, does not infer or default
2. **Reject Fabric Attestation without explicit environment** - Gateway cannot resolve canonical invariants, denies eligibility
3. **Deny eligibility on environment mismatch** - Context Bundle environment `staging` does not match Fabric Attestation environment `prod`; Gateway returns `ENVIRONMENT_MISMATCH`
4. **Perform exact, case-sensitive string matching** - `prod` ≠ `PROD` ≠ `production`; no match if strings differ
5. **Verify environment is signed** - Modifying environment in Fabric Attestation without re-signing causes signature verification failure
6. **Log environment in audit trail** - Every eligibility decision records Context Bundle environment and Fabric Attestation environment
7. **Partition canonical state by environment** - Attestation for environment `staging` does not authorize execution in environment `prod`

These behaviors are **testable, observable, and falsifiable** by inspection or replay.

## Related Decisions

- **ADR-007: Slice Identity Strategy** - Defines slice identity within domain/type. Environment is orthogonal to identity; same identity may have different canonical state per environment.
- **ADR-008: Correctness and Consistency Contract** - Defines canonical state guarantees. This ADR clarifies that canonical state is environment-scoped (G-CAN-1).
- **ADR-019: Gateway Authority and Signing Model** - Establishes Gateway enforces but does not attest. This ADR establishes Gateway enforces environment matching but does not define environment semantics.
- **ADR-022: Fail-Closed Semantics** - Defines fail-closed triggers. This ADR establishes environment mismatch as a fail-closed trigger.

## Traceability

**Closes Gap:** GAP-2 (Environment Definition / Blocker 5.1) from STE Specification Gap Analysis

**Requirements:**
- §7.1.1 Canonical State (G-CAN-1: "For any given environment and element identity, canonical state is unambiguous")
- §8.1.7 Fabric Attestation (includes environment in attestation scope)
- ADR-018 Relationship Artifacts (environment-scoped)

**Views:**
- `specifications/ste-system.iso42010.md` §7.1 (Canonical State)
- `specifications/ste-system.iso42010.md` §8.1.4 (Eligibility Evaluation Algorithm)
- `specifications/ste-system.iso42010.md` §8.1.7 (Fabric Attestation)

**Stakeholders:**
- ADF Implementers (must assign environment to artifacts)
- Gateway Implementers (must enforce environment matching)
- Runtime Implementers (must include environment in Context Bundles)
- Security/Compliance Teams (environment partitions authority)

---

**Last Updated:** 2025-12-29  
**Status:** Accepted  
**Next Review:** After v1 Implementation Feedback


