"""Pydantic models for PROJECT.yaml metadata."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectInfo(BaseModel):
    """Project identification."""

    name: str = Field(..., pattern=r"^[a-z0-9-]+$")
    description: str
    type: str = Field(..., pattern=r"^(service|library|platform|system|tool)$")


class OnCallRotation(BaseModel):
    """On-call rotation configuration."""

    schedule: str
    rotation: str = Field(..., pattern=r"^(daily|weekly|biweekly|monthly)$")
    members: List[str]
    backup: Optional[str] = None


class ProjectOwnership(BaseModel):
    """Project ownership metadata."""

    team: str
    tech_lead: Optional[str] = None
    on_call: Optional[OnCallRotation] = None


class Repository(BaseModel):
    """Repository information."""

    url: str
    primary_branch: str


class ProjectImplementationIdentifiers(BaseModel):
    """Implementation identifiers for correction agents."""

    service_name: Optional[str] = None
    namespace: Optional[str] = None
    deployment_name: Optional[str] = None
    package_name: Optional[str] = None
    module_path: Optional[str] = None


class AutomationPermissions(BaseModel):
    """Automation permissions for correction agents."""

    auto_merge_allowed: bool = False
    auto_deploy_staging: bool = False
    auto_deploy_production: bool = False
    requires_human_review: bool = True
    comfort_level: str = Field("conservative", pattern=r"^(conservative|moderate|aggressive)$")


class DevelopmentMethodology(BaseModel):
    """Development methodology and quality practices (project authority)."""

    approach: str = Field(..., pattern=r"^(test-driven-development|behavior-driven-development|test-after|exploratory)$")
    testing_framework: Optional[str] = None
    coverage_target: Optional[int] = Field(None, ge=0, le=100)
    quality_gates: Optional[List[str]] = None
    tdd_cycle: Optional[str] = Field(None, pattern=r"^(red-green-refactor|test-first|test-after)$")
    rationale: Optional[str] = None
    authority: Optional[str] = None


class SCMIntegration(BaseModel):
    """Source control management integration."""

    type: str = Field(..., pattern=r"^(github|gitlab|bitbucket)$")
    app_installation_id: Optional[str] = None
    required_approvers: List[str] = Field(default_factory=list)


class CIIntegration(BaseModel):
    """CI/CD integration."""

    type: str = Field(..., pattern=r"^(github_actions|jenkins|circleci|gitlab_ci)$")
    workflow_path: Optional[str] = None
    required_checks: List[str] = Field(default_factory=list)


class MetricsConfig(BaseModel):
    """Metrics configuration."""

    provider: str = Field(..., pattern=r"^(datadog|prometheus|cloudwatch|newrelic)$")
    dashboards: List[str] = Field(default_factory=list)


class LogsConfig(BaseModel):
    """Logs configuration."""

    provider: str = Field(..., pattern=r"^(cloudwatch|datadog|splunk|elasticsearch)$")
    log_groups: List[str] = Field(default_factory=list)


class AlertsConfig(BaseModel):
    """Alerts configuration."""

    provider: str = Field(..., pattern=r"^(pagerduty|opsgenie|victorops)$")
    escalation_policy: Optional[str] = None


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    metrics: Optional[MetricsConfig] = None
    logs: Optional[LogsConfig] = None
    alerts: Optional[AlertsConfig] = None


class Integrations(BaseModel):
    """External integrations."""

    scm: Optional[SCMIntegration] = None
    ci: Optional[CIIntegration] = None
    observability: Optional[ObservabilityConfig] = None


class RequiredControls(BaseModel):
    """Required security controls."""

    encryption_at_rest: bool = False
    encryption_in_transit: bool = False
    mfa_required: bool = False
    audit_logging: bool = False


class ComplianceRequirements(BaseModel):
    """Compliance and security requirements."""

    security_level: Optional[str] = Field(None, pattern=r"^(high|medium|low)$")
    data_classification: Optional[str] = Field(None, pattern=r"^(public|internal|confidential|restricted)$")
    regulatory_requirements: List[str] = Field(default_factory=list)
    license: Optional[str] = None
    required_controls: Optional[RequiredControls] = None


class ArchitectureDocumentation(BaseModel):
    """Architecture documentation location."""

    adr_directory: str = "adrs/"
    manifest_path: str = "adrs/manifest.yaml"
    architecture_namespace: Optional[str] = None


class ProjectMetadata(BaseModel):
    """PROJECT.yaml - project-level metadata (one per repository)."""

    schema_version: str = Field("1.0", pattern=r"^1\.0$")
    type: str = Field("project_metadata", pattern=r"^project_metadata$")

    project: ProjectInfo
    ownership: ProjectOwnership
    repository: Repository
    architecture_documentation: ArchitectureDocumentation

    implementation_identifiers: Optional[ProjectImplementationIdentifiers] = None
    automation: Optional[AutomationPermissions] = None
    development_methodology: Optional[DevelopmentMethodology] = None
    integrations: Optional[Integrations] = None
    compliance: Optional[ComplianceRequirements] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "schema_version": "1.0",
                "type": "project_metadata",
                "project": {
                    "name": "payment-service",
                    "description": "Payment processing microservice",
                    "type": "service"
                },
                "ownership": {
                    "team": "team-payments",
                    "tech_lead": "@alice"
                },
                "repository": {
                    "url": "github.com/org/payment-service",
                    "primary_branch": "main"
                },
                "architecture_documentation": {
                    "adr_directory": "adrs/",
                    "manifest_path": "adrs/manifest.yaml"
                }
            }]
        }
    )
