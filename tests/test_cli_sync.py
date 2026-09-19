"""Tests for CLI sync and dry-run options."""

from click.testing import CliRunner
from grab_medium.cli import cli


def test_cli_sync_and_dry_run(tmp_path):
    scan_dir = tmp_path / "scan_target"
    scan_dir.mkdir()
    (scan_dir / "file1.txt").write_text("Hello")

    db_file = str(tmp_path / "sync_cli.duckdb")
    runner = CliRunner()

    # Initial scan
    res1 = runner.invoke(cli, ["--name", "test_collection", "--path", str(scan_dir), "--db-path", db_file])
    assert res1.exit_code == 0
    assert "Done! Media ID: 1" in res1.output

    # Add second file
    (scan_dir / "file2.txt").write_text("World")

    # Sync with dry-run
    res_dry = runner.invoke(cli, ["--name", "test_collection", "--path", str(scan_dir), "--db-path", db_file, "--sync", "--dry-run"])
    assert res_dry.exit_code == 0
    assert "Dry Run complete!" in res_dry.output
    assert "'new': 1" in res_dry.output

    # Sync actual
    res_sync = runner.invoke(cli, ["--name", "test_collection", "--path", str(scan_dir), "--db-path", db_file, "--sync"])
    assert res_sync.exit_code == 0
    assert "Done! Media ID: 1" in res_sync.output
