"""Validate structured responses without resolving external schema references."""

import json
from copy import deepcopy

from jsonschema import validators


def validate_schema(schema):
    # A schema supplied by application code must never fetch a remote document.
    def check_refs(node):
        if isinstance(node, dict):
            for key in ("$ref", "$dynamicRef", "$recursiveRef"):
                if key in node and not node[key].startswith("#"):
                    raise ValueError("External JSON schema references are unsupported")
            for item in node.values():
                check_refs(item)
        elif isinstance(node, list):
            for item in node:
                check_refs(item)

    check_refs(schema)
    validator = validators.validator_for(schema)
    validator.check_schema(schema)
    return validator(schema)


def validate_json(text: str, schema: dict | None = None):
    try:
        value = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise ValueError("AI response is not valid JSON") from exc
    if schema is not None:
        if not validate_schema(schema).is_valid(value):
            # ValidationError messages can contain document text. Keep diagnostics content-free.
            raise ValueError("AI response does not match the requested JSON schema")
    return value


def codex_output_schema(schema):
    """Adapt finite object schemas to the CLI's strict structured-output subset.

    Optional properties use null on the wire and are omitted again before local
    validation. Open-ended maps/references use prompted JSON plus local validation.
    """
    validate_schema(schema)
    result = deepcopy(schema)

    def normalize(node):
        if not isinstance(node, dict):
            return True
        if any(key in node for key in ("$ref", "$dynamicRef", "$recursiveRef")):
            return False
        if node.get("type") == "object" or "properties" in node:
            if "additionalProperties" in node and node["additionalProperties"] is not False:
                return False
            if "properties" not in node:
                return False
            properties = node["properties"]
            required = node.get("required", [])
            for key, prop in list(properties.items()):
                if not normalize(prop):
                    return False
                if key not in required:
                    properties[key] = {"anyOf": [prop, {"type": "null"}]}
            node["required"] = list(properties)
            node["additionalProperties"] = False
        for key in ("items",):
            if key in node and not normalize(node[key]):
                return False
        for key in ("anyOf", "oneOf", "allOf", "prefixItems"):
            if any(not normalize(part) for part in node.get(key, [])):
                return False
        return True

    return result if normalize(result) else None


def omit_optional_nulls(value, schema):
    if not isinstance(schema, dict):
        return value
    root_validator = validate_schema(schema)

    def clean(item, node):
        if not isinstance(node, dict):
            return item
        # Pydantic's tool envelopes namespace references under the root $defs.
        # Detached branch validators lose that root and fail on otherwise valid
        # budget/tool calls. Resolve local pointers for cleanup and preserve the
        # root resolver when selecting an anyOf/oneOf branch.
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            target = schema
            try:
                for token in ref[2:].split("/"):
                    target = target[token.replace("~1", "/").replace("~0", "~")]
            except (KeyError, TypeError):
                raise ValueError("Local JSON schema reference is unresolved") from None
            if target is not node:
                return clean(item, target)
        for keyword in ("anyOf", "oneOf"):
            for branch in node.get(keyword, []):
                candidate = clean(item, branch)
                if root_validator.evolve(schema=branch).is_valid(candidate):
                    return candidate
        for branch in node.get("allOf", []):
            item = clean(item, branch)
        if isinstance(item, dict):
            required = node.get("required", [])
            properties = node.get("properties", {})
            return {
                key: clean(entry, properties.get(key, {}))
                for key, entry in item.items()
                if not (key in properties and key not in required and entry is None)
            }
        if isinstance(item, list):
            return [clean(entry, node.get("items", {})) for entry in item]
        return item

    return clean(value, schema)
