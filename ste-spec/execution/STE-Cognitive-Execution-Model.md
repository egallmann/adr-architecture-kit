# STE Cognitive Execution Model  
## Deterministic Lifecycle for STE-Governed Reasoning

## Publication Notice

This cognitive execution model references the RECON Protocol document (`STE-RECON-Protocol.md`) which exists in the working repository but is not included in the v1.0.0 public release.

The architectural principles governing RECON execution are described in this document and in STE-Architecture.md. Detailed implementation protocols may be published in future releases.

---

# 1. Purpose of This Document
This file defines the **canonical execution model** STE uses to ensure deterministic, constraint-governed cognition.

Its objectives are to:

- transform invariants into enforceable cognitive behavior  
- eliminate implicit reasoning  
- validate documentation-state before and after each task  
- surface and resolve divergence  
- ensure synchronized, predictable reasoning outcomes  

This model governs all STE reasoning, including generation, analysis, validation, and framework evolution.

This file is canonical and must remain synchronized with:

- STE-Prime-Invariant
- STE-System-Invariants
- STE-Divergence-Taxonomy
- STE-Divergence-Communication-Protocol
- STE-Documentation-Checkpoint-Protocol
- STE-AI-DOC-Sliceability-Protocol
- STE-Architecture

---

# 2. Execution Model Overview  
STE reasoning follows a deterministic lifecycle composed of:

1. **Initialization**  
2. **State Loading**  
3. **Pre-Task Validation**  
4. **Divergence Detection**  
5. **Divergence Communication**  
6. **Correction and Reconvergence**  
7. **Reasoning Execution**  
8. **Post-Task Validation**  
9. **Final Convergence**

Each stage must be completed in order.  
No stage may be skipped.

---

# 3. Stage 1 — Initialization  
The system initializes by:

1. Loading the Prime Invariant  
2. Loading System Invariants  
3. Establishing the invariant hierarchy boundaries  
4. Preparing validators  
5. Establishing the cognitive environment devoid of implicit assumptions  
6. Verifying RECON completion status  

Initialization must occur before any reasoning step that depends on documentation-state or domain knowledge.

If RECON-Incomplete divergence is detected, initialization halts.

---

# 4. Stage 2 — State Loading

The system loads **only the explicit state** relevant to the task through a multi-step process:

## 4.1 Task Analysis (Task Analysis Protocol)

Before loading state, the system analyzes the user's request:

1. **Task Decomposition**
   - Parse natural language request into structured components
   - Extract: intent, target_type, target_identifier, keywords
   - Determine scope and domain hints
   - Assign confidence to decomposition

2. **Domain Resolution**
   - Map task components to AI-DOC domains
   - Prioritize primary and secondary domains
   - Prepare domain-specific search strategies

Output: Structured task analysis ready for entry point discovery

## 4.2 Entry Point Discovery (Task Analysis Protocol + RSS)

Using the task analysis, identify starting nodes for RSS traversal:

1. **Candidate Discovery**
   - Load relevant domain indexes
   - Filter by tags, keywords, target identifier
   - Filter by type (endpoint, entity, module, etc.)
   - Generate candidate list
   - **Note:** If domain unpopulated (lazy loading), trigger on-demand population or hybrid fallback

2. **Candidate Scoring**
   - Apply multi-factor scoring algorithm
   - Rank candidates by relevance
   - Filter by confidence thresholds

3. **Entry Point Selection**
   - **High confidence:** Auto-select top candidate
   - **Medium confidence:** Present options to user
   - **Low confidence:** Request clarification
   - **Multi-node tasks:** Select multiple entry points

Output: List of (domain, type, id) tuples for RSS traversal

## 4.3 RSS Graph Traversal

For each identified entry point, RSS assembles task-relevant context:

1. **Graph Traversal** — Traverse AI-DOC using `_slice` metadata
   - `dependencies(item, depth)` — Forward traversal
   - `dependents(item, depth)` — Backward traversal  
   - `by_tag(tag)` — Cross-domain queries
   
2. **Context Bounds Enforcement**
   - Respect maximum token budget
   - Respect maximum traversal depth
   - Apply domain filtering if specified

