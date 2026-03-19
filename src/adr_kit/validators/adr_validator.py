"""ADR validator - validates ADRs against schema and business rules.

Implements ADR-L-0007: Multi-scope ADR architecture.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union, Dict

from ..decorators import implements_adr
from ..models import (
    ImplementationAuthority,
    LogicalADR,
    ObjectionOverride,
    PhysicalADR,
    PhysicalComponentADR,
    PhysicalSystemADR,
)
from ..parser import ADRParser, ADRParseError, ADRSchemaValidationError
from ..scope import ProjectScopeResolver, ProjectScope


@dataclass
class ValidationError:
    """Validation error details."""
    
    severity: str  # "error" or "warning"
    rule: str
    message: str
    field: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of ADR validation."""
    
    valid: bool
    mode: str
    errors: List[ValidationError]
    warnings: List[ValidationError]
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


@implements_adr("ADR-L-0015")
class ADRValidator:
    """Validate ADRs against schema and business rules.
    
    Supports multi-scope operation per ADR-L-0007.
    """
    
    def __init__(self, parser: ADRParser = None, project_root: Path = None, scope_resolver: ProjectScopeResolver = None):
        """Initialize validator.
        
        Args:
            parser: ADR parser (creates new one if not provided)
            project_root: Root directory of project (for checking file existence)
            scope_resolver: Project scope resolver (creates new one if not provided)
        """
        self.parser = parser or ADRParser()
        self.project_root = Path(project_root) if project_root else None
        self.scope_resolver = scope_resolver or ProjectScopeResolver()
    
    def _discover_adr_files(self, adr_dir: Path) -> tuple[list[Path], list[Path]]:
        """Discover logical and physical ADR files.

        Frontmatter determines exact ADR subtype. Directory structure only distinguishes
        logical from physical.
        """
        logical_files = list((adr_dir / "logical").glob("*.yaml")) if (adr_dir / "logical").exists() else []

        physical_files: list[Path] = []
        for dirname in ("physical", "physical-system", "physical-component"):
            candidate_dir = adr_dir / dirname
            if candidate_dir.exists():
                physical_files.extend(candidate_dir.glob("*.yaml"))

        deduped_physical = list(dict.fromkeys(path.resolve() for path in physical_files))
        return logical_files, [Path(path) for path in deduped_physical]

    def _discover_override_files(self, adr_dir: Path) -> list[Path]:
        """Discover objection override artifacts deterministically."""
        override_dir = adr_dir / "decisions" / "overrides"
        if not override_dir.exists():
            return []
        return sorted(path.resolve() for path in override_dir.glob("*.yaml"))

    def _schema_name_for_data(self, data: dict) -> str:
        """Map adr_type to parser schema names."""
        adr_type = data.get("adr_type")
        mapping = {
            "logical": "logical",
            "physical": "physical",
            "physical-system": "physical_system",
            "physical-component": "physical_component",
        }
        schema_name = mapping.get(adr_type)
        if schema_name is None:
            raise ADRParseError(f"Unknown adr_type: {adr_type}")
        return schema_name

    def validate_file(self, file_path: Union[str, Path], mode: str = "complete") -> ValidationResult:
        """Validate ADR file.
        
        Args:
            file_path: Path to ADR YAML file
            
        Returns:
            ValidationResult with errors and warnings
        """
        file_path = Path(file_path)
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        if mode not in {"complete", "structural"}:
            errors.append(ValidationError(
                severity="error",
                rule="invalid_mode",
                message=f"Unknown validation mode: {mode}"
            ))
            return ValidationResult(valid=False, mode=mode, errors=errors, warnings=warnings)

        if mode == "structural":
            try:
                data = self.parser.parse_yaml(file_path)
                self.parser.validate_against_schema(
                    data,
                    self._schema_name_for_data(data),
                    mode="structural",
                )
            except ADRSchemaValidationError as e:
                errors.append(ValidationError(
                    severity="error",
                    rule="schema_validation",
                    message=str(e)
                ))
            except ADRParseError as e:
                errors.append(ValidationError(
                    severity="error",
                    rule="parse_error",
                    message=str(e)
                ))
            except Exception as e:
                errors.append(ValidationError(
                    severity="error",
                    rule="unknown_error",
                    message=f"Unexpected error: {e}"
                ))
            return ValidationResult(valid=len(errors) == 0, mode=mode, errors=errors, warnings=warnings)
        
        try:
            raw_data = self.parser.parse_yaml(file_path)
        except ADRParseError as e:
            errors.append(ValidationError(
                severity="error",
                rule="parse_error",
                message=str(e)
            ))
            return ValidationResult(valid=False, mode=mode, errors=errors, warnings=warnings)

        # Try to parse ADR
        try:
            adr = self.parser.parse_adr(file_path)
        except ADRSchemaValidationError as e:
            errors.append(ValidationError(
                severity="error",
                rule="schema_validation",
                message=str(e)
            ))
            return ValidationResult(valid=False, mode=mode, errors=errors, warnings=warnings)
        except ADRParseError as e:
            errors.append(ValidationError(
                severity="error",
                rule="parse_error",
                message=str(e)
            ))
            return ValidationResult(valid=False, mode=mode, errors=errors, warnings=warnings)
        except Exception as e:
            errors.append(ValidationError(
                severity="error",
                rule="unknown_error",
                message=f"Unexpected error: {e}"
            ))
            return ValidationResult(valid=False, mode=mode, errors=errors, warnings=warnings)
        
        self._validate_governance_metadata(adr, raw_data, errors, warnings)

        # Run business rule validations
        if isinstance(adr, LogicalADR):
            self._validate_logical_adr(adr, errors, warnings)
        elif isinstance(adr, PhysicalSystemADR):
            self._validate_physical_system_adr(adr, errors, warnings)
        elif isinstance(adr, PhysicalComponentADR):
            self._validate_physical_component_adr(adr, errors, warnings)
        elif isinstance(adr, PhysicalADR):
            self._validate_physical_adr(adr, errors, warnings)
        
        return ValidationResult(
            valid=len(errors) == 0,
            mode=mode,
            errors=errors,
            warnings=warnings
        )

    def _validate_governance_metadata(self, adr, raw_data: dict, errors: List[ValidationError], warnings: List[ValidationError]):
        """Validate deterministic governance semantics on one ADR."""
        governance = getattr(adr, "governance", None)

        if "related_ledgers" in raw_data:
            warnings.append(ValidationError(
                severity="warning",
                rule="governance_deprecation",
                message="Top-level related_ledgers is deprecated; use governance.related_ledgers instead",
                field="related_ledgers",
            ))

        if governance is None:
            return

        if governance.approved_by and governance.approved_date is None:
            errors.append(ValidationError(
                severity="error",
                rule="governance_pairing",
                message="governance.approved_by requires governance.approved_date",
                field="governance.approved_date",
            ))

        if governance.approved_date is not None and not governance.approved_by:
            errors.append(ValidationError(
                severity="error",
                rule="governance_pairing",
                message="governance.approved_date requires governance.approved_by",
                field="governance.approved_by",
            ))

        if governance.steelman_review_required is True and governance.steelman_review_completed is None:
            errors.append(ValidationError(
                severity="error",
                rule="governance_steelman",
                message="governance.steelman_review_required=true requires an explicit governance.steelman_review_completed value",
                field="governance.steelman_review_completed",
            ))

        if governance.steelman_review_required is False and governance.steelman_review_completed is True:
            errors.append(ValidationError(
                severity="error",
                rule="governance_steelman",
                message="governance.steelman_review_completed=true is invalid when governance.steelman_review_required=false",
                field="governance.steelman_review_completed",
            ))

        if governance.implementation_authority == ImplementationAuthority.IMPLEMENTATION_AUTHORITATIVE:
            if not governance.approved_by or governance.approved_date is None:
                errors.append(ValidationError(
                    severity="error",
                    rule="governance_implementation_authority",
                    message="governance.implementation_authority=implementation_authoritative requires approval metadata",
                    field="governance.implementation_authority",
                ))
    
    def _validate_logical_adr(self, adr: LogicalADR, errors: List[ValidationError], warnings: List[ValidationError]):
        """Validate logical ADR business rules.
        
        Args:
            adr: Logical ADR model
            errors: List to append errors to
            warnings: List to append warnings to
        """
        # INV-0002: Logical ADRs must not contain implementation details
        impl_keywords = ["class", "function", "module", "package", "import", "npm", "pip"]
        context_lower = adr.context.lower() if adr.context else ""
        
        for keyword in impl_keywords:
            if keyword in context_lower:
                warnings.append(ValidationError(
                    severity="warning",
                    rule="INV-0002",
                    message=f"Logical ADR may contain implementation details (found '{keyword}')",
                    field="context"
                ))
                break
        
        # Check that decisions exist for fully realized ADR-L artifacts.
        if adr.id.startswith("ADR-L-") and (not adr.decisions or len(adr.decisions) == 0):
            warnings.append(ValidationError(
                severity="warning",
                rule="completeness",
                message="Logical ADR has no decisions defined",
                field="decisions"
            ))
        
        # Check that invariants have unique IDs
        inv_ids = [inv.id for inv in adr.invariants]
        if len(inv_ids) != len(set(inv_ids)):
            errors.append(ValidationError(
                severity="error",
                rule="INV-0005",
                message="Duplicate invariant IDs found",
                field="invariants"
            ))
    
    def _validate_physical_adr(self, adr: PhysicalADR, errors: List[ValidationError], warnings: List[ValidationError]):
        """Validate physical ADR business rules.
        
        Args:
            adr: Physical ADR model
            errors: List to append errors to
            warnings: List to append warnings to
        """
        # INV-0003: Physical ADRs must reference at least one logical ADR
        if not adr.implements_logical or len(adr.implements_logical) == 0:
            errors.append(ValidationError(
                severity="error",
                rule="INV-0003",
                message="Physical ADR must reference at least one logical ADR",
                field="implements_logical"
            ))
        
        # Check that component specifications exist
        if not adr.component_specifications or len(adr.component_specifications) == 0:
            warnings.append(ValidationError(
                severity="warning",
                rule="completeness",
                message="Physical ADR has no component specifications",
                field="component_specifications"
            ))
        
        # Validate implementation identifiers point to real files (if project_root provided)
        if self.project_root:
            for comp in adr.component_specifications:
                if comp.implementation_identifiers:
                    for impl_id in comp.implementation_identifiers:
                        # Check if it looks like a file path
                        if "/" in impl_id or "\\" in impl_id:
                            impl_path = self.project_root / impl_id
                            if not impl_path.exists():
                                warnings.append(ValidationError(
                                    severity="warning",
                                    rule="implementation_identifier",
                                    message=f"Implementation identifier not found: {impl_id}",
                                    field="component_specifications.implementation_identifiers"
                                ))
    
    def _validate_physical_system_adr(self, adr: PhysicalSystemADR, errors: List[ValidationError], warnings: List[ValidationError]):
        """Validate physical-system ADR business rules.
        
        Args:
            adr: Physical-System ADR model
            errors: List to append errors to
            warnings: List to append warnings to
        """
        # Must reference at least one logical ADR
        if not adr.implements_logical or len(adr.implements_logical) == 0:
            errors.append(ValidationError(
                severity="error",
                rule="physical_system_logical_ref",
                message="Physical-System ADR must reference at least one logical ADR",
                field="implements_logical"
            ))
        
        # System boundaries should be defined
        if not adr.system_boundaries or len(adr.system_boundaries) == 0:
            warnings.append(ValidationError(
                severity="warning",
                rule="completeness",
                message="Physical-System ADR should define system boundaries",
                field="system_boundaries"
            ))
        
        # references_components is optional and defaults to an empty list in the model,
        # so an empty value alone is not useful signal.
        if adr.references_components and len(adr.references_components) == 0:
            warnings.append(ValidationError(
                severity="warning",
                rule="completeness",
                message="references_components is empty, consider removing or adding component references",
                field="references_components"
            ))
    
    def _validate_physical_component_adr(self, adr: PhysicalComponentADR, errors: List[ValidationError], warnings: List[ValidationError]):
        """Validate physical-component ADR business rules.
        
        Args:
            adr: Physical-Component ADR model
            errors: List to append errors to
            warnings: List to append warnings to
        """
        # Must reference at least one Physical-System ADR
        if not adr.implements_system or len(adr.implements_system) == 0:
            errors.append(ValidationError(
                severity="error",
                rule="physical_component_system_ref",
                message="Physical-Component ADR must reference at least one Physical-System ADR",
                field="implements_system"
            ))
        
        # Must reference at least one logical ADR (inherited or direct)
        if not adr.implements_logical or len(adr.implements_logical) == 0:
            errors.append(ValidationError(
                severity="error",
                rule="physical_component_logical_ref",
                message="Physical-Component ADR must reference at least one logical ADR",
                field="implements_logical"
            ))
        
        # Must have at least one component specification
        if not adr.component_specifications or len(adr.component_specifications) == 0:
            errors.append(ValidationError(
                severity="error",
                rule="completeness",
                message="Physical-Component ADR must have at least one component specification",
                field="component_specifications"
            ))
        
        # Validate component specifications for AI generation readiness
        for comp in adr.component_specifications:
            # Must have implementation_identifiers for AI generation
            if not comp.implementation_identifiers:
                errors.append(ValidationError(
                    severity="error",
                    rule="ai_generation_readiness",
                    message=f"Component {comp.id} missing implementation_identifiers (required for AI generation)",
                    field="component_specifications.implementation_identifiers"
                ))
            
            # Must have at least one interface
            if not comp.interfaces or len(comp.interfaces) == 0:
                errors.append(ValidationError(
                    severity="error",
                    rule="ai_generation_readiness",
                    message=f"Component {comp.id} missing interfaces (required for AI generation)",
                    field="component_specifications.interfaces"
                ))
            
            # Must have generation_context
            if not comp.generation_context:
                errors.append(ValidationError(
                    severity="error",
                    rule="ai_generation_readiness",
                    message=f"Component {comp.id} missing generation_context (required for AI generation)",
                    field="component_specifications.generation_context"
                ))
            
            # Must have implementation_requirements
            if not comp.implementation_requirements:
                errors.append(ValidationError(
                    severity="error",
                    rule="ai_generation_readiness",
                    message=f"Component {comp.id} missing implementation_requirements (required for AI generation)",
                    field="component_specifications.implementation_requirements"
                ))
        
        # Validate granularity (2-8 components typical, >10 needs justification)
        if len(adr.component_specifications) > 10:
            warnings.append(ValidationError(
                severity="warning",
                rule="granularity",
                message=f"Physical-Component ADR has {len(adr.component_specifications)} components (>10). Ensure granularity is justified.",
                field="component_specifications"
            ))
        
        # If interface_compatibility is set, validate supersedes reference
        if adr.interface_compatibility and adr.interface_compatibility.supersedes_adr:
            if not adr.supersedes or adr.interface_compatibility.supersedes_adr not in adr.supersedes:
                warnings.append(ValidationError(
                    severity="warning",
                    rule="interface_compatibility",
                    message="interface_compatibility.supersedes_adr should be listed in supersedes field",
                    field="interface_compatibility"
                ))
    
    def validate_directory(self, adr_dir: Path, scope: Optional[ProjectScope] = None, mode: str = "complete") -> dict:
        """Validate all ADRs in directory.
        
        Args:
            adr_dir: Path to adrs/ directory
            scope: Project scope (auto-detected if not provided)
            
        Returns:
            Dict with validation results per file
        """
        adr_dir = Path(adr_dir)
        
        # Auto-detect scope if not provided (ADR-L-0007: CAP-0001)
        if scope is None:
            scope = self.scope_resolver.resolve(adr_dir.parent)
            print(f"Auto-detected project scope: {scope.name} at {scope.root}")
        
        results = {}
        
        # Find all ADR files
        logical_files, physical_files = self._discover_adr_files(adr_dir)

        for file_path in logical_files + physical_files:
            result = self.validate_file(file_path, mode=mode)
            results[str(file_path)] = result
        
        return results
    
    def validate_scope(self, scope: Optional[ProjectScope] = None, mode: str = "complete") -> dict:
        """Validate ADRs for project scope (ADR-L-0007: CAP-0003).
        
        Args:
            scope: Project scope (auto-detected if not provided)
            
        Returns:
            Dict with validation results per file
        """
        if scope is None:
            scope = self.scope_resolver.resolve()
        
        return self.validate_directory(scope.adr_dir, scope, mode=mode)
    
    def validate_recursive(self, scope: Optional[ProjectScope] = None, mode: str = "complete") -> Dict[str, dict]:
        """Validate ADRs for all scopes recursively (ADR-L-0007: CAP-0003, INV-0019).
        
        Args:
            scope: Root project scope (auto-detected if not provided)
            
        Returns:
            Dict mapping scope name to validation results
        """
        if scope is None:
            scope = self.scope_resolver.resolve()
        
        scopes = self.scope_resolver.resolve_recursive(scope.root)
        all_results = {}
        
        for s in scopes:
            if s.adr_dir.exists():
                try:
                    results = self.validate_directory(s.adr_dir, s, mode=mode)
                    all_results[s.name or str(s.root)] = results
                except Exception as e:
                    print(f"Warning: Failed to validate {s.name}: {e}")
        
        return all_results
    
    def validate_cross_references(self, adr_dir: Path) -> ValidationResult:
        """Validate cross-references between ADRs.
        
        Args:
            adr_dir: Path to adrs/ directory
            
        Returns:
            ValidationResult with cross-reference errors
        """
        adr_dir = Path(adr_dir)
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        # Parse all ADRs
        logical_adrs = {}
        physical_adrs = {}
        physical_system_adrs = {}
        physical_component_adrs = {}
        overrides: Dict[str, ObjectionOverride] = {}
        
        logical_files, physical_files = self._discover_adr_files(adr_dir)
        
        for file_path in logical_files:
            try:
                adr = self.parser.parse_logical_adr(file_path)
                logical_adrs[adr.id] = adr
            except Exception as e:
                errors.append(ValidationError(
                    severity="error",
                    rule="parse_error",
                    message=f"Failed to parse {file_path}: {e}"
                ))
        
        for file_path in physical_files:
            try:
                adr = self.parser.parse_adr(file_path)
                if isinstance(adr, PhysicalComponentADR):
                    physical_component_adrs[adr.id] = adr
                elif isinstance(adr, PhysicalSystemADR):
                    physical_system_adrs[adr.id] = adr
                elif isinstance(adr, PhysicalADR):
                    physical_adrs[adr.id] = adr
            except Exception as e:
                errors.append(ValidationError(
                    severity="error",
                    rule="parse_error",
                    message=f"Failed to parse {file_path}: {e}"
                ))

        for file_path in self._discover_override_files(adr_dir):
            try:
                override = self.parser.parse_objection_override(file_path)
                overrides[override.id] = override
            except Exception as e:
                errors.append(ValidationError(
                    severity="error",
                    rule="parse_error",
                    message=f"Failed to parse {file_path}: {e}"
                ))
        
        # Validate physical ADRs reference existing logical ADRs
        for phys_id, phys_adr in physical_adrs.items():
            for logical_ref in phys_adr.implements_logical:
                if logical_ref not in logical_adrs:
                    errors.append(ValidationError(
                        severity="error",
                        rule="cross_reference",
                        message=f"Physical ADR {phys_id} references non-existent logical ADR {logical_ref}",
                        field="implements_logical"
                    ))
        
        # Validate physical-system ADRs reference existing logical ADRs
        for sys_id, sys_adr in physical_system_adrs.items():
            for logical_ref in sys_adr.implements_logical:
                if logical_ref not in logical_adrs:
                    errors.append(ValidationError(
                        severity="error",
                        rule="cross_reference",
                        message=f"Physical-System ADR {sys_id} references non-existent logical ADR {logical_ref}",
                        field="implements_logical"
                    ))
            
            # Validate references_components if present
            if sys_adr.references_components:
                for comp_ref in sys_adr.references_components:
                    if comp_ref not in physical_component_adrs:
                        errors.append(ValidationError(
                            severity="error",
                            rule="cross_reference",
                            message=f"Physical-System ADR {sys_id} references non-existent Physical-Component ADR {comp_ref}",
                            field="references_components"
                        ))
        
        # Validate physical-component ADRs reference existing system and logical ADRs
        for comp_id, comp_adr in physical_component_adrs.items():
            for sys_ref in comp_adr.implements_system:
                if sys_ref not in physical_system_adrs:
                    errors.append(ValidationError(
                        severity="error",
                        rule="cross_reference",
                        message=f"Physical-Component ADR {comp_id} references non-existent Physical-System ADR {sys_ref}",
                        field="implements_system"
                    ))
            
            for logical_ref in comp_adr.implements_logical:
                if logical_ref not in logical_adrs:
                    errors.append(ValidationError(
                        severity="error",
                        rule="cross_reference",
                        message=f"Physical-Component ADR {comp_id} references non-existent logical ADR {logical_ref}",
                        field="implements_logical"
                    ))
        
        # Validate related_adrs exist
        all_adr_ids = set(logical_adrs.keys()) | set(physical_adrs.keys()) | set(physical_system_adrs.keys()) | set(physical_component_adrs.keys())
        
        for adr in list(logical_adrs.values()) + list(physical_adrs.values()) + list(physical_system_adrs.values()) + list(physical_component_adrs.values()):
            if adr.related_adrs:
                for related_id in adr.related_adrs:
                    if related_id not in all_adr_ids:
                        warnings.append(ValidationError(
                            severity="warning",
                            rule="cross_reference",
                            message=f"ADR {adr.id} references non-existent related ADR {related_id}",
                            field="related_adrs"
                        ))

            governance = getattr(adr, "governance", None)
            if governance and governance.related_overrides:
                for override_id in governance.related_overrides:
                    override = overrides.get(override_id)
                    if override is None:
                        errors.append(ValidationError(
                            severity="error",
                            rule="override_reference",
                            message=f"ADR {adr.id} references non-existent objection override {override_id}",
                            field="governance.related_overrides",
                        ))
                        continue
                    if override.related_adr != adr.id:
                        errors.append(ValidationError(
                            severity="error",
                            rule="override_reference",
                            message=f"Objection override {override.id} points to {override.related_adr} but is referenced by {adr.id}",
                            field="governance.related_overrides",
                        ))

        for override in overrides.values():
            related_adr = (
                logical_adrs.get(override.related_adr)
                or physical_adrs.get(override.related_adr)
                or physical_system_adrs.get(override.related_adr)
                or physical_component_adrs.get(override.related_adr)
            )
            if related_adr is None:
                errors.append(ValidationError(
                    severity="error",
                    rule="override_reference",
                    message=f"Objection override {override.id} references non-existent ADR {override.related_adr}",
                    field="related_adr",
                ))
                continue

            if override.related_adr_version is not None and getattr(related_adr, "modified_date", None) != override.related_adr_version:
                warnings.append(ValidationError(
                    severity="warning",
                    rule="stale_override",
                    message=f"Objection override {override.id} targets ADR version {override.related_adr_version} but {related_adr.id} is currently at {related_adr.modified_date}",
                    field="related_adr_version",
                ))
        
        # INV-0005: Check for duplicate IDs
        all_ids = list(logical_adrs.keys()) + list(physical_adrs.keys()) + list(physical_system_adrs.keys()) + list(physical_component_adrs.keys())
        if len(all_ids) != len(set(all_ids)):
            errors.append(ValidationError(
                severity="error",
                rule="INV-0005",
                message="Duplicate ADR IDs found across all ADR types"
            ))
        
        return ValidationResult(
            valid=len(errors) == 0,
            mode="complete",
            errors=errors,
            warnings=warnings
        )
