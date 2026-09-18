"""Configuration management for grab_medium using db.cfg (JSON)."""

import json
from pathlib import Path
from typing import Optional, Tuple

DEFAULT_CONFIG_PATH = "db.cfg"
DEFAULT_DB_PATH = "grab_medium.duckdb"


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Loads configuration from JSON file. Returns empty dict if file does not exist or is invalid."""
    path = Path(config_path)
    if path.exists() and path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(config_data: dict, config_path: str = DEFAULT_CONFIG_PATH) -> None:
    """Saves configuration dictionary to JSON file."""
    path = Path(config_path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)


def resolve_config(
    data_path: Optional[str] = None,
    db_path: Optional[str] = None,
    config_path: str = DEFAULT_CONFIG_PATH,
) -> Tuple[str, str]:
    """Resolves data_path and db_path from CLI arguments and db.cfg file, updating db.cfg.

    Raises ValueError if data_path cannot be resolved.
    """
    config = load_config(config_path)

    # Resolve data_path
    resolved_data_path = data_path or config.get("data_path")
    if not resolved_data_path:
        raise ValueError(
            "Data path not specified. Please provide --path or configure data_path in db.cfg."
        )

    # Resolve db_path: CLI parameter > db.cfg > DEFAULT_DB_PATH
    resolved_db_path = db_path or config.get("db_path") or DEFAULT_DB_PATH

    # Update and save config
    config["data_path"] = resolved_data_path
    config["db_path"] = resolved_db_path
    save_config(config, config_path)

    return resolved_data_path, resolved_db_path
