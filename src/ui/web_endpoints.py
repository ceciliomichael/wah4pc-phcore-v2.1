"""Web frontend endpoints for FHIR resource browser."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.lib.resource_loader import resource_loader
from src.constants.fhir_constants import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Create router for web endpoints
web_router = APIRouter()

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Resource paths
FHIR_BASE_PATH = PROJECT_ROOT / "resources" / "fhir_base"
PH_CORE_PATH = PROJECT_ROOT / "resources" / "implementation_guides" / "ph_core"
EXAMPLES_PATH = PROJECT_ROOT / "resources" / "examples"


class FHIRResourceBrowser:
    """FHIR Resource Browser for web interface."""
    
    def __init__(self):
        """Initialize the resource browser."""
        self._fhir_base_resources: Dict[str, Any] = {}
        self._ph_core_resources: Dict[str, Any] = {}
        self._example_resources: Dict[str, Any] = {}
        self._load_resources()
    
    def reload_resources(self) -> None:
        """Reload all FHIR resources from filesystem."""
        # Clear existing resources
        self._fhir_base_resources.clear()
        self._ph_core_resources.clear()
        self._example_resources.clear()
        
        # Reload from filesystem
        self._load_resources()
    
    def _load_resources(self) -> None:
        """Load all FHIR resources."""
        try:
            # Load FHIR Base resources
            self._load_fhir_base_resources()
            # Load PH Core resources
            self._load_ph_core_resources()
            # Load example resources
            self._load_example_resources()
            
            logger.info(f"Resource loading complete: {len(self._fhir_base_resources)} FHIR base, {len(self._ph_core_resources)} PH Core, {len(self._example_resources)} example resources")
            
        except Exception as e:
            logger.error(f"Error loading resources: {e}")
            raise
    
    def _load_fhir_base_resources(self) -> None:
        """Load FHIR base resources and extract individual resource schemas."""
        if not FHIR_BASE_PATH.exists():
            logger.warning(f"FHIR base path not found: {FHIR_BASE_PATH}")
            return
        
        # Load the main profiles-resources.json which contains individual resource schemas
        profiles_path = FHIR_BASE_PATH / "profiles-resources.json"
        if profiles_path.exists():
            try:
                with open(profiles_path, 'r', encoding='utf-8') as f:
                    bundle = json.load(f)
                    
                # Extract individual StructureDefinition resources from the Bundle
                if (bundle.get("resourceType") == "Bundle" and 
                    bundle.get("type") == "collection" and 
                    "entry" in bundle):
                    
                    for entry in bundle.get("entry", []):
                        if "resource" in entry:
                            resource = entry["resource"]
                            
                            # Only include StructureDefinition resources for base FHIR resource types
                            if (resource.get("resourceType") == "StructureDefinition" and
                                resource.get("kind") == "resource" and
                                resource.get("abstract") == False and
                                resource.get("type") and
                                not resource.get("url", "").startswith("http://hl7.org/fhir/StructureDefinition/Extension")):
                                
                                resource_type = resource.get("type")
                                if resource_type and resource_type != "Extension":
                                    # Use the resource type as the key for easy lookup
                                    self._fhir_base_resources[resource_type] = resource
                                    
            except Exception as e:
                logger.warning(f"Failed to load FHIR profiles: {e}")
        
        # Also load other useful base resources like ValueSets and CodeSystems
        for file_name in ["valuesets.json", "v3-codesystems.json"]:
            file_path = FHIR_BASE_PATH / file_name
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        resource = json.load(f)
                        
                    # Extract individual resources from Bundle if needed
                    if (resource.get("resourceType") == "Bundle" and 
                        resource.get("type") == "collection" and 
                        "entry" in resource):
                        
                        for entry in resource.get("entry", [])[:10]:  # Limit to first 10 for performance
                            if "resource" in entry:
                                individual_resource = entry["resource"]
                                resource_type = individual_resource.get("resourceType")
                                resource_id = individual_resource.get("id", "unknown")
                                
                                if resource_type in ["ValueSet", "CodeSystem"]:
                                    key = f"{resource_type}_{resource_id}"
                                    self._fhir_base_resources[key] = individual_resource
                    else:
                        self._fhir_base_resources[file_path.stem] = resource
                        
                except Exception as e:
                    logger.warning(f"Failed to load {file_name}: {e}")
    
    def _load_ph_core_resources(self) -> None:
        """Load PH Core resources."""
        if not PH_CORE_PATH.exists():
            logger.warning(f"PH Core path not found: {PH_CORE_PATH}")
            return
        
        for file_path in PH_CORE_PATH.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    resource = json.load(f)
                    self._ph_core_resources[file_path.stem] = resource
            except Exception as e:
                logger.warning(f"Failed to load PH Core resource {file_path}: {e}")
    
    def _load_example_resources(self) -> None:
        """Load example resources from organized folder structure."""
        if not EXAMPLES_PATH.exists():
            logger.warning(f"Examples path not found: {EXAMPLES_PATH}")
            return
        
        # Load from valid examples
        valid_path = EXAMPLES_PATH / "valid"
        if valid_path.exists():
            for resource_type_dir in valid_path.iterdir():
                if resource_type_dir.is_dir():
                    resource_type = resource_type_dir.name
                    for file_path in resource_type_dir.glob("*.json"):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                resource = json.load(f)
                                # Use a key that includes the path structure
                                key = f"valid/{resource_type}/{file_path.stem}"
                                self._example_resources[key] = resource
                        except Exception as e:
                            logger.warning(f"Failed to load valid example {file_path}: {e}")
        
        # Load from invalid examples
        invalid_path = EXAMPLES_PATH / "invalid"
        if invalid_path.exists():
            for resource_type_dir in invalid_path.iterdir():
                if resource_type_dir.is_dir():
                    resource_type = resource_type_dir.name
                    for file_path in resource_type_dir.glob("*.json"):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                resource = json.load(f)
                                # Use a key that includes the path structure
                                key = f"invalid/{resource_type}/{file_path.stem}"
                                self._example_resources[key] = resource
                        except Exception as e:
                            logger.warning(f"Failed to load invalid example {file_path}: {e}")
        
        # Also load any remaining files in the root examples directory for backward compatibility
        for file_path in EXAMPLES_PATH.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    resource = json.load(f)
                    self._example_resources[file_path.stem] = resource
            except Exception as e:
                logger.warning(f"Failed to load example resource {file_path}: {e}")
    
    def get_resource_types(self) -> Dict[str, Any]:
        """Get organized resource types."""
        resource_types = {
            "fhir_base": [],
            "ph_core": {},
            "examples": {}
        }
        
        # Organize FHIR base resources (just list the resource type names)
        for name, resource in self._fhir_base_resources.items():
            resource_types["fhir_base"].append(name)
        
        # Organize PH Core resources by type
        ph_core_by_type = {}
        for name, resource in self._ph_core_resources.items():
            resource_type = resource.get("resourceType", "Unknown")
            if resource_type not in ph_core_by_type:
                ph_core_by_type[resource_type] = []
            ph_core_by_type[resource_type].append(name)
        resource_types["ph_core"] = ph_core_by_type
        
        # Organize examples by validity and resource type
        examples_by_type = {
            "valid": {},
            "invalid": {},
            "other": {}
        }
        
        for name, resource in self._example_resources.items():
            resource_type = resource.get("resourceType", "Unknown")
            
            if name.startswith("valid/"):
                # Extract resource type from path: valid/Patient/patient -> Patient
                path_parts = name.split("/")
                if len(path_parts) >= 2:
                    resource_type = path_parts[1]
                if resource_type not in examples_by_type["valid"]:
                    examples_by_type["valid"][resource_type] = []
                examples_by_type["valid"][resource_type].append(name)
            elif name.startswith("invalid/"):
                # Extract resource type from path: invalid/Patient/invalid-patient -> Patient
                path_parts = name.split("/")
                if len(path_parts) >= 2:
                    resource_type = path_parts[1]
                if resource_type not in examples_by_type["invalid"]:
                    examples_by_type["invalid"][resource_type] = []
                examples_by_type["invalid"][resource_type].append(name)
            else:
                # Legacy examples in root directory
                if resource_type not in examples_by_type["other"]:
                    examples_by_type["other"][resource_type] = []
                examples_by_type["other"][resource_type].append(name)
        
        resource_types["examples"] = examples_by_type
        
        # Log resource summary
        logger.info(f"Loaded resource types: FHIR Base ({len(resource_types['fhir_base'])}), PH Core ({len(ph_core_by_type)} types, {sum(len(resources) for resources in ph_core_by_type.values())} resources), Examples ({len(examples_by_type)} types, {sum(len(resources) for resources in examples_by_type.values())} resources)")
        
        return resource_types
    
    def get_resource(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific resource."""
        if category == "fhir_base":
            return self._fhir_base_resources.get(name)
        elif category == "ph_core":
            return self._ph_core_resources.get(name)
        elif category == "examples":
            return self._example_resources.get(name)
        return None
    
    def get_all_resources(self) -> Dict[str, Dict[str, Any]]:
        """Get all resources organized by category."""
        return {
            "fhir_base": self._fhir_base_resources,
            "ph_core": self._ph_core_resources,
            "examples": self._example_resources
        }
    
    def get_resource_schema(self, resource_type: str) -> Optional[Dict[str, Any]]:
        """Generate a clean JSON schema format for a FHIR resource type."""
        structure_def = self._fhir_base_resources.get(resource_type)
        if not structure_def or structure_def.get("resourceType") != "StructureDefinition":
            return None
        
        # Create a clean schema representation
        schema = {
            "resourceType": resource_type,
            "description": structure_def.get("description", ""),
            "properties": {}
        }
        
        # Extract elements from the StructureDefinition
        snapshot = structure_def.get("snapshot", {})
        elements = snapshot.get("element", [])
        
        # Process elements to create a clean schema
        for element in elements:
            path = element.get("path", "")
            
            # Skip the root element
            if path == resource_type:
                continue
                
            # Only include direct properties (not nested)
            if path.count('.') == 1 and path.startswith(f"{resource_type}."):
                property_name = path.split('.')[1]
                
                # Skip backbone elements that are too complex for basic schema
                if '[x]' in property_name:
                    property_name = property_name.replace('[x]', '')
                
                element_info = {
                    "type": self._get_element_type(element),
                    "cardinality": self._get_cardinality(element),
                    "description": element.get("short", ""),
                    "required": element.get("min", 0) > 0
                }
                
                # Add binding information for coded elements
                binding = element.get("binding")
                if binding:
                    element_info["binding"] = {
                        "strength": binding.get("strength"),
                        "valueSet": binding.get("valueSet")
                    }
                
                schema["properties"][property_name] = element_info
        
        return schema
    
    def _get_element_type(self, element: Dict[str, Any]) -> str:
        """Extract the type information from an element."""
        types = element.get("type", [])
        if not types:
            return "string"
        
        # Handle multiple types
        if len(types) == 1:
            return types[0].get("code", "string")
        else:
            return " | ".join([t.get("code", "string") for t in types])
    
    def _get_cardinality(self, element: Dict[str, Any]) -> str:
        """Get the cardinality (min..max) for an element."""
        min_val = element.get("min", 0)
        max_val = element.get("max", "*")
        return f"{min_val}..{max_val}"
    
    def get_ph_core_resource_schema(self, resource_name: str) -> Optional[Dict[str, Any]]:
        """Generate a clean JSON schema format for a PH Core StructureDefinition."""
        structure_def = self._ph_core_resources.get(resource_name)
        if not structure_def or structure_def.get("resourceType") != "StructureDefinition":
            return None
        
        # Get the base resource type
        base_resource_type = structure_def.get("type")
        if not base_resource_type:
            return None
        
        # Create a clean schema representation
        schema = {
            "resourceType": base_resource_type,
            "profileName": structure_def.get("title", structure_def.get("name", resource_name)),
            "profileUrl": structure_def.get("url", ""),
            "description": structure_def.get("description", ""),
            "baseDefinition": structure_def.get("baseDefinition", ""),
            "properties": {},
            "ph_core_extensions": [],
            "ph_core_constraints": []
        }
        
        # Get the FHIR base schema for this resource type to use as foundation
        base_schema = self.get_resource_schema(base_resource_type)
        if base_schema and base_schema.get("properties"):
            schema["properties"] = base_schema["properties"].copy()
        
        # Process differential elements to show PH Core specific changes
        differential = structure_def.get("differential", {})
        elements = differential.get("element", [])
        
        for element in elements:
            path = element.get("path", "")
            element_id = element.get("id", "")
            
            # Skip the root element
            if path == base_resource_type:
                continue
            
            # Handle extensions
            if "extension" in path and "sliceName" in element:
                slice_name = element.get("sliceName")
                extension_info = {
                    "name": slice_name,
                    "path": path,
                    "cardinality": self._get_cardinality(element),
                    "description": element.get("short", element.get("definition", "")),
                    "required": element.get("min", 0) > 0,
                    "type": "Extension"
                }
                
                # Add profile information if available
                element_type = element.get("type", [])
                if element_type and len(element_type) > 0:
                    profiles = element_type[0].get("profile", [])
                    if profiles:
                        extension_info["profile"] = profiles[0]
                
                schema["ph_core_extensions"].append(extension_info)
            
            # Handle identifier slices
            elif "identifier" in path and "sliceName" in element:
                slice_name = element.get("sliceName")
                constraint_info = {
                    "name": slice_name,
                    "path": path,
                    "cardinality": self._get_cardinality(element),
                    "description": element.get("short", element.get("definition", "")),
                    "required": element.get("min", 0) > 0,
                    "type": "Identifier Slice"
                }
                schema["ph_core_constraints"].append(constraint_info)
            
            # Handle other constraints and modifications
            elif path.count('.') == 1 and path.startswith(f"{base_resource_type}."):
                property_name = path.split('.')[1]
                
                # Update existing property or add new one
                if property_name in schema["properties"]:
                    # Update existing property with PH Core constraints
                    prop_info = schema["properties"][property_name]
                    
                    # Update cardinality if specified
                    if "min" in element or "max" in element:
                        prop_info["cardinality"] = self._get_cardinality(element)
                        prop_info["required"] = element.get("min", 0) > 0
                    
                    # Update type constraints if specified
                    element_type = element.get("type", [])
                    if element_type:
                        if len(element_type) == 1:
                            type_info = element_type[0]
                            if "profile" in type_info:
                                # Handle profile as list or string
                                profiles = type_info["profile"]
                                if isinstance(profiles, list) and len(profiles) > 0:
                                    prop_info["ph_core_profile"] = profiles[0] if len(profiles) == 1 else profiles
                                elif isinstance(profiles, str):
                                    prop_info["ph_core_profile"] = profiles
                        prop_info["type"] = self._get_element_type(element)
                    
                    # Update binding if specified
                    binding = element.get("binding")
                    if binding:
                        prop_info["binding"] = {
                            "strength": binding.get("strength"),
                            "valueSet": binding.get("valueSet")
                        }
                    
                    # Add PH Core specific description
                    if element.get("short") or element.get("definition"):
                        prop_info["ph_core_description"] = element.get("short", element.get("definition", ""))
                else:
                    # Add new property specific to PH Core
                    element_info = {
                        "type": self._get_element_type(element),
                        "cardinality": self._get_cardinality(element),
                        "description": element.get("short", element.get("definition", "")),
                        "required": element.get("min", 0) > 0,
                        "ph_core_specific": True
                    }
                    
                    # Add binding information for coded elements
                    binding = element.get("binding")
                    if binding:
                        element_info["binding"] = {
                            "strength": binding.get("strength"),
                            "valueSet": binding.get("valueSet")
                        }
                    
                    schema["properties"][property_name] = element_info
        
        return schema
    
    def get_enhanced_codesystem_display(self, codesystem: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enhanced display information for a PH Core CodeSystem."""
        enhanced = {
            "resourceType": "CodeSystem",
            "name": codesystem.get("name", ""),
            "title": codesystem.get("title", ""),
            "description": codesystem.get("description", ""),
            "url": codesystem.get("url", ""),
            "status": codesystem.get("status", ""),
            "content": codesystem.get("content", ""),
            "caseSensitive": codesystem.get("caseSensitive", False),
            "count": codesystem.get("count", 0),
            "concepts": [],
            "usage_context": "Philippines Healthcare Context"
        }
        
        # Process concepts
        concepts = codesystem.get("concept", [])
        for concept in concepts:
            concept_info = {
                "code": concept.get("code", ""),
                "display": concept.get("display", ""),
                "definition": concept.get("definition", "")
            }
            enhanced["concepts"].append(concept_info)
        
        return enhanced
    
    def get_enhanced_valueset_display(self, valueset: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enhanced display information for a PH Core ValueSet."""
        enhanced = {
            "resourceType": "ValueSet",
            "name": valueset.get("name", ""),
            "title": valueset.get("title", ""),
            "description": valueset.get("description", ""),
            "url": valueset.get("url", ""),
            "status": valueset.get("status", ""),
            "experimental": valueset.get("experimental", False),
            "compose": valueset.get("compose", {}),
            "included_concepts": [],
            "referenced_codesystems": [],
            "usage_context": "Philippines Healthcare Context"
        }
        
        # Process compose includes
        compose = valueset.get("compose", {})
        includes = compose.get("include", [])
        
        for include in includes:
            system = include.get("system", "")
            if system:
                enhanced["referenced_codesystems"].append(system)
            
            # Get concepts from this include
            concepts = include.get("concept", [])
            for concept in concepts:
                concept_info = {
                    "code": concept.get("code", ""),
                    "display": concept.get("display", ""),
                    "system": system
                }
                enhanced["included_concepts"].append(concept_info)
        
        return enhanced
    
    def get_enhanced_namingsystem_display(self, namingsystem: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enhanced display information for a PH Core NamingSystem."""
        enhanced = {
            "resourceType": "NamingSystem",
            "name": namingsystem.get("name", ""),
            "description": namingsystem.get("description", ""),
            "kind": namingsystem.get("kind", ""),
            "status": namingsystem.get("status", ""),
            "date": namingsystem.get("date", ""),
            "publisher": namingsystem.get("publisher", ""),
            "jurisdiction": namingsystem.get("jurisdiction", []),
            "unique_ids": [],
            "usage_context": "Philippines Healthcare Context"
        }
        
        # Process unique IDs
        unique_ids = namingsystem.get("uniqueId", [])
        for uid in unique_ids:
            uid_info = {
                "type": uid.get("type", ""),
                "value": uid.get("value", ""),
                "preferred": uid.get("preferred", False),
                "comment": uid.get("comment", "")
            }
            enhanced["unique_ids"].append(uid_info)
        
        return enhanced
    
    def get_enhanced_example_display(self, resource: Dict[str, Any], resource_name: str) -> Dict[str, Any]:
        """Generate enhanced display information for examples."""
        resource_type = resource.get("resourceType", "Unknown")
        
        # Determine validation status and context from resource name
        is_valid = resource_name.startswith("valid/")
        is_invalid = resource_name.startswith("invalid/")
        is_ph_core = False
        
        # Check if this is a PH Core example
        meta = resource.get("meta", {})
        profiles = meta.get("profile", [])
        for profile in profiles:
            if "ph-core" in profile or "https://wah4pc-validation.echosphere.cfd" in profile:
                is_ph_core = True
                break
        
        enhanced = {
            "resourceType": resource_type,
            "title": f"{resource_type} Example",
            "description": f"Example {resource_type} resource",
            "profile_urls": [],
            "ph_core_features": [],
            "validation_status": "Unknown",
            "validation_category": "Unknown",
            "usage_context": "FHIR Healthcare Context",
            "validation_issues": []
        }
        
        # Set validation status based on folder structure
        if is_valid:
            enhanced["validation_status"] = "Valid Example"
            enhanced["validation_category"] = "valid"
            enhanced["description"] = f"Valid example {resource_type} resource demonstrating proper FHIR structure"
        elif is_invalid:
            enhanced["validation_status"] = "Invalid Example"
            enhanced["validation_category"] = "invalid"
            enhanced["description"] = f"Invalid example {resource_type} resource demonstrating common validation errors"
            enhanced["validation_issues"] = self._analyze_validation_issues(resource)
        else:
            enhanced["validation_status"] = "Standard Example"
            enhanced["validation_category"] = "other"
        
        # Update context if PH Core
        if is_ph_core:
            enhanced["usage_context"] = "Philippines Healthcare Context"
            if is_valid:
                enhanced["description"] = f"Valid example {resource_type} resource conforming to PH Core profiles"
        
        # Extract profile information from meta
        meta = resource.get("meta", {})
        profiles = meta.get("profile", [])
        for profile in profiles:
            if "ph-core" in profile or "https://wah4pc-validation.echosphere.cfd" in profile:
                enhanced["profile_urls"].append(profile)
        
        # Identify PH Core specific features
        if resource_type == "Patient":
            # Look for PH Core extensions
            extensions = resource.get("extension", [])
            for ext in extensions:
                url = ext.get("url", "")
                if "indigenous-people" in url:
                    enhanced["ph_core_features"].append("Indigenous People Extension")
                elif "indigenous-group" in url:
                    enhanced["ph_core_features"].append("Indigenous Group Extension")
                elif "patient-nationality" in url:
                    enhanced["ph_core_features"].append("Nationality Extension")
                elif "patient-religion" in url:
                    enhanced["ph_core_features"].append("Religion Extension")
                elif "race" in url:
                    enhanced["ph_core_features"].append("Race Extension")
            
            # Look for PhilHealth ID
            identifiers = resource.get("identifier", [])
            for identifier in identifiers:
                system = identifier.get("system", "")
                if "philhealth" in system.lower():
                    enhanced["ph_core_features"].append("PhilHealth ID")
        
        elif resource_type == "Address":
            # Look for PSGC extensions
            extensions = resource.get("extension", [])
            for ext in extensions:
                url = ext.get("url", "")
                if "city-municipality" in url:
                    enhanced["ph_core_features"].append("PSGC City/Municipality")
                elif "province" in url:
                    enhanced["ph_core_features"].append("PSGC Province")
                elif "barangay" in url:
                    enhanced["ph_core_features"].append("PSGC Barangay")
        
        # Set validation status based on profile compliance
        if enhanced["profile_urls"]:
            enhanced["validation_status"] = "PH Core Compliant"
        else:
            enhanced["validation_status"] = "Standard FHIR"
        
        return enhanced
    
    def _analyze_validation_issues(self, resource: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze common validation issues in invalid examples."""
        issues = []
        
        # Check for common issues
        if resource.get("active") and not isinstance(resource.get("active"), bool):
            issues.append({
                "severity": "error",
                "field": "active",
                "issue": "Boolean field contains non-boolean value",
                "value": str(resource.get("active"))
            })
        
        # Check for invalid dates
        date_fields = ["birthDate", "deceasedDateTime"]
        for field in date_fields:
            if field in resource:
                value = resource[field]
                if isinstance(value, str) and not self._is_valid_date_format(value):
                    issues.append({
                        "severity": "error",
                        "field": field,
                        "issue": "Invalid date format",
                        "value": value
                    })
        
        # Check for invalid enums
        if "gender" in resource:
            valid_genders = ["male", "female", "other", "unknown"]
            if resource["gender"] not in valid_genders:
                issues.append({
                    "severity": "error",
                    "field": "gender",
                    "issue": f"Invalid gender value. Must be one of: {', '.join(valid_genders)}",
                    "value": resource["gender"]
                })
        
        # Check for empty required fields
        identifiers = resource.get("identifier", [])
        for i, identifier in enumerate(identifiers):
            if identifier.get("system") == "":
                issues.append({
                    "severity": "error",
                    "field": f"identifier[{i}].system",
                    "issue": "Empty system value in identifier",
                    "value": ""
                })
        
        # Check for invalid references
        reference_fields = ["subject", "performer", "generalPractitioner"]
        for field in reference_fields:
            if field in resource:
                ref_value = resource[field]
                if isinstance(ref_value, dict) and ref_value.get("reference"):
                    ref = ref_value["reference"]
                    if not self._is_valid_reference_format(ref):
                        issues.append({
                            "severity": "warning",
                            "field": field,
                            "issue": "Invalid reference format",
                            "value": ref
                        })
        
        return issues
    
    def _is_valid_date_format(self, date_str: str) -> bool:
        """Check if a string is in valid FHIR date format."""
        import re
        # Basic FHIR date patterns
        patterns = [
            r'^\d{4}$',  # YYYY
            r'^\d{4}-\d{2}$',  # YYYY-MM
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?([+-]\d{2}:\d{2}|Z)?$'  # DateTime
        ]
        return any(re.match(pattern, date_str) for pattern in patterns)
    
    def _is_valid_reference_format(self, ref: str) -> bool:
        """Check if a reference string is in valid FHIR format."""
        import re
        # ResourceType/id or relative/absolute URLs
        patterns = [
            r'^[A-Z][a-zA-Z]+/[A-Za-z0-9\-\.]{1,64}$',  # ResourceType/id
            r'^https?://.*',  # Absolute URL
            r'^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'  # UUID
        ]
        return any(re.match(pattern, ref) for pattern in patterns)


# Initialize the browser
resource_browser = FHIRResourceBrowser()


@web_router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with resource overview."""
    # Reload resources to get the latest counts from filesystem
    resource_browser.reload_resources()
    resource_types = resource_browser.get_resource_types()
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "resource_types": resource_types,
            "title": "FHIR Resource Browser"
        }
    )


@web_router.get("/resources/{category}", response_class=HTMLResponse)
async def list_resources(request: Request, category: str):
    """List resources by category."""
    if category not in ["fhir_base", "ph_core", "examples"]:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Always reload resources to get the latest from filesystem (real-time)
    resource_browser.reload_resources()
    resource_types = resource_browser.get_resource_types()
    category_resources = resource_types.get(category, {})
    
    # For examples, check if completely empty
    is_empty = False
    if category == "examples":
        total_examples = 0
        if isinstance(category_resources, dict):
            for validity_type, resource_types_dict in category_resources.items():
                if isinstance(resource_types_dict, dict):
                    total_examples += sum(len(examples) for examples in resource_types_dict.values())
                else:
                    total_examples += len(resource_types_dict) if resource_types_dict else 0
        is_empty = total_examples == 0
    
    return templates.TemplateResponse(
        "resource_list.html",
        {
            "request": request,
            "category": category,
            "resources": category_resources,
            "is_empty": is_empty,
            "title": f"{category.replace('_', ' ').title()} Resources"
        }
    )


@web_router.get("/resources/examples/{validity}/{resource_type}/{example_name}", response_class=HTMLResponse)
async def view_nested_example(request: Request, validity: str, resource_type: str, example_name: str):
    """View a specific nested example (valid/invalid/resource_type/example)."""
    if validity not in ["valid", "invalid"]:
        raise HTTPException(status_code=404, detail="Invalid validity type")
    
    # Construct the full resource name path
    full_resource_name = f"{validity}/{resource_type}/{example_name}"
    
    # Always reload resources to get the latest from filesystem (real-time)
    resource_browser.reload_resources()
    resource = resource_browser.get_resource("examples", full_resource_name)
    if not resource:
        raise HTTPException(status_code=404, detail="Example not found")
    
    # Show enhanced example display with validation info
    enhanced_example = resource_browser.get_enhanced_example_display(resource, full_resource_name)
    if enhanced_example:
        resource_json = json.dumps(resource, indent=2, ensure_ascii=False)
        return templates.TemplateResponse(
            "ph_core_example.html",
            {
                "request": request,
                "category": "examples",
                "resource_name": full_resource_name,
                "resource": resource,
                "enhanced_info": enhanced_example,
                "resource_json": resource_json,
                "title": f"{enhanced_example.get('title', example_name)} - Example"
            }
        )
    
    # Fallback to regular detail view
    resource_json = json.dumps(resource, indent=2, ensure_ascii=False)
    return templates.TemplateResponse(
        "resource_detail.html",
        {
            "request": request,
            "category": "examples",
            "resource_name": full_resource_name,
            "resource": resource,
            "resource_json": resource_json,
            "title": f"{example_name} - Example"
        }
    )


@web_router.get("/resources/examples/{resource_type}", response_class=HTMLResponse)
async def list_examples_by_type(request: Request, resource_type: str):
    """List examples by resource type."""
    # Always reload resources to get the latest from filesystem (real-time)
    resource_browser.reload_resources()
    resource_types = resource_browser.get_resource_types()
    examples = resource_types.get("examples", {})
    
    # Collect all examples for this resource type
    type_examples = {
        "valid": examples.get("valid", {}).get(resource_type, []),
        "invalid": examples.get("invalid", {}).get(resource_type, []),
        "other": examples.get("other", {}).get(resource_type, [])
    }
    
    # Always return the template, even if empty (let template handle empty state)
    return templates.TemplateResponse(
        "examples_by_type.html",
        {
            "request": request,
            "resource_type": resource_type,
            "examples": type_examples,
            "title": f"{resource_type} Examples"
        }
    )


@web_router.get("/resources/{category}/{resource_name}", response_class=HTMLResponse)
async def view_resource(request: Request, category: str, resource_name: str):
    """View a specific resource."""
    if category not in ["fhir_base", "ph_core", "examples"]:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Reload resources to get the latest from filesystem
    resource_browser._load_resources()
    resource = resource_browser.get_resource(category, resource_name)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # For FHIR base resources, show clean schema instead of raw StructureDefinition
    if category == "fhir_base" and resource.get("resourceType") == "StructureDefinition":
        schema = resource_browser.get_resource_schema(resource_name)
        if schema:
            resource_json = json.dumps(schema, indent=2, ensure_ascii=False)
            return templates.TemplateResponse(
                "resource_schema.html",
                {
                    "request": request,
                    "category": category,
                    "resource_name": resource_name,
                    "resource": schema,
                    "resource_json": resource_json,
                    "title": f"{resource_name} Schema - FHIR Resource"
                }
            )
    
    # For PH Core resources, show enhanced displays based on resource type
    if category == "ph_core":
        resource_type = resource.get("resourceType")
        
        # StructureDefinitions - show clean schema instead of raw StructureDefinition
        if resource_type == "StructureDefinition":
            schema = resource_browser.get_ph_core_resource_schema(resource_name)
            if schema:
                resource_json = json.dumps(schema, indent=2, ensure_ascii=False)
                return templates.TemplateResponse(
                    "ph_core_schema.html",
                    {
                        "request": request,
                        "category": category,
                        "resource_name": resource_name,
                        "resource": schema,
                        "resource_json": resource_json,
                        "title": f"{resource.get('title', resource_name)} - PH Core Profile"
                    }
                )
        
        # CodeSystems - show enhanced code system display
        elif resource_type == "CodeSystem":
            enhanced_codesystem = resource_browser.get_enhanced_codesystem_display(resource)
            if enhanced_codesystem:
                resource_json = json.dumps(enhanced_codesystem, indent=2, ensure_ascii=False)
                return templates.TemplateResponse(
                    "ph_core_codesystem.html",
                    {
                        "request": request,
                        "category": category,
                        "resource_name": resource_name,
                        "resource": enhanced_codesystem,
                        "resource_json": resource_json,
                        "title": f"{resource.get('title', resource_name)} - PH Core CodeSystem"
                    }
                )
        
        # ValueSets - show enhanced value set display
        elif resource_type == "ValueSet":
            enhanced_valueset = resource_browser.get_enhanced_valueset_display(resource)
            if enhanced_valueset:
                resource_json = json.dumps(enhanced_valueset, indent=2, ensure_ascii=False)
                return templates.TemplateResponse(
                    "ph_core_valueset.html",
                    {
                        "request": request,
                        "category": category,
                        "resource_name": resource_name,
                        "resource": enhanced_valueset,
                        "resource_json": resource_json,
                        "title": f"{resource.get('title', resource_name)} - PH Core ValueSet"
                    }
                )
        
        # NamingSystems - show enhanced naming system display
        elif resource_type == "NamingSystem":
            enhanced_namingsystem = resource_browser.get_enhanced_namingsystem_display(resource)
            if enhanced_namingsystem:
                resource_json = json.dumps(enhanced_namingsystem, indent=2, ensure_ascii=False)
                return templates.TemplateResponse(
                    "ph_core_namingsystem.html",
                    {
                        "request": request,
                        "category": category,
                        "resource_name": resource_name,
                        "resource": enhanced_namingsystem,
                        "resource_json": resource_json,
                        "title": f"{resource.get('name', resource_name)} - PH Core NamingSystem"
                    }
                )
        
        # Examples and other resources - show enhanced example display with validation info
        else:
            enhanced_example = resource_browser.get_enhanced_example_display(resource, resource_name)
            if enhanced_example:
                resource_json = json.dumps(resource, indent=2, ensure_ascii=False)
                return templates.TemplateResponse(
                    "ph_core_example.html",
                    {
                        "request": request,
                        "category": category,
                        "resource_name": resource_name,
                        "resource": resource,
                        "enhanced_info": enhanced_example,
                        "resource_json": resource_json,
                        "title": f"{enhanced_example.get('title', resource_name)} - PH Core Example"
                    }
                )
    
    # For PH Core and Examples, show the actual resource
    resource_json = json.dumps(resource, indent=2, ensure_ascii=False)
    
    return templates.TemplateResponse(
        "resource_detail.html",
        {
            "request": request,
            "category": category,
            "resource_name": resource_name,
            "resource": resource,
            "resource_json": resource_json,
            "title": f"{resource_name} - {category.replace('_', ' ').title()}"
        }
    )


@web_router.get("/reload", response_class=HTMLResponse)
async def reload_resources_endpoint(request: Request):
    """Manually reload resources and redirect to home."""
    resource_browser.reload_resources()
    return RedirectResponse(url="/", status_code=302)


@web_router.get("/search", response_class=HTMLResponse)
async def search_resources(request: Request, q: Optional[str] = None):
    """Search resources."""
    results = []
    if q:
        # Reload resources to get the latest from filesystem
        resource_browser.reload_resources()
        q_lower = q.lower()
        all_resources = resource_browser.get_all_resources()
        
        for category, resources in all_resources.items():
            for name, resource in resources.items():
                if (q_lower in name.lower() or 
                    q_lower in str(resource.get("resourceType", "")).lower() or
                    q_lower in str(resource.get("title", "")).lower() or
                    q_lower in str(resource.get("description", "")).lower()):
                    results.append({
                        "category": category,
                        "name": name,
                        "resource_type": resource.get("resourceType", "Unknown"),
                        "title": resource.get("title", name),
                        "description": resource.get("description", "")
                    })
    
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "query": q or "",
            "results": results,
            "title": f"Search Results for '{q}'" if q else "Search Resources"
        }
    )
