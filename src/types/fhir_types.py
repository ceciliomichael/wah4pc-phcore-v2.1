"""FHIR validation server type definitions."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class ValidationSeverity(str, Enum):
    """Validation issue severity levels."""
    FATAL = "fatal"
    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"


class ValidationStatus(str, Enum):
    """Validation result status."""
    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"


class ValidationIssue(BaseModel):
    """Individual validation issue."""
    severity: ValidationSeverity
    code: str
    details: str
    location: Optional[str] = None
    expression: Optional[str] = None


class ValidationResult(BaseModel):
    """FHIR resource validation result."""
    status: ValidationStatus
    message: str
    issues: List[ValidationIssue] = Field(default_factory=list)
    resource_type: Optional[str] = None
    valid: bool


class FHIRResource(BaseModel):
    """Generic FHIR resource model."""
    resourceType: str
    id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    implicitRules: Optional[str] = None
    language: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow additional fields for FHIR resources


class ValidationRequest(BaseModel):
    """FHIR validation request model."""
    resource: Dict[str, Any]
    profile: Optional[str] = None
    validate_code_systems: bool = Field(default=True)
    validate_value_sets: bool = Field(default=True)
    use_ph_core: bool = Field(default=True)
    strict_ph_core: bool = Field(default=True)


class ValidationResponse(BaseModel):
    """FHIR validation response model."""
    validation_result: ValidationResult
    processed_at: str
    processing_time_ms: int


class ServerInfo(BaseModel):
    """Server information model."""
    name: str
    version: str
    description: str
    fhir_version: str
    supported_formats: List[str]
    supported_operations: List[str]


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    uptime_seconds: int
