# FHIR Validation Server API Endpoints Documentation

## Server Information
- **Server Name**: FHIR Validation Server
- **Version**: 1.0.0
- **Base URL**: `http://localhost:6789`
- **API Version**: v1
- **FHIR Version**: R4 (4.0.1)
- **Implementation Guide**: PH-Core v0.1.0

## Quick Start
```bash
# Start the server
python main.py

# Server will be available at http://localhost:6789
# Interactive API docs at http://localhost:6789/docs
# Alternative docs at http://localhost:6789/redoc
```

---

## 1. Validation Endpoints (`/api/v1/`)

### POST `/api/v1/validate`
**Standard FHIR Validation** - Validates against FHIR R4 specification only (no PH-Core requirements)

**HTTP Status Codes:**
- `200 OK` - Validation successful (valid=true, status=success)
- `400 Bad Request` - Validation failed (valid=false, status=failed)
- `422 Unprocessable Entity` - Validation passed with warnings (valid=true, status=warning)
- `500 Internal Server Error` - Server error during validation

**Request Body:**
```json
{
  "resource": {
    "resourceType": "Patient",
    "id": "example-patient",
    "name": [{"family": "Doe", "given": ["John"]}],
    "gender": "male",
    "birthDate": "1990-01-01"
  },
  "profile": "https://wah4pc-validation.echosphere.cfd/StructureDefinition/ph-core-patient",
  "validate_code_systems": true,
  "validate_value_sets": true,
  "use_ph_core": false,
  "strict_ph_core": false
}
```

**Success Response (200 OK):**
```json
{
  "validation_result": {
    "status": "success",
    "message": "Validation successful",
    "issues": [],
    "resource_type": "Patient",
    "valid": true
  },
  "processed_at": "2024-01-01T12:00:00.000000",
  "processing_time_ms": 150
}
```

**Failure Response (400 Bad Request):**
```json
{
  "validation_result": {
    "status": "failed",
    "message": "Validation failed with 3 error(s)",
    "issues": [
      {
        "severity": "error",
        "code": "missing-required-field",
        "details": "Patient must have a name",
        "location": "name"
      }
    ],
    "resource_type": "Patient",
    "valid": false
  },
  "processed_at": "2024-01-01T12:00:00.000000",
  "processing_time_ms": 150
}
```

**Warning Response (422 Unprocessable Entity):**
```json
{
  "validation_result": {
    "status": "warning",
    "message": "Validation passed with 2 warning(s)",
    "issues": [
      {
        "severity": "warning",
        "code": "missing-identifier",
        "details": "Patient should have an identifier",
        "location": "identifier"
      }
    ],
    "resource_type": "Patient",
    "valid": true
  },
  "processed_at": "2024-01-01T12:00:00.000000",
  "processing_time_ms": 150
}
```

### POST `/api/v1/validate/ph-core`
**PH-Core STRICT Validation** - Validates against BOTH FHIR R4 AND PH-Core IG (STRICT COMPLIANCE REQUIRED)

**Key Difference:** Resources that don't meet PH-Core requirements will FAIL validation.

**HTTP Status Codes:**
- `200 OK` - Validation successful (valid=true, status=success)
- `400 Bad Request` - Validation failed (valid=false, status=failed)
- `422 Unprocessable Entity` - Validation passed with warnings (valid=true, status=warning)
- `500 Internal Server Error` - Server error during validation

**Request Body:**
```json
{
  "resource": {
    "resourceType": "Patient",
    "id": "ph-core-patient",
    "meta": {
      "profile": ["https://wah4pc-validation.echosphere.cfd/StructureDefinition/ph-core-patient"]
    },
    "extension": [
      {
        "url": "https://wah4pc-validation.echosphere.cfd/StructureDefinition/indigenous-people",
        "valueBoolean": false
      }
    ],
    "name": [{"use": "official", "family": "Dela Cruz", "given": ["Juan"]}],
    "gender": "male",
    "birthDate": "1980-01-01"
  },
  "validate_code_systems": true,
  "validate_value_sets": true
}
```

