# STE Divergence Taxonomy  
## Canonical Classification System for Detecting, Routing, and Resolving Divergence in STE

## Publication Notice
This document defines architectural constraints and responsibilities. It does not prescribe implementation.

# 1. Purpose of This Document
This file defines the **authoritative taxonomy** used to classify all divergence within the System of Thought Engineering (STE).

It ensures that:

- all inconsistencies are surfaced predictably  
- divergence is never ignored  
- corrective actions are deterministic  
- validators have a standard mapping  
- reconvergence follows a documented lifecycle  
- no implicit or ambiguous failure modes exist  

This taxonomy is canonical and must remain synchronized with:

- STE-Manifest  
- STE-Invariant-Hierarchy  
- STE-Framework-Validation-Rules  
- STE-RECON-Protocol  
- STE-Divergence-Communication-Protocol  
- Documentation-State Validator  
- Domain and Artifact validators  

---

# 2. Role of Divergence in STE
Divergence is not an error.  
It is the **signal** that the system has encountered:

- drift  
- inconsistency  
- misalignment  
- missing structure  
- stale documentation  
- rule conflicts  
- incomplete bootstrap  

STE requires that all divergence be:

1. **Detected**  
2. **Classified**  
3. **Corrected**  
4. **Revalidated**  
5. **Reconverged**  

No reasoning may proceed while unresolved divergence exists.

---

# 3. Taxonomy Structure  
The taxonomy is organized across the STE invariant layers:

1. **System-Level Divergence**  
2. **Domain-Level Divergence**  
3. **Artifact-Level Divergence**  
4. **Documentation-State Divergence**  
5. **Framework-Level Divergence**  

Each category contains explicit divergence types.

---

# 4. System-Level Divergence  
System-level divergence affects the highest layers of reasoning.

### **System-Hierarchy-Violation**
**Occurs when:**
- a rule contradicts a higher-level invariant  
- an invariant is misplaced  
- a specialization attempts to override higher constraints  

**Gate Type:** Blocking  
**Resolution Path:** Manual correction of conflicting invariant or rule placement  
**Auto-Resolvable:** No  

### **System-Ambiguity-Drift**
**Occurs when:**
- a rule creates ambiguity  
- definitions conflict  
- reasoning boundaries become unclear  

**Gate Type:** Blocking  
**Resolution Path:** Clarify definitions or resolve conflicting rules  
**Auto-Resolvable:** No  

### **System-Implicit-Reasoning**
**Occurs when:**
- reasoning uses unstated assumptions  
- constraints are invoked without declaration  

**Gate Type:** Blocking  
**Resolution Path:** Declare assumptions explicitly or remove implicit reasoning  
**Auto-Resolvable:** No  

### **System-Missing-Invariant**
**Occurs when:**
- a required invariant is missing  
- a domain references constraints that do not exist  

**Gate Type:** Blocking  
**Resolution Path:** Create missing invariant following STE-Invariant-Template  
**Auto-Resolvable:** No  

### **RECON-Incomplete**
**Occurs when:**
- the RECON protocol has not completed successfully  
- invariants are inferred but not validated  
- structural extraction is partial  
- assumptions remain implicit in the documentation-state  
- AI-DOC population is insufficient for reasoning  

**Gate Type:** User-Gated  
**Resolution Path:** Execute RECON-INITIALIZATION (full RECON Protocol)  
**Auto-Resolvable:** No  
**User Prompt:** "Execute RECON-INITIALIZATION"  

**RECON-Incomplete blocks all reasoning until resolved.**

This divergence type is introduced by the STE-RECON-Protocol and enforces that STE cannot operate without a valid bootstrap.

System-level divergence blocks all reasoning until corrected.

---

# 5. Domain-Level Divergence  

### **Domain-Constraint-Violation**
**Occurs when:**
- reasoning violates domain-specific rules  
- inputs contradict domain boundaries  

**Gate Type:** Blocking  
**Resolution Path:** Review domain constraints; adjust reasoning or update constraints  
**Auto-Resolvable:** No  

### **Domain-Context-Bleed**
**Occurs when:**
- reasoning applies rules from one domain to another incorrectly  

**Gate Type:** User-Gated  
**Resolution Path:** Identify cross-domain leakage; isolate reasoning to correct domain  
**Auto-Resolvable:** No  
**User Prompt:** "Confirm domain boundary correction"  

