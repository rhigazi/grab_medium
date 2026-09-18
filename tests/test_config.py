import json
import pytest
from grab_medium.config import load_config, save_config, resolve_config


def test_save_and_load_config(tmp_path):
    cfg_path = str(tmp_path / "db.cfg")
    data = {"data_path": "/some/data", "db_path": "test.duckdb"}

    save_config(data, cfg_path)
    loaded = load_config(cfg_path)

    assert loaded == data


def test_load_nonexistent_config(tmp_path):
    cfg_path = str(tmp_path / "nonexistent.cfg")
    loaded = load_config(cfg_path)
    assert loaded == {}


def test_resolve_config_with_cli_args(tmp_path):
    cfg_path = str(tmp_path / "db.cfg")
    data_path, db_path = resolve_config(
        data_path="/path/a",
        db_path="my_db.duckdb",
        config_path=cfg_path,
    )

    assert data_path == "/path/a"
    assert db_path == "my_db.duckdb"

    # Verify saved in db.cfg
    loaded = load_config(cfg_path)
    assert loaded["data_path"] == "/path/a"
    assert loaded["db_path"] == "my_db.duckdb"


def test_resolve_config_from_file_fallback(tmp_path):
    cfg_path = str(tmp_path / "db.cfg")
    initial_data = {"data_path": "/path/b", "db_path": "existing.duckdb"}
    save_config(initial_data, cfg_path)

    data_path, db_path = resolve_config(
        data_path=None,
        db_path=None,
        config_path=cfg_path,
    )

    assert data_path == "/path/b"
    assert db_path == "existing.duckdb"


def test_resolve_config_missing_data_path(tmp_path):
    cfg_path = str(tmp_path / "db.cfg")
    with pytest.raises(ValueError, match="Data path not specified"):
        resolve_config(data_path=None, db_path=None, config_path=cfg_path)
