"""
A command-line utility to validate a FHIR JSON resource using the validation server.

Usage:
    python validator.py <path_to_fhir_resource.json>
"""

import sys
import json
import requests

# The URL of the local validation server
VALIDATION_URL = "http://localhost:8000/api/v1/validate"


def validate_fhir_resource(file_path: str):
    """
    Reads a FHIR resource from a file and sends it to the validation server.

    Args:
        file_path (str): The path to the JSON file containing the FHIR resource.
    """
    print(f"▶️  Validating resource from: {file_path}")

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

    # 2. Construct the request payload
    payload = {
        "resource": resource_data,
        "validate_code_systems": True,
        "validate_value_sets": True
    }

    # 3. Send the POST request to the server
    try:
        print(f"▶️  Sending request to: {VALIDATION_URL}")
        response = requests.post(VALIDATION_URL, json=payload, timeout=30)
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
    if len(sys.argv) != 2:
        print("Usage: python validator.py <path_to_fhir_resource.json>")
        sys.exit(1)

    file_to_validate = sys.argv[1]
    validate_fhir_resource(file_to_validate)