### **Domain-Missing-Subdomain**
**Occurs when:**
- a referenced subdomain invariant does not exist  
- specialization is needed but missing  

**Gate Type:** User-Gated  
**Resolution Path:** Create subdomain invariant or remove reference  
**Auto-Resolvable:** No  
**User Prompt:** "Create missing subdomain invariant"  

### **Domain-Semantic-Shift**
**Occurs when:**
- domain rules drift semantically over time  

**Gate Type:** User-Gated  
**Resolution Path:** Review and realign domain definitions with canonical meaning  
**Auto-Resolvable:** No  
**User Prompt:** "Confirm semantic realignment"  

Domain-level divergence must be corrected before domain reasoning continues.

---

# 6. Artifact-Level Divergence  

### **Artifact-Type-Mismatch**
**Occurs when:**
- a file does not conform to artifact specification rules  
- structure or formatting violates canonical expectations  

**Gate Type:** User-Gated  
**Resolution Path:** Restructure artifact to match STE-Artifact-Specifications  
**Auto-Resolvable:** No  
**User Prompt:** "Confirm artifact restructuring"  

### **Artifact-Semantic-Shift**
**Occurs when:**
- language or definitions drift from canonical meaning  

**Gate Type:** User-Gated  
**Resolution Path:** Review and correct language to match canonical definitions  
**Auto-Resolvable:** No  
**User Prompt:** "Confirm semantic correction"  

### **Artifact-Structure-Violation**
**Occurs when:**
- required sections are missing  
- required ordering is violated  

**Gate Type:** User-Gated  
**Resolution Path:** Add missing sections or reorder per artifact specification  
**Auto-Resolvable:** Partial (missing sections can be auto-generated with user consent)  
**User Prompt:** "Add missing artifact sections"  

Artifact divergence affects output correctness and must be resolved.

---

# 7. Documentation-State Divergence  

Documentation-state is the foundation for deterministic reasoning.  
All divergence here is critical.

### **Doc-Missing-Inventory**
**Occurs when:**
- required documentation-state artifacts are missing  
- inventories do not reflect actual truth  

**Gate Type:** User-Gated  
**Resolution Path:** Create missing inventory or populate from source artifacts  
**Auto-Resolvable:** No  
**User Prompt:** "Create missing inventory"  

### **Doc-State-Staleness**
**Occurs when:**
- documentation is outdated relative to system truth  

**Gate Type:** Auto-Resolvable  
**Resolution Path:** Refresh documentation-state from current source artifacts  
**Auto-Resolvable:** Yes  

### **Doc-Linkage-Inconsistency**
**Occurs when:**
- cross-artifact references are inconsistent  
- dependencies point to nonexistent files or definitions  

**Gate Type:** Auto-Resolvable  
**Resolution Path:** Update cross-artifact references to reflect current state  
**Auto-Resolvable:** Yes  

### **Doc-Implicit-State**
**Occurs when:**
- state is assumed but not declared  

**Gate Type:** User-Gated  
**Resolution Path:** Surface implicit assumptions for user validation; declare explicitly  
**Auto-Resolvable:** No  
**User Prompt:** "Validate assumptions"  

### **Doc-Constraint-Drift**
**Occurs when:**
- documentation violates constraints defined by invariants  

**Gate Type:** User-Gated  
**Resolution Path:** Realign documentation with governing invariants  
**Auto-Resolvable:** No  
**User Prompt:** "Confirm constraint realignment"  

---

## 7.1 AI-DOC Graph Divergence

The following divergence types govern AI-DOC sliceability and graph integrity per SYS-12, SYS-13, and SYS-14.

### **Doc-Sliceability-Violation**
**Occurs when:**
- AI-DOC item is missing `_slice` metadata block  
- Required `_slice` fields are absent  

**Gate Type:** Blocking  
**Resolution Path:** Add `_slice` metadata block per STE-AI-DOC-Sliceability-Protocol  
**Auto-Resolvable:** No  

### **Doc-Identifier-Collision**
**Occurs when:**
- Two AI-DOC items in the same domain share the same `_slice.id`  

**Gate Type:** Blocking  
**Resolution Path:** Rename one item's identifier to be unique  
**Auto-Resolvable:** No  

