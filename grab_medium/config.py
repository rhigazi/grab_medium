"""Configuration management for grab_medium and InvestigateMedia."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Configuration model for InvestigateMedia."""

    data_path: str
    db_path: str


def load_config(
    config_file: Optional[str] = None,
    db_path_override: Optional[str] = None,
    data_path_override: Optional[str] = None,
) -> Config:
    """Loads configuration from file or environment variables with optional CLI overrides.

    Precedence for config path:
    1. Direct parameter `config_file`
    2. Environment variable `INVESTIGATE_MEDIA_CONFIG`
    3. Environment variable `GRAB_MEDIUM_CONFIG`
    4. Default `db.cfg` in current working directory.
    """
    if db_path_override and data_path_override:
        return Config(data_path=data_path_override, db_path=db_path_override)

    cfg_path: Optional[Path] = None

    if config_file:
        cfg_path = Path(config_file)
    elif os.getenv("INVESTIGATE_MEDIA_CONFIG"):
        cfg_path = Path(os.environ["INVESTIGATE_MEDIA_CONFIG"])
    elif os.getenv("GRAB_MEDIUM_CONFIG"):
        cfg_path = Path(os.environ["GRAB_MEDIUM_CONFIG"])
    else:
        default_cfg = Path.cwd() / "db.cfg"
        if default_cfg.exists():
            cfg_path = default_cfg

    data_path = data_path_override
    db_path = db_path_override

    if cfg_path and cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not data_path:
                    data_path = data.get("data_path")
                if not db_path:
                    db_path = data.get("db_path")
        except Exception as e:
            raise ValueError(f"Failed to parse configuration file '{cfg_path}': {e}")
    elif not (db_path and data_path):
        raise FileNotFoundError(
            "Configuration file 'db.cfg' not found. "
            "Please create 'db.cfg' with 'data_path' and 'db_path' or specify command-line arguments."
        )

    if not data_path or not db_path:
        raise ValueError(
            "Configuration incomplete. Both 'data_path' and 'db_path' must be specified in 'db.cfg' or via arguments."
        )

    return Config(data_path=data_path, db_path=db_path)