**Response:** Same format as `/api/v1/validate` but with PH-Core specific validation issues

### POST `/api/v1/validate/batch`
**Batch Validation** - Validate multiple FHIR resources (Standard FHIR only)

**HTTP Status Codes:**
- `200 OK` - All resources validated successfully
- `207 Multi-Status` - Mixed validation results (some passed, some failed)
- `400 Bad Request` - All resources failed validation OR invalid batch request (e.g., too many resources)
- `500 Internal Server Error` - Server error during validation

**Request Body:**
```json
[
  {
    "resource": {"resourceType": "Patient", "id": "patient-1", "name": [{"family": "Smith", "given": ["Jane"]}]}
  },
  {
    "resource": {"resourceType": "Observation", "id": "obs-1", "status": "final", "code": {"coding": [{"system": "http://loinc.org", "code": "55284-4"}]}}
  }
]
```

**Response:** Array of ValidationResponse objects (one for each resource)

**Limits:** Maximum 100 resources per batch

---

## 2. Information Endpoints (`/api/v1/`)

### GET `/api/v1/resource-types`
**Get Supported Resource Types**

**Response:**
```json
["Patient", "Practitioner", "Organization", "Location", "Encounter", "Observation", ...]
```

### GET `/api/v1/profile/{resource_type}`
**Get Resource Profile Definition**

**Example:** `GET /api/v1/profile/Patient`

**Response:** Complete FHIR StructureDefinition for the specified resource type

### GET `/api/v1/server-info`
**Get Server Information**

**Response:**
```json
{
  "name": "FHIR Validation Server",
  "version": "1.0.0",
  "description": "Universal FHIR Resource Validation API",
  "fhir_version": "R4",
  "supported_formats": ["application/fhir+json", "application/json"],
  "supported_operations": [
    "validate-standard",
    "validate-ph-core",
    "batch-validate",
    "resource-info",
    "fhir-base-resources",
    "ph-core-resources"
  ]
}
```

### GET `/api/v1/health`
**Health Check**

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

### GET `/api/v1/resources/fhir-base`
**List All FHIR Base Resources**

**Response:**
```json
[
  {
    "id": "Patient",
    "resourceType": "StructureDefinition",
    "url": "http://hl7.org/fhir/StructureDefinition/Patient",
    "name": "Patient",
    "title": "Patient",
    "status": "active",
    "version": "4.0.1",
    "description": "Demographics and other administrative information about an individual...",
    "type": "Patient",
    "kind": "resource",
    "abstract": false,
    "context": null,
    "purpose": null
  }
]
```

### GET `/api/v1/resources/ph-core`
**List All PH-Core Resources**

**Response:**
```json
[
  {
    "id": "ph-core-patient",
    "resourceType": "StructureDefinition",
    "url": "https://wah4pc-validation.echosphere.cfd/StructureDefinition/ph-core-patient",
    "name": "PHCorePatient",
    "title": "PH Core Patient",
    "status": "active",
    "version": "0.1.0",
    "description": "Philippines-specific patient profile...",
    "type": "Patient",
    "kind": "resource",
    "abstract": false,
    "context": null,
    "purpose": null,
    "baseDefinition": "http://hl7.org/fhir/StructureDefinition/Patient",
    "derivation": "constraint",
    "experimental": false,
    "jurisdiction": [{"coding": [{"system": "urn:iso:std:iso:3166", "code": "PH"}]}],
    "publisher": "ECHOSPHERE",
    "contact": [...]
  }
]
```

---

## 3. PH-Core Implementation Guide Endpoints (Root Level)

### GET `/StructureDefinition/{profile_id}`
**Get PH-Core StructureDefinition**

**Example:** `GET /StructureDefinition/ph-core-patient`

**Response:** Complete PH-Core StructureDefinition JSON

### GET `/ValueSet/{valueset_id}`
**Get PH-Core ValueSet**

**Example:** `GET /ValueSet/ph-core-gender`

**Response:** Complete PH-Core ValueSet JSON

### GET `/CodeSystem/{codesystem_id}`
**Get PH-Core CodeSystem**

