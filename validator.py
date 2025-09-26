"""
A command-line utility to validate a FHIR JSON resource using the validation server.

Usage:
    python validator.py <path_to_fhir_resource.json>
"""

import sys
import json
import requests

# The URL of the local validation server (PH-Core STRICT validation)
VALIDATION_URL = "http://localhost:6789/api/v1/validate/ph-core"
STANDARD_VALIDATION_URL = "http://localhost:6789/api/v1/validate"


def validate_fhir_resource(file_path: str, use_ph_core: bool = True):
    """
    Reads a FHIR resource from a file and sends it to the validation server.

    Args:
        file_path (str): The path to the JSON file containing the FHIR resource.
        use_ph_core (bool): Whether to use PH-Core strict validation (default: True)
    """
    if use_ph_core:
        print(f"▶️  PH-CORE STRICT VALIDATION for: {file_path}")
        print("⚠️  This validates against BOTH FHIR R4 AND PH-Core Implementation Guide")
        print("   Resources MUST comply with PH-Core requirements or validation will FAIL")
        validation_url = VALIDATION_URL
    else:
        print(f"▶️  STANDARD FHIR VALIDATION for: {file_path}")
        print("ℹ️  This validates against FHIR R4 specification only (no PH-Core requirements)")
        validation_url = STANDARD_VALIDATION_URL

    # 1. Read and parse the JSON file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            resource_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found at '{file_path}'")
        return
    except json.JSONDecodeError:
        print(f"❌ Error: The file at '{file_path}' is not a valid JSON file.")
        return
    except Exception as e:
        print(f"❌ Error: An unexpected error occurred while reading the file: {e}")
        return

    # 2. Construct the request payload (PH-Core endpoint doesn't need these flags)
    payload = {
        "resource": resource_data,
        "validate_code_systems": True,
        "validate_value_sets": True
    }

    # 3. Send the POST request to the server
    try:
        print(f"▶️  Sending request to: {validation_url}")
        response = requests.post(validation_url, json=payload, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Could not connect to the validation server.")
        print("   Please ensure the server is running with 'python main.py'")
        return
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code} {e.response.reason}")
        print("   Server response:")
        print(json.dumps(e.response.json(), indent=2))
        return
    except requests.exceptions.RequestException as e:
        print(f"\n❌ An unexpected request error occurred: {e}")
        return

    # 4. Pretty-print the validation result
    print("\n✅ Validation Complete! Server response:")
    print("-----------------------------------------")
    response_json = response.json()
    print(json.dumps(response_json, indent=2))
    print("-----------------------------------------")

    # Summarize the result
    result = response_json.get("validation_result", {})
    status = result.get("status", "unknown").upper()
    message = result.get("message", "No message provided.")
    print(f"\nSummary: [{status}] - {message}")


if __name__ == "__main__":
    # Check for the file path argument
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python validator.py <path_to_fhir_resource.json> [--standard]")
        print("  By default: PH-Core STRICT validation (FHIR + PH-Core compliance required)")
        print("  With --standard: Standard FHIR validation only (no PH-Core requirements)")
        sys.exit(1)

    file_to_validate = sys.argv[1]
    use_ph_core = True
    
    if len(sys.argv) == 3 and sys.argv[2] == "--standard":
        use_ph_core = False
    
    validate_fhir_resource(file_to_validate, use_ph_core)
