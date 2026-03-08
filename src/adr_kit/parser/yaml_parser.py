"""YAML parser with JSON Schema validation for ADR artifacts."""

import json
from pathlib import Path
from typing import Union

import jsonschema
from jsonschema import RefResolver
import yaml
from pydantic import ValidationError

from ..models import (
    LogicalADR,
    Manifest,
    PhysicalADR,
    ProjectMetadata,
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
    
    def __init__(self, schema_dir: Path = None):
        """Initialize parser with schema directory.
        
        Args:
            schema_dir: Path to schema directory (defaults to package schema/v1.0)
        """
        if schema_dir is None:
            schema_dir = Path(__file__).parent.parent.parent.parent / "schema" / "v1.0"
        
        self.schema_dir = Path(schema_dir)
        self._schemas = {}
        self._resolvers = {}
        self._load_schemas()
    
    def _load_schemas(self):
        """Load all JSON schemas and create resolvers."""
        schema_files = {
            "types": "types.schema.json",
            "common": "adr-common.schema.json",
            "logical": "adr-logical.schema.json",
            "physical": "adr-physical.schema.json",
            "invariant": "invariant.schema.json",
            "project": "project-metadata.schema.json",
            "manifest": "manifest.schema.json",
        }
        
        # Load all schemas
        for name, filename in schema_files.items():
            schema_path = self.schema_dir / filename
            if schema_path.exists():
                with open(schema_path) as f:
                    self._schemas[name] = json.load(f)
        
        # Create schema store for resolver
        schema_store = {}
        for name, schema in self._schemas.items():
            if "$id" in schema:
                schema_store[schema["$id"]] = schema
        
        # Create resolvers for each schema
        for name, schema in self._schemas.items():
            if "$id" in schema:
                resolver = RefResolver.from_schema(schema, store=schema_store)
                self._resolvers[name] = resolver
    
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
        resolver = self._resolvers.get(schema_name)
        
        try:
            if resolver:
                jsonschema.validate(data, schema, resolver=resolver)
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
    
    def parse_adr(self, file_path: Union[str, Path]) -> Union[LogicalADR, PhysicalADR]:
        """Parse ADR (auto-detect type).
        
        Args:
            file_path: Path to ADR YAML file
            
        Returns:
            Validated LogicalADR or PhysicalADR model
            
        Raises:
            ADRParseError: If parsing fails or type unknown
        """
        data = self.parse_yaml(file_path)
        
        adr_type = data.get('adr_type')
        
        if adr_type == 'logical':
            return self.parse_logical_adr(file_path)
        elif adr_type == 'physical':
            return self.parse_physical_adr(file_path)
        elif adr_type == 'decision':
            raise ADRParseError("Decision ADRs not yet implemented")
        else:
            raise ADRParseError(f"Unknown adr_type: {adr_type}")