**Example:** `GET /CodeSystem/ph-core-ethnicity`

**Response:** Complete PH-Core CodeSystem JSON

### GET `/ImplementationGuide/{ig_id}`
**Get PH-Core Implementation Guide**

**Example:** `GET /ImplementationGuide/localhost.fhir.ph.core`

**Response:** Complete PH-Core ImplementationGuide JSON

### GET `/ig-summary`
**Get PH-Core IG Summary**

**Response:**
```json
{
  "implementation_guide": "PH-Core v0.1.0",
  "base_url": "https://wah4pc-validation.echosphere.cfd",
  "total_resources": 62,
  "resources_by_type": {
    "StructureDefinition": 25,
    "ValueSet": 15,
    "CodeSystem": 12,
    "NamingSystem": 8,
    "ImplementationGuide": 1,
    "CapabilityStatement": 1
  },
  "status": "loaded"
}
```

### GET `/ig-health`
**PH-Core IG Health Check**

**Response:**
```json
{
  "status": "healthy",
  "message": "PH-Core IG loaded with 62 resources",
  "total_resources": 62,
  "resource_types": ["StructureDefinition", "ValueSet", "CodeSystem", "NamingSystem", "ImplementationGuide", "CapabilityStatement"]
}
```

---

## 4. Web Interface Endpoints (Root Level)

### GET `/`
**Home Page** - Resource browser overview

### GET `/resources/{category}`
**List Resources by Category**

**Categories:** `fhir_base`, `ph_core`, `examples`

**Example:** `GET /resources/ph_core`

### GET `/resources/{category}/{resource_name}`
**View Specific Resource**

**Example:** `GET /resources/ph_core/ph-core-patient`

### GET `/resources/examples/{validity}/{resource_type}/{example_name}`
**View Example Resource**

**Example:** `GET /resources/examples/valid/Patient/patient-001`

### GET `/resources/examples/{resource_type}`
**List Examples by Resource Type**

**Example:** `GET /resources/examples/Patient`

### GET `/search?q={query}`
**Search Resources**

**Example:** `GET /search?q=patient`

### GET `/reload`
**Reload Resources** - Manually refresh resource cache

### GET `/api/docs`
**API Documentation Index**

### GET `/api/docs/overview`
**API Overview Documentation**

### GET `/api/docs/validation`
**Validation Documentation**

### GET `/api/docs/information`
**Information Endpoints Documentation**

### GET `/api/docs/health`
**Health & Status Documentation**

### GET `/api/docs/ph-core-ig`
**PH-Core IG Documentation**

### GET `/api/docs/additional`
**Additional Resources Documentation**

---

## Validation Request/Response Types

### ValidationRequest
```python
class ValidationRequest:
    resource: Dict[str, Any]          # FHIR resource JSON
    profile: Optional[str] = None     # Profile URL to validate against
    validate_code_systems: bool = True # Check code systems
    validate_value_sets: bool = True   # Check value sets
    use_ph_core: bool = False         # Enable PH-Core validation
    strict_ph_core: bool = False      # Strict PH-Core mode (failures = errors)
```

### ValidationResponse
```python
class ValidationResponse:
    validation_result: ValidationResult
    processed_at: str                    # ISO timestamp
    processing_time_ms: int
```

### ValidationResult
```python
class ValidationResult:
    status: str                         # "success" | "error" | "warning"
    message: str                        # Human readable message
    issues: List[ValidationIssue]       # Detailed issues
    resource_type: Optional[str]        # FHIR resource type
    valid: bool                         # Overall validity
```

### ValidationIssue
```python
class ValidationIssue:
    severity: str                       # "error" | "warning" | "info"
    code: str                           # Issue code
    details: str                        # Human readable details
    expression: List[str]               # FHIRPath expressions
    location: Optional[str] = None      # Location in resource
```

---

## HTTP Status Codes Summary

