"""PH-Core specific FHIR validation utilities."""

import json
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from src.types.fhir_types import (
    ValidationResult, ValidationIssue, ValidationSeverity, ValidationStatus
)
from src.ui.ig_endpoints import ph_core_ig_server

logger = logging.getLogger(__name__)


class PHCoreValidator:
    """PH-Core Implementation Guide specific validator."""
    
    def __init__(self):
        """Initialize the PH-Core validator."""
        self._supported_profiles = self._load_supported_profiles()
    
    def _load_supported_profiles(self) -> Dict[str, str]:
        """Load supported PH-Core profiles mapping."""
        profile_mapping = {
            "Patient": "ph-core-patient",
            "Encounter": "ph-core-encounter", 
            "Organization": "ph-core-organization",
            "Practitioner": "ph-core-practitioner",
            "Observation": "ph-core-observation",
            "Immunization": "ph-core-immunization",
            "Medication": "ph-core-medication",
            "RelatedPerson": "ph-core-relatedperson",
            "Procedure": "ph-core-procedure",
            "Location": "ph-core-location",
            # Resources with PHCore examples but no specific profiles (use base FHIR)
            "Condition": None,  # Uses base FHIR Condition profile
            "AllergyIntolerance": None,  # Uses base FHIR AllergyIntolerance profile
            "Bundle": None  # Uses base FHIR Bundle profile
        }
        
        logger.info(f"Loaded {len(profile_mapping)} PH-Core profile mappings")
        return profile_mapping
    
    def is_ph_core_resource(self, resource_type: str) -> bool:
        """Check if a resource type has a PH-Core profile."""
        return resource_type in self._supported_profiles
    
    def get_profile_url(self, resource_type: str) -> Optional[str]:
        """Get the PH-Core profile URL for a resource type."""
        if resource_type in self._supported_profiles:
            profile_id = self._supported_profiles[resource_type]
            return f"https://wah4pc-validation.echosphere.cfd/StructureDefinition/{profile_id}"
        return None
    
    def _validate_required_extensions(
        self, 
        resource: Dict[str, Any], 
        profile: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate required extensions based on PH-Core profile."""
        issues = []
        
        if not profile or "differential" not in profile:
            return issues
        
        extensions = resource.get("extension", [])
        extension_urls = {ext.get("url") for ext in extensions if isinstance(ext, dict)}
        
        # STRICT VALIDATION: Check for specific PH-Core required extensions
        resource_type = resource.get("resourceType")
        
        if resource_type == "Patient":
            # Indigenous People extension is REQUIRED for PH-Core Patient (min: 1)
            indigenous_people_url = "https://wah4pc-validation.echosphere.cfd/StructureDefinition/indigenous-people"
            if indigenous_people_url not in extension_urls:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="missing-required-ph-core-extension",
                    details=f"PH-Core Patient profile requires 'indigenousPeople' extension: {indigenous_people_url}",
                    location="extension (indigenousPeople)"
                ))
        
        # Check for required extensions in the profile differential
        for element in profile["differential"].get("element", []):
            element_id = element.get("id", "")
            
            # Look for required extension elements (min > 0)
            if ":extension" in element_id and element.get("min", 0) > 0:
                extension_slice_name = element_id.split(":")[-1]
                
                # Find the corresponding extension definition
                for profile_element in profile["differential"].get("element", []):
                    if (profile_element.get("id", "") == element_id and 
                        "type" in profile_element):
                        
                        extension_profiles = []
                        for type_def in profile_element["type"]:
                            if type_def.get("code") == "Extension":
                                extension_profiles.extend(type_def.get("profile", []))
                        
                        # Check if any required extension is missing
                        for ext_profile in extension_profiles:
                            if not any(url and ext_profile == url for url in extension_urls):
                                issues.append(ValidationIssue(
                                    severity=ValidationSeverity.ERROR,
                                    code="missing-required-extension",
                                    details=f"Required PH-Core extension missing: {ext_profile} (slice: {extension_slice_name})",
                                    location=f"extension ({extension_slice_name})"
                                ))
        
        return issues
    
    def _validate_identifier_constraints(
        self,
        resource: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate PH-Core identifier constraints."""
        issues = []
        
        identifiers = resource.get("identifier", [])
        if not isinstance(identifiers, list):
            return issues
        
        # Check for specific PH-Core identifier requirements
        if resource.get("resourceType") == "Patient":
            # Check for PhilHealth ID constraints
            philhealth_identifiers = [
                ident for ident in identifiers
                if isinstance(ident, dict) and 
                "philhealth" in str(ident.get("system", "")).lower()
            ]
            
            for ident in philhealth_identifiers:
                # Validate PhilHealth ID format (should be numeric and proper length)
                value = ident.get("value", "")
                if value and not value.replace("-", "").isdigit():
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="invalid-philhealth-id-format",
                        details=f"PhilHealth ID should be numeric: {value}",
                        location="identifier.value"
                    ))
        
        return issues
    
    def _validate_terminology_bindings(
        self,
        resource: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate terminology bindings for PH-Core resources."""
        issues = []
        
        # Validate marital status binding for Patient resources
        if resource.get("resourceType") == "Patient" and "maritalStatus" in resource:
            marital_status = resource["maritalStatus"]
            if isinstance(marital_status, dict) and "coding" in marital_status:
                for coding in marital_status["coding"]:
                    if isinstance(coding, dict):
                        system = coding.get("system", "")
                        if system and "marital-status" not in system:
                            issues.append(ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                code="invalid-terminology-binding",
                                details=f"Marital status should use FHIR marital-status value set: {system}",
                                location="maritalStatus.coding.system"
                            ))
        
        return issues
    
    def _validate_address_profile(
        self,
        resource: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate PH-Core address profile constraints."""
        issues = []
        
        addresses = resource.get("address", [])
        if not isinstance(addresses, list):
            addresses = [addresses] if addresses else []
        
        for i, address in enumerate(addresses):
            if not isinstance(address, dict):
                continue
            
            # Check for Philippine address requirements
            if address.get("country") and address["country"].upper() != "PH":
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFORMATION,
                    code="non-philippine-address",
                    details=f"Address country is not Philippines: {address['country']}",
                    location=f"address[{i}].country"
                ))
            
            # Validate address structure for Philippine context
            if not address.get("city") and not address.get("district"):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="incomplete-philippine-address",
                    details="Philippine addresses should include city/municipality information",
                    location=f"address[{i}]"
                ))
        
        return issues
    
    def validate_ph_core_resource(
        self,
        resource: Dict[str, Any],
        strict_mode: bool = True
    ) -> ValidationResult:
        """Validate a FHIR resource against PH-Core profiles.
        
        Args:
            resource: FHIR resource to validate
            strict_mode: Whether to enforce strict PH-Core compliance
            
        Returns:
            ValidationResult with PH-Core specific validation
        """
        start_time = datetime.now()
        all_issues = []
        
        try:
            resource_type = resource.get("resourceType")
            if not resource_type:
                return ValidationResult(
                    status=ValidationStatus.FAILED,
                    message="Resource must have a resourceType field",
                    issues=[ValidationIssue(
                        severity=ValidationSeverity.FATAL,
                        code="missing-resource-type",
                        details="Resource must have a resourceType field"
                    )],
                    resource_type=None,
                    valid=False
                )
            
            # Check if this resource type has a PH-Core profile
            if not self.is_ph_core_resource(resource_type):
                if strict_mode:
                    return ValidationResult(
                        status=ValidationStatus.FAILED,
                        message=f"Resource type '{resource_type}' is not supported by PH-Core profiles",
                        issues=[ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="unsupported-resource-type",
                            details=f"PH-Core does not define a profile for '{resource_type}'"
                        )],
                        resource_type=resource_type,
                        valid=False
                    )
                else:
                    # In non-strict mode, just add a warning
                    all_issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFORMATION,
                        code="no-ph-core-profile",
                        details=f"No PH-Core profile available for '{resource_type}', using base FHIR validation only"
                    ))
            
            # Get the PH-Core profile
            profile_id = self._supported_profiles.get(resource_type)
            if profile_id:
                profile = ph_core_ig_server.get_structure_definition(profile_id)
                
                if not profile:
                    all_issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="profile-not-loaded",
                        details=f"PH-Core profile '{profile_id}' not found in loaded IG"
                    ))
                else:
                    # Perform PH-Core specific validations
                    extension_issues = self._validate_required_extensions(resource, profile)
                    all_issues.extend(extension_issues)
                    
                    identifier_issues = self._validate_identifier_constraints(resource, profile)
                    all_issues.extend(identifier_issues)
                    
                    terminology_issues = self._validate_terminology_bindings(resource, profile)
                    all_issues.extend(terminology_issues)
                    
                    address_issues = self._validate_address_profile(resource)
                    all_issues.extend(address_issues)
            elif profile_id is None and self.is_ph_core_resource(resource_type):
                # Resource is supported by PHCore but uses base FHIR profile
                all_issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFORMATION,
                    code="using-base-fhir-profile",
                    details=f"'{resource_type}' is supported by PH-Core but uses base FHIR profile (no PH-Core specific constraints)"
                ))
            
            # Determine overall validation status
            fatal_issues = [i for i in all_issues if i.severity == ValidationSeverity.FATAL]
            error_issues = [i for i in all_issues if i.severity == ValidationSeverity.ERROR]
            warning_issues = [i for i in all_issues if i.severity == ValidationSeverity.WARNING]
            
            if fatal_issues:
                status = ValidationStatus.FAILED
                message = f"PH-Core validation failed with {len(fatal_issues)} fatal error(s)"
                valid = False
            elif error_issues:
                if strict_mode:
                    status = ValidationStatus.FAILED
                    message = f"PH-Core validation failed with {len(error_issues)} error(s) (strict mode)"
                    valid = False
                else:
                    status = ValidationStatus.WARNING
                    message = f"PH-Core validation passed with {len(error_issues)} error(s) (non-strict mode)"
                    valid = True
            elif warning_issues:
                status = ValidationStatus.WARNING
                message = f"PH-Core validation passed with {len(warning_issues)} warning(s)"
                valid = True
            else:
                status = ValidationStatus.SUCCESS
                message = "PH-Core validation successful"
                valid = True
            
            return ValidationResult(
                status=status,
                message=message,
                issues=all_issues,
                resource_type=resource_type,
                valid=valid
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during PH-Core validation: {e}")
            return ValidationResult(
                status=ValidationStatus.FAILED,
                message=f"PH-Core validation error: {str(e)}",
                issues=[ValidationIssue(
                    severity=ValidationSeverity.FATAL,
                    code="ph-core-validation-exception",
                    details=str(e)
                )],
                resource_type=resource.get("resourceType") if isinstance(resource, dict) else None,
                valid=False
            )


# Global PH-Core validator instance
ph_core_validator = PHCoreValidator()
