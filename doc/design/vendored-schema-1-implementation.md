# Vendored Schema Implementation

This document outlines the implementation of the vendored schema solution described in [vendored-schema-1.md](./vendored-schema-1.md).

## Problem

As described in the design document, the current approach has the following issues:

1. We do not actually support or use multiple versions of the schema in dandi-archive
2. We use two instantiations of the schema and rely on an external process to generate JSONSchema from Pydantic models
3. We manually trigger updates of web frontend files according to a specific version of the schema
4. We hardcoded vendorization inside the dandi-archive codebase (backend and frontend)
5. Any vendorization done via Configuration at runtime for Pydantic is not reflected in the JSONSchema serialization used by the web frontend since it's loaded from a generic serialization

## Solution Implementation

The implemented solution addresses these issues by:

1. Creating an API endpoint to dynamically generate JSONSchema from the Pydantic models at runtime
2. Updating the info endpoint to point to our local schema endpoint instead of GitHub
3. Implementing proper serialization using Pydantic's TypeAdapter to generate the JSONSchema

### New Endpoints

We've added the following API endpoints:

- `/api/schemas/available/` - Returns the list of available schema models that can be used as a query parameter value for the `/api/schemas/` endpoint
- `/api/schemas/` - Returns the JSONSchema for a queried model specified with the `model` query parameter (e.g., `?model=Dandiset`)

These endpoints use Pydantic's TypeAdapter to generate the JSONSchema directly from the models, ensuring that any runtime vendorization or customization is reflected in the schema.

### Updated Info Endpoint

The `/api/info/` endpoint has been updated to point to our local schema endpoint instead of the GitHub URL. This ensures that frontend clients like the web UI use the schema that matches the running backend exactly, including any vendorization.

### Benefits

This implementation provides several benefits:

1. **Runtime Consistency**: The schema used by the frontend will always match the one used by the backend, including any vendorization or customizations.
2. **Simplified Deployment**: No need to manually update schema files or manage separate repositories for schema serialization.
3. **Future-Proofing**: The implementation allows for future support of multiple schema versions if needed.
4. **Reduced Dependencies**: Removes the dependency on external GitHub URLs for schema definitions.

### Future Considerations

While the current implementation only supports the currently configured schema version, the endpoint structure allows for future extension to support multiple versions if needed. This would require additional changes to store and serve historical schema versions.

Additionally, the JSON-LD context.json could also be similarly generated and served by the backend if needed in the future.
