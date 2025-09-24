"""FHIR resource loader for base definitions and schemas."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from functools import lru_cache

from src.constants.fhir_constants import (
    RESOURCES_PATH, FHIR_SCHEMA_FILE, PROFILES_RESOURCES_FILE,
    PROFILES_TYPES_FILE, VALUESETS_FILE, EXTENSION_DEFINITIONS_FILE
)

logger = logging.getLogger(__name__)


class FHIRResourceLoader:
    """Loads and manages FHIR base definitions and schemas."""
    
    def __init__(self):
        """Initialize the resource loader."""
        self._schemas: Optional[Dict[str, Any]] = None
        self._profiles: Optional[Dict[str, Any]] = None
        self._value_sets: Optional[Dict[str, Any]] = None
        self._extensions: Optional[Dict[str, Any]] = None
        self._loaded = False
    
    def _load_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load a JSON file safely.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Loaded JSON data or None if file doesn't exist or is invalid
        """
        try:
            if not file_path.exists():
                logger.warning(f"FHIR resource file not found: {file_path}")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            return None
    
    def _load_resources(self) -> None:
        """Load all FHIR base resources."""
        logger.info("Loading FHIR base resources...")
        
        # Load FHIR schema
        self._schemas = self._load_json_file(FHIR_SCHEMA_FILE)
        
        # Load profiles
        profiles_resources = self._load_json_file(PROFILES_RESOURCES_FILE)
        profiles_types = self._load_json_file(PROFILES_TYPES_FILE)
        
        # Combine profiles
        self._profiles = {}
        if profiles_resources:
            self._profiles.update(profiles_resources)
        if profiles_types:
            self._profiles.update(profiles_types)
        
        # Load value sets
        self._value_sets = self._load_json_file(VALUESETS_FILE)
        
        # Load extensions
        self._extensions = self._load_json_file(EXTENSION_DEFINITIONS_FILE)
        
        self._loaded = True
        logger.info("FHIR base resources loaded successfully")
    
    def ensure_loaded(self) -> None:
        """Ensure resources are loaded."""
        if not self._loaded:
            self._load_resources()
    
    @property
    def schemas(self) -> Dict[str, Any]:
        """Get FHIR schemas.
        
        Returns:
            FHIR schema definitions
        """
        self.ensure_loaded()
        return self._schemas or {}
    
    @property
    def profiles(self) -> Dict[str, Any]:
        """Get FHIR profiles.
        
        Returns:
            FHIR profile definitions
        """
        self.ensure_loaded()
        return self._profiles or {}
    
    @property
    def value_sets(self) -> Dict[str, Any]:
        """Get FHIR value sets.
        
        Returns:
            FHIR value set definitions
        """
        self.ensure_loaded()
        return self._value_sets or {}
    
    @property
    def extensions(self) -> Dict[str, Any]:
        """Get FHIR extensions.
        
        Returns:
            FHIR extension definitions
        """
        self.ensure_loaded()
        return self._extensions or {}
    
    def get_resource_profile(self, resource_type: str) -> Optional[Dict[str, Any]]:
        """Get profile definition for a specific resource type.
        
        Args:
            resource_type: FHIR resource type (e.g., 'Patient', 'Observation')
            
        Returns:
            Profile definition or None if not found
        """
        self.ensure_loaded()
        profiles = self.profiles
        
        # Look for the resource profile
        if isinstance(profiles, dict) and 'entry' in profiles:
            for entry in profiles.get('entry', []):
                resource = entry.get('resource', {})
                if (resource.get('type') == resource_type and 
                    resource.get('kind') == 'resource'):
                    return resource
        
        return None
    
    def get_value_set(self, value_set_url: str) -> Optional[Dict[str, Any]]:
        """Get value set by URL.
        
        Args:
            value_set_url: Value set URL
            
        Returns:
            Value set definition or None if not found
        """
        self.ensure_loaded()
        value_sets = self.value_sets
        
        if isinstance(value_sets, dict) and 'entry' in value_sets:
            for entry in value_sets.get('entry', []):
                resource = entry.get('resource', {})
                if resource.get('url') == value_set_url:
                    return resource
        
        return None
    
    def is_valid_resource_type(self, resource_type: str) -> bool:
        """Check if a resource type is valid.
        
        Args:
            resource_type: Resource type to check
            
        Returns:
            True if valid resource type
        """
        # First check if we can get a profile
        profile = self.get_resource_profile(resource_type)
        if profile is not None:
            return True
        
        # Fallback to known FHIR R4 resource types if profiles not available
        known_resource_types = [
            "Account", "ActivityDefinition", "AdverseEvent", "AllergyIntolerance", "Appointment",
            "AppointmentResponse", "AuditEvent", "Basic", "Binary", "BiologicallyDerivedProduct",
            "BodyStructure", "Bundle", "CapabilityStatement", "CarePlan", "CareTeam", "CatalogEntry",
            "ChargeItem", "ChargeItemDefinition", "Claim", "ClaimResponse", "ClinicalImpression",
            "CodeSystem", "Communication", "CommunicationRequest", "CompartmentDefinition",
            "Composition", "ConceptMap", "Condition", "Consent", "Contract", "Coverage",
            "CoverageEligibilityRequest", "CoverageEligibilityResponse", "DetectedIssue", "Device",
            "DeviceDefinition", "DeviceMetric", "DeviceRequest", "DeviceUseStatement",
            "DiagnosticReport", "DocumentManifest", "DocumentReference", "DomainResource",
            "EffectEvidenceSynthesis", "Encounter", "Endpoint", "EnrollmentRequest", "EnrollmentResponse",
            "EpisodeOfCare", "EventDefinition", "Evidence", "EvidenceVariable", "ExampleScenario",
            "ExplanationOfBenefit", "FamilyMemberHistory", "Flag", "Goal", "GraphDefinition", "Group",
            "GuidanceResponse", "HealthcareService", "ImagingStudy", "Immunization", "ImmunizationEvaluation",
            "ImmunizationRecommendation", "ImplementationGuide", "InsurancePlan", "Invoice", "Library",
            "Linkage", "List", "Location", "Measure", "MeasureReport", "Media", "Medication",
            "MedicationAdministration", "MedicationDispense", "MedicationKnowledge", "MedicationRequest",
            "MedicationStatement", "MedicinalProduct", "MedicinalProductAuthorization",
            "MedicinalProductContraindication", "MedicinalProductIndication", "MedicinalProductIngredient",
            "MedicinalProductInteraction", "MedicinalProductManufactured", "MedicinalProductPackaged",
            "MedicinalProductPharmaceutical", "MedicinalProductUndesirableEffect", "MessageDefinition",
            "MessageHeader", "MolecularSequence", "NamingSystem", "NutritionOrder", "Observation",
            "ObservationDefinition", "OperationDefinition", "OperationOutcome", "Organization",
            "OrganizationAffiliation", "Parameters", "Patient", "PaymentNotice", "PaymentReconciliation",
            "Person", "PlanDefinition", "Practitioner", "PractitionerRole", "Procedure", "Provenance",
            "Questionnaire", "QuestionnaireResponse", "RelatedPerson", "RequestGroup", "ResearchDefinition",
            "ResearchElementDefinition", "ResearchStudy", "ResearchSubject", "Resource", "RiskAssessment",
            "RiskEvidenceSynthesis", "Schedule", "SearchParameter", "ServiceRequest", "Slot", "Specimen",
            "SpecimenDefinition", "StructureDefinition", "StructureMap", "Subscription", "Substance",
            "SubstanceNucleicAcid", "SubstancePolymer", "SubstanceProtein", "SubstanceReferenceInformation",
            "SubstanceSourceMaterial", "SubstanceSpecification", "SupplyDelivery", "SupplyRequest", "Task",
            "TerminologyCapabilities", "TestReport", "TestScript", "ValueSet", "VerificationResult", "VisionPrescription"
        ]
        
        return resource_type in known_resource_types
    
    def get_available_resource_types(self) -> List[str]:
        """Get list of available resource types.
        
        Returns:
            List of available FHIR resource types
        """
        self.ensure_loaded()
        resource_types = []
        profiles = self.profiles
        
        if isinstance(profiles, dict) and 'entry' in profiles:
            for entry in profiles.get('entry', []):
                resource = entry.get('resource', {})
                if (resource.get('kind') == 'resource' and 
                    resource.get('type')):
                    resource_types.append(resource['type'])
        
        return sorted(list(set(resource_types)))


# Global resource loader instance
resource_loader = FHIRResourceLoader()
