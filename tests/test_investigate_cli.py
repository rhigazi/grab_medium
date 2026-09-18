"""Tests for InvestigateMedia CLI interface in grab_medium.investigate_cli."""

import json
import pytest
from click.testing import CliRunner
from grab_medium.database import Database
from grab_medium.investigate_cli import cli


@pytest.fixture
def cli_db_config(tmp_path):
    db_file = tmp_path / "test_cli.duckdb"
    db = Database(str(db_file))
    db.init_schema()
    conn = db.get_connection()

    conn.execute(
        "INSERT INTO media (id, name, scanned_at) VALUES (1, 'photos_2023', '2023-08-01 10:00:00')"
    )
    conn.execute(
        """
        INSERT INTO entries (id, media_id, parent_id, name, extension, relative_path, is_dir, size_bytes, created_at, modified_at)
        VALUES
        (1, 1, NULL, 'photos_2023', NULL, 'photos_2023', TRUE, 0, NULL, NULL),
        (2, 1, 1, 'pic1.jpg', 'jpg', 'photos_2023/pic1.jpg', FALSE, 2048, NULL, NULL),
        (3, 1, 1, 'notes.txt', 'txt', 'photos_2023/notes.txt', FALSE, 100, NULL, NULL)
        """
    )
    db.close()

    cfg_file = tmp_path / "db.cfg"
    cfg_data = {
        "data_path": str(tmp_path),
        "db_path": str(db_file),
    }
    cfg_file.write_text(json.dumps(cfg_data), encoding="utf-8")

    return str(cfg_file), str(db_file), str(tmp_path)


def test_cli_info(cli_db_config):
    cfg_file, _, _ = cli_db_config
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", cfg_file, "info"])
    assert result.exit_code == 0
    assert "media" in result.output
    assert "entries" in result.output


def test_cli_info_json(cli_db_config):
    cfg_file, _, _ = cli_db_config
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", cfg_file, "--format", "json", "info"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert any(item["table_name"] == "media" for item in data)


def test_cli_list_media(cli_db_config):
    cfg_file, _, _ = cli_db_config
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", cfg_file, "list-media"])
    assert result.exit_code == 0
    assert "photos_2023" in result.output


def test_cli_search_content(cli_db_config):
    cfg_file, _, _ = cli_db_config
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", cfg_file, "search-content", "pic1"])
    assert result.exit_code == 0
    assert "pic1.jpg" in result.output


def test_cli_search_file_type(cli_db_config):
    cfg_file, _, _ = cli_db_config
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", cfg_file, "search-file-type", "photos_2023", "jpg"])
    assert result.exit_code == 0
    assert "pic1.jpg" in result.output


def test_cli_tree_view(cli_db_config):
    cfg_file, _, _ = cli_db_config
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", cfg_file, "tree-view", "photos_2023"])
    assert result.exit_code == 0
    assert "photos_2023" in result.output
    assert "pic1.jpg" in result.output


def test_cli_tree_view_with_size(cli_db_config):
    cfg_file, _, _ = cli_db_config
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", cfg_file, "tree-view-with-size", "1"])
    assert result.exit_code == 0
    assert "photos_2023" in result.output
    assert "2.10 KB" in result.output or "2.00 KB" in result.output or "2148 B" in result.output


def test_cli_query(cli_db_config):
    cfg_file, _, _ = cli_db_config
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", cfg_file, "query", "SELECT name FROM media"])
    assert result.exit_code == 0
    assert "photos_2023" in result.output
