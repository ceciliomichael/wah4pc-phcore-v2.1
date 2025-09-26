"""FHIR resource validation utilities."""

import json
import logging
import re
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
    
    def _validate_fhir_data_types(self, resource: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate FHIR data types for ANY resource type."""
        issues = []
        
        def validate_boolean_field(obj: Any, field_path: str, field_name: str) -> None:
            """Validate boolean fields recursively."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{field_path}.{key}" if field_path else key
                    
                    # Check if this is a boolean field (common FHIR boolean fields)
                    boolean_fields = ['active', 'deceased', 'preferred', 'multipleBirth', 'experimental', 'immutable']
                    if any(bool_field in key.lower() for bool_field in boolean_fields):
                        if value is not None and not isinstance(value, bool):
                            issues.append(ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                code="invalid-boolean-type",
                                details=f"Field '{key}' must be boolean (true/false), got: {type(value).__name__}",
                                location=current_path
                            ))
                    
                    # Recursively validate nested objects
                    validate_boolean_field(value, current_path, key)
                    
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{field_path}[{i}]" if field_path else f"[{i}]"
                    validate_boolean_field(item, current_path, field_name)
        
        def validate_date_fields(obj: Any, field_path: str) -> None:
            """Validate date fields recursively."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{field_path}.{key}" if field_path else key
                    
                    # Check if this is a date field
                    if 'date' in key.lower() and isinstance(value, str):
                        if not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                            issues.append(ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                code="invalid-date-format",
                                details=f"Date field '{key}' must be in YYYY-MM-DD format, got: {value}",
                                location=current_path
                            ))
                    
                    # Recursively validate nested objects
                    validate_date_fields(value, current_path)
                    
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{field_path}[{i}]" if field_path else f"[{i}]"
                    validate_date_fields(item, current_path)
        
        def validate_coding_fields(obj: Any, field_path: str) -> None:
            """Validate coding and CodeableConcept fields."""
            if isinstance(obj, dict):
                # If this is a coding object
                if 'system' in obj and 'code' in obj:
                    if not isinstance(obj.get('system'), str) or not obj.get('system'):
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="invalid-coding-system",
                            details="Coding.system must be a non-empty URI string",
                            location=f"{field_path}.system" if field_path else "system"
                        ))
                    
                    if not isinstance(obj.get('code'), str) or not obj.get('code'):
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="invalid-coding-code",
                            details="Coding.code must be a non-empty string",
                            location=f"{field_path}.code" if field_path else "code"
                        ))
                
                # Recursively validate nested objects
                for key, value in obj.items():
                    current_path = f"{field_path}.{key}" if field_path else key
                    validate_coding_fields(value, current_path)
                    
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{field_path}[{i}]" if field_path else f"[{i}]"
                    validate_coding_fields(item, current_path)
        
        # Run all generic validations
        validate_boolean_field(resource, "", "")
        validate_date_fields(resource, "")
        validate_coding_fields(resource, "")
        
        return issues
    
    def _validate_required_fields(self, resource: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate required fields and strict FHIR constraints.
        
        Args:
            resource: FHIR resource to validate
            
        Returns:
            List of validation issues
        """
        issues = []
        resource_type = resource.get('resourceType')
        
        if not resource_type:
            return issues
        
        # The FHIR schema validation now handles most constraints
        # Keep only validations that the schema doesn't cover well
        
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
            else:
                # Validate Encounter status values strictly
                enc_status = resource.get('status')
                valid_enc_status = ['planned', 'arrived', 'triaged', 'in-progress', 'onleave', 'finished', 'cancelled', 'entered-in-error', 'unknown']
                if enc_status not in valid_enc_status:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="invalid-encounter-status",
                        details=f"Invalid Encounter status '{enc_status}'. Must be one of: {', '.join(valid_enc_status)}",
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
            else:
                # Validate Observation status values
                obs_status = resource.get('status')
                valid_obs_status = [
                    'registered', 'preliminary', 'final', 'amended', 
                    'corrected', 'cancelled', 'entered-in-error', 'unknown'
                ]
                if obs_status not in valid_obs_status:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="invalid-observation-status",
                        details=f"Invalid Observation status '{obs_status}'. Must be one of: {', '.join(valid_obs_status)}",
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
            
            # Create a validator that will collect ALL errors
            validator = Draft7Validator(validator_schema, resolver=resolver)
            
            # Collect all validation errors
            schema_errors = list(validator.iter_errors(resource))
            
            for error in schema_errors:
                # Determine severity based on the type of validation error
                severity = ValidationSeverity.ERROR
                code = "schema-validation-error"
                
                # Critical data type and value constraints should be ERRORS
                error_message = error.message.lower()
                if any(keyword in error_message for keyword in [
                    'is not one of', 'is not valid', 'does not match', 
                    'is not of type', 'invalid', 'required', 'is a required property'
                ]):
                    severity = ValidationSeverity.ERROR
                    code = "fhir-schema-error"
                
                location = ".".join(str(x) for x in error.path) if error.path else error.schema_path[-1] if error.schema_path else None
                
                issues.append(ValidationIssue(
                    severity=severity,
                    code=code,
                    details=f"FHIR schema violation: {error.message}",
                    location=location,
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
        validate_value_sets: bool = True,
        use_ph_core: bool = True,
        strict_ph_core: bool = True
    ) -> ValidationResult:
        """Validate a FHIR resource.
        
        Args:
            resource: FHIR resource to validate
            profile_url: Optional profile URL for additional validation
            validate_code_systems: Whether to validate coding systems
            validate_value_sets: Whether to validate value sets
            use_ph_core: Whether to use PH-Core validation
            strict_ph_core: Whether to enforce strict PH-Core compliance
            
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
            
            # Validate against JSON schema (uses FHIR base schemas)
            schema_issues = self._validate_json_schema(resource)
            all_issues.extend(schema_issues)
            
            # FHIR schema validation above now handles data types comprehensively
            
            # Validate required fields and specific constraints
            required_field_issues = self._validate_required_fields(resource)
            all_issues.extend(required_field_issues)
            
            # Validate coding systems if requested
            if validate_code_systems:
                coding_issues = self._validate_coding_systems(resource)
                all_issues.extend(coding_issues)
            
            # PH-Core validation if requested
            if use_ph_core:
                try:
                    # Import here to avoid circular imports
                    from src.utils.ph_core_validator import ph_core_validator
                    
                    ph_core_result = ph_core_validator.validate_ph_core_resource(
                        resource, 
                        strict_mode=strict_ph_core
                    )
                    
                    # Merge PH-Core validation issues
                    if ph_core_result.issues:
                        all_issues.extend(ph_core_result.issues)
                    
                    # If PH-Core validation failed in strict mode, override result
                    if strict_ph_core and not ph_core_result.valid:
                        # Check if we have base FHIR errors vs PH-Core specific errors
                        base_fhir_errors = [i for i in all_issues if i.severity in [ValidationSeverity.FATAL, ValidationSeverity.ERROR] and not any(ph_keyword in i.code.lower() for ph_keyword in ['ph-core', 'indigenous', 'philhealth'])]
                        ph_core_errors = [i for i in all_issues if i.severity in [ValidationSeverity.FATAL, ValidationSeverity.ERROR] and any(ph_keyword in i.code.lower() for ph_keyword in ['ph-core', 'indigenous', 'philhealth'])]
                        
                        if base_fhir_errors and ph_core_errors:
                            message = f"Validation failed with {len(base_fhir_errors)} FHIR error(s) and {len(ph_core_errors)} PH-Core error(s)"
                        elif base_fhir_errors:
                            message = f"FHIR validation failed with {len(base_fhir_errors)} error(s)"
                        else:
                            message = f"PH-Core validation failed with {len(ph_core_errors)} error(s)"
                        
                        return ValidationResult(
                            status=ValidationStatus.FAILED,
                            message=message,
                            issues=all_issues,
                            resource_type=resource_type,
                            valid=False
                        )
                        
                except ImportError as e:
                    logger.warning(f"PH-Core validator not available: {e}")
                    all_issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="ph-core-validator-unavailable",
                        details="PH-Core validator could not be loaded"
                    ))
                except Exception as e:
                    logger.error(f"Error during PH-Core validation: {e}")
                    all_issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="ph-core-validation-error",
                        details=f"PH-Core validation failed: {str(e)}"
                    ))
            
            # Determine overall validation status
            fatal_issues = [i for i in all_issues if i.severity == ValidationSeverity.FATAL]
            error_issues = [i for i in all_issues if i.severity == ValidationSeverity.ERROR]
            warning_issues = [i for i in all_issues if i.severity == ValidationSeverity.WARNING]
            
            # Count FHIR vs PH-Core errors for better messaging
            fhir_errors = [i for i in error_issues if not any(ph_keyword in i.code.lower() for ph_keyword in ['ph-core', 'indigenous', 'philhealth'])]
            ph_core_errors = [i for i in error_issues if any(ph_keyword in i.code.lower() for ph_keyword in ['ph-core', 'indigenous', 'philhealth'])]
            
            if fatal_issues:
                status = ValidationStatus.FAILED
                message = f"Validation failed with {len(fatal_issues)} fatal error(s)"
                valid = False
            elif error_issues:
                status = ValidationStatus.FAILED
                if fhir_errors and ph_core_errors:
                    message = f"Validation failed with {len(fhir_errors)} FHIR error(s) and {len(ph_core_errors)} PH-Core error(s)"
                elif fhir_errors:
                    message = f"FHIR validation failed with {len(fhir_errors)} error(s)"
                elif ph_core_errors:
                    message = f"PH-Core validation failed with {len(ph_core_errors)} error(s)"
                else:
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