3. **Multi-Entry Point Convergence Validation**
   
   When Task Analysis identifies multiple high-confidence entry points, RSS validates semantic coherence through convergence measurement:
   
   **Entry Point Selection Strategy:**
   - 1 candidate → Single-entry RSS (standard traversal)
   - 2 candidates → Dual-entry RSS with overlap notification
   - 3+ candidates → Triple-entry RSS with convergence validation
   
   **Convergence Validation Protocol:**
   - Traverse independently from each of 3 entry points
   - Measure subgraph overlap between all pairs: (A,B), (A,C), (B,C)
   - Convergence metric: `overlap = |subgraph_X ∩ subgraph_Y| / |subgraph_X ∪ subgraph_Y|`
   - Threshold: 70% overlap indicates convergent subgraphs
   
   **Convergence Classification:**
   - **3 of 3 converge** (all pairs ≥70% overlap) → Ideal confidence, proceed
   - **2 of 3 converge** (2+ pairs ≥70% overlap) → Strong confidence, proceed with notation
   - **<2 of 3 converge** (0-1 pairs ≥70% overlap) → **Task-Entry-Point-Semantic-Divergence** detected
   
   **Rationale:** Validates that Task Analysis identified semantically coherent entry points leading to the same architectural region. Detects failure modes including ambiguous identifiers, homonyms, stale AI-DOC structure, and Task Analysis scoring errors. Provides measurable confidence without introducing non-determinism.
   
   **Failure Detection:** Divergent entry points indicate:
   - Multiple unrelated entities with similar names
   - Stale AI-DOC where relationships have changed
   - Task Analysis misinterpretation of user intent
   - Graph structure inconsistencies requiring attention

4. **Multi-Entry Point Merging**
   - Combine contexts from convergent entry points
   - Deduplicate overlapping nodes
   - Maintain relationship integrity
   - Include convergence confidence in context metadata

Output: Sliced AI-DOC nodes relevant to task with convergence confidence level

## 4.4 Context Assembly

Transform RSS output into LLM-ready context:

1. **Load Source Files**
   - For each AI-DOC node, load `source_files`
   - Include node metadata and relationships
   
2. **Assemble Final Context**
   - Sliced AI-DOC (semantic structure)
   - Source code (implementation)
   - Relationships (dependencies/dependents)
   - Domain constraints
   - **Tier Selection (Hybrid Context Assembly Protocol):**
     - **Tier 1:** Full RSS (deterministic, 100% confidence)
     - **Tier 2:** RSS + semantic search for gaps (70-90% confidence, user notified)
     - **Tier 3:** Semantic search only (30-60% confidence, user consent required)
   
3. **Context Delivery**
   - Package for LLM consumption
   - Ensure token budget respected
   - Mark if context was truncated
   - Include confidence level and tier metadata

Output: Minimally Viable Context (MVC) for task with explicit confidence

## 4.5 State Loading Constraints

State loading must not infer or assume anything not explicitly defined.

If missing state is detected → divergence is triggered.

Task Analysis failure → Task-Analysis-Incomplete divergence  
Entry point not found → Task-Entry-Point-Not-Found divergence

RSS ensures AI-DOC size and context size are decoupled.
Large projects can have comprehensive AI-DOC while individual tasks receive bounded context.

---

# 5. Stage 3 — Pre-Task Validation  
Before reasoning begins, the system must verify the integrity of:

- documentation-state  
- AI-DOC sliceability and graph integrity
- cross-artifact references  
- invariant alignment  
- artifact structure  
- hierarchical consistency  
- synchronization with the framework  
- plan completeness (for multi-artifact changes)

Validators involved:

- Documentation Validator  
- AI-DOC Graph Validator (verifies `_slice` metadata and relationships)
- AI-DOC Currency Validator (verifies AI-DOC currency, detects staleness per DOC-16)
- Framework Validator  
- Domain Validator (if domain-specific reasoning is required)
- Plan Validator (if framework modification, per STE-Plan-Validation-Protocol)

If any validator reports divergence → reasoning halts.

---

# 6. Stage 4 — Divergence Detection  
During or prior to reasoning, the system must detect inconsistencies such as:

- stale documentation  
- missing inventories  
- implicit assumptions  
- structural violations  
- hierarchy conflicts  
- taxonomy gaps  
- misplaced artifacts  
- semantic drift  

Each divergence must be classified using the STE Divergence Taxonomy.

Reasoning must not continue until classification is complete.

---

# 7. Stage 5 — Divergence Communication  
Once divergence is detected and classified, the agent must communicate it to the user per the **STE-Divergence-Communication-Protocol**.

This stage ensures:

