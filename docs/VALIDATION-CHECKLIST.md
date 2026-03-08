# Validation Checklist - Multi-Scope Implementation

**Purpose**: Checklist for validating CODEX implementation against ADR-L-0002 and ADR-P-0003  
**Validator**: Cursor Agent (me)  
**Authority**: ADR-L-0002, ADR-P-0003

---

## Pre-Implementation Checklist

- [x] ADR-L-0002 created with clear invariants
- [x] ADR-P-0003 created with component specifications
- [x] Implementation prompts generated for CODEX
- [x] Test requirements specified
- [x] Success criteria defined

---

## Component 1: Project Scope Resolver (COMP-0001)

### Code Review
- [ ] File exists: `src/adr_kit/scope/__init__.py`
- [ ] File exists: `src/adr_kit/scope/resolver.py`
- [ ] `ProjectScope` dataclass has all required fields
- [ ] `ProjectScope` is immutable (`frozen=True`)
- [ ] `ProjectScopeResolver` class exists
- [ ] Method exists: `resolve(start_dir) -> ProjectScope`
- [ ] Method exists: `resolve_recursive(start_dir) -> List[ProjectScope]`
- [ ] Type hints are complete and correct
- [ ] Docstrings present for all public methods

### Invariant Enforcement
- [ ] **INV-0014**: Explicit scope parameter supported
- [ ] **INV-0015**: Marker hierarchy implemented correctly:
  - [ ] 1. Explicit `--scope` parameter (highest priority)
  - [ ] 2. `ste.config.json`
  - [ ] 3. `PROJECT.yaml`
  - [ ] 4. `pyproject.toml`
  - [ ] 5. `package.json`
  - [ ] 6. `.git` directory
- [ ] **INV-0018**: Workspace boundary enforcement:
  - [ ] Stops at `.git` directory
  - [ ] Stops at system boundaries (`Users`, `Documents`, `home`, `/`)
  - [ ] Raises error if boundary violated

### Test Coverage
- [ ] File exists: `tests/test_scope_resolver.py`
- [ ] Test: `test_explicit_scope_overrides_detection`
- [ ] Test: `test_detect_from_ste_config`
- [ ] Test: `test_detect_from_project_yaml`
- [ ] Test: `test_detect_from_pyproject_toml`
- [ ] Test: `test_marker_priority_order`
- [ ] Test: `test_stops_at_git_directory`
- [ ] Test: `test_stops_at_documents_directory`
- [ ] Test: `test_detect_parent_scope`
- [ ] Test: `test_find_all_sub_modules`
- [ ] Test: `test_adr_architecture_kit_workspace`
- [ ] All tests pass: `pytest tests/test_scope_resolver.py -v`

### Integration Testing
- [ ] Detects `adr-architecture-kit` workspace root
- [ ] Detects `ste-runtime` as sub-module
- [ ] Works from any subdirectory
- [ ] Clear error when no project found

---

## Component 2: Scope-Aware Manifest Generator (COMP-0002)

### Code Review
- [ ] File modified: `src/adr_kit/generators/manifest_generator.py`
- [ ] `__init__` accepts `scope_resolver` parameter
- [ ] `generate_from_directory` accepts `scope` parameter
- [ ] Method added: `generate_from_scope(scope) -> Manifest`
- [ ] Method added: `generate_recursive(scope) -> Dict[str, Manifest]`
- [ ] Type hints complete
- [ ] Docstrings present

### Invariant Enforcement
- [ ] **INV-0016**: Each scope generates independent manifest
- [ ] **IMPL-0004**: Backward compatibility maintained:
  - [ ] Old code works without changes
  - [ ] `generate_from_directory(adr_dir)` still works
  - [ ] No breaking changes to existing API

### Test Coverage
- [ ] File exists: `tests/test_multi_scope_generator.py`
- [ ] Test: `test_generate_from_scope_auto_detection`
- [ ] Test: `test_generate_from_scope_explicit`
- [ ] Test: `test_generate_recursive`
- [ ] Test: `test_scoped_manifest_only_includes_scope_adrs`
- [ ] Test: `test_generate_from_directory_still_works`
- [ ] All tests pass: `pytest tests/test_multi_scope_generator.py -v`

### Integration Testing
- [ ] Generates manifest for workspace root
- [ ] Generates manifest for ste-runtime
- [ ] Recursive mode finds all scopes
- [ ] Manifest only includes ADRs from its scope

---

