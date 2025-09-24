"""FHIR validation API endpoints."""

import time
import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import JSONResponse

from src.types.fhir_types import (
    ValidationRequest, ValidationResponse, ValidationResult,
    ServerInfo, HealthStatus, FHIRResource
)
from src.utils.fhir_validator import fhir_validator
from src.lib.resource_loader import resource_loader
from src.constants.fhir_constants import (
    SERVER_NAME, SERVER_VERSION, SERVER_DESCRIPTION,
    HTTP_400_BAD_REQUEST, HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR, CONTENT_TYPE_FHIR_JSON
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post(
    "/validate",
    response_model=ValidationResponse,
    summary="Validate FHIR Resource",
    description="Validate a FHIR resource against base FHIR specification and optional profiles",
    tags=["Validation"]
)
async def validate_fhir_resource(
    request: ValidationRequest = Body(
        ...,
        examples={
            "patient_example": {
                "summary": "Example Patient Resource",
                "description": "A sample Patient resource for validation",
                "value": {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "example-patient",
                        "name": [
                            {
                                "use": "official",
                                "family": "Doe",
                                "given": ["John"]
                            }
                        ],
                        "gender": "male",
                        "birthDate": "1990-01-01"
                    },
                    "profile": None,
                    "validate_code_systems": True,
                    "validate_value_sets": True
                }
            }
        }
    )
) -> ValidationResponse:
    """Validate a FHIR resource.
    
    Args:
        request: Validation request containing the resource and options
        
    Returns:
        Validation response with results
        
    Raises:
        HTTPException: If validation fails due to server error
    """
    start_time = time.time()
    
    try:
        # Validate the resource
        validation_result = fhir_validator.validate_resource(
            resource=request.resource,
            profile_url=request.profile,
            validate_code_systems=request.validate_code_systems,
            validate_value_sets=request.validate_value_sets
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return ValidationResponse(
            validation_result=validation_result,
            processed_at=datetime.now().isoformat(),
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error validating resource: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during validation: {str(e)}"
        )


@router.post(
    "/validate/batch",
    response_model=List[ValidationResponse],
    summary="Validate Multiple FHIR Resources",
    description="Validate multiple FHIR resources in a single request",
    tags=["Validation"]
)
async def validate_batch_resources(
    resources: List[ValidationRequest] = Body(
        ...,
        examples={
            "batch_example": {
                "summary": "Example Batch Validation",
                "description": "Sample batch with Patient and Observation resources",
                "value": [
                    {
                        "resource": {
                            "resourceType": "Patient",
                            "id": "patient-1",
                            "name": [{"family": "Smith", "given": ["Jane"]}]
                        }
                    },
                    {
                        "resource": {
                            "resourceType": "Observation",
                            "id": "obs-1",
                            "status": "final",
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://loinc.org",
                                        "code": "55284-4"
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        }
    )
) -> List[ValidationResponse]:
    """Validate multiple FHIR resources.
    
    Args:
        resources: List of validation requests
        
    Returns:
        List of validation responses
        
    Raises:
        HTTPException: If batch validation fails
    """
    if len(resources) > 100:  # Limit batch size
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Batch size cannot exceed 100 resources"
        )
    
    results = []
    
    for i, request in enumerate(resources):
        try:
            start_time = time.time()
            
            validation_result = fhir_validator.validate_resource(
                resource=request.resource,
                profile_url=request.profile,
                validate_code_systems=request.validate_code_systems,
                validate_value_sets=request.validate_value_sets
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            results.append(ValidationResponse(
                validation_result=validation_result,
                processed_at=datetime.now().isoformat(),
                processing_time_ms=processing_time
            ))
            
        except Exception as e:
            logger.error(f"Error validating resource {i}: {e}")
            # Create error response for this resource
            results.append(ValidationResponse(
                validation_result=ValidationResult(
                    status="failed",
                    message=f"Validation failed: {str(e)}",
                    issues=[],
                    resource_type=request.resource.get('resourceType') if isinstance(request.resource, dict) else None,
                    valid=False
                ),
                processed_at=datetime.now().isoformat(),
                processing_time_ms=0
            ))
    
    return results


@router.get(
    "/resource-types",
    response_model=List[str],
    summary="Get Supported Resource Types",
    description="Get list of supported FHIR resource types",
    tags=["Information"]
)
async def get_supported_resource_types() -> List[str]:
    """Get list of supported FHIR resource types.
    
    Returns:
        List of supported resource types
    """
    try:
        return resource_loader.get_available_resource_types()
    except Exception as e:
        logger.error(f"Error getting resource types: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving supported resource types"
        )


@router.get(
    "/profile/{resource_type}",
    summary="Get Resource Profile",
    description="Get the FHIR profile definition for a specific resource type",
    tags=["Information"]
)
async def get_resource_profile(resource_type: str) -> Dict[str, Any]:
    """Get profile for a specific resource type.
    
    Args:
        resource_type: FHIR resource type
        
    Returns:
        Resource profile definition
        
    Raises:
        HTTPException: If resource type not found
    """
    try:
        profile = resource_loader.get_resource_profile(resource_type)
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Profile not found for resource type: {resource_type}"
            )
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile for {resource_type}: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving resource profile"
        )


@router.get(
    "/server-info",
    response_model=ServerInfo,
    summary="Get Server Information",
    description="Get information about the FHIR validation server",
    tags=["Information"]
)
async def get_server_info() -> ServerInfo:
    """Get server information.
    
    Returns:
        Server information
    """
    return ServerInfo(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        description=SERVER_DESCRIPTION,
        fhir_version="R4",
        supported_formats=[CONTENT_TYPE_FHIR_JSON, "application/json"],
        supported_operations=["validate", "batch-validate", "resource-info"]
    )


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Health Check",
    description="Check server health status",
    tags=["Health"]
)
async def health_check() -> HealthStatus:
    """Perform health check.
    
    Returns:
        Health status
    """
    import psutil
    import os
    
    try:
        # Basic health checks
        process = psutil.Process(os.getpid())
        uptime = time.time() - process.create_time()
        
        return HealthStatus(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version=SERVER_VERSION,
            uptime_seconds=int(uptime)
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthStatus(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            version=SERVER_VERSION,
            uptime_seconds=0
        )
