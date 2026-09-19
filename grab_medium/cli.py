"""CLI entry point for grab_medium."""

import sys
from typing import Optional
import click
from grab_medium.config import resolve_config, DEFAULT_CONFIG_PATH
from grab_medium.database import Database
from grab_medium.orchestrator import Orchestrator


@click.command()
@click.option(
    "--name",
    required=True,
    help="Name of the media collection.",
)
@click.option(
    "--path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    default=None,
    help="Directory path to scan.",
)
@click.option(
    "--db-path",
    default=None,
    help="DuckDB database file path.",
)
@click.option(
    "--log-path",
    default="grab_medium_errors.log",
    show_default=True,
    help="Error log file path.",
)
@click.option(
    "--sync",
    is_flag=True,
    default=False,
    help="Enable update/sync mode for an existing media collection.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simulate sync without committing changes to database.",
)
def cli(name: str, path: str, db_path: str, log_path: str, sync: bool, dry_run: bool) -> None:
    """grab_medium: High-performance media directory scanner and DuckDB ingester."""
    mode_str = "[Syncing" if sync else "[Scanning"
    if dry_run:
        mode_str += " (Dry Run)"
    click.echo(f"{mode_str} {path}...]")

    db = Database(db_path)
    orchestrator = Orchestrator(db, log_path=log_path)

    try:
        click.echo("[Processing metadata...]")
        res = orchestrator.run_scan(name=name, target_path=path, sync=sync, dry_run=dry_run)
        if dry_run and isinstance(res, dict):
            click.echo(f"[Dry Run complete! Summary: {res}]")
        else:
            click.echo(f"[Done! Media ID: {res} (Errors logged to {log_path})]")
    except Exception as e:
        click.echo(f"[Error: {e}]", err=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    cli()