### **Doc-Domain-Mismatch**
**Occurs when:**
- `_slice.domain` value is not one of the 13 canonical domains  
- File location doesn't match declared domain  

**Gate Type:** User-Gated  
**Resolution Path:** Correct domain value or relocate file  
**Auto-Resolvable:** No  
**User Prompt:** "Correct domain mismatch"  

### **Doc-Reference-Unresolvable**
**Occurs when:**
- `_slice.references` entry points to non-existent AI-DOC item  
- `_slice.referenced_by` entry points to non-existent item  

**Gate Type:** Auto-Resolvable  
**Resolution Path:** Remove invalid reference or create missing item  
**Auto-Resolvable:** Partial (removal auto, creation requires consent)  

### **Doc-Bidirectional-Inconsistency**
**Occurs when:**
- Item A references Item B, but B doesn't list A in `referenced_by`  
- Item B lists A in `referenced_by`, but A doesn't reference B  

**Gate Type:** Auto-Resolvable  
**Resolution Path:** Add missing back-reference or forward reference  
**Auto-Resolvable:** Yes  

### **Doc-Orphaned-Item**
**Occurs when:**
- AI-DOC item is not listed in domain index  
- Item is not referenced by any other item  
- Item is undiscoverable by RSS  

**Gate Type:** User-Gated  
**Resolution Path:** Add to index or establish references  
**Auto-Resolvable:** No  
**User Prompt:** "Resolve orphaned AI-DOC item"  

### **Doc-Index-Incomplete**
**Occurs when:**
- Domain `index.yaml` doesn't list all items in domain directory  

**Gate Type:** Auto-Resolvable  
**Resolution Path:** Add missing items to index  
**Auto-Resolvable:** Yes  

### **Doc-Index-Stale**
**Occurs when:**
- Domain `index.yaml` lists items that don't exist  

**Gate Type:** Auto-Resolvable  
**Resolution Path:** Remove non-existent items from index  
**Auto-Resolvable:** Yes  

### **Doc-Source-Missing**
**Occurs when:**
- `_slice.source_files` lists files that don't exist in codebase  

**Gate Type:** User-Gated  
**Resolution Path:** Update source files or verify file locations  
**Auto-Resolvable:** No  
**User Prompt:** "Verify source file locations"  

### **Doc-Placement-Violation**
**Occurs when:**
- AI-DOC item file is in wrong directory for its declared domain  

**Gate Type:** User-Gated  
**Resolution Path:** Move file to correct directory or update domain  
**Auto-Resolvable:** No  
**User Prompt:** "Correct file placement"  

### **Doc-Schema-Violation**
**Occurs when:**
- AI-DOC item doesn't conform to domain schema in STE-AI-DOC-Schema  

**Gate Type:** User-Gated  
**Resolution Path:** Update item to conform to schema  
**Auto-Resolvable:** No  
**User Prompt:** "Fix schema violation"  

### **Doc-Parse-Error**
**Occurs when:**
- AI-DOC YAML file cannot be parsed  
- Invalid YAML syntax  

**Gate Type:** Blocking  
**Resolution Path:** Fix YAML syntax errors  
**Auto-Resolvable:** No  

### **Doc-Format-Invalid**
**Occurs when:**
- AI-DOC file has wrong extension (not `.yaml`)  
- File encoding is not UTF-8  

**Gate Type:** User-Gated  
**Resolution Path:** Rename file or fix encoding  
**Auto-Resolvable:** No  
**User Prompt:** "Fix file format"  

### **Doc-Extraction-Missing**
**Occurs when:**
- `_slice.extraction` metadata block is missing  
- `extraction.method` or `extraction.confidence` not specified  

**Gate Type:** Auto-Resolvable  
**Resolution Path:** Add extraction metadata with appropriate values  
**Auto-Resolvable:** Partial (can default to `inferred`/`low`)  

### **Doc-Confidence-Undeclared**
**Occurs when:**
- `extraction.confidence` is missing or invalid  
- Low-confidence items not flagged for review  

**Gate Type:** Auto-Resolvable  
**Resolution Path:** Add or correct confidence level  
**Auto-Resolvable:** Yes (default to `low`)  

### **Doc-Graph-Integrity-Violation**
**Occurs when:**
- AI-DOC graph has structural inconsistencies  
- Multiple relationship violations detected  
- Graph is not traversable  

