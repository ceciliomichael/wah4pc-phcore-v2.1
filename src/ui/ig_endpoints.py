"""PH-Core Implementation Guide hosting endpoints."""

import json
import logging
from typing import Any, Dict, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Path as PathParam
from fastapi.responses import JSONResponse

from src.lib.resource_loader import resource_loader
from src.constants.fhir_constants import (
    HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR,
    PROJECT_ROOT
)

logger = logging.getLogger(__name__)

# Create router for IG endpoints
ig_router = APIRouter()

# PH-Core Implementation Guide path
PH_CORE_PATH = PROJECT_ROOT / "resources" / "implementation_guides" / "ph_core"


class PHCoreIGServer:
    """PH-Core Implementation Guide server."""
    
    def __init__(self):
        """Initialize the IG server."""
        self._ig_resources: Dict[str, Dict[str, Any]] = {}
        self._load_ig_resources()
    
    def _load_ig_resources(self) -> None:
        """Load all PH-Core IG resources into memory."""
        try:
            if not PH_CORE_PATH.exists():
                logger.error(f"PH-Core path does not exist: {PH_CORE_PATH}")
                return
            
            logger.info(f"Loading PH-Core IG resources from: {PH_CORE_PATH}")
            
            # Load all JSON files in the PH-Core directory
            for json_file in PH_CORE_PATH.glob("*.json"):
                try:
                    # Load JSON file directly
                    with open(json_file, 'r', encoding='utf-8') as f:
                        resource_data = json.load(f)
                    
                    if isinstance(resource_data, dict) and "resourceType" in resource_data:
                        resource_type = resource_data["resourceType"]
                        resource_id = resource_data.get("id", json_file.stem)
                        
                        # Store by resource type and ID for easy lookup
                        if resource_type not in self._ig_resources:
                            self._ig_resources[resource_type] = {}
                        
                        self._ig_resources[resource_type][resource_id] = resource_data
                        
                        logger.debug(f"Loaded {resource_type}/{resource_id} from {json_file.name}")
                        
                except Exception as e:
                    logger.warning(f"Failed to load {json_file}: {e}")
            
            total_resources = sum(len(resources) for resources in self._ig_resources.values())
            logger.info(f"Successfully loaded {total_resources} PH-Core IG resources")
            
        except Exception as e:
            logger.error(f"Error loading PH-Core IG resources: {e}")
    
    def get_resource(self, resource_type: str, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific IG resource by type and ID."""
        return self._ig_resources.get(resource_type, {}).get(resource_id)
    
    def get_all_resources_by_type(self, resource_type: str) -> Dict[str, Dict[str, Any]]:
        """Get all resources of a specific type."""
        return self._ig_resources.get(resource_type, {})
    
    def get_structure_definition(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get a StructureDefinition by ID."""
        return self.get_resource("StructureDefinition", profile_id)
    
    def get_value_set(self, valueset_id: str) -> Optional[Dict[str, Any]]:
        """Get a ValueSet by ID."""
        return self.get_resource("ValueSet", valueset_id)
    
    def get_code_system(self, codesystem_id: str) -> Optional[Dict[str, Any]]:
        """Get a CodeSystem by ID."""
        return self.get_resource("CodeSystem", codesystem_id)
    
    def get_implementation_guide(self) -> Optional[Dict[str, Any]]:
        """Get the main Implementation Guide resource."""
        return self.get_resource("ImplementationGuide", "localhost.fhir.ph.core")
    
    def list_all_resources(self) -> Dict[str, int]:
        """Get a summary of all loaded resources."""
        return {
            resource_type: len(resources)
            for resource_type, resources in self._ig_resources.items()
        }


# Global IG server instance
ph_core_ig_server = PHCoreIGServer()


@ig_router.get(
    "/StructureDefinition/{profile_id}",
    summary="Get PH-Core StructureDefinition",
    description="Get a specific PH-Core StructureDefinition profile",
    tags=["PH-Core IG"]
)
async def get_structure_definition(
    profile_id: str = PathParam(..., description="StructureDefinition ID")
) -> JSONResponse:
    """Get a PH-Core StructureDefinition profile.
    
    Args:
        profile_id: The StructureDefinition ID
        
    Returns:
        The StructureDefinition resource
        
    Raises:
        HTTPException: If profile not found
    """
    try:
        profile = ph_core_ig_server.get_structure_definition(profile_id)
        if not profile:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"StructureDefinition '{profile_id}' not found in PH-Core IG"
            )
        
        return JSONResponse(content=profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving StructureDefinition {profile_id}: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving StructureDefinition"
        )


