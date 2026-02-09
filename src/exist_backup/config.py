"""Load configuration from TOML file and environment variables."""

import os
import tomllib
from pathlib import Path


DEFAULT_CONFIG = {
    "auth": {"token": ""},
    "sync": {"database": "/data/exist.db"},
    "export": {"output_dir": "/export", "template": "daily"},
}


def load_config(config_path=None):
    """Load config from TOML file, with env var overrides.

    Config file path resolution:
    1. Explicit config_path argument
    2. EXIST_BACKUP_CONFIG env var
    3. /config/config.toml (default for container)
    """
    if config_path is None:
        config_path = os.environ.get("EXIST_BACKUP_CONFIG", "/config/config.toml")

    config_path = Path(config_path)

    config = dict(DEFAULT_CONFIG)
    if config_path.exists():
        with open(config_path, "rb") as f:
            file_config = tomllib.load(f)
        # Merge sections
        for section in ("auth", "sync", "export"):
            if section in file_config:
                config[section] = {**DEFAULT_CONFIG.get(section, {}), **file_config[section]}

    # EXIST_TOKEN env var overrides auth.token
    env_token = os.environ.get("EXIST_TOKEN")
    if env_token:
        config["auth"]["token"] = env_token

    return config
