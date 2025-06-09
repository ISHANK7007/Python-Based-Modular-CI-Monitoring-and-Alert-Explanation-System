import yaml

def load_system_config(config_path: str) -> dict:
    """Loads and parses the system configuration YAML file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
