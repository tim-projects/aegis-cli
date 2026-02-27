import os
import json
from pathlib import Path

DEFAULT_AEGIS_VAULT_DIR = os.path.expanduser("~/.config/aegis-tui")
CONFIG_FILE_PATH = Path(DEFAULT_AEGIS_VAULT_DIR) / "config.json"

def load_config():
    if CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, 'r') as f:
                config = json.load(f)
                # Provide default values for new config keys if they don't exist
                if "last_opened_vault" not in config: config["last_opened_vault"] = None
                if "last_vault_dir" not in config: config["last_vault_dir"] = None
                if "default_color_mode" not in config: config["default_color_mode"] = True # Default to color enabled
                return config
        except json.JSONDecodeError:
            print(f"Warning: Could not parse config file {CONFIG_FILE_PATH}. Using default config.")
    return {"last_opened_vault": None, "last_vault_dir": None, "default_color_mode": True}

def save_config(config):
    CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE_PATH, 'w') as f:
        json.dump(config, f, indent=4)
