"""Pydantic models for Physical-Component ADRs - executable specifications."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import ADRFrontmatter, ADRType, Alternative, Gap
from .physical_system_adr import (
    TechnologyChoice,
    DeploymentModel,
    OperationalRequirements,
    ConversationMetadata,
)


class GenerationContext(BaseModel):
    """Context for AI code generation (prompt template)."""
    purpose: str = Field(..., description="Single sentence: what this component does")
    key_responsibilities: List[str] = Field(..., min_length=1)
    constraints: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)


class Interface(BaseModel):
    """Component interface specification."""
    id: str = Field(..., pattern=r"^IFACE-\d{4}$")
    type: str = Field(..., pattern=r"^(REST|gRPC|GraphQL|message|event|stream|batch|CLI|library_api)$")
    specification: str = Field(..., description="Complete interface spec (OpenAPI, proto, etc.)")
    contract_reference: Optional[str] = None
    contract_tests: Optional[str] = None


class ImplementationIdentifiers(BaseModel):
    """Identifiers for code generation and EDR matching."""
    module_path: str = Field(..., description="Code location (REQUIRED for AI generation)")
    service_name: Optional[str] = None
    repository: Optional[str] = None
    entry_point: Optional[str] = None
    test_path: Optional[str] = None
    deployment_name: Optional[str] = None


class Algorithm(BaseModel):
    """Algorithm specification for implementation."""
    name: str
    specification: str = Field(..., description="Complete algorithm specification")
    rationale: Optional[str] = None
    complexity: Optional[str] = None
    edge_cases: List[str] = Field(default_factory=list)


class ErrorType(BaseModel):
    """Error type specification."""
    type: str
    http_status: int
    response_format: str
    retry_strategy: Optional[str] = None
    logging_level: Optional[str] = None


class CircuitBreaker(BaseModel):
    """Circuit breaker configuration."""
    enabled: bool
    threshold: Optional[int] = None
    timeout: Optional[str] = None


class ErrorHandling(BaseModel):
    """Complete error handling specification."""
    strategy: str
    error_types: List[ErrorType] = Field(default_factory=list)
    circuit_breaker: Optional[CircuitBreaker] = None


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str
    structured: bool
    correlation_id: Optional[bool] = None
    sensitive_data_handling: Optional[str] = None


class Metric(BaseModel):
    """Metric specification."""
    name: str
    type: str = Field(..., pattern=r"^(counter|gauge|histogram|summary)$")
    description: Optional[str] = None
    labels: List[str] = Field(default_factory=list)


class Tracing(BaseModel):
    """Tracing configuration."""
    enabled: Optional[bool] = None
    sampler: Optional[str] = None
    propagation: Optional[str] = None


class Observability(BaseModel):
    """Complete observability specification."""
    logging: LoggingConfig
    metrics: List[Metric] = Field(..., min_length=1)
    tracing: Optional[Tracing] = None


class TestingRequirements(BaseModel):
    """Complete testing specification."""
    unit_test_coverage: str = Field(..., description="Minimum coverage (e.g., '>= 80%')")
    integration_tests: Optional[str] = None
    contract_tests: Optional[str] = None
    performance_tests: Optional[str] = None
    test_data: Optional[str] = None


class RateLimit(BaseModel):
    """Rate limit specification."""
    scope: Optional[str] = None
    limit: Optional[str] = None
    window: Optional[str] = None


class RateLimiting(BaseModel):
    """Rate limiting configuration."""
    strategy: Optional[str] = None
    limits: List[RateLimit] = Field(default_factory=list)


class SecurityRequirements(BaseModel):
    """Security requirements for implementation."""
    authentication: Optional[str] = None
    authorization: Optional[str] = None
    data_encryption: Optional[str] = None
    input_validation: Optional[str] = None
    rate_limiting: Optional[RateLimiting] = None


class LatencyRequirements(BaseModel):
    """Latency requirements."""
    p50: Optional[str] = None
    p95: Optional[str] = None
    p99: Optional[str] = None


class ResourceLimits(BaseModel):
    """Resource limits."""
    cpu: Optional[str] = None
    memory: Optional[str] = None
    connections: Optional[int] = None


class PerformanceRequirements(BaseModel):
    """Performance requirements and SLOs."""
    latency: Optional[LatencyRequirements] = None
    throughput: Optional[str] = None
    resource_limits: Optional[ResourceLimits] = None


class ImplementationRequirements(BaseModel):
    """Complete implementation requirements for AI generation."""
    algorithms: List[Algorithm] = Field(default_factory=list)
    error_handling: ErrorHandling
    observability: Observability
    testing_requirements: TestingRequirements
    security_requirements: Optional[SecurityRequirements] = None
    performance_requirements: Optional[PerformanceRequirements] = None


class ComponentSpecification(BaseModel):
    """Detailed component specification with implementation details."""
    id: str = Field(..., pattern=r"^COMP-\d{4}$")
    name: str
    type: str = Field(..., pattern=r"^(service|library|database|queue|cache|gateway|proxy|worker|scheduler)$")
    responsibilities: str
    
    generation_context: GenerationContext
    interfaces: List[Interface] = Field(..., min_length=1)
    implementation_identifiers: ImplementationIdentifiers
    implementation_requirements: ImplementationRequirements
    
    dependencies: List[str] = Field(default_factory=list)
    upstream_services: List[str] = Field(default_factory=list)
    downstream_services: List[str] = Field(default_factory=list)
    
    implements_capabilities: List[str] = Field(default_factory=list)
    realizes_entities: List[str] = Field(default_factory=list)


class DataArchitecture(BaseModel):
    """Data architecture specification."""
    entity: str
    storage: str
    schema_definition: Optional[str] = Field(None, alias="schema")
    access_patterns: Optional[str] = None
    indexes: List[str] = Field(default_factory=list)
    migrations: Optional[str] = None
    
    model_config = ConfigDict(populate_by_name=True)


class ImplementationDecision(BaseModel):
    """Implementation-level decision."""
    id: str = Field(..., pattern=r"^IMPL-\d{4}$")
    summary: str
    rationale: str
    implements_invariants: List[str] = Field(default_factory=list)
    alternatives_considered: List[Alternative] = Field(default_factory=list)


class IntegrationPoint(BaseModel):
    """Integration point between systems."""
    id: str = Field(..., pattern=r"^INTEG-\d{4}$")
    systems: List[str] = Field(..., min_length=2)
    protocol: str
    specification: str
    contract_adr: Optional[str] = Field(None, pattern=r"^ADR-(L|P|PS|PC|D)-\d{4}$")


class BreakingChange(BaseModel):
    """Breaking change from superseded ADR."""
    interface: str
    change: str
    impact: str
    mitigation: Optional[str] = None


class InterfaceCompatibility(BaseModel):
    """Interface compatibility for component replacement/migration."""
    supersedes_adr: Optional[str] = Field(None, pattern=r"^ADR-PC-\d{4}$")
    contract_preservation: Optional[bool] = None
    breaking_changes: List[BreakingChange] = Field(default_factory=list)
    migration_strategy: Optional[str] = None


class PhysicalComponentADR(ADRFrontmatter):
    """Physical-Component ADR - executable specification for autonomous code generation."""
    
    adr_type: ADRType = Field(ADRType.PHYSICAL_COMPONENT, frozen=True)
    id: str = Field(..., pattern=r"^ADR-PC-\d{4}$")
    
    implements_system: List[str] = Field(..., min_length=1)
    implements_logical: List[str] = Field(..., min_length=1)
    technologies: List[str] = Field(default_factory=list)
    
    context: str = Field(..., description="Implementation context and technology choices")
    
    technology_stack: List[TechnologyChoice] = Field(..., min_length=1)
    component_specifications: List[ComponentSpecification] = Field(..., min_length=1)
    
    data_architecture: List[DataArchitecture] = Field(default_factory=list)
    implementation_decisions: List[ImplementationDecision] = Field(default_factory=list)
    integration_points: List[IntegrationPoint] = Field(default_factory=list)
    
    deployment_model: Optional[DeploymentModel] = None
    operational_requirements: Optional[OperationalRequirements] = None
    
    interface_compatibility: Optional[InterfaceCompatibility] = None
    conversation_metadata: Optional[ConversationMetadata] = None
    gaps: List[Gap] = Field(default_factory=list)
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "schema_version": "1.0",
                "adr_type": "physical-component",
                "id": "ADR-PC-0001",
                "title": "User Service API Component",
                "status": "accepted",
                "created_date": "2026-03-10",
                "authors": ["erik.gallmann"],
                "domains": ["user-management", "api"],
                "implements_system": ["ADR-PS-0001"],
                "implements_logical": ["ADR-L-0042"],
                "technologies": ["nodejs", "express", "jwt"],
                "context": "REST API component for user management...",
                "technology_stack": [{
                    "category": "framework",
                    "name": "Express",
                    "version": "4.x",
                    "rationale": "Battle-tested REST framework"
                }],
                "component_specifications": [{
                    "id": "COMP-0001",
                    "name": "User API",
                    "type": "service",
                    "responsibilities": "User CRUD operations",
                    "generation_context": {
                        "purpose": "REST API for user management",
                        "key_responsibilities": ["User CRUD", "JWT auth"]
                    },
                    "interfaces": [{
                        "id": "IFACE-0001",
                        "type": "REST",
                        "specification": "OpenAPI 3.0 spec..."
                    }],
                    "implementation_identifiers": {
                        "module_path": "src/api"
                    },
                    "implementation_requirements": {
                        "error_handling": {
                            "strategy": "RFC 7807 Problem Details"
                        },
                        "observability": {
                            "logging": {"level": "info", "structured": True},
                            "metrics": [{"name": "requests_total", "type": "counter"}]
                        },
                        "testing_requirements": {
                            "unit_test_coverage": ">= 80%"
                        }
                    }
                }]
            }]
        }
    )