- all divergences are surfaced explicitly  
- user consent is obtained where required  
- decline handling follows deterministic rules  
- no implicit behavior occurs at the agent-user boundary  

## 7.1 Gate Type Determination  
Each divergence is assigned a gate type:

- **Auto-Resolvable:** Agent may proceed without explicit consent  
- **User-Gated:** Agent must wait for user confirmation  
- **Blocking:** Agent cannot auto-resolve; requires user guidance  

## 7.2 Communication Flow  
1. Select canonical message template for divergence type  
2. Present divergence to user  
3. If User-Gated: wait for consent before proceeding  
4. If Blocking: wait for user guidance or manual correction  
5. If Auto-Resolvable: inform user and proceed automatically  
6. Handle decline if user does not consent  

## 7.3 Decline Handling  
If user declines a required operation:

1. Agent states the consequence explicitly  
2. If operation is blocking, agent exits STE governance  
3. Agent may continue without STE guarantees  
4. No implicit fallback behavior  

See: `/.ste/protocols/STE-Divergence-Communication-Protocol.md`

---

# 8. Stage 6 — Correction and Reconvergence  
Once divergence is classified, correction must occur through:

1. updating documentation-state  
2. correcting artifacts  
3. adjusting invariant placement  
4. resolving structural inconsistencies  
5. re-running validators  

Reconvergence requires:

- no further divergence  
- validation success  
- restored consistency across artifacts, invariants, and documentation-state  

Only then may the cognitive process resume.

---

# 9. Stage 7 — Reasoning Execution  
After successful reconvergence, reasoning proceeds under full adherence to:

- invariant hierarchy  
- artifact specifications  
- documentation-state  
- domain constraints  
- validator constraints  
- synchronization rules  

Reasoning must remain:

- explicit  
- bounded  
- deterministic  
- non-narrative  
- aligned with documentation-state  

Reasoning may not:

- modify documentation-state  
- update artifacts  
- change constraints  
without triggering a state-mutating checkpoint.

---

# 10. Stage 8 — Post-Task Validation  
Once reasoning completes, validators must run again to ensure:

- no divergence was introduced  
- no structural rules were violated  
- no documentation-state inconsistencies appeared  
- the output conforms to artifact specifications  
- cross-artifact relationships remain intact  

If divergence is detected, reasoning is invalid and must be corrected.

---

# 11. Stage 9 — Final Convergence  
The cognitive task is accepted only when:

- all validators pass  
- all invariants remain satisfied  
- framework synchronization is preserved  
- documentation-state is complete  
- divergence is absent  
- all dependencies are satisfied  

Final convergence produces a **deterministic, high-integrity output**.

---

# 12. Execution Rules

## 12.1 No Implicit Reasoning  
Any attempt to reason using unstated assumptions triggers divergence.

## 12.2 No Partial State  
Documentation-state must be complete before reasoning.

## 12.3 No Skipped Validation  
Skipping checkpoints invalidates the cognitive result.

## 12.4 No Out-of-Bound Cognition  
Reasoning must remain within declared scopes and domains.

## 12.5 No Unclassified Divergence  
Any inconsistency must be classified via taxonomy before correction.

---

# 13. Validator Integration  
Validators enforce the execution model by:

- detecting divergence  
- enforcing artifact specifications  
- ensuring documentation-state integrity  
- applying domain and system rules  
- validating cross-file consistency  
- preventing implicit reasoning  

Validators do not introduce new rules.

---

# 14. Dependencies  
This file depends on:

- Prime Invariant  
- System Invariants (SYS-1 through SYS-16)
- STE-Foundations  
- STE-Invariant-Hierarchy  
- STE-Divergence-Taxonomy  
- STE-Divergence-Communication-Protocol  
- STE-Documentation-Checkpoint-Protocol  
- STE-Framework-Validation-Rules  
- STE-RECON-Protocol
- STE-Lazy-Population-Protocol
- STE-Hybrid-Context-Assembly-Protocol
- STE-AI-DOC-Schema
- STE-AI-DOC-Sliceability-Protocol
- STE-AI-DOC-Graph-Validator
- STE-AI-DOC-Currency-Validator
- STE-Plan-Validation-Protocol
- STE-Task-Analysis-Protocol  

---

# 15. Canon Status  
This file is canonical.  
Any modification requires:

- Framework Validator approval  
- Inventory update  
- Directory verification  
- Reconvergence under divergence rules  

All STE reasoning must follow this execution model.