## Component 3: Scope-Aware Validator (COMP-0003)

### Code Review
- [ ] File modified: `src/adr_kit/validators/adr_validator.py`
- [ ] `__init__` accepts `scope_resolver` parameter
- [ ] `validate_directory` accepts `scope` parameter
- [ ] Method added: `validate_scope(scope) -> dict`
- [ ] Method added: `validate_recursive(scope) -> Dict[str, dict]`
- [ ] Type hints complete
- [ ] Docstrings present

### Invariant Enforcement
- [ ] **INV-0019**: Recursive validation validates all sub-modules
- [ ] **IMPL-0004**: Backward compatibility maintained:
  - [ ] Old validation code works unchanged
  - [ ] No breaking changes to existing API

### Test Coverage
- [ ] File exists: `tests/test_adr_validator.py`
- [ ] Test: `test_validate_valid_logical_adr`
- [ ] Test: `test_validate_directory`
- [ ] Test: `test_validate_cross_references`
- [ ] Test: `test_validate_scope_auto_detection`
- [ ] Test: `test_validate_recursive`
- [ ] Test: `test_validate_file_still_works`
- [ ] All tests pass: `pytest tests/test_adr_validator.py -v`

### Integration Testing
- [ ] Validates workspace ADRs
- [ ] Validates ste-runtime ADRs
- [ ] Recursive mode validates all scopes
- [ ] Clear validation reports per scope

---

## Component 4: Multi-Scope CLI (COMP-0004)

### Code Review
- [ ] File exists: `src/adr_kit/cli/__init__.py`
- [ ] File exists: `src/adr_kit/cli/main.py`
- [ ] CLI group defined: `cli()`
- [ ] Command: `generate-manifest` with `--scope`, `--recursive`, `--output`
- [ ] Command: `validate` with `--scope`, `--recursive`, `--cross-references`
- [ ] Command: `scope` with `--recursive`
- [ ] Entry point configured in `pyproject.toml`
- [ ] Type hints complete
- [ ] Help text clear and complete

### Invariant Enforcement
- [ ] **INV-0014**: `--scope` parameter works for all commands
- [ ] **INV-0019**: `--recursive` flag works for validation
- [ ] **CAP-0004**: Commands work from any directory

### Test Coverage
- [ ] File exists: `tests/test_cli.py`
- [ ] Test: `test_cli_generate_manifest_auto_detect`
- [ ] Test: `test_cli_generate_manifest_explicit_scope`
- [ ] Test: `test_cli_generate_manifest_recursive`
- [ ] Test: `test_cli_validate_auto_detect`
- [ ] Test: `test_cli_validate_recursive`
- [ ] Test: `test_cli_scope_display`
- [ ] Test: `test_cli_help_text`
- [ ] All tests pass: `pytest tests/test_cli.py -v`

### Integration Testing
- [ ] `adr --help` works
- [ ] `adr generate-manifest` works from workspace root
- [ ] `adr generate-manifest` works from ste-runtime
- [ ] `adr generate-manifest --recursive` finds all scopes
- [ ] `adr validate` works from any directory
- [ ] `adr validate --recursive` validates all scopes
- [ ] `adr scope` shows detected scope
- [ ] `adr scope --recursive` shows all scopes
- [ ] Error messages are clear and helpful

---

## Overall Test Suite

### Test Execution
- [ ] All tests pass: `pytest tests/ -v`
- [ ] No test failures
- [ ] No test errors
- [ ] Test coverage ≥ 80% (per ADR-L-0003 INV-0026)

### Test Quality
- [ ] Tests follow TDD methodology (IMPL-0001)
- [ ] Tests are isolated (no interdependencies)
- [ ] Tests are deterministic (same input → same output)
- [ ] Tests have clear names describing behavior
- [ ] Tests use fixtures appropriately

---

## Capability Verification (ADR-L-0002)

- [ ] **CAP-0001**: Automatic Project Scope Detection
  - [ ] Detects workspace root from any subdirectory
  - [ ] Detects sub-module root when run from sub-module
  - [ ] Respects explicit `--scope` parameter
  - [ ] Fails gracefully with clear error if no project found

- [ ] **CAP-0002**: Scoped Manifest Generation
  - [ ] Manifest includes only ADRs from detected scope
  - [ ] File paths in manifest are relative to project root
  - [ ] Cross-scope references validated but not included
  - [ ] Generated manifest includes scope metadata