**Gate Type:** Blocking  
**Resolution Path:** Run AI-DOC Graph Validator and fix all issues  
**Auto-Resolvable:** No  

### **Doc-Ambiguity-Detected**
**Occurs when:**
- AI-DOC contains implicit or ambiguous state  
- Narrative language implies unstated facts  

**Gate Type:** User-Gated  
**Resolution Path:** Make implicit state explicit or remove ambiguity  
**Auto-Resolvable:** No  
**User Prompt:** "Clarify ambiguous state"  

### **Doc-Population-Bypass**
**Occurs when:**
- AI-DOC manually authored without RECON  
- Bulk manual population bypassing extraction  

**Gate Type:** User-Gated  
**Resolution Path:** Validate manual content or re-run RECON  
**Auto-Resolvable:** No  
**User Prompt:** "Validate manual AI-DOC population"  

### **Doc-Update-Bypass**
**Occurs when:**
- AI-DOC modified without following Update Workflow Protocol  
- Updates made without checkpoint validation  

**Gate Type:** User-Gated  
**Resolution Path:** Validate changes through proper workflow  
**Auto-Resolvable:** No  
**User Prompt:** "Validate AI-DOC update"  

Documentation divergence must be corrected before any reasoning continues.

---

# 8. Framework-Level Divergence  

Framework divergence represents inconsistencies in the STE framework itself.

### **Framework-Structure-Violation**
**Occurs when:**
- canonical files are placed incorrectly  
- directory structure rules are violated  

**Gate Type:** User-Gated  
**Resolution Path:** Relocate files per STE-Framework-Directory-Structure  
**Auto-Resolvable:** Partial (can auto-correct with user consent)  
**User Prompt:** "Fix framework structure"  

### **Framework-Missing-Sync-Rule**
**Occurs when:**
- synchronization rules are incomplete or missing  

**Gate Type:** Blocking  
**Resolution Path:** Define missing synchronization rule in framework  
**Auto-Resolvable:** No  

### **Framework-Inventory-Inconsistency**
**Occurs when:**
- inventory does not match actual files  

**Gate Type:** Auto-Resolvable  
**Resolution Path:** Synchronize inventory with actual file system state  
**Auto-Resolvable:** Yes  

### **Framework-Update-Protocol-Violation**
**Occurs when:**
- contributor workflow is bypassed  
- updates occur without validation  

**Gate Type:** Blocking  
**Resolution Path:** Revert changes; re-apply following Contributor Workflow  
**Auto-Resolvable:** No  

### **Framework-Reference-Unresolvable**
**Occurs when:**
- Invariant references divergence type not in Taxonomy  
- Protocol references component that doesn't exist  
- Validator references invariant that doesn't exist  
- Forward reference to undefined artifact  

**Gate Type:** Blocking  
**Resolution Path:** Create missing artifact or remove invalid reference  
**Auto-Resolvable:** No  

This divergence enforces SYS-15 (Framework Reference Resolution).

### **Framework-Cascade-Incomplete**
**Occurs when:**
- New divergence types added without Taxonomy update  
- New components added without Architecture update  
- New artifacts added without Manifest update  
- Multi-artifact change partially completed  

**Gate Type:** Blocking  
**Resolution Path:** Complete all cascade updates or revert partial changes  
**Auto-Resolvable:** No  

This divergence enforces SYS-16 (Cascade Update Requirement).

Framework divergence prevents further framework evolution until corrected.

---

## 7.2 Task Analysis Divergence

The following divergence types govern Task Analysis Protocol execution and entry point discovery per CEM Stage 2.

### **Task-Entry-Point-Ambiguous**

**Occurs when:**
- Multiple candidates scored equally or above threshold
- 2+ candidates score within 10 points of each other above threshold
- User input insufficient to distinguish candidates
- Multiple valid interpretations of task exist

**Severity:** Warning

**Gate Type:** User-Gated  
**Resolution Path:** Present candidates to user for selection, request additional context, or allow user to specify domain/identifier more precisely  
**Auto-Resolvable:** No  
**User Prompt:** "Multiple matches found. Please select:"

**Validator:** Task Analysis Validator

**Example:**
```
Task: "Update user endpoint"
Candidates:
  - api/get-user-endpoint (score: 85)
  - api/update-user-endpoint (score: 82)
  - api/delete-user-endpoint (score: 80)
```

