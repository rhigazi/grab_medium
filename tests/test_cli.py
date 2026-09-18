import pytest
from click.testing import CliRunner
from grab_medium.cli import cli
from grab_medium.database import Database


def test_cli_success(tmp_path):
    scan_dir = tmp_path / "my_photos"
    scan_dir.mkdir()
    (scan_dir / "img1.png").write_bytes(b"data")

    db_path = str(tmp_path / "cli_test.duckdb")
    log_path = str(tmp_path / "cli_errors.log")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--name", "vacation_photos",
            "--path", str(scan_dir),
            "--db-path", db_path,
            "--log-path", log_path,
        ]
    )

    assert result.exit_code == 0
    assert "[Scanning" in result.output
    assert "[Done!" in result.output

    # Verify DuckDB content
    db = Database(db_path)
    conn = db.get_connection()
    media_count = conn.execute("SELECT COUNT(*) FROM media WHERE name = 'vacation_photos'").fetchone()[0]
    assert media_count == 1
    db.close()


def test_cli_duplicate_name(tmp_path):
    scan_dir = tmp_path / "my_photos"
    scan_dir.mkdir()

    db_path = str(tmp_path / "cli_dup.duckdb")
    log_path = str(tmp_path / "cli_dup_errors.log")

    runner = CliRunner()
    # First scan
    runner.invoke(
        cli,
        ["--name", "photos", "--path", str(scan_dir), "--db-path", db_path, "--log-path", log_path]
    )

    # Duplicate scan
    result = runner.invoke(
        cli,
        ["--name", "photos", "--path", str(scan_dir), "--db-path", db_path, "--log-path", log_path]
    )

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_cli_missing_options():
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code != 0
    assert "Missing option" in result.output
