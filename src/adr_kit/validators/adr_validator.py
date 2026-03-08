"""ADR validator - validates ADRs against schema and business rules.

Implements ADR-L-0007: Multi-scope ADR architecture.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union, Dict

from ..models import LogicalADR, PhysicalADR
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
    
    def validate_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate ADR file.
        
        Args:
            file_path: Path to ADR YAML file
            
        Returns:
            ValidationResult with errors and warnings
        """
        file_path = Path(file_path)
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        # Try to parse ADR
        try:
            adr = self.parser.parse_adr(file_path)
        except ADRSchemaValidationError as e:
            errors.append(ValidationError(
                severity="error",
                rule="schema_validation",
                message=str(e)
            ))
            return ValidationResult(valid=False, errors=errors, warnings=warnings)
        except ADRParseError as e:
            errors.append(ValidationError(
                severity="error",
                rule="parse_error",
                message=str(e)
            ))
            return ValidationResult(valid=False, errors=errors, warnings=warnings)
        except Exception as e:
            errors.append(ValidationError(
                severity="error",
                rule="unknown_error",
                message=f"Unexpected error: {e}"
            ))
            return ValidationResult(valid=False, errors=errors, warnings=warnings)
        
        # Run business rule validations
        if isinstance(adr, LogicalADR):
            self._validate_logical_adr(adr, errors, warnings)
        elif isinstance(adr, PhysicalADR):
            self._validate_physical_adr(adr, errors, warnings)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
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
        
        # Check that decisions exist
        if not adr.decisions or len(adr.decisions) == 0:
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
    
    def validate_directory(self, adr_dir: Path, scope: Optional[ProjectScope] = None) -> dict:
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
        logical_files = list((adr_dir / "logical").glob("*.yaml")) if (adr_dir / "logical").exists() else []
        physical_files = list((adr_dir / "physical").glob("*.yaml")) if (adr_dir / "physical").exists() else []
        
        for file_path in logical_files + physical_files:
            result = self.validate_file(file_path)
            results[str(file_path)] = result
        
        return results
    
    def validate_scope(self, scope: Optional[ProjectScope] = None) -> dict:
        """Validate ADRs for project scope (ADR-L-0007: CAP-0003).
        
        Args:
            scope: Project scope (auto-detected if not provided)
            
        Returns:
            Dict with validation results per file
        """
        if scope is None:
            scope = self.scope_resolver.resolve()
        
        return self.validate_directory(scope.adr_dir, scope)
    
    def validate_recursive(self, scope: Optional[ProjectScope] = None) -> Dict[str, dict]:
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
                    results = self.validate_directory(s.adr_dir, s)
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
        
        logical_files = list((adr_dir / "logical").glob("*.yaml")) if (adr_dir / "logical").exists() else []
        physical_files = list((adr_dir / "physical").glob("*.yaml")) if (adr_dir / "physical").exists() else []
        
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
                adr = self.parser.parse_physical_adr(file_path)
                physical_adrs[adr.id] = adr
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
        
        # Validate related_adrs exist
        all_adr_ids = set(logical_adrs.keys()) | set(physical_adrs.keys())
        
        for adr in list(logical_adrs.values()) + list(physical_adrs.values()):
            if adr.related_adrs:
                for related_id in adr.related_adrs:
                    if related_id not in all_adr_ids:
                        warnings.append(ValidationError(
                            severity="warning",
                            rule="cross_reference",
                            message=f"ADR {adr.id} references non-existent related ADR {related_id}",
                            field="related_adrs"
                        ))
        
        # INV-0005: Check for duplicate IDs
        all_ids = list(logical_adrs.keys()) + list(physical_adrs.keys())
        if len(all_ids) != len(set(all_ids)):
            errors.append(ValidationError(
                severity="error",
                rule="INV-0005",
                message="Duplicate ADR IDs found across logical and physical ADRs"
            ))
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