---

### **Task-Entry-Point-Semantic-Divergence**

**Occurs when:**
- RSS traversal from 3 entry points produces non-convergent subgraphs
- Fewer than 2 of 3 entry point pairs achieve ≥70% subgraph overlap
- Entry points lead to disconnected or semantically unrelated regions
- Convergence validation detects semantic incoherence

**Severity:** Warning (1 of 3 pairs converge) or Error (0 of 3 pairs converge)

**Gate Type:** User-Gated  
**Resolution Path:**
- Present divergent subgraphs to user for manual disambiguation
- Display convergence metrics and overlap analysis
- Request additional task context to refine entry point selection
- User selects correct semantic region or entry point
- May indicate AI-DOC staleness requiring RECON refresh
- May reveal homonyms or ambiguous identifiers requiring clarification

**Auto-Resolvable:** No  
**User Prompt:** "Entry points lead to different semantic regions (convergence: X of 3). Which context is correct?"

**Validator:** RSS Convergence Validator

**Example:**
```
Task: "Update auth service"
Entry Points:
  - auth-service-api (leads to: API endpoints, controllers, routes)
  - auth-service-core (leads to: Business logic, validators, models)
  - auth-legacy (leads to: Deprecated authentication system)

Convergence Analysis:
  - auth-service-api ∩ auth-service-core: 75% overlap (converge)
  - auth-service-api ∩ auth-legacy: 15% overlap (diverge)
  - auth-service-core ∩ auth-legacy: 10% overlap (diverge)

Result: 1 of 3 pairs converge → Task-Entry-Point-Semantic-Divergence
Resolution: User clarifies: "Update current auth service" (exclude auth-legacy)
```

**Rationale:** Validates that Task Analysis identified semantically coherent entry points. Detects failure modes including ambiguous identifiers, homonyms, stale graph structure, and misinterpreted user intent. Prevents reasoning from incorrect semantic region.

---

### **Task-Entry-Point-Not-Found**

**Occurs when:**
- No candidates found in any searched domain
- All candidates score below minimum threshold
- Target identifier doesn't match any AI-DOC items
- Zero candidates discovered during candidate discovery

**Severity:** Error (blocking)

**Gate Type:** Blocking  
**Resolution Path:**
- Verify AI-DOC is current (run RECON refresh)
- Verify target code/entity actually exists in codebase
- Check if RECON-Incomplete divergence is present
- User may need to browse domain indexes manually
- Task may need clarification or rephrasing

**Auto-Resolvable:** No

**Validator:** Task Analysis Validator

**Example:**
```
Task: "Update payment gateway integration"
Result: No items found in graph/external domain matching "payment gateway"
Action: Run RECON to populate AI-DOC or verify integration exists
```

---

### **Task-Decomposition-Failure**

**Occurs when:**
- Unable to parse task into structured components
- Task is too vague or ambiguous
- Task contains conflicting intents
- Task lacks actionable target
- Required fields missing from decomposition
- Invalid enum values in decomposition

**Severity:** Error (blocking)

**Gate Type:** Blocking  
**Resolution Path:**
- Request user rephrase task more explicitly
- Suggest task decomposition format
- Provide examples of well-formed tasks
- Ask user to specify intent, target type, or identifier

**Auto-Resolvable:** No

**Validator:** Task Analysis Validator

**Example:**
```
Task: "Make it better"
Failure: No clear intent, target_type, or identifier
Resolution: User should specify: "Update the login endpoint to improve validation"
```

---

### **Task-Analysis-Incomplete**

**Occurs when:**
- Task Analysis Protocol not executed at CEM Stage 2
- Task Analysis Validator failed
- Entry point discovery returned no results
- Task decomposition skipped
- Domain resolution not performed
- Required Task Analysis steps not completed

**Severity:** Error (blocking)

**Gate Type:** Blocking  
**Resolution Path:**
- Execute Task Analysis Protocol completely
- Resolve underlying divergence (Entry-Point-Not-Found, Decomposition-Failure, etc.)
- Ensure CEM follows proper execution flow
- Verify Task Analysis Protocol is properly integrated

**Auto-Resolvable:** No

**Validator:** Task Analysis Validator, CEM Validator

