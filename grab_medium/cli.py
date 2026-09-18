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
    "--config-path",
    default=DEFAULT_CONFIG_PATH,
    show_default=True,
    help="Configuration file path (db.cfg).",
)
def cli(
    name: str,
    path: Optional[str],
    db_path: Optional[str],
    log_path: str,
    config_path: str,
) -> None:
    """grab_medium: High-performance media directory scanner and DuckDB ingester."""
    try:
        data_path, resolved_db_path = resolve_config(
            data_path=path,
            db_path=db_path,
            config_path=config_path,
        )
    except ValueError as e:
        click.echo(f"[Error: {e}]", err=True)
        sys.exit(1)

    click.echo(f"[Scanning {data_path}...]")
    db = Database(resolved_db_path)
    orchestrator = Orchestrator(db, log_path=log_path)

    try:
        click.echo("[Ingesting metadata...]")
        media_id = orchestrator.run_scan(name=name, target_path=data_path)
        click.echo(f"[Done! Media ID: {media_id} (Errors logged to {log_path})]")
    except Exception as e:
        click.echo(f"[Error: {e}]", err=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    cli()
