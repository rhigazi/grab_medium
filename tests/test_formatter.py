"""Tests for output formatters in grab_medium.formatter."""

import json
import pytest
from grab_medium.formatter import format_output, FormatType


def test_format_output_json():
    data = [{"id": 1, "name": "test", "is_dir": True}]
    res = format_output(data, fmt=FormatType.JSON)
    parsed = json.loads(res)
    assert parsed == data


def test_format_output_csv():
    data = [
        {"id": 1, "name": "alpha", "size": 100},
        {"id": 2, "name": "beta", "size": 200},
    ]
    res = format_output(data, fmt=FormatType.CSV)
    lines = res.strip().splitlines()
    assert lines[0] == "id,name,size"
    assert lines[1] == "1,alpha,100"
    assert lines[2] == "2,beta,200"


def test_format_output_terminal():
    data = [{"id": 1, "name": "test_media"}]
    res = format_output(data, fmt=FormatType.TERMINAL)
    assert "test_media" in res
    assert "id" in res.lower() or "ID" in res


def test_format_query_result_terminal():
    columns = ["id", "title"]
    rows = [(1, "First"), (2, "Second")]
    res = format_output((columns, rows), fmt=FormatType.TERMINAL)
    assert "title" in res
    assert "First" in res


def test_format_query_result_json():
    columns = ["id", "title"]
    rows = [(1, "First"), (2, "Second")]
    res = format_output((columns, rows), fmt=FormatType.JSON)
    parsed = json.loads(res)
    assert parsed == [{"id": 1, "title": "First"}, {"id": 2, "title": "Second"}]


def test_format_query_result_csv():
    columns = ["id", "title"]
    rows = [(1, "First"), (2, "Second")]
    res = format_output((columns, rows), fmt=FormatType.CSV)
    assert "id,title" in res
    assert "1,First" in res