**Example:**
```
CEM Stage 2 attempted to invoke RSS without first executing Task Analysis
Resolution: Execute Stage 2.1-2.2 (Task Analysis + Entry Point Discovery) before Stage 2.3 (RSS Graph Traversal)
```

---

## 7.3 Operational Divergence

The following divergence types govern operational AI-DOC maintenance, including currency, incremental updates, lazy population, and merge operations.

### **Doc-State-Staleness**

**Occurs when:**
- AI-DOC item's extraction timestamp < source file modification timestamp
- Source code changed but AI-DOC not updated
- Incremental RECON not executed after file changes
- File watcher or git hook failed to trigger update

**Severity:** Error (blocking for reasoning tasks) | Warning (for analysis tasks)

**Gate Type:** Blocking (reasoning) | User-Gated (analysis)

**Resolution Path:**
- Execute Incremental RECON for affected items
- Re-extract stale items from current source code
- Validate updated items pass AI-DOC Graph Validator
- Update extraction timestamps

**Auto-Resolvable:** Yes (if incremental RECON available)

**Validator:** AI-DOC Currency Validator

**Example:**
```
File: src/api/users.py modified at 2024-12-10T15:30:00Z
AI-DOC: api/get-user-endpoint extracted at 2024-12-10T10:00:00Z
Staleness: 5 hours 30 minutes
Resolution: Run incremental-recon src/api/users.py
```

---

### **AI-DOC-Domain-Unpopulated**

**Occurs when:**
- Task requires domain not yet populated (lazy loading)
- RSS cannot traverse unpopulated domain
- On-demand population not yet triggered
- User working during Phase 1 or before Phase 3 complete

**Severity:** Warning

**Gate Type:** User-Gated

**Resolution Path:**
- Populate domain on-demand (user consent, ~5 seconds)
- Use Hybrid Context Assembly fallback (semantic search)
- Defer task until background population complete
- User can choose to proceed with lower confidence context

**Auto-Resolvable:** No (requires user consent for on-demand population)

**Validator:** Lazy Population Validator

**Example:**
```
Task: "Optimize database connection pooling"
Entry Point: infrastructure/database-layer (unpopulated)
Resolution Options:
  1. Populate infrastructure domain now (~5s)
  2. Use hybrid fallback (Tier 2 context, 70% confidence)
  3. Wait for background population
```

---

### **Doc-Merge-Regeneration-Failed**

**Occurs when:**
- AI-DOC merge conflict detected during git operation
- Attempted regeneration from merged source code
- Regeneration failed (parse error, extraction error, validation failure)
- Source code has syntax errors or structural issues

**Severity:** Error (blocking)

**Gate Type:** Blocking

**Resolution Path:**
- Resolve source code conflicts/errors first
- Ensure source code compiles/parses successfully
- Re-run incremental RECON after source resolution
- Validate regenerated AI-DOC passes all validators
- If regeneration continues to fail, run full RECON

**Auto-Resolvable:** No (requires source code fix)

**Validator:** Incremental RECON Validator, AI-DOC Merge Validator

**Example:**
```
Git Operation: merge feature-branch
AI-DOC Conflicts: api/endpoints/get-user.yaml
Source Resolution: src/api/users.py resolved but has SyntaxError line 42
Regeneration: Failed (cannot parse source)
Resolution: Fix syntax error in src/api/users.py, then retry regeneration
```

---

### **Incremental-Update-Failed**

**Occurs when:**
- Incremental RECON attempted
- Update validation failed (equivalence, complexity, or atomicity check)
- Incremental result != full RECON result
- Bidirectional consistency violated
- Performance exceeded O(changed files) bounds

**Severity:** Error (blocking)

**Gate Type:** Blocking

**Resolution Path:**
- Rollback to previous AI-DOC state (preserve consistency)
- Fall back to full RECON (guaranteed correct result)
- Investigate incremental algorithm (may indicate implementation bug)
- Log failure details for debugging
- User proceeds with full RECON (may take longer)

**Auto-Resolvable:** Yes (automatic fallback to full RECON)

**Validator:** Incremental RECON Validator

**Example:**
```
Incremental Update: src/api/users.py
Validation: Equivalence check failed
Issue: Incremental result missing dependency (models/role)
Action: Rollback incremental changes
Fallback: Running full RECON (~2 minutes)
Result: Full RECON completed successfully
```

---

# 9. User Gate Classification  

