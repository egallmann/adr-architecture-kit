# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest published pre-1.0 release | Supported |
| Earlier pre-1.0 releases | Not supported |

This project is pre-1.0. Security fixes are applied to the latest published release only.

Security support applies to the ADR-Kit source release and its published supported distributions together — PyPI `adr-architecture-kit` and npm `@system-of-thought/adr-kit` — as a shared release lineage (ADR-L-0024), not as independent product lines.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Prefer **private vulnerability reporting** on this repository (Security → Report a vulnerability), or open a [GitHub Security Advisory](https://github.com/egallmann/adr-architecture-kit/security/advisories/new). Both keep the report private until a fix is available.

Include in your report:

- A description of the vulnerability and its potential impact
- Steps to reproduce or a minimal proof of concept
- Affected versions (if known)
- Any suggested mitigations

You can expect an acknowledgement within **5 business days** and a status update within **14 days** of the initial report.

## Scope

This package is a developer tool for authoring and validating Architecture Decision Records. The Python toolkit reads YAML and JSON from the local filesystem, writes generated discovery/projection artifacts when those commands are invoked, and ships GitHub Actions for CI, CodeQL, and release publishing. The official TypeScript consumer binding (`@system-of-thought/adr-kit`) is a read-only projection of accepted ADR-Kit authority (ADR-L-0024): no network access, no identity allocation, no graph admission, and no repository writes.

Primary attack surfaces include:

- **YAML parsing** — malicious YAML files passed to the parser
- **JSON Schema validation** — untrusted schema or ADR inputs
- **CLI path handling** — `--scope`, `--evidence`, and output paths that can overwrite generated artifacts
- **Generated artifact writes** — index, manifest, projection, and shim files written under an explicit project tree
- **npm package / release artifact integrity** — retained bundle identity and provenance for `@system-of-thought/adr-kit`
- **Node filesystem repository loading** — local ADR repository reads through Node entry points
- **Packaged canonical schema mirrors** — schema bytes shipped inside the npm package
- **Browser-safe vs Node-only entry-point isolation** — ensuring browser bundles cannot reach Node-only filesystem loaders
- **Release trust** — GitHub Actions OIDC / PyPI and npm trusted publishing and workflow `permissions` (human-gated; see admission rules below)

If you identify a vulnerability in a dependency (e.g. PyYAML, jsonschema, Pydantic), please report it upstream to that project and notify us so we can update the dependency.

## Out of Scope

- Issues in development tools (`pytest`, `ruff`, `black`, `mypy`) used only in dev environments
- Theoretical vulnerabilities without a practical exploit path
- TypeScript surfaces that would require network access, identity minting, graph admission, or repository writes (not exposed by the v1 consumer binding)

## Security tooling (enabled posture)

This public repository intends to keep the following GitHub security features enabled:

| Feature | Intent |
|---------|--------|
| Security policy (`SECURITY.md`) | How to report |
| Security advisories | Coordinated disclosure / published fixes |
| Private vulnerability reporting | Private inbound reports |
| Dependabot alerts | Dependency CVE notification (alerts; PRs optional) |
| Secret scanning (+ push protection when available) | Stop credential leaks |
| Code scanning (CodeQL) | Common vulnerability / bug classes |

CI dependency audit (`pip-audit`) remains a release-quality gate and does not replace Dependabot alerts.

## Security tooling and finding admission

Findings may be triaged with AI assistance. **Admission is human.**

### Roles

- **AI / agent** — inventory findings; classify; draft fixes or dismissal rationale; never close or dismiss unilaterally.
- **Maintainer (human)** — admit fix, dismiss, accept risk, or escalate; merge or close only after that admission.

### Disposition classes

| Class | Meaning | Default action |
|-------|---------|----------------|
| `fix` | True positive, actionable | Patch / bump / config change via PR |
| `false_positive` | Not exploitable in this product | Dismiss with written rationale |
| `accepted_risk` | Real but deferred | Document residual risk + revisit trigger |
| `upstream` | Belongs in a dependency | Track upstream; bump when fixed |
| `stop_the_line` | Secret exposure or release-trust issue | Immediate human handling; no dismiss |

### Hard rules

1. **No silent closes.** Every dismiss/close needs finding ID/URL, severity, rationale, residual risk, and admitted disposition.
2. **Secret scanning is `stop_the_line`.** Confirm, rotate if real, remediate; do not dismiss as noise.
3. **Release/publish trust is human-gated.** OIDC, PyPI/npm trusted publishing, GitHub Environments, and workflow `permissions:` changes are never “alert cleanup.”
4. **Minimal diffs.** Prefer the smallest safe fix. No opportunistic refactors in security PRs.
5. **Session habit.** When working in this repo, check open security alerts and clear or schedule them before considering the session done if alerts are in scope for the task.

### Admission comment template

```text
Disposition: fix | false_positive | accepted_risk | upstream | stop_the_line
Finding: <id or URL>
Severity: <GitHub severity>
Rationale: <one short paragraph>
Residual risk: <none | …>
Admitted by: <maintainer>
```
