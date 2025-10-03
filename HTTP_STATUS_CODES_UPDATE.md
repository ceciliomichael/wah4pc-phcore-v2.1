# HTTP Status Codes Implementation

## Overview
Updated the FHIR Validation API to return proper HTTP status codes based on validation results, improving REST API compliance and client-side error handling.

## Changes Made

### Previous Behavior
- **Problem**: API returned HTTP `200 OK` for all validation responses, regardless of whether validation succeeded or failed
- **Impact**: Clients couldn't determine validation outcome from HTTP status alone; had to parse response body
- **Example**: Failed validation returned `200 OK` with `{"valid": false}` in body

### New Behavior
The API now returns appropriate HTTP status codes that reflect the actual validation outcome:

#### Standard Validation Endpoint (`POST /api/v1/validate`)
- **200 OK**: Validation successful (`valid=true`, `status=success`)
- **400 Bad Request**: Validation failed (`valid=false`, `status=failed`)
- **422 Unprocessable Entity**: Validation passed with warnings (`valid=true`, `status=warning`)
- **500 Internal Server Error**: Server error during validation

#### PH-Core Validation Endpoint (`POST /api/v1/validate/ph-core`)
- **200 OK**: Validation successful (`valid=true`, `status=success`)
- **400 Bad Request**: Validation failed (`valid=false`, `status=failed`)
- **422 Unprocessable Entity**: Validation passed with warnings (`valid=true`, `status=warning`)
- **500 Internal Server Error**: Server error during validation

#### Batch Validation Endpoint (`POST /api/v1/validate/batch`)
- **200 OK**: All resources validated successfully
- **207 Multi-Status**: Mixed validation results (some passed, some failed)
- **400 Bad Request**: All resources failed validation OR invalid request (e.g., batch size exceeded)
- **500 Internal Server Error**: Server error during validation

## Technical Implementation

### Modified Files
1. **`src/ui/api_endpoints.py`**
   - Updated `validate_fhir_resource()` endpoint
   - Updated `validate_ph_core_fhir_resource()` endpoint
   - Updated `validate_batch_resources()` endpoint
   - All validation endpoints now return `JSONResponse` with appropriate status codes

2. **`API_ENDPOINTS_DOCUMENTATION.md`**
   - Added HTTP status code documentation for all validation endpoints
   - Included example responses for each status code
   - Added comprehensive "HTTP Status Codes Summary" section
   - Updated "Error Response Formats" section

### Code Changes

#### Before:
```python
@router.post("/validate", response_model=ValidationResponse, ...)
async def validate_fhir_resource(request: ValidationRequest) -> ValidationResponse:
    validation_result = fhir_validator.validate_resource(...)
    return ValidationResponse(
        validation_result=validation_result,
        processed_at=datetime.now().isoformat(),
        processing_time_ms=processing_time
    )
    # Always returned 200 OK
```

#### After:
```python
@router.post("/validate", ...)
async def validate_fhir_resource(request: ValidationRequest):
    validation_result = fhir_validator.validate_resource(...)
    response_data = ValidationResponse(...)
    
    # Return appropriate HTTP status code
    if not validation_result.valid:
        return JSONResponse(status_code=400, content=response_data.model_dump())
    elif validation_result.status == ValidationStatus.WARNING:
        return JSONResponse(status_code=422, content=response_data.model_dump())
    else:
        return JSONResponse(status_code=200, content=response_data.model_dump())
```

## Benefits

### 1. REST API Compliance
- Follows HTTP specification and REST best practices
- Status codes semantically represent the outcome
- Easier integration with standard HTTP clients

### 2. Improved Client Experience
- Clients can check HTTP status before parsing response body
- Standard error handling patterns apply
- Better support for HTTP middleware and proxies

### 3. Better Monitoring & Logging
- HTTP status codes appear in access logs
- Easier to track API health metrics
- Clear distinction between validation failures and server errors

### 4. Framework Integration
- Works seamlessly with HTTP client libraries (axios, fetch, requests, etc.)
- Automatic error handling in many frameworks
- Better support for API gateways and load balancers

## Migration Guide for API Consumers