Divergences are classified into three gate types that determine how the agent communicates with the user and whether consent is required before correction.

## 9.1 Auto-Resolvable (No Gate)  
The agent may resolve these divergences without explicit user consent.

**Criteria:**
- resolution does not mutate project state significantly  
- resolution is low-cost (time, compute)  
- resolution has no user-visible side effects  
- resolution is deterministic and reversible  

**Divergence Types:**
- Doc-State-Staleness  
- Doc-Linkage-Inconsistency  
- Doc-Bidirectional-Inconsistency  
- Doc-Index-Incomplete  
- Doc-Index-Stale  
- Doc-Confidence-Undeclared  
- Framework-Inventory-Inconsistency  

## 9.2 User-Gated (Requires Consent)  
The agent must obtain explicit user consent before resolving these divergences.

**Criteria:**
- resolution involves significant state mutation  
- resolution is expensive (time, compute, context)  
- resolution may surface assumptions requiring user validation  
- resolution affects project structure  

**Divergence Types:**
- RECON-Incomplete  
- Doc-Implicit-State  
- Doc-Missing-Inventory  
- Doc-Constraint-Drift  
- Doc-Domain-Mismatch  
- Doc-Orphaned-Item  
- Doc-Source-Missing  
- Doc-Placement-Violation  
- Doc-Schema-Violation  
- Doc-Format-Invalid  
- Doc-Ambiguity-Detected  
- Doc-Population-Bypass  
- Doc-Update-Bypass  
- Domain-Context-Bleed  
- Domain-Missing-Subdomain  
- Domain-Semantic-Shift  
- Artifact-Type-Mismatch  
- Artifact-Semantic-Shift  
- Artifact-Structure-Violation  
- Framework-Structure-Violation  

## 9.3 Blocking (Cannot Auto-Resolve)  
The agent cannot resolve these divergences automatically; they require manual intervention.

**Criteria:**
- resolution requires human judgment  
- resolution involves choices the agent cannot make  
- resolution may require external action  

**Divergence Types:**
- System-Hierarchy-Violation  
- System-Ambiguity-Drift  
- System-Implicit-Reasoning  
- System-Missing-Invariant  
- Domain-Constraint-Violation  
- Doc-Sliceability-Violation  
- Doc-Identifier-Collision  
- Doc-Parse-Error  
- Doc-Graph-Integrity-Violation  
- Framework-Missing-Sync-Rule  
- Framework-Update-Protocol-Violation  
- Framework-Reference-Unresolvable  
- Framework-Cascade-Incomplete  

See: `/.ste/protocols/STE-Divergence-Communication-Protocol.md`

---

# 10. Divergence Resolution Lifecycle  

All divergences must follow this lifecycle:

1. **Detection**  
   Identify the presence of divergence.

2. **Classification**  
   Assign divergence type using this taxonomy.

3. **Communication**  
   Surface divergence to user per STE-Divergence-Communication-Protocol.

4. **Correction**  
   Update invariants, documentation-state, structure, or artifacts.
   - If Auto-Resolvable: proceed automatically after informing user  
   - If User-Gated: wait for user consent before proceeding  
   - If Blocking: wait for user guidance or manual correction  

5. **Revalidation**  
   Run validators to ensure correction succeeded.

6. **Reconvergence**  
   Confirm the system has returned to stable deterministic state.

No step may be skipped.

---

# 11. Validator Integration  
Validators must:

- detect violations  
- classify divergence using this taxonomy  
- route divergence to the correct layer  
- enforce correction before reasoning proceeds  

Validators must not introduce new divergence types.

---

# 12. Dependencies  
This file depends on:

- Prime Invariant  
- System Invariants (SYS-1 through SYS-16)  
- STE-Manifest  
- STE-Invariant-Hierarchy  
- STE-Framework-Validation-Rules  
- STE-RECON-Protocol  
- STE-Divergence-Communication-Protocol  
- STE-AI-DOC-Schema  
- STE-AI-DOC-Sliceability-Protocol  
- STE-AI-DOC-Invariants  
- STE-AI-DOC-Graph-Validator  

---

# 13. Canon Status  
This file is canonical.  
Any modification requires:

- inventory update  
- directory structure verification  
- validator execution  
- reconvergence loop  

All divergence classification across STE must use this taxonomy.

