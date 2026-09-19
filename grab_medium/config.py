"""Configuration management for grab_medium and InvestigateMedia."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Union, Dict, Any

DEFAULT_CONFIG_PATH = "db.cfg"


@dataclass
class Config:
    """Configuration model for InvestigateMedia."""

    data_path: str
    db_path: str


def resolve_config(
    data_path: Optional[str] = None,
    db_path: Optional[str] = None,
    config_path: Optional[str] = None,
) -> Tuple[str, str]:
    """Resolves data_path and db_path from CLI arguments, env vars, or configuration file.

    Precedence:
    1. CLI arguments (data_path, db_path)
    2. Environment variables INVESTIGATE_MEDIA_CONFIG or GRAB_MEDIUM_CONFIG
    3. Configuration file (config_path or db.cfg)
    """
    cfg_path: Optional[Path] = None

    if config_path:
        cfg_path = Path(config_path)
    elif os.getenv("INVESTIGATE_MEDIA_CONFIG"):
        cfg_path = Path(os.environ["INVESTIGATE_MEDIA_CONFIG"])
    elif os.getenv("GRAB_MEDIUM_CONFIG"):
        cfg_path = Path(os.environ["GRAB_MEDIUM_CONFIG"])
    else:
        default_cfg = Path.cwd() / DEFAULT_CONFIG_PATH
        if default_cfg.exists():
            cfg_path = default_cfg
        else:
            cfg_path = Path(DEFAULT_CONFIG_PATH)

    res_data_path = data_path
    res_db_path = db_path

    if cfg_path and cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
                if not res_data_path:
                    res_data_path = cfg_data.get("data_path")
                if not res_db_path:
                    res_db_path = cfg_data.get("db_path")
        except Exception as e:
            raise ValueError(f"Failed to parse configuration file '{cfg_path}': {e}")
    elif not (res_db_path and res_data_path):
        raise FileNotFoundError(
            f"Configuration file '{cfg_path or DEFAULT_CONFIG_PATH}' not found. "
            "Please create 'db.cfg' with 'data_path' and 'db_path' or specify command-line arguments."
        )

    if not res_data_path or not res_db_path:
        raise ValueError(
            "Configuration incomplete. Both 'data_path' and 'db_path' must be specified in 'db.cfg' or via arguments."
        )

    return res_data_path, res_db_path


def load_config(
    config_path: Optional[str] = None,
    config_file: Optional[str] = None,
    db_path_override: Optional[str] = None,
    data_path_override: Optional[str] = None,
    **kwargs: Any,
) -> Config:
    """Loads configuration and returns a Config object. Accepts multiple argument style aliases for compatibility."""
    cfg_file = config_path or config_file or kwargs.get("config")
    db_path = db_path_override or kwargs.get("db_path")
    data_path = data_path_override or kwargs.get("data_path")

    res_data_path, res_db_path = resolve_config(
        data_path=data_path,
        db_path=db_path,
        config_path=cfg_file,
    )

    return Config(data_path=res_data_path, db_path=res_db_path)
