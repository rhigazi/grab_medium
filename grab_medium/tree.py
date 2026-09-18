"""Tree view generation module for InvestigateMedia."""

from typing import Any, Dict, List, Optional
from rich.tree import Tree
from rich.console import Console
from grab_medium.database import Database


class TreeNode:
    """Represents a filesystem entry in the tree structure."""

    def __init__(
        self,
        entry_id: int,
        name: str,
        relative_path: str,
        is_dir: bool,
        size_bytes: int = 0,
    ):
        self.entry_id = entry_id
        self.name = name
        self.relative_path = relative_path
        self.is_dir = is_dir
        self.size_bytes = size_bytes
        self.children: List[TreeNode] = []

    def compute_aggregated_size(self) -> int:
        """Recursively calculates aggregated size for directory nodes."""
        if not self.is_dir:
            return self.size_bytes

        total = 0
        for child in self.children:
            total += child.compute_aggregated_size()
        self.size_bytes = total
        return total


def format_human_size(bytes_val: int) -> str:
    """Formats byte size into human readable string with exact bytes in parentheses."""
    if bytes_val < 1024:
        return f"{bytes_val} B"

    units = ["KB", "MB", "GB", "TB", "PB"]
    val = float(bytes_val)
    unit_str = "B"
    for u in units:
        val /= 1024.0
        unit_str = u
        if val < 1024.0:
            break

    return f"{val:.2f} {unit_str} ({bytes_val} B)"


def build_media_tree(db: Database, media_id: int) -> List[TreeNode]:
    """Constructs tree hierarchy from database entries for a given media_id."""
    conn = db.get_connection()
    query = """
        SELECT id, parent_id, name, relative_path, is_dir, size_bytes
        FROM entries
        WHERE media_id = ?
        ORDER BY is_dir DESC, name ASC;
    """
    rows = conn.execute(query, [media_id]).fetchall()

    nodes: Dict[int, TreeNode] = {}
    parent_map: Dict[int, Optional[int]] = {}

    for row in rows:
        e_id, p_id, name, rel_path, is_dir, size_bytes = row
        node = TreeNode(
            entry_id=e_id,
            name=name,
            relative_path=rel_path,
            is_dir=is_dir,
            size_bytes=size_bytes if size_bytes else 0,
        )
        nodes[e_id] = node
        parent_map[e_id] = p_id

    roots: List[TreeNode] = []

    for e_id, node in nodes.items():
        p_id = parent_map.get(e_id)
        if p_id is not None and p_id in nodes:
            nodes[p_id].children.append(node)
        else:
            roots.append(node)

    for root in roots:
        root.compute_aggregated_size()

    return roots


def _build_rich_tree(node: TreeNode, rich_node: Tree, include_size: bool) -> None:
    for child in node.children:
        if include_size:
            label = f"{child.name} [{format_human_size(child.size_bytes)}]"
        else:
            label = child.name

        if child.is_dir:
            sub = rich_node.add(f"[bold blue]{label}[/bold blue]")
            _build_rich_tree(child, sub, include_size)
        else:
            rich_node.add(label)


def render_terminal_tree(roots: List[TreeNode], include_size: bool = False) -> str:
    """Renders tree structure as a formatted terminal string using Rich."""
    console = Console(record=True, width=120)

    for root in roots:
        if include_size:
            root_label = f"[bold blue]{root.name}[/bold blue] [{format_human_size(root.size_bytes)}]"
        else:
            root_label = f"[bold blue]{root.name}[/bold blue]"

        tree = Tree(root_label)
        _build_rich_tree(root, tree, include_size)
        console.print(tree)

    return console.export_text()


def _node_to_dict(node: TreeNode, include_size: bool) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "name": node.name,
        "path": node.relative_path,
        "is_dir": node.is_dir,
    }
    if include_size:
        res["size_bytes"] = node.size_bytes
        res["size_formatted"] = format_human_size(node.size_bytes)

    if node.is_dir:
        res["children"] = [_node_to_dict(c, include_size) for c in node.children]

    return res


def render_json_tree(roots: List[TreeNode], include_size: bool = False) -> List[Dict[str, Any]]:
    """Converts tree hierarchy into nested list of dictionaries for JSON output."""
    return [_node_to_dict(root, include_size) for root in roots]


def _flatten_node_for_csv(node: TreeNode, include_size: bool, rows: List[Dict[str, Any]]) -> None:
    row: Dict[str, Any] = {
        "path": node.relative_path,
        "name": node.name,
        "type": "directory" if node.is_dir else "file",
    }
    if include_size:
        row["size_bytes"] = node.size_bytes
        row["size_formatted"] = format_human_size(node.size_bytes)

    rows.append(row)
    for child in node.children:
        _flatten_node_for_csv(child, include_size, rows)


def render_csv_tree(roots: List[TreeNode], include_size: bool = False) -> List[Dict[str, Any]]:
    """Flattens tree hierarchy into list of dictionaries for CSV output."""
    rows: List[Dict[str, Any]] = []
    for root in roots:
        _flatten_node_for_csv(root, include_size, rows)
    return rows
