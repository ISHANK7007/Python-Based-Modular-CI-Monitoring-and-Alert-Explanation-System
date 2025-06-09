import yaml
import os

# Schema definition for config.yaml validation
CONFIG_SCHEMA = {
    "exports": {
        "default_export_format": str,
        "default_filters": {
            "min_confidence": float,
            "categories": list,
            "max_results": int,
        },
        "presentation": {
            "theme_mode": str,
            "color_output": bool,
            "detail_level": str,
        },
        "cli": {
            "interactive": bool,
            "progress_bar": bool,
            "result_pagination": int,
        },
        "batch": {
            "summary_header": bool,
            "include_metadata": bool,
            "file_naming_pattern": str,
        },
    }
}

def validate_config(config: dict, schema: dict = CONFIG_SCHEMA) -> list:
    """Validates the config dictionary against the expected schema."""
    errors = []

    def _validate(d, s, path="root"):
        for key, expected_type in s.items():
            full_path = f"{path}.{key}"
            if key not in d:
                errors.append(f"Missing key: {full_path}")
            elif isinstance(expected_type, dict):
                if not isinstance(d[key], dict):
                    errors.append(f"{full_path} should be a dict.")
                else:
                    _validate(d[key], expected_type, full_path)
            elif not isinstance(d[key], expected_type):
                errors.append(f"{full_path} should be of type {expected_type.__name__}, got {type(d[key]).__name__}")

    _validate(config, schema)
    return errors
