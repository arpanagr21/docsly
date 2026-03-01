from typing import Optional, Any
import jsonschema


def validate_component_schema(schema: dict) -> Optional[str]:
    """Validate that a component schema is a valid JSON Schema."""
    required_fields = ["type", "properties"]

    if not isinstance(schema, dict):
        return "Schema must be an object"

    if schema.get("type") != "object":
        return "Schema type must be 'object'"

    if "properties" not in schema:
        return "Schema must have 'properties' field"

    if not isinstance(schema["properties"], dict):
        return "Schema properties must be an object"

    return None


def validate_props(props: dict, schema: dict) -> Optional[str]:
    """Validate component props against its JSON schema."""
    try:
        jsonschema.validate(instance=props, schema=schema)
        return None
    except jsonschema.ValidationError as e:
        return str(e.message)
    except jsonschema.SchemaError as e:
        return f"Invalid schema: {e.message}"
