"""FHIR resource validation utilities."""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import jsonschema
from jsonschema import validate, ValidationError, Draft7Validator, RefResolver

from src.types.fhir_types import (
    ValidationResult, ValidationIssue, ValidationSeverity, ValidationStatus
)
from src.lib.resource_loader import resource_loader
from src.constants.fhir_constants import FHIR_RESOURCE_TYPES

logger = logging.getLogger(__name__)


class FHIRValidator:
    """FHIR resource validator."""
    
    def __init__(self):
        """Initialize the FHIR validator."""
        self._resource_schemas: Dict[str, Dict[str, Any]] = {}
    
    def _validate_resource_type(self, resource: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate the resource type.
        
        Args:
            resource: FHIR resource to validate
            
        Returns:
            List of validation issues
        """
        issues = []
        
        resource_type = resource.get('resourceType')
        if not resource_type:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.FATAL,
                code="missing-resource-type",
                details="Resource must have a resourceType field",
                location="resourceType"
            ))
            return issues
        
        if not isinstance(resource_type, str):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="invalid-resource-type",
                details="resourceType must be a string",
                location="resourceType"
            ))
            return issues
        
        # Check if resource type is known (make this informational instead of warning)
        if not resource_loader.is_valid_resource_type(resource_type):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFORMATION,
                code="unknown-resource-type",
                details=f"Resource type '{resource_type}' not found in loaded profiles (using fallback validation)",
                location="resourceType"
            ))
        
        return issues
    
    def _validate_required_fields(self, resource: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate required fields based on resource type.
        
        Args:
            resource: FHIR resource to validate
            
        Returns:
            List of validation issues
        """
        issues = []
        resource_type = resource.get('resourceType')
        
        if not resource_type:
            return issues
        
        # FHIR R4 specific required field validation
        if resource_type == 'Encounter':
            # Encounter must have status and class
            if not resource.get('status'):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="missing-required-field",
                    details="Encounter must have a status field",
                    location="status"
                ))
            elif resource.get('status') not in ['planned', 'arrived', 'triaged', 'in-progress', 'onleave', 'finished', 'cancelled', 'entered-in-error', 'unknown']:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="invalid-status-value",
                    details=f"Invalid Encounter status: {resource.get('status')}",
                    location="status"
                ))
            
            if not resource.get('class'):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="missing-required-field",
                    details="Encounter must have a class field",
                    location="class"
                ))
        
        elif resource_type == 'Patient':
            # Patient validation
            if not resource.get('id') and not resource.get('identifier'):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="missing-identifier",
                    details="Patient should have either an id or identifier",
                    location="id or identifier"
                ))
        
        elif resource_type == 'Observation':
            # Observation must have status and code
            if not resource.get('status'):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="missing-required-field",
                    details="Observation must have a status field",
                    location="status"
                ))
            
            if not resource.get('code'):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="missing-required-field",
                    details="Observation must have a code field",
                    location="code"
                ))
        
        return issues
    
    def _validate_json_schema(self, resource: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate resource against JSON schema if available."""
        issues = []
        schema = resource_loader.schemas
        resource_type = resource.get("resourceType")

        if not schema or 'definitions' not in schema:
            return issues  # Cannot perform schema validation

        # Try to find a specific schema definition for the resource type
        resource_schema = None
        if resource_type and resource_type in schema.get('definitions', {}):
            resource_schema = schema['definitions'][resource_type]

        try:
            # Use the specific resource schema if found, otherwise fallback to the full schema
            validator_schema = resource_schema or schema
            # A resolver is needed to handle internal references ($ref) within the schema
            resolver = RefResolver.from_schema(schema)
            validate(instance=resource, schema=validator_schema, resolver=resolver)
        except ValidationError as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="schema-validation-warning",
                details=f"Schema validation issue: {e.message}",
                location=".".join(str(x) for x in e.path) if e.path else None,
            ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="schema-validator-error",
                details=f"An unexpected error occurred during schema validation: {str(e)}",
            ))

        return issues
    
    def _validate_coding_systems(self, resource: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate coding systems and value sets.
        
        Args:
            resource: FHIR resource to validate
            
        Returns:
            List of validation issues
        """
        issues = []
        
        def check_coding(obj: Any, path: str = "") -> None:
            """Recursively check for coding elements."""
            if isinstance(obj, dict):
                # Check if this is a Coding element
                if 'system' in obj and 'code' in obj:
                    system = obj.get('system')
                    code = obj.get('code')
                    
                    if not isinstance(system, str) or not system:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            code="invalid-coding-system",
                            details="Coding system must be a valid URI",
                            location=f"{path}.system" if path else "system"
                        ))
                    
                    if not isinstance(code, str) or not code:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            code="invalid-coding-code",
                            details="Coding code must be a non-empty string",
                            location=f"{path}.code" if path else "code"
                        ))
                
                # Recursively check nested objects
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    check_coding(value, new_path)
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}[{i}]" if path else f"[{i}]"
                    check_coding(item, new_path)
        
        check_coding(resource)
        return issues
    
    def validate_resource(
        self, 
        resource: Dict[str, Any], 
        profile_url: Optional[str] = None,
        validate_code_systems: bool = True,
        validate_value_sets: bool = True
    ) -> ValidationResult:
        """Validate a FHIR resource.
        
        Args:
            resource: FHIR resource to validate
            profile_url: Optional profile URL for additional validation
            validate_code_systems: Whether to validate coding systems
            validate_value_sets: Whether to validate value sets
            
        Returns:
            ValidationResult with validation outcome
        """
        start_time = datetime.now()
        all_issues = []
        
        try:
            # Basic structure validation
            if not isinstance(resource, dict):
                return ValidationResult(
                    status=ValidationStatus.FAILED,
                    message="Resource must be a JSON object",
                    issues=[ValidationIssue(
                        severity=ValidationSeverity.FATAL,
                        code="invalid-format",
                        details="Resource must be a JSON object"
                    )],
                    resource_type=None,
                    valid=False
                )
            
            # Validate resource type
            resource_type_issues = self._validate_resource_type(resource)
            all_issues.extend(resource_type_issues)
            
            resource_type = resource.get('resourceType')
            
            # If we have fatal issues, return early
            fatal_issues = [i for i in all_issues if i.severity == ValidationSeverity.FATAL]
            if fatal_issues:
                return ValidationResult(
                    status=ValidationStatus.FAILED,
                    message="Fatal validation errors found",
                    issues=all_issues,
                    resource_type=resource_type,
                    valid=False
                )
            
            # Validate against JSON schema
            schema_issues = self._validate_json_schema(resource)
            all_issues.extend(schema_issues)
            
            # Validate required fields
            required_field_issues = self._validate_required_fields(resource)
            all_issues.extend(required_field_issues)
            
            # Validate coding systems if requested
            if validate_code_systems:
                coding_issues = self._validate_coding_systems(resource)
                all_issues.extend(coding_issues)
            
            # Determine overall validation status
            error_issues = [i for i in all_issues if i.severity in [ValidationSeverity.FATAL, ValidationSeverity.ERROR]]
            warning_issues = [i for i in all_issues if i.severity == ValidationSeverity.WARNING]
            
            if error_issues:
                status = ValidationStatus.FAILED
                message = f"Validation failed with {len(error_issues)} error(s)"
                valid = False
            elif warning_issues:
                status = ValidationStatus.WARNING
                message = f"Validation passed with {len(warning_issues)} warning(s)"
                valid = True
            else:
                status = ValidationStatus.SUCCESS
                message = "Validation successful"
                valid = True
            
            return ValidationResult(
                status=status,
                message=message,
                issues=all_issues,
                resource_type=resource_type,
                valid=valid
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            return ValidationResult(
                status=ValidationStatus.FAILED,
                message=f"Validation error: {str(e)}",
                issues=[ValidationIssue(
                    severity=ValidationSeverity.FATAL,
                    code="validation-exception",
                    details=str(e)
                )],
                resource_type=resource.get('resourceType') if isinstance(resource, dict) else None,
                valid=False
            )


# Global validator instance
fhir_validator = FHIRValidator()
