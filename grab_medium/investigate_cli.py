"""CLI interface for InvestigateMedia tool."""

import sys
import click
from grab_medium.config import load_config
from grab_medium.database import Database
from grab_medium.formatter import format_output, FormatType
from grab_medium.investigate_db import InvestigateDB
from grab_medium.tree import (
    build_media_tree,
    render_csv_tree,
    render_json_tree,
    render_terminal_tree,
)


@click.group()
@click.option(
    "--config",
    "-c",
    default=None,
    help="Path to db.cfg configuration file.",
)
@click.option(
    "--db-path",
    default=None,
    help="Override DuckDB database path.",
)
@click.option(
    "--data-path",
    default=None,
    help="Override media root data path.",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["terminal", "json", "csv"], case_sensitive=False),
    default="terminal",
    show_default=True,
    help="Output format (terminal, json, csv).",
)
@click.pass_context
def cli(ctx: click.Context, config: str, db_path: str, data_path: str, format: str) -> None:
    """InvestigateMedia: High-performance CLI for media data analysis and visualization."""
    ctx.ensure_object(dict)
    fmt = FormatType(format.lower())
    ctx.obj["format"] = fmt

    try:
        cfg = load_config(
            config_file=config,
            db_path_override=db_path,
            data_path_override=data_path,
        )
        db = Database(cfg.db_path)
        ctx.obj["db"] = db
        ctx.obj["investigate_db"] = InvestigateDB(db)
    except Exception as e:
        click.echo(f"Configuration / Database Error: {e}", err=True)
        sys.exit(1)


@cli.result_callback()
@click.pass_context
def process_result(ctx: click.Context, result, **kwargs) -> None:
    """Closes database connection after command completion."""
    db = ctx.obj.get("db")
    if db:
        db.close()


@cli.command("info")
@click.pass_context
def info_cmd(ctx: click.Context) -> None:
    """Prints database schema structure, columns, and data types."""
    inv_db: InvestigateDB = ctx.obj["investigate_db"]
    fmt: FormatType = ctx.obj["format"]
    schema = inv_db.get_schema_info()
    out = format_output(schema, fmt=fmt)
    click.echo(out)


@cli.command("list-media")
@click.pass_context
def list_media_cmd(ctx: click.Context) -> None:
    """Lists all captured media collections with names and timestamps."""
    inv_db: InvestigateDB = ctx.obj["investigate_db"]
    fmt: FormatType = ctx.obj["format"]
    media = inv_db.list_media()
    out = format_output(media, fmt=fmt)
    click.echo(out)


@cli.command("search-content")
@click.argument("text")
@click.pass_context
def search_content_cmd(ctx: click.Context, text: str) -> None:
    """Searches notes or relative paths for a keyword."""
    inv_db: InvestigateDB = ctx.obj["investigate_db"]
    fmt: FormatType = ctx.obj["format"]
    results = inv_db.search_content(text)
    out = format_output(results, fmt=fmt)
    click.echo(out)


@cli.command("search-file-type")
@click.argument("medium")
@click.argument("endung")
@click.pass_context
def search_file_type_cmd(ctx: click.Context, medium: str, endung: str) -> None:
    """Filters files by medium (name or ID) and file extension."""
    inv_db: InvestigateDB = ctx.obj["investigate_db"]
    fmt: FormatType = ctx.obj["format"]
    try:
        results = inv_db.search_file_type(medium, endung)
        out = format_output(results, fmt=fmt)
        click.echo(out)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("tree-view")
@click.argument("medium")
@click.pass_context
def tree_view_cmd(ctx: click.Context, medium: str) -> None:
    """Generates visual directory tree structure for a media collection."""
    inv_db: InvestigateDB = ctx.obj["investigate_db"]
    db: Database = ctx.obj["db"]
    fmt: FormatType = ctx.obj["format"]

    try:
        m_id = inv_db.resolve_media_id(medium)
        roots = build_media_tree(db, m_id)

        if fmt == FormatType.JSON:
            json_tree = render_json_tree(roots, include_size=False)
            out = format_output(json_tree, fmt=fmt)
        elif fmt == FormatType.CSV:
            csv_tree = render_csv_tree(roots, include_size=False)
            out = format_output(csv_tree, fmt=fmt)
        else:
            out = render_terminal_tree(roots, include_size=False)

        click.echo(out)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("tree-view-with-size")
@click.argument("medium")
@click.pass_context
def tree_view_with_size_cmd(ctx: click.Context, medium: str) -> None:
    """Generates visual directory tree structure with aggregated sizes per directory."""
    inv_db: InvestigateDB = ctx.obj["investigate_db"]
    db: Database = ctx.obj["db"]
    fmt: FormatType = ctx.obj["format"]

    try:
        m_id = inv_db.resolve_media_id(medium)
        roots = build_media_tree(db, m_id)

        if fmt == FormatType.JSON:
            json_tree = render_json_tree(roots, include_size=True)
            out = format_output(json_tree, fmt=fmt)
        elif fmt == FormatType.CSV:
            csv_tree = render_csv_tree(roots, include_size=True)
            out = format_output(csv_tree, fmt=fmt)
        else:
            out = render_terminal_tree(roots, include_size=True)

        click.echo(out)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("query")
@click.argument("sql")
@click.pass_context
def query_cmd(ctx: click.Context, sql: str) -> None:
    """Executes direct SQL SELECT queries on DuckDB database."""
    inv_db: InvestigateDB = ctx.obj["investigate_db"]
    fmt: FormatType = ctx.obj["format"]

    try:
        cols, rows = inv_db.execute_query(sql)
        out = format_output((cols, rows), fmt=fmt)
        click.echo(out)
    except Exception as e:
        click.echo(f"Query Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
