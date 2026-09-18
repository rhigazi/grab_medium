"""Tests for tree rendering engine in grab_medium.tree."""

import pytest
from grab_medium.database import Database
from grab_medium.tree import (
    TreeNode,
    build_media_tree,
    format_human_size,
    render_json_tree,
    render_csv_tree,
    render_terminal_tree,
)


@pytest.fixture
def db_with_tree_data(tmp_path):
    db_file = str(tmp_path / "test_tree.duckdb")
    db = Database(db_file)
    db.init_schema()
    conn = db.get_connection()

    conn.execute(
        "INSERT INTO media (id, name, scanned_at) VALUES (1, 'my_media', '2023-08-01 10:00:00')"
    )

    conn.execute(
        """
        INSERT INTO entries (id, media_id, parent_id, name, extension, relative_path, is_dir, size_bytes, created_at, modified_at)
        VALUES
        (1, 1, NULL, 'my_media', NULL, 'my_media', TRUE, 0, NULL, NULL),
        (2, 1, 1, 'docs', NULL, 'my_media/docs', TRUE, 0, NULL, NULL),
        (3, 1, 2, 'file1.txt', 'txt', 'my_media/docs/file1.txt', FALSE, 1024, NULL, NULL),
        (4, 1, 2, 'file2.txt', 'txt', 'my_media/docs/file2.txt', FALSE, 2048, NULL, NULL),
        (5, 1, 1, 'images', NULL, 'my_media/images', TRUE, 0, NULL, NULL),
        (6, 1, 5, 'photo.jpg', 'jpg', 'my_media/images/photo.jpg', FALSE, 1048576, NULL, NULL)
        """
    )
    yield db
    db.close()


def test_format_human_size():
    assert format_human_size(0) == "0 B"
    assert format_human_size(500) == "500 B"
    assert "1.00 KB (1024 B)" in format_human_size(1024)
    assert "1.00 MB (1048576 B)" in format_human_size(1048576)


def test_build_media_tree(db_with_tree_data):
    roots = build_media_tree(db_with_tree_data, 1)
    assert len(roots) == 1
    root = roots[0]
    assert root.name == "my_media"
    # Root dir total size should be sum of file1 (1024) + file2 (2048) + photo (1048576) = 1051648
    assert root.size_bytes == 1051648

    docs_node = next(c for c in root.children if c.name == "docs")
    assert docs_node.size_bytes == 3072


def test_render_json_tree(db_with_tree_data):
    roots = build_media_tree(db_with_tree_data, 1)
    json_data = render_json_tree(roots, include_size=True)
    assert len(json_data) == 1
    root_dict = json_data[0]
    assert root_dict["name"] == "my_media"
    assert root_dict["is_dir"] is True
    assert root_dict["size_bytes"] == 1051648
    assert len(root_dict["children"]) == 2


def test_render_csv_tree(db_with_tree_data):
    roots = build_media_tree(db_with_tree_data, 1)
    csv_rows = render_csv_tree(roots, include_size=True)
    assert len(csv_rows) == 6
    paths = [r["path"] for r in csv_rows]
    assert "my_media" in paths
    assert "my_media/docs/file1.txt" in paths


def test_render_terminal_tree(db_with_tree_data):
    roots = build_media_tree(db_with_tree_data, 1)
    rendered = render_terminal_tree(roots, include_size=True)
    assert "my_media" in rendered
    assert "docs" in rendered
    assert "file1.txt" in rendered
    assert "1.00 KB" in rendered or "1.00 MB" in rendered
