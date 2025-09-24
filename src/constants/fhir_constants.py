"""FHIR validation server constants."""

from pathlib import Path

# Server configuration
SERVER_NAME = "FHIR Validation Server"
SERVER_VERSION = "1.0.0"
SERVER_DESCRIPTION = "Universal FHIR Resource Validation API"

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
RESOURCES_PATH = PROJECT_ROOT / "resources" / "fhir_base"

# FHIR Resource files
FHIR_SCHEMA_FILE = RESOURCES_PATH / "fhir.schema.json" / "fhir.schema.json"
PROFILES_RESOURCES_FILE = RESOURCES_PATH / "profiles-resources.json"
PROFILES_TYPES_FILE = RESOURCES_PATH / "profiles-types.json"
PROFILES_OTHERS_FILE = RESOURCES_PATH / "profiles-others.json"
VALUESETS_FILE = RESOURCES_PATH / "valuesets.json"
EXTENSION_DEFINITIONS_FILE = RESOURCES_PATH / "extension-definitions.json"
SEARCH_PARAMETERS_FILE = RESOURCES_PATH / "search-parameters.json"
CONCEPTMAPS_FILE = RESOURCES_PATH / "conceptmaps.json"
DATAELEMENTS_FILE = RESOURCES_PATH / "dataelements.json"
V2_TABLES_FILE = RESOURCES_PATH / "v2-tables.json"
V3_CODESYSTEMS_FILE = RESOURCES_PATH / "v3-codesystems.json"
VERSION_INFO_FILE = RESOURCES_PATH / "version.info"

# HTTP Status codes
HTTP_200_OK = 200
HTTP_400_BAD_REQUEST = 400
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_500_INTERNAL_SERVER_ERROR = 500

# Validation result statuses
VALIDATION_SUCCESS = "success"
VALIDATION_ERROR = "error"
VALIDATION_WARNING = "warning"

# FHIR Resource types (common ones)
FHIR_RESOURCE_TYPES = [
    "Patient", "Practitioner", "Organization", "Location", "Encounter",
    "Observation", "DiagnosticReport", "Medication", "MedicationRequest",
    "AllergyIntolerance", "Condition", "Procedure", "Immunization",
    "CarePlan", "Goal", "Bundle", "Binary", "DocumentReference"
]

# Content types
CONTENT_TYPE_FHIR_JSON = "application/fhir+json"
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_XML = "application/fhir+xml"
