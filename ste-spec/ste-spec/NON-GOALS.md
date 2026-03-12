# Non-Goals

## Purpose

This document clarifies what the STE specification is NOT to prevent common misinterpretations.

## What This Specification Is NOT

### Not an Agent Framework or SDK

This is not a library, framework, or software development kit for building AI agents.

**What it is**: An architectural specification defining constraints, execution semantics, and governance protocols.

**What it is not**: Code you can import, install, or link against.

**If you want**: A framework for building agents, you must implement one that conforms to this specification. This specification does not provide implementation code.

### Not Deployment-Ready

This is not a system you can deploy, run, or operate.

**What it is**: Architectural constraints and requirements that implementations must satisfy.

**What it is not**: A runtime, service, application, or deployable artifact.

**If you want**: A deployable system, you must build or adopt an implementation that conforms to this specification. This specification does not provide deployment artifacts.

### Not an Attack System

This is not a tool, system, or guide for attacking, exploiting, or compromising systems.

**What it is**: An architecture for governing AI cognition through explicit constraints and oversight mechanisms.

**What it is not**: An exploitation framework, attack toolkit, or security testing tool.

**If you interpret**: The governance mechanisms as enabling harmful applications, note that the architecture prioritizes transparency, auditability, and constraint enforcement to enable oversight, not evasion.

### Not a Tutorial or How-To Guide

This is not a step-by-step implementation guide or educational tutorial.

**What it is**: A normative architectural specification for technical audiences requiring precision.

**What it is not**: A "getting started" guide, implementation walkthrough, or tutorial series.

**If you want**: Implementation guidance, consult reference implementations or implementation-specific documentation. This specification defines requirements, not procedures.

### Not Complete System Realization

This is not an exhaustive, end-to-end description of every system component, interaction, and data flow.

**What it is**: Architectural viewpoints addressing stakeholder concerns, structured using ISO/IEC/IEEE 42010 concepts.

**What it is not**: Complete architectural views with exhaustive implementation detail.

**If you expect**: Every component, every interaction, every data transformation to be specified, you are seeking implementation guidance, not architectural specification. This specification intentionally preserves design freedom.

### Not a Marketing Document

This is not promotional material, product positioning, or market-oriented messaging.

**What it is**: Technical specification using precise, professional language.

**What it is not**: Persuasive content aimed at non-technical audiences.

**If you find**: The language dense, formal, or inaccessible, that is intentional. This specification targets architectural researchers, governance system designers, and standards bodies, not general audiences.

### Not Implementation Prescription

This is not a mandate for specific programming languages, frameworks, platforms, or tools.

**What it is**: Requirements that implementations must satisfy (invariants, execution stages, governance protocols).

**What it is not**: Prescription of how implementations achieve conformance.

**If you think**: This specification requires specific technologies, you are misinterpreting normative constraints as implementation prescription. Conformance is defined by satisfaction of requirements, not use of specific mechanisms.

## Common Misinterpretations to Avoid

### "This tells me how to build an AI agent"

**Correction**: This tells you what constraints an AI agent must satisfy if it conforms to STE. Implementation is your responsibility.

### "This is a library I can use in my project"

**Correction**: This is a specification. You must implement or adopt a conformant library. The specification itself is not code.

### "This provides deployment templates for my infrastructure"

**Correction**: This specifies architectural constraints. Deployment topology is implementation-specific and intentionally excluded.

### "This includes working examples I can copy"

**Correction**: This includes conceptual descriptions and normative requirements. Reference implementations exist separately.

### "This is complete documentation of the entire system"

**Correction**: This is a set of architectural viewpoints. Complete views are intentionally excluded to preserve design freedom.

### "This shows me how to implement the Cognitive Execution Model"

**Correction**: This defines the stages, responsibilities, and validation requirements of the Cognitive Execution Model. Implementation mechanisms are your choice as long as requirements are satisfied.

### "This gives me operational procedures for running a system"

**Correction**: This gives you architectural constraints. Operational procedures depend on your deployment context, infrastructure, and organizational policies.

## What to Expect from This Specification

### You Will Find

- Clear definitions of constraints (invariants)
- Stage definitions and responsibilities (Cognitive Execution Model)
- Validation requirements (governance protocols)
- Classification systems (divergence taxonomy)
- Authority boundaries (attestation/enforcement/execution)
- Architectural decisions with rationale (ADRs)

### You Will NOT Find

- Step-by-step implementation guides
- Code examples or templates
- Deployment procedures
- Infrastructure recommendations
- Performance tuning advice
- Operational runbooks
- Monitoring dashboards
- Incident response procedures

## Intended Use

This specification is intended for:

1. **Architectural researchers** studying constraint-based AI governance
2. **Governance system designers** building deterministic cognition frameworks
3. **Standards bodies** evaluating approaches to AI oversight
4. **Implementation teams** needing normative requirements for conformance

This specification is NOT intended for:

1. General audiences seeking introductory material
2. Developers seeking quickstart guides or tutorials
3. Operators seeking deployment and operational procedures
4. Organizations seeking turnkey solutions

## If You Are Looking For

| You Want | You Should |
|----------|------------|
| Understanding of constraints | Read this specification (especially architecture/ and invariants/) |
| Implementation code | Build or adopt a conformant implementation (specification does not provide code) |
| Deployment guide | Consult implementation-specific documentation (not architectural specification) |
| Tutorial or walkthrough | Seek educational material aimed at your audience (not normative specification) |
| Complete system description | Recognize that architectural viewpoints are intentionally incomplete (design freedom) |
| Operational procedures | Develop procedures for your deployment context (not specified architecturally) |

## Summary

This is an architectural specification defining constraints, execution semantics, and governance protocols for AI cognition systems. It is not a framework, runtime, toolkit, tutorial, or complete system description. It provides normative requirements while preserving implementation design freedom.

**If you are uncertain whether your need is architectural or operational, ask**:

- **Architectural**: What must be true?
- **Operational**: How do I make it true?

This specification addresses architectural questions. Operational questions require implementation-specific guidance.

### What RECON Is Not

**RECON is not a security scanner.**

RECON extracts semantic state from artifacts to populate AI-DOC. It does not:
- Perform security vulnerability scanning
- Detect malicious code
- Replace SAST/DAST tooling
- Enforce security policies
- Validate code quality or safety

Organizations should use CI/CD security gates to validate code BEFORE it reaches canonical state that RECON extracts from.

**RECON documents what exists; CI/CD validates whether it should exist.**

If canonical state contains vulnerabilities, RECON will document them accurately. This is not a failure—it's correct extraction behavior. Security remediation follows normal development processes (fix code, pass CI/CD, merge, incremental RECON updates AI-DOC).

**Security scanning tools (examples):**
- SAST: SonarQube, CodeQL, Checkmarx, Veracode, Semgrep
- DAST: OWASP ZAP, Burp Suite, Acunetix, AppScan
- SCA: Snyk, Dependabot, WhiteSource, Black Duck
- Container: Trivy, Clair, Anchore, Aqua Security
- Secret: GitGuardian, TruffleHog, detect-secrets

These tools should run in CI/CD pipelines before code merges to canonical branches.

See SECURITY.md for trust assumptions regarding canonical state security.

---

**Use this specification to understand requirements, not to copy procedures.**
