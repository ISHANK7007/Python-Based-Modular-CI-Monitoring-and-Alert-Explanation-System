import os
import yaml

def load_cli_config(config_path="config.yaml"):
    """
    Loads CLI configuration from a YAML file.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Example usage
if __name__ == "__main__":
    config = load_cli_config()
    print(config.get("display", {}))