@ig_router.get(
    "/ValueSet/{valueset_id}",
    summary="Get PH-Core ValueSet",
    description="Get a specific PH-Core ValueSet",
    tags=["PH-Core IG"]
)
async def get_value_set(
    valueset_id: str = PathParam(..., description="ValueSet ID")
) -> JSONResponse:
    """Get a PH-Core ValueSet.
    
    Args:
        valueset_id: The ValueSet ID
        
    Returns:
        The ValueSet resource
        
    Raises:
        HTTPException: If ValueSet not found
    """
    try:
        valueset = ph_core_ig_server.get_value_set(valueset_id)
        if not valueset:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"ValueSet '{valueset_id}' not found in PH-Core IG"
            )
        
        return JSONResponse(content=valueset)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving ValueSet {valueset_id}: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving ValueSet"
        )


@ig_router.get(
    "/CodeSystem/{codesystem_id}",
    summary="Get PH-Core CodeSystem",
    description="Get a specific PH-Core CodeSystem",
    tags=["PH-Core IG"]
)
async def get_code_system(
    codesystem_id: str = PathParam(..., description="CodeSystem ID")
) -> JSONResponse:
    """Get a PH-Core CodeSystem.
    
    Args:
        codesystem_id: The CodeSystem ID
        
    Returns:
        The CodeSystem resource
        
    Raises:
        HTTPException: If CodeSystem not found
    """
    try:
        codesystem = ph_core_ig_server.get_code_system(codesystem_id)
        if not codesystem:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"CodeSystem '{codesystem_id}' not found in PH-Core IG"
            )
        
        return JSONResponse(content=codesystem)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving CodeSystem {codesystem_id}: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving CodeSystem"
        )


@ig_router.get(
    "/ImplementationGuide/{ig_id}",
    summary="Get PH-Core Implementation Guide",
    description="Get the main PH-Core Implementation Guide resource",
    tags=["PH-Core IG"]
)
async def get_implementation_guide(
    ig_id: str = PathParam(..., description="Implementation Guide ID")
) -> JSONResponse:
    """Get the PH-Core Implementation Guide.
    
    Args:
        ig_id: The Implementation Guide ID
        
    Returns:
        The ImplementationGuide resource
        
    Raises:
        HTTPException: If IG not found
    """
    try:
        if ig_id != "localhost.fhir.ph.core":
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Implementation Guide '{ig_id}' not found. Only 'localhost.fhir.ph.core' is supported."
            )
        
        ig = ph_core_ig_server.get_implementation_guide()
        if not ig:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="PH-Core Implementation Guide not found"
            )
        
        return JSONResponse(content=ig)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving Implementation Guide {ig_id}: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving Implementation Guide"
        )


@ig_router.get(
    "/ig-summary",
    summary="Get PH-Core IG Summary",
    description="Get a summary of all loaded PH-Core IG resources",
    tags=["PH-Core IG"]
)
async def get_ig_summary() -> Dict[str, Any]:
    """Get a summary of the loaded PH-Core IG.
    
    Returns:
        Summary of loaded resources
    """
    try:
        summary = ph_core_ig_server.list_all_resources()
        total_resources = sum(summary.values())
        
        return {
            "implementation_guide": "PH-Core v0.1.0",
            "base_url": "http://localhost:6789",
            "total_resources": total_resources,
            "resources_by_type": summary,
            "status": "loaded"
        }
        
    except Exception as e:
        logger.error(f"Error getting IG summary: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving IG summary"
        )


# Health check for IG server
@ig_router.get(
    "/ig-health",
    summary="PH-Core IG Health Check",
    description="Check if PH-Core IG resources are loaded",
    tags=["PH-Core IG"]
)
async def ig_health_check() -> Dict[str, Any]:
    """Check PH-Core IG health status.
    
    Returns:
        Health status of the IG server
    """
    try:
        summary = ph_core_ig_server.list_all_resources()
        total_resources = sum(summary.values())
        
        if total_resources == 0:
            return {
                "status": "unhealthy",
                "message": "No PH-Core IG resources loaded",
                "total_resources": 0
            }
        
        return {
            "status": "healthy",
            "message": f"PH-Core IG loaded with {total_resources} resources",
            "total_resources": total_resources,
            "resource_types": list(summary.keys())
        }
        
    except Exception as e:
        logger.error(f"IG health check failed: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "total_resources": 0
        }