### Validation Endpoints
- **200 OK** - Validation successful (valid=true, status=success)
- **400 Bad Request** - Validation failed (valid=false) OR invalid request (e.g., batch size exceeded)
- **422 Unprocessable Entity** - Validation passed with warnings (valid=true, status=warning)
- **207 Multi-Status** - Batch validation with mixed results (some passed, some failed)
- **500 Internal Server Error** - Server error during validation

### Information & Resource Endpoints
- **200 OK** - Request successful
- **404 Not Found** - Resource not found
- **500 Internal Server Error** - Server error

## Error Response Formats

### Validation Failure (400 Bad Request)
Validation endpoints return the full ValidationResponse with status code 400:
```json
{
  "validation_result": {
    "status": "failed",
    "message": "Validation failed with 2 error(s)",
    "issues": [
      {
        "severity": "error",
        "code": "missing-required-field",
        "details": "Patient must have a name",
        "location": "name"
      }
    ],
    "resource_type": "Patient",
    "valid": false
  },
  "processed_at": "2024-01-01T12:00:00.000000",
  "processing_time_ms": 150
}
```

### Invalid Request (400 Bad Request)
```json
{
  "detail": "Batch size cannot exceed 100 resources"
}
```

### Resource Not Found (404 Not Found)
```json
{
  "detail": "StructureDefinition 'invalid-profile' not found in PH-Core IG"
}
```

### Validation Warning (422 Unprocessable Entity)
Validation endpoints return the full ValidationResponse with status code 422:
```json
{
  "validation_result": {
    "status": "warning",
    "message": "Validation passed with 1 warning(s)",
    "issues": [
      {
        "severity": "warning",
        "code": "missing-identifier",
        "details": "Patient should have an identifier",
        "location": "identifier"
      }
    ],
    "resource_type": "Patient",
    "valid": true
  },
  "processed_at": "2024-01-01T12:00:00.000000",
  "processing_time_ms": 150
}
```

### Server Error (500 Internal Server Error)
```json
{
  "detail": "Internal server error during validation: {error_message}"
}
```

---

## Content Types

- **Request:** `application/json`
- **Response:** `application/json`
- **FHIR Content:** `application/fhir+json`

---

## Rate Limits & Constraints

- **Batch Validation:** Maximum 100 resources per request
- **Request Size:** Limited by server configuration
- **Timeout:** Validation operations may take several seconds for complex resources

---

## Authentication

Currently no authentication required for API endpoints.

---

## Examples

### Validate Standard Patient
```bash
curl -X POST "http://localhost:6789/api/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "resource": {
      "resourceType": "Patient",
      "name": [{"family": "Doe", "given": ["John"]}],
      "gender": "male",
      "birthDate": "1990-01-01"
    }
  }'
```

### Validate PH-Core Patient
```bash
curl -X POST "http://localhost:6789/api/v1/validate/ph-core" \
  -H "Content-Type: application/json" \
  -d '{
    "resource": {
      "resourceType": "Patient",
      "meta": {
        "profile": ["https://wah4pc-validation.echosphere.cfd/StructureDefinition/ph-core-patient"]
      },
      "extension": [{
        "url": "https://wah4pc-validation.echosphere.cfd/StructureDefinition/indigenous-people",
        "valueBoolean": false
      }],
      "name": [{"family": "Dela Cruz", "given": ["Juan"]}],
      "gender": "male",
      "birthDate": "1980-01-01"
    }
  }'
```

### Get Server Health
```bash
curl -X GET "http://localhost:6789/api/v1/health"
```

### Get PH-Core Resources List
```bash
curl -X GET "http://localhost:6789/api/v1/resources/ph-core"
```

### Access PH-Core Profile
```bash
curl -X GET "http://localhost:6789/StructureDefinition/ph-core-patient"
```

---

## Development Notes

- Server auto-reloads on code changes in development mode
- Resources are cached in memory for performance
- Web interface provides interactive browsing of all FHIR resources
- Both REST API and web interface support CORS
- Comprehensive OpenAPI/Swagger documentation available at `/docs`
- Alternative ReDoc documentation at `/redoc`

---

*This documentation covers all endpoints as of FHIR Validation Server v1.0.0*
