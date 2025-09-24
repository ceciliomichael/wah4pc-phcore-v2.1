# Implementation Guides

This folder contains FHIR Implementation Guides (IGs) that define specific profiles, extensions, and constraints for Philippines healthcare use cases.

## Folder Structure

```
implementation_guides/
├── README.md                    # This file
└── ph_core/                     # Philippines Core Implementation Guide
```

## Philippines Core Implementation Guide

### PH Core
- **Purpose**: Base profiles for Philippines healthcare
- **Use Cases**: Philippines healthcare interoperability
- **Key Resources**: PH Core Patient, Practitioner, Organization profiles
- **Jurisdiction**: Philippines (PH)

## Adding New Implementation Guides

1. Create a new folder with a descriptive name
2. Include the IG package files (package.json, profiles, etc.)
3. Add a README.md describing the IG purpose and usage
4. Update this main README.md to document the new IG

## Usage in Validation

Implementation Guides can be loaded by the validation server to:
- Validate resources against specific profiles
- Check conformance to jurisdictional requirements
- Enforce custom business rules
- Validate extensions and value sets

Example validation with PH Core profile:
```bash
python validator.py resources/examples/patient.json --profile "http://fhir.org.ph/core/StructureDefinition/ph-core-patient"
```
