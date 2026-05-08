"""MCP server exposing Trello tools for Claude Code."""

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from . import trello

load_dotenv()

mcp = FastMCP(
    "mtl-trello",
    instructions="Trello project management for Claude Code — boards, lists, cards, search",
)


# --- Board tools ---


@mcp.tool()
def trello_list_boards() -> str:
    """List all Trello boards for the authenticated user.

    Returns board names, IDs, and URLs. Use board IDs for other operations.
    """
    boards = trello.get_boards()
    open_boards = [b for b in boards if not b.get("closed")]

    if not open_boards:
        return "No open boards found."

    lines = [f"# Trello Boards ({len(open_boards)} open)\n"]
    for b in open_boards:
        lines.append(
            f"- **{b['name']}**\n  ID: `{b['id']}`\n  URL: {b.get('url', 'N/A')}\n"
        )
    return "\n".join(lines)


@mcp.tool()
def trello_get_board(board_id: str) -> str:
    """Get details about a specific Trello board, including all lists and their cards.

    Args:
        board_id: Trello board ID (from trello_list_boards)
    """
    board = trello.get_board(board_id)
    lists = trello.get_lists(board_id)

    lines = [
        f"# {board.get('name', 'Unknown Board')}\n",
        f"**URL:** {board.get('url', 'N/A')}",
        f"**Lists:** {len(lists)}\n",
    ]

    for lst in lists:
        cards = trello.get_cards(lst["id"])
        lines.append(f"## {lst['name']} ({len(cards)} cards)\n")
        if cards:
            for c in cards:
                due = f" | Due: {c.get('due', '')[:10]}" if c.get("due") else ""
                labels = ", ".join(
                    lbl.get("name", "")
                    for lbl in c.get("labels", [])
                    if lbl.get("name")
                )
                label_str = f" | Labels: {labels}" if labels else ""
                lines.append(f"- **{c['name']}**{due}{label_str}\n  ID: `{c['id']}`\n")
        else:
            lines.append("- *(empty)*\n")

    return "\n".join(lines)


# --- List tools ---


@mcp.tool()
def trello_get_lists(board_id: str) -> str:
    """Get all lists in a Trello board.

    Args:
        board_id: Trello board ID
    """
    lists = trello.get_lists(board_id)

    if not lists:
        return "No lists found in this board."

    lines = [f"# Lists ({len(lists)})\n"]
    for lst in lists:
        lines.append(f"- **{lst['name']}** — ID: `{lst['id']}`")
    return "\n".join(lines)


@mcp.tool()
def trello_create_list(board_id: str, name: str) -> str:
    """Create a new list in a Trello board.

    Args:
        board_id: Trello board ID
        name: Name for the new list
    """
    lst = trello.create_list(board_id, name)
    return f"Created list **{lst['name']}** (ID: `{lst['id']}`)"


# --- Card tools ---


@mcp.tool()
def trello_get_card(card_id: str) -> str:
    """Get full details about a specific Trello card.

    Args:
        card_id: Trello card ID
    """
    card = trello.get_card(card_id)
    members = card.get("members", [])
    labels = card.get("labels", [])

    lines = [
        f"# {card.get('name', 'Unknown Card')}\n",
        f"**ID:** `{card['id']}`",
        f"**URL:** {card.get('url', 'N/A')}",
        f"**List:** `{card.get('idList', 'N/A')}`",
        f"**Due:** {card.get('due', 'None')}",
        f"**Archived:** {card.get('closed', False)}",
    ]

    if members:
        member_str = ", ".join(
            f"{m.get('fullName', '')} (@{m.get('username', '')})" for m in members
        )
        lines.append(f"**Members:** {member_str}")

    if labels:
        label_str = ", ".join(
            f"{lbl.get('name', 'unnamed')} ({lbl.get('color', '')})" for lbl in labels
        )
        lines.append(f"**Labels:** {label_str}")

    desc = card.get("desc", "")
    if desc:
        lines.extend(["\n## Description\n", desc])

    return "\n".join(lines)


