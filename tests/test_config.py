"""Tests for config loading in grab_medium.config."""

import json
import pytest
from pathlib import Path
from grab_medium.config import load_config, Config


def test_load_config_from_explicit_file(tmp_path):
    cfg_file = tmp_path / "db.cfg"
    cfg_data = {
        "data_path": "/path/to/media",
        "db_path": "test.duckdb",
    }
    cfg_file.write_text(json.dumps(cfg_data), encoding="utf-8")

    config = load_config(config_file=str(cfg_file))
    assert config.data_path == "/path/to/media"
    assert config.db_path == "test.duckdb"


def test_load_config_with_cli_overrides(tmp_path):
    cfg_file = tmp_path / "db.cfg"
    cfg_data = {
        "data_path": "/path/to/media",
        "db_path": "test.duckdb",
    }
    cfg_file.write_text(json.dumps(cfg_data), encoding="utf-8")

    config = load_config(
        config_file=str(cfg_file),
        db_path_override="override.duckdb",
        data_path_override="/override/path",
    )
    assert config.data_path == "/override/path"
    assert config.db_path == "override.duckdb"


def test_load_config_env_var(tmp_path, monkeypatch):
    cfg_file = tmp_path / "custom.cfg"
    cfg_data = {
        "data_path": "/env/media",
        "db_path": "env.duckdb",
    }
    cfg_file.write_text(json.dumps(cfg_data), encoding="utf-8")

    monkeypatch.setenv("INVESTIGATE_MEDIA_CONFIG", str(cfg_file))
    config = load_config()
    assert config.data_path == "/env/media"
    assert config.db_path == "env.duckdb"


def test_load_config_missing_raises_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("INVESTIGATE_MEDIA_CONFIG", raising=False)
    monkeypatch.delenv("GRAB_MEDIUM_CONFIG", raising=False)

    with pytest.raises(FileNotFoundError, match="Configuration file 'db.cfg' not found"):
        load_config()


def test_load_config_missing_file_with_overrides(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("INVESTIGATE_MEDIA_CONFIG", raising=False)
    monkeypatch.delenv("GRAB_MEDIUM_CONFIG", raising=False)

    # When CLI overrides are provided for both, it should work even if db.cfg is missing
    config = load_config(db_path_override="override.duckdb", data_path_override="/override/path")
    assert config.data_path == "/override/path"
    assert config.db_path == "override.duckdb"