- [ ] **CAP-0003**: Scoped Validation
  - [ ] Validates ADRs in detected scope
  - [ ] Validates cross-references within scope
  - [ ] Warns on cross-scope references
  - [ ] Recursive mode validates all sub-scopes

- [ ] **CAP-0004**: Multi-Scope CLI Interface
  - [ ] `adr generate-manifest` works from any directory
  - [ ] `adr validate` works from any directory
  - [ ] `--scope` parameter overrides auto-detection
  - [ ] `--recursive` enables multi-scope operations

---

## Invariant Verification (ADR-L-0002)

- [ ] **INV-0014**: Explicit scope parameter supported
- [ ] **INV-0015**: Marker hierarchy matches specification
- [ ] **INV-0016**: Each scope maintains independent adrs/ and manifest.yaml
- [ ] **INV-0017**: Cross-scope references use qualified IDs (documented)
- [ ] **INV-0018**: Workspace boundary enforcement prevents escape
- [ ] **INV-0019**: Recursive validation validates all sub-modules

---

## Implementation Decision Verification (ADR-P-0003)

- [ ] **IMPL-0001**: TDD methodology followed
  - [ ] Tests written before implementation
  - [ ] Red-Green-Refactor cycle evident
  - [ ] Test coverage comprehensive

- [ ] **IMPL-0002**: Dataclasses used for ProjectScope
  - [ ] `@dataclass(frozen=True)` used
  - [ ] Immutable scope objects

- [ ] **IMPL-0003**: Marker hierarchy mirrors ste-runtime
  - [ ] Same marker priority order
  - [ ] Consistent behavior across tools

- [ ] **IMPL-0004**: Backward compatible API
  - [ ] Existing code works unchanged
  - [ ] No breaking changes

- [ ] **IMPL-0005**: Click used for CLI
  - [ ] Click framework used
  - [ ] Professional CLI UX
  - [ ] Good help documentation

- [ ] **IMPL-0006**: Auto-detection by default
  - [ ] Zero-configuration experience
  - [ ] Tools work from any directory
  - [ ] Explicit override available

---

## Documentation Verification

- [ ] All public methods have docstrings
- [ ] Type hints complete and correct
- [ ] CLI help text clear and complete
- [ ] Error messages user-friendly
- [ ] README.md updated (if needed)

---

## Real-World Validation

### Test with adr-architecture-kit
- [ ] Run from workspace root: `adr scope`
- [ ] Expected: Shows adr-architecture-kit as root
- [ ] Run: `adr generate-manifest`
- [ ] Expected: Generates manifest for workspace ADRs only
- [ ] Run: `adr validate`
- [ ] Expected: Validates workspace ADRs

### Test with ste-runtime
- [ ] Run from ste-runtime: `cd ste-runtime && adr scope`
- [ ] Expected: Shows ste-runtime as root (sub-module)
- [ ] Run: `adr generate-manifest`
- [ ] Expected: Generates manifest for ste-runtime ADRs only
- [ ] Run: `adr validate`
- [ ] Expected: Validates ste-runtime ADRs

### Test recursive operations
- [ ] Run from workspace: `adr scope --recursive`
- [ ] Expected: Shows workspace + ste-runtime
- [ ] Run: `adr generate-manifest --recursive`
- [ ] Expected: Generates manifests for both scopes
- [ ] Run: `adr validate --recursive`
- [ ] Expected: Validates both scopes

---

## Final Sign-Off

### Code Quality
- [ ] No linting errors
- [ ] No type checking errors (mypy)
- [ ] Code follows project style
- [ ] No code smells or anti-patterns

### Completeness
- [ ] All 4 components implemented
- [ ] All 40+ tests passing
- [ ] All invariants enforced
- [ ] All capabilities delivered
- [ ] All implementation decisions followed

### Integration
- [ ] Works with real workspace
- [ ] Works with sub-modules
- [ ] Backward compatible
- [ ] No breaking changes

### Documentation
- [ ] Code documented
- [ ] Tests documented
- [ ] CLI help complete
- [ ] Error messages clear

---

## Validation Result

**Status**: [ ] PASS / [ ] FAIL

**Issues Found**:
- (List any issues discovered during validation)

**Recommendations**:
- (List any improvements or follow-up work)

**Sign-Off**:
- Validator: Cursor Agent
- Date: _____________
- ADR Authority: ADR-L-0002, ADR-P-0003

---

**This checklist ensures complete compliance with architectural decisions.**