@mcp.tool()
def trello_create_card(
    list_id: str,
    name: str,
    desc: str = "",
    due: str = "",
    label_ids: str = "",
    member_ids: str = "",
) -> str:
    """Create a new Trello card in a list.

    Args:
        list_id: ID of the list to add the card to
        name: Card title
        desc: Card description (Markdown supported)
        due: Due date in ISO format (e.g. "2026-03-15")
        label_ids: Comma-separated label IDs to apply
        member_ids: Comma-separated member IDs to assign
    """
    card = trello.create_card(
        list_id=list_id,
        name=name,
        desc=desc or None,
        due=due or None,
        label_ids=label_ids or None,
        member_ids=member_ids or None,
    )
    return (
        f"Created card **{card['name']}**\n"
        f"ID: `{card['id']}`\n"
        f"URL: {card.get('url', 'N/A')}"
    )


@mcp.tool()
def trello_update_card(
    card_id: str,
    name: str = "",
    desc: str = "",
    due: str = "",
) -> str:
    """Update a Trello card's name, description, or due date.

    Args:
        card_id: Trello card ID
        name: New card title (leave empty to keep current)
        desc: New description (leave empty to keep current)
        due: New due date in ISO format (leave empty to keep current)
    """
    card = trello.update_card(
        card_id=card_id,
        name=name or None,
        desc=desc or None,
        due=due or None,
    )
    return f"Updated card **{card.get('name', 'Unknown')}** (ID: `{card_id}`)"


@mcp.tool()
def trello_move_card(card_id: str, list_id: str) -> str:
    """Move a Trello card to a different list.

    Args:
        card_id: Trello card ID
        list_id: Target list ID
    """
    card = trello.move_card(card_id, list_id)
    return f"Moved card **{card.get('name', 'Unknown')}** to list `{list_id}`"


@mcp.tool()
def trello_archive_card(card_id: str) -> str:
    """Archive a Trello card (soft delete — can be unarchived later).

    Args:
        card_id: Trello card ID
    """
    card = trello.archive_card(card_id)
    return f"Archived card **{card.get('name', 'Unknown')}** (ID: `{card_id}`)"


@mcp.tool()
def trello_assign_card(card_id: str, member_ids: str) -> str:
    """Assign members to a Trello card.

    Args:
        card_id: Trello card ID
        member_ids: Comma-separated member IDs to assign (from trello_get_members)
    """
    card = trello.update_card(card_id=card_id, member_ids=member_ids)
    return (
        f"Assigned members to card **{card.get('name', 'Unknown')}** (ID: `{card_id}`)"
    )


# --- Labels & Members ---


@mcp.tool()
def trello_get_labels(board_id: str) -> str:
    """Get all labels available on a Trello board.

    Args:
        board_id: Trello board ID
    """
    labels = trello.get_labels(board_id)

    if not labels:
        return "No labels found on this board."

    lines = [f"# Labels ({len(labels)})\n"]
    for lbl in labels:
        name = lbl.get("name", "") or "(unnamed)"
        lines.append(
            f"- **{name}** ({lbl.get('color', 'no color')}) — ID: `{lbl['id']}`"
        )
    return "\n".join(lines)


@mcp.tool()
def trello_get_members(board_id: str) -> str:
    """Get all members of a Trello board.

    Args:
        board_id: Trello board ID
    """
    members = trello.get_board_members(board_id)

    if not members:
        return "No members found on this board."

    lines = [f"# Board Members ({len(members)})\n"]
    for m in members:
        lines.append(
            f"- **{m.get('fullName', 'Unknown')}** (@{m.get('username', '')}) — ID: `{m['id']}`"
        )
    return "\n".join(lines)


# --- Search ---


@mcp.tool()
def trello_search(query: str, board_id: str = "") -> str:
    """Search for Trello cards by keyword.

    Uses Trello search syntax. Can optionally filter by board.

    Args:
        query: Search query (e.g. "audio fingerprinting", "@mariusz", "label:bug")
        board_id: Optional board ID to limit search to a specific board
    """
    cards = trello.search_cards(query, board_id=board_id or None)

    if not cards:
        return f"No cards found for '{query}'."

    lines = [f'# Search: "{query}" ({len(cards)} results)\n']
    for c in cards:
        board_name = c.get("board", {}).get("name", "")
        list_name = c.get("list", {}).get("name", "")
        context = f" | {board_name} → {list_name}" if board_name else ""
        lines.append(f"- **{c['name']}**{context}\n  ID: `{c['id']}`\n")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
