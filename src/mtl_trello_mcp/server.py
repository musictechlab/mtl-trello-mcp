"""MCP server exposing Trello tools for Claude Code."""

import fnmatch
import mimetypes
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from . import trello

load_dotenv()

mcp = FastMCP(
    "mtl-trello",
    instructions="Trello project management for Claude Code — boards, lists, cards, search",
)

# Filename globs that must never be uploaded, even from inside the allowed root.
# These are the usual homes of credentials and private keys.
_SENSITIVE_GLOBS = (
    "*.pem",
    "*.key",
    "*.env",
    ".env",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    ".netrc",
    "credentials",
)
# Hard cap on upload size (overridable via TRELLO_MAX_UPLOAD_MB).
_DEFAULT_MAX_UPLOAD_MB = 50


def _resolve_upload_path(file_path: str) -> str:
    """Resolve and validate a local file path before uploading it to Trello.

    Guards the attachment tools against arbitrary local-file reads — e.g. a
    prompt-injected path pointed at a card an attacker can read. Layered checks:

    - Confine to an allowed root: TRELLO_UPLOAD_DIR if set, else the user's home
      directory. Symlinks are resolved first so they can't escape the root.
    - Must be a regular file (no directories, devices, or missing paths).
    - Reject any hidden path component (a part starting with `.`, such as
      `.ssh`, `.aws`, `.config`, `.env`). Secrets overwhelmingly live in
      dotfiles/dotdirs; legitimate attachments essentially never do. This is
      what actually blocks `~/.ssh/id_rsa` under the default home root. Set
      TRELLO_ALLOW_HIDDEN=1 to opt out.
    - Reject sensitive filename patterns (keys, certs, *.env) even when not
      hidden — see `_SENSITIVE_GLOBS`.
    - Enforce a size cap (TRELLO_MAX_UPLOAD_MB, default 50 MB).
    """
    base = os.path.realpath(
        os.environ.get("TRELLO_UPLOAD_DIR") or os.path.expanduser("~")
    )
    resolved = os.path.realpath(file_path)
    if resolved != base and not resolved.startswith(base + os.sep):
        raise ValueError(f"file_path must be within {base}")
    if not os.path.isfile(resolved):
        raise ValueError(f"file_path is not a regular file: {resolved}")

    if os.environ.get("TRELLO_ALLOW_HIDDEN") != "1":
        rel = os.path.relpath(resolved, base)
        for part in rel.split(os.sep):
            if part.startswith("."):
                raise ValueError(
                    f"refusing hidden path component '{part}' "
                    "(set TRELLO_ALLOW_HIDDEN=1 to override)"
                )

    name = os.path.basename(resolved).lower()
    if any(fnmatch.fnmatch(name, glob) for glob in _SENSITIVE_GLOBS):
        raise ValueError(
            f"refusing to upload sensitive file: {os.path.basename(resolved)}"
        )

    try:
        max_mb = int(os.environ.get("TRELLO_MAX_UPLOAD_MB", _DEFAULT_MAX_UPLOAD_MB))
    except ValueError:
        max_mb = _DEFAULT_MAX_UPLOAD_MB
    size = os.path.getsize(resolved)
    if size > max_mb * 1024 * 1024:
        raise ValueError(f"file too large: {size} bytes exceeds {max_mb} MB limit")

    return resolved


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
    label_ids: str = "",
) -> str:
    """Update a Trello card's name, description, due date, or labels.

    Args:
        card_id: Trello card ID
        name: New card title (leave empty to keep current)
        desc: New description (leave empty to keep current)
        due: New due date in ISO format (leave empty to keep current)
        label_ids: Comma-separated label IDs — REPLACES the card's full label set.
            Use trello_add_label_to_card / trello_remove_label_from_card for
            incremental changes. Leave empty to keep current labels.
    """
    card = trello.update_card(
        card_id=card_id,
        name=name or None,
        desc=desc or None,
        due=due or None,
        label_ids=label_ids if label_ids else None,
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
def trello_add_attachment(card_id: str, file_path: str, name: str = "") -> str:
    """Attach a local file (image, PDF, etc.) to a Trello card.

    Args:
        card_id: Trello card ID
        file_path: Absolute path to the local file to upload
        name: Optional display name for the attachment (defaults to the filename)
    """
    safe_path = _resolve_upload_path(file_path)
    att = trello.add_attachment(card_id, safe_path, name or None)
    return (
        f"Attached **{att.get('name', file_path)}** to card `{card_id}`\n"
        f"URL: {att.get('url', 'N/A')}"
    )


@mcp.tool()
def trello_attach_link(card_id: str, url: str, name: str = "") -> str:
    """Attach a URL (web link) to a Trello card.

    Args:
        card_id: Trello card ID
        url: The URL to attach
        name: Optional display name for the link (defaults to the URL)
    """
    att = trello.attach_link(card_id, url, name or None)
    return (
        f"Attached link **{att.get('name', url)}** to card `{card_id}`\n"
        f"URL: {att.get('url', url)}"
    )


@mcp.tool()
def trello_get_comments(card_id: str, limit: int = 50) -> str:
    """Get comments on a Trello card, newest first.

    Args:
        card_id: Trello card ID
        limit: Max number of comments to return (default 50, max 1000)
    """
    actions = trello.get_card_comments(card_id, limit=limit)

    if not actions:
        return f"No comments on card `{card_id}`."

    lines = [f"# Comments on `{card_id}` ({len(actions)})\n"]
    for a in actions:
        data = a.get("data", {})
        member = a.get("memberCreator", {})
        author = f"{member.get('fullName', '')} (@{member.get('username', '')})".strip()
        when = a.get("date", "")[:19].replace("T", " ")
        text = data.get("text", "")
        lines.append(f"## {author} — {when}\n\n{text}\n")
    return "\n".join(lines)


@mcp.tool()
def trello_add_comment(card_id: str, text: str) -> str:
    """Add a comment to a Trello card.

    Args:
        card_id: Trello card ID
        text: Comment body (supports Markdown)
    """
    action = trello.add_comment(card_id, text)
    member = action.get("memberCreator", {})
    author = f"{member.get('fullName', '')} (@{member.get('username', '')})".strip()
    return f"Added comment to card `{card_id}`" + (
        f" as {author}" if author != "(@)" else ""
    )


@mcp.tool()
def trello_comment_with_attachment(
    card_id: str, file_path: str, text: str = "", name: str = ""
) -> str:
    """Add a comment to a Trello card with a local file attached to it.

    Trello has no native file-on-comment concept — attachments belong to the
    card. This uploads the file as a card attachment, then posts a comment that
    embeds it (images render inline) or links it (other file types).

    Args:
        card_id: Trello card ID
        file_path: Absolute path to the local file to upload
        text: Optional comment body to prepend above the attachment (Markdown)
        name: Optional display name for the attachment (defaults to the filename)
    """
    safe_path = _resolve_upload_path(file_path)
    att = trello.add_attachment(card_id, safe_path, name or None)
    att_url = att.get("url", "")
    att_name = att.get("name") or name or os.path.basename(safe_path)

    mime = att.get("mimeType") or mimetypes.guess_type(safe_path)[0] or ""
    is_image = mime.startswith("image/")
    embed = f"![{att_name}]({att_url})" if is_image else f"[{att_name}]({att_url})"
    body = f"{text}\n\n{embed}" if text else embed

    trello.add_comment(card_id, body)
    kind = "image" if is_image else "file"
    return (
        f"Posted comment with {kind} attachment **{att_name}** on card `{card_id}`\n"
        f"URL: {att_url or 'N/A'}"
    )


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
def trello_create_label(board_id: str, name: str, color: str = "") -> str:
    """Create a new label on a Trello board.

    Args:
        board_id: Trello board ID
        name: Label name
        color: One of yellow, purple, blue, red, green, orange, black, sky, pink, lime.
            Leave empty for a "no color" label.
    """
    label = trello.create_label(board_id, name, color or None)
    return f"Created label **{label.get('name')}** ({label.get('color') or 'no color'}) — ID: `{label.get('id')}`"


@mcp.tool()
def trello_update_label(label_id: str, name: str = "", color: str = "") -> str:
    """Rename or recolor an existing Trello label.

    Args:
        label_id: Trello label ID
        name: New label name (leave empty to keep current)
        color: New color — yellow, purple, blue, red, green, orange, black, sky, pink, lime.
            Leave empty to keep current.
    """
    label = trello.update_label(
        label_id,
        name=name or None,
        color=color or None,
    )
    return f"Updated label **{label.get('name')}** ({label.get('color') or 'no color'}) — ID: `{label.get('id')}`"


@mcp.tool()
def trello_add_label_to_card(card_id: str, label_id: str) -> str:
    """Attach a single label to a Trello card without affecting other labels.

    Args:
        card_id: Trello card ID
        label_id: Trello label ID (from trello_get_labels)
    """
    trello.add_label_to_card(card_id, label_id)
    return f"Added label `{label_id}` to card `{card_id}`"


@mcp.tool()
def trello_remove_label_from_card(card_id: str, label_id: str) -> str:
    """Detach a single label from a Trello card.

    Args:
        card_id: Trello card ID
        label_id: Trello label ID
    """
    trello.remove_label_from_card(card_id, label_id)
    return f"Removed label `{label_id}` from card `{card_id}`"


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