### Breaking Changes
⚠️ **Important**: This is a breaking change for clients that expect `200 OK` for all responses.

### Before (Old Behavior)
```javascript
// Client had to always check response body
const response = await fetch('/api/v1/validate', {
    method: 'POST',
    body: JSON.stringify(request)
});

// Always 200, regardless of validation result
const data = await response.json();
if (!data.validation_result.valid) {
    // Handle validation failure
}
```

### After (New Behavior)
```javascript
// Client can check HTTP status
const response = await fetch('/api/v1/validate', {
    method: 'POST',
    body: JSON.stringify(request)
});

if (response.ok) {
    // 200 OK - Validation successful
    const data = await response.json();
    console.log('Validation passed!');
} else if (response.status === 400) {
    // Validation failed
    const data = await response.json();
    console.error('Validation failed:', data.validation_result.issues);
} else if (response.status === 422) {
    // Validation passed with warnings
    const data = await response.json();
    console.warn('Validation warnings:', data.validation_result.issues);
}
```

### Python Example
```python
import requests

response = requests.post(
    'http://localhost:6789/api/v1/validate',
    json={'resource': {...}}
)

if response.status_code == 200:
    print('✓ Validation successful')
elif response.status_code == 400:
    print('✗ Validation failed')
    print(response.json()['validation_result']['issues'])
elif response.status_code == 422:
    print('⚠ Validation warnings')
    print(response.json()['validation_result']['issues'])
```

## Response Format

The response body format **remains unchanged** - only the HTTP status code changes based on outcome.

### Success Response (200 OK)
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

### Failure Response (400 Bad Request)
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

### Warning Response (422 Unprocessable Entity)
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

## HTTP Status Code Reference

### Success Codes
- **200 OK**: Request successful, validation passed
- **207 Multi-Status**: Batch request with mixed results

### Client Error Codes
- **400 Bad Request**: Validation failed OR invalid request parameters
- **404 Not Found**: Requested resource/profile not found
- **422 Unprocessable Entity**: Validation passed with warnings

### Server Error Codes
- **500 Internal Server Error**: Server error during processing

## Testing the Changes

### Test Successful Validation
```bash
curl -i -X POST "http://localhost:6789/api/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "resource": {
      "resourceType": "Patient",
      "name": [{"family": "Doe", "given": ["John"]}],
      "gender": "male",
      "birthDate": "1990-01-01"
    }
  }'

# Should return: HTTP/1.1 200 OK
```

### Test Failed Validation
```bash
curl -i -X POST "http://localhost:6789/api/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "resource": {
      "resourceType": "Patient",
      "gender": "invalid-gender"
    }
  }'

# Should return: HTTP/1.1 400 Bad Request
```

### Test Validation with Warnings
```bash
curl -i -X POST "http://localhost:6789/api/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "resource": {
      "resourceType": "Patient",
      "name": [{"family": "Doe"}],
      "gender": "male"
    }
  }'

# May return: HTTP/1.1 422 Unprocessable Entity (if warnings present)
```

## Backward Compatibility

### Breaking Change Notice
This update introduces a **breaking change** for API consumers who:
- Assume all responses return `200 OK`
- Don't check the `valid` field in response body
- Have hardcoded status code checks for `200`

### Recommended Client Updates
1. Update HTTP status code handling
2. Treat `400` as validation failure
3. Treat `422` as validation warning (still valid)
4. Implement proper error handling for each status code

## Implementation Notes

- Status codes are determined by the `ValidationResult.valid` field and `ValidationResult.status` field
- The response body format remains completely unchanged
- All existing validation logic remains the same
- Only the HTTP status code mapping has changed
- Server errors (500) continue to raise `HTTPException` as before

## References

- [RFC 7231 - HTTP Status Codes](https://tools.ietf.org/html/rfc7231#section-6)
- [RFC 4918 - HTTP 207 Multi-Status](https://tools.ietf.org/html/rfc4918#section-11.1)
- [REST API Design Best Practices](https://www.rfc-editor.org/rfc/rfc7231.html)

---

**Version**: 1.0.0  
**Date**: October 3, 2025  
**Author**: FHIR Validation Server Team

