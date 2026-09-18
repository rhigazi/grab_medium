import json
import pytest
from click.testing import CliRunner
from grab_medium.cli import cli
from grab_medium.database import Database


def test_cli_success_with_cli_args(tmp_path):
    scan_dir = tmp_path / "my_photos"
    scan_dir.mkdir()
    (scan_dir / "img1.png").write_bytes(b"data")

    db_path = str(tmp_path / "cli_test.duckdb")
    log_path = str(tmp_path / "cli_errors.log")
    config_path = str(tmp_path / "db.cfg")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--name", "vacation_photos",
            "--path", str(scan_dir),
            "--db-path", db_path,
            "--log-path", log_path,
            "--config-path", config_path,
        ]
    )

    assert result.exit_code == 0
    assert "[Scanning" in result.output
    assert "[Done!" in result.output

    # Verify db.cfg created
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    assert config["data_path"] == str(scan_dir)
    assert config["db_path"] == db_path

    # Verify DuckDB content
    db = Database(db_path)
    conn = db.get_connection()
    media_count = conn.execute("SELECT COUNT(*) FROM media WHERE name = 'vacation_photos'").fetchone()[0]
    assert media_count == 1
    db.close()


def test_cli_using_config_file_fallback(tmp_path):
    scan_dir = tmp_path / "my_photos"
    scan_dir.mkdir()
    (scan_dir / "img1.png").write_bytes(b"data")

    db_path = str(tmp_path / "cli_cfg_test.duckdb")
    log_path = str(tmp_path / "cli_cfg_errors.log")
    config_path = str(tmp_path / "db.cfg")

    # Pre-populate db.cfg
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"data_path": str(scan_dir), "db_path": db_path}, f)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--name", "vacation_photos_cfg",
            "--log-path", log_path,
            "--config-path", config_path,
        ]
    )

    assert result.exit_code == 0
    assert f"[Scanning {scan_dir}...]" in result.output

    # Verify DuckDB content
    db = Database(db_path)
    conn = db.get_connection()
    media_count = conn.execute("SELECT COUNT(*) FROM media WHERE name = 'vacation_photos_cfg'").fetchone()[0]
    assert media_count == 1
    db.close()


def test_cli_missing_path_and_config(tmp_path):
    config_path = str(tmp_path / "db.cfg")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--name", "test_name", "--config-path", config_path]
    )

    assert result.exit_code == 1
    assert "Data path not specified" in result.output
