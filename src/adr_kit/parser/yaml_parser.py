"""YAML parser with JSON Schema validation for ADR artifacts."""

import json
from pathlib import Path
from typing import Union

import jsonschema
from jsonschema.validators import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7
import yaml
from pydantic import ValidationError

from ..models import (
    DecisionLedger,
    EntityRegistry,
    LogicalADR,
    Manifest,
    PhysicalADR,
    PhysicalSystemADR,
    PhysicalComponentADR,
    ProjectMetadata,
    RequirementsSnapshot,
    StandaloneInvariant,
)


class ADRParseError(Exception):
    """Error parsing ADR artifact."""
    pass


class ADRSchemaValidationError(Exception):
    """Error validating ADR against JSON Schema."""
    pass


class ADRParser:
    """Parser for ADR YAML artifacts with schema validation."""
    
    def __init__(self, schema_dir: Path = None, schema_v11_dir: Path = None):
        """Initialize parser with schema directory.
        
        Args:
            schema_dir: Path to v1.0 schema directory (defaults to package schema/v1.0)
            schema_v11_dir: Path to v1.1 schema directory (defaults to package schema/v1.1)
        """
        if schema_dir is None:
            schema_dir = Path(__file__).parent.parent.parent.parent / "schema" / "v1.0"
        if schema_v11_dir is None:
            schema_v11_dir = Path(__file__).parent.parent.parent.parent / "schema" / "v1.1"
        
        self.schema_dir = Path(schema_dir)
        self.schema_v11_dir = Path(schema_v11_dir)
        self._schemas = {}
        self._validators = {}
        self._load_schemas()
    
    def _load_schemas(self):
        """Load all JSON schemas and create resolvers."""
        schema_files = {
            "types": "types.schema.json",
            "common": "adr-common.schema.json",
            "logical": "adr-logical.schema.json",
            "physical": "adr-physical.schema.json",
            "physical_base": "adr-physical-base.schema.json",
            "physical_system": "adr-physical-system.schema.json",
            "physical_component": "adr-physical-component.schema.json",
            "invariant": "invariant.schema.json",
            "project": "project-metadata.schema.json",
            "manifest": "manifest.schema.json",
        }
        
        schema_v11_files = {
            "entity_registry": "entity-registry.schema.json",
            "requirements_snapshot": "requirements-snapshot.schema.json",
            "decision_ledger": "decision-ledger.schema.json",
        }
        
        # Load v1.0 schemas
        for name, filename in schema_files.items():
            schema_path = self.schema_dir / filename
            if schema_path.exists():
                with open(schema_path) as f:
                    self._schemas[name] = json.load(f)
        
        # Load v1.1 schemas
        for name, filename in schema_v11_files.items():
            schema_path = self.schema_v11_dir / filename
            if schema_path.exists():
                with open(schema_path) as f:
                    self._schemas[name] = json.load(f)
        
        resources = []
        for schema in self._schemas.values():
            schema_id = schema.get("$id")
            if schema_id:
                resources.append((schema_id, Resource.from_contents(schema, default_specification=DRAFT7)))

        registry = Registry().with_resources(resources)

        for name, schema in self._schemas.items():
            self._validators[name] = Draft7Validator(schema, registry=registry)
    
    def validate_against_schema(self, data: dict, schema_name: str):
        """Validate data against JSON Schema.
        
        Args:
            data: Parsed YAML data
            schema_name: Schema to validate against (logical, physical, etc.)
            
        Raises:
            ADRSchemaValidationError: If validation fails
        """
        if schema_name not in self._schemas:
            raise ADRParseError(f"Schema '{schema_name}' not found")
        
        schema = self._schemas[schema_name]
        try:
            validator = self._validators.get(schema_name)
            if validator is not None:
                validator.validate(data)
            else:
                jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            raise ADRSchemaValidationError(
                f"Schema validation failed: {e.message}\nPath: {'.'.join(str(p) for p in e.path)}"
            ) from e
    
    def parse_yaml(self, file_path: Union[str, Path]) -> dict:
        """Parse YAML file.
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            Parsed YAML data as dict
            
        Raises:
            ADRParseError: If YAML parsing fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ADRParseError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                raise ADRParseError(f"Expected YAML object, got {type(data)}")
            
            return data
        except yaml.YAMLError as e:
            raise ADRParseError(f"YAML parsing failed: {e}") from e
    
    def parse_logical_adr(self, file_path: Union[str, Path]) -> LogicalADR:
        """Parse and validate logical ADR.
        
        Args:
            file_path: Path to logical ADR YAML file
            
        Returns:
            Validated LogicalADR model
            
        Raises:
            ADRParseError: If parsing fails
            ADRSchemaValidationError: If schema validation fails
            ValidationError: If Pydantic validation fails
        """
        data = self.parse_yaml(file_path)
        
        # Validate against JSON Schema
        self.validate_against_schema(data, "logical")
        
        # Parse into Pydantic model
        try:
            return LogicalADR(**data)
        except ValidationError as e:
            raise ADRParseError(f"Pydantic validation failed: {e}") from e
    
    def parse_physical_adr(self, file_path: Union[str, Path]) -> PhysicalADR:
        """Parse and validate physical ADR.
        
        Args:
            file_path: Path to physical ADR YAML file
            
        Returns:
            Validated PhysicalADR model
            
        Raises:
            ADRParseError: If parsing fails
            ADRSchemaValidationError: If schema validation fails
            ValidationError: If Pydantic validation fails
        """
        data = self.parse_yaml(file_path)
        
        # Validate against JSON Schema
        self.validate_against_schema(data, "physical")
        
        # Parse into Pydantic model
        try:
            return PhysicalADR(**data)
        except ValidationError as e:
            raise ADRParseError(f"Pydantic validation failed: {e}") from e
    
    def parse_physical_system_adr(self, file_path: Union[str, Path]) -> PhysicalSystemADR:
        """Parse and validate physical-system ADR.
        
        Args:
            file_path: Path to physical-system ADR YAML file
            
        Returns:
            Validated PhysicalSystemADR model
            
        Raises:
            ADRParseError: If parsing fails
            ADRSchemaValidationError: If schema validation fails
            ValidationError: If Pydantic validation fails
        """
        data = self.parse_yaml(file_path)
        
        # Validate against JSON Schema
        self.validate_against_schema(data, "physical_system")
        
        # Parse into Pydantic model
        try:
            return PhysicalSystemADR(**data)
        except ValidationError as e:
            raise ADRParseError(f"Pydantic validation failed: {e}") from e
    
    def parse_physical_component_adr(self, file_path: Union[str, Path]) -> PhysicalComponentADR:
        """Parse and validate physical-component ADR.
        
        Args:
            file_path: Path to physical-component ADR YAML file
            
        Returns:
            Validated PhysicalComponentADR model
            
        Raises:
            ADRParseError: If parsing fails
            ADRSchemaValidationError: If schema validation fails
            ValidationError: If Pydantic validation fails
        """
        data = self.parse_yaml(file_path)
        
        # Validate against JSON Schema
        self.validate_against_schema(data, "physical_component")
        
        # Parse into Pydantic model
        try:
            return PhysicalComponentADR(**data)
        except ValidationError as e:
            raise ADRParseError(f"Pydantic validation failed: {e}") from e
    
    def parse_invariant(self, file_path: Union[str, Path]) -> StandaloneInvariant:
        """Parse and validate standalone invariant.
        
        Args:
            file_path: Path to invariant YAML file
            
        Returns:
            Validated StandaloneInvariant model
            
        Raises:
            ADRParseError: If parsing fails
            ADRSchemaValidationError: If schema validation fails
            ValidationError: If Pydantic validation fails
        """
        data = self.parse_yaml(file_path)
        
        # Validate against JSON Schema
        self.validate_against_schema(data, "invariant")
        
        # Parse into Pydantic model
        try:
            return StandaloneInvariant(**data)
        except ValidationError as e:
            raise ADRParseError(f"Pydantic validation failed: {e}") from e
    
    def parse_project_metadata(self, file_path: Union[str, Path]) -> ProjectMetadata:
        """Parse and validate PROJECT.yaml.
        
        Args:
            file_path: Path to PROJECT.yaml file
            
        Returns:
            Validated ProjectMetadata model
            
        Raises:
            ADRParseError: If parsing fails
            ADRSchemaValidationError: If schema validation fails
            ValidationError: If Pydantic validation fails
        """
        data = self.parse_yaml(file_path)
        
        # Validate against JSON Schema
        self.validate_against_schema(data, "project")
        
        # Parse into Pydantic model
        try:
            return ProjectMetadata(**data)
        except ValidationError as e:
            raise ADRParseError(f"Pydantic validation failed: {e}") from e
    
    def parse_manifest(self, file_path: Union[str, Path]) -> Manifest:
        """Parse and validate manifest.yaml.
        
        Args:
            file_path: Path to manifest.yaml file
            
        Returns:
            Validated Manifest model
            
        Raises:
            ADRParseError: If parsing fails
            ADRSchemaValidationError: If schema validation fails
            ValidationError: If Pydantic validation fails
        """
        data = self.parse_yaml(file_path)
        
        # Validate against JSON Schema
        self.validate_against_schema(data, "manifest")
        
        # Parse into Pydantic model
        try:
            return Manifest(**data)
        except ValidationError as e:
            raise ADRParseError(f"Pydantic validation failed: {e}") from e
    
    def parse_adr(self, file_path: Union[str, Path]) -> Union[LogicalADR, PhysicalADR, PhysicalSystemADR, PhysicalComponentADR]:
        """Parse ADR (auto-detect type).
        
        Args:
            file_path: Path to ADR YAML file
            
        Returns:
            Validated LogicalADR, PhysicalADR, PhysicalSystemADR, or PhysicalComponentADR model
            
        Raises:
            ADRParseError: If parsing fails or type unknown
        """
        data = self.parse_yaml(file_path)
        
        adr_type = data.get('adr_type')
        
        if adr_type == 'logical':
            return self.parse_logical_adr(file_path)
        elif adr_type == 'physical':
            return self.parse_physical_adr(file_path)
        elif adr_type == 'physical-system':
            return self.parse_physical_system_adr(file_path)
        elif adr_type == 'physical-component':
            return self.parse_physical_component_adr(file_path)
        elif adr_type == 'decision':
            raise ADRParseError("Decision ADRs not yet implemented")
        else:
            raise ADRParseError(f"Unknown adr_type: {adr_type}")
    
    def parse_entity_registry(self, file_path: Union[str, Path]) -> EntityRegistry:
        """Parse and validate entity registry.
        
        Args:
            file_path: Path to entity registry YAML file
            
        Returns:
            Validated EntityRegistry model
            
        Raises:
            ADRParseError: If parsing fails
            ADRSchemaValidationError: If schema validation fails
            ValidationError: If Pydantic validation fails
        """
        data = self.parse_yaml(file_path)
        self.validate_against_schema(data, "entity_registry")
        
        try:
            return EntityRegistry(**data)
        except ValidationError as e:
            raise ADRParseError(f"Pydantic validation failed: {e}")
    
    def parse_requirements_snapshot(self, file_path: Union[str, Path]) -> RequirementsSnapshot:
        """Parse and validate requirements snapshot.
        
        Args:
            file_path: Path to requirements snapshot YAML file
            
        Returns:
            Validated RequirementsSnapshot model
            
        Raises:
            ADRParseError: If parsing fails
            ADRSchemaValidationError: If schema validation fails
            ValidationError: If Pydantic validation fails
        """
        data = self.parse_yaml(file_path)
        self.validate_against_schema(data, "requirements_snapshot")
        
        try:
            return RequirementsSnapshot(**data)
        except ValidationError as e:
            raise ADRParseError(f"Pydantic validation failed: {e}")
    
    def parse_decision_ledger(self, file_path: Union[str, Path]) -> DecisionLedger:
        """Parse and validate decision ledger.
        
        Args:
            file_path: Path to decision ledger YAML file
            
        Returns:
            Validated DecisionLedger model
            
        Raises:
            ADRParseError: If parsing fails
            ADRSchemaValidationError: If schema validation fails
            ValidationError: If Pydantic validation fails
        """
        data = self.parse_yaml(file_path)
        self.validate_against_schema(data, "decision_ledger")
        
        try:
            return DecisionLedger(**data)
        except ValidationError as e:
            raise ADRParseError(f"Pydantic validation failed: {e}")
