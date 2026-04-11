# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x (current) | Yes |

This project is currently pre-1.0. Security fixes are applied to the latest release only.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

To report a vulnerability, open a [GitHub Security Advisory](https://github.com/egallmann/adr-architecture-kit/security/advisories/new) on this repository. This keeps the report private until a fix is available.

Include in your report:

- A description of the vulnerability and its potential impact
- Steps to reproduce or a minimal proof of concept
- Affected versions (if known)
- Any suggested mitigations

You can expect an acknowledgement within **5 business days** and a status update within **14 days** of the initial report.

## Scope

This package is a developer tool for authoring and validating Architecture Decision Records. It reads YAML and JSON files from the local filesystem and runs validation logic. The primary attack surfaces are:

- **YAML parsing** — malicious YAML files passed to the parser
- **JSON Schema validation** — untrusted schema or ADR inputs
- **CLI argument handling** — paths and flags passed to the `adr` CLI

If you identify a vulnerability in a dependency (e.g. PyYAML, jsonschema, Pydantic), please report it upstream to that project and notify us so we can update the dependency.

## Out of Scope

- Issues in development tools (`pytest`, `ruff`, `black`, `mypy`) used only in dev environments
- Theoretical vulnerabilities without a practical exploit path
