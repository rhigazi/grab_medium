"""Output formatting module supporting Terminal (Rich), JSON, and CSV formats."""

import csv
import io
import json
from enum import Enum
from typing import Any, Dict, List, Tuple, Union
from rich.console import Console
from rich.table import Table


class FormatType(str, Enum):
    TERMINAL = "terminal"
    JSON = "json"
    CSV = "csv"


def format_output(
    data: Union[List[Dict[str, Any]], Tuple[List[str], List[Tuple[Any, ...]]], str],
    fmt: Union[FormatType, str] = FormatType.TERMINAL,
) -> str:
    """Formats list of dictionaries, tuple of (columns, rows), or string into specified format."""
    if isinstance(fmt, str):
        fmt = FormatType(fmt.lower())

    # If data is already a string (e.g. pre-rendered terminal tree) and format is TERMINAL
    if isinstance(data, str):
        return data

    # Normalize data into columns and rows
    columns: List[str] = []
    rows: List[List[Any]] = []

    if isinstance(data, tuple) and len(data) == 2:
        cols, rws = data
        columns = list(cols)
        rows = [list(r) for r in rws]
    elif isinstance(data, list):
        if not data:
            columns = []
            rows = []
        elif isinstance(data[0], dict):
            columns = list(data[0].keys())
            rows = [[item.get(col) for col in columns] for item in data]

    if fmt == FormatType.JSON:
        if isinstance(data, list) and (not data or isinstance(data[0], dict)):
            return json.dumps(data, indent=2, default=str)
        dict_rows = [dict(zip(columns, row)) for row in rows]
        return json.dumps(dict_rows, indent=2, default=str)

    elif fmt == FormatType.CSV:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(row)
        return output.getvalue()

    elif fmt == FormatType.TERMINAL:
        if not columns:
            return "No results found."

        console = Console(record=True, width=120)
        table = Table(show_header=True, header_style="bold magenta")

        for col in columns:
            table.add_column(str(col))

        for row in rows:
            table.add_row(*[str(val) if val is not None else "" for val in row])

        console.print(table)
        return console.export_text()

    raise ValueError(f"Unsupported format type: {fmt}")
