"""CLI entry point for grab_medium."""

import sys
import click
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
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    help="Directory path to scan.",
)
@click.option(
    "--db-path",
    default="grab_medium.duckdb",
    show_default=True,
    help="DuckDB database file path.",
)
@click.option(
    "--log-path",
    default="grab_medium_errors.log",
    show_default=True,
    help="Error log file path.",
)
def cli(name: str, path: str, db_path: str, log_path: str) -> None:
    """grab_medium: High-performance media directory scanner and DuckDB ingester."""
    click.echo(f"[Scanning {path}...]")
    db = Database(db_path)
    orchestrator = Orchestrator(db, log_path=log_path)

    try:
        click.echo("[Ingesting metadata...]")
        media_id = orchestrator.run_scan(name=name, target_path=path)
        click.echo(f"[Done! Media ID: {media_id} (Errors logged to {log_path})]")
    except Exception as e:
        click.echo(f"[Error: {e}]", err=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    cli()
