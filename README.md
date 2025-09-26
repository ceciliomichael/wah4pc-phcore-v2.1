# FHIR Validation Server

A universal FHIR (Fast Healthcare Interoperability Resources) validation server with Swagger API documentation.

## Features

- **Universal FHIR Validation**: Validate FHIR resources against base FHIR R4 specification
- **Swagger/OpenAPI Documentation**: Interactive API documentation and testing interface
- **Batch Validation**: Validate multiple resources in a single request
- **Resource Type Discovery**: Get information about supported FHIR resource types
- **Profile Support**: Validation against specific FHIR profiles
- **Health Monitoring**: Built-in health check endpoints
- **CORS Support**: Cross-origin resource sharing for web applications

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Server**:
   ```bash
   python main.py
   ```

3. **Access the API**:
   - Swagger UI: https://wah4pc-validation.echosphere.cfd/docs
   - ReDoc: https://wah4pc-validation.echosphere.cfd/redoc
   - API Base URL: https://wah4pc-validation.echosphere.cfd/api/v1

## API Endpoints

### Validation
- `POST /api/v1/validate` - Validate a single FHIR resource
- `POST /api/v1/validate/batch` - Validate multiple FHIR resources

### Information
- `GET /api/v1/resource-types` - Get supported FHIR resource types
- `GET /api/v1/profile/{resource_type}` - Get profile for specific resource type
- `GET /api/v1/server-info` - Get server information

### Health
- `GET /api/v1/health` - Health check endpoint

## Example Usage

### Validate a Patient Resource

```bash
curl -X POST "https://wah4pc-validation.echosphere.cfd/api/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
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
    }
  }'
```

### Response Format

```json
{
  "validation_result": {
    "status": "success",
    "message": "Validation successful",
    "issues": [],
    "resource_type": "Patient",
    "valid": true
  },
  "processed_at": "2025-09-24T10:30:00.000Z",
  "processing_time_ms": 45
}
```

## Project Structure

```
src/
├── constants/          # Application constants and configuration
├── lib/               # Core libraries and utilities
├── types/             # Type definitions and data models
├── ui/                # API endpoints and interface layer
└── utils/             # Utility functions and helpers

resources/             # FHIR base resources and schemas
main.py               # Application entry point
requirements.txt      # Python dependencies
```

## Configuration

The server loads FHIR base resources from the `resources/fhir_base/` directory:
- FHIR schemas and structure definitions
- Resource profiles and extensions
- Value sets and code systems
- Search parameters and concept maps

## Development

The server is built with:
- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic**: Data validation and settings management
- **jsonschema**: JSON Schema validation
- **uvicorn**: ASGI server implementation

## License

MIT License
