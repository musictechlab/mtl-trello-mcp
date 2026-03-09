# mtl-trello-mcp

An [MCP server](https://modelcontextprotocol.io/) that gives Claude Code full access to Trello — boards, lists, cards, labels, members, and search.

> **Private** — Built for MusicTech Lab internal use.

## Tools

| Tool | Description |
|------|-------------|
| `trello_list_boards` | List all boards |
| `trello_get_board` | Get board with all lists and cards |
| `trello_get_lists` | Get lists in a board |
| `trello_create_list` | Create a new list |
| `trello_get_card` | Get full card details |
| `trello_create_card` | Create a new card |
| `trello_update_card` | Update card name, description, due date |
| `trello_move_card` | Move card to a different list |
| `trello_archive_card` | Archive a card |
| `trello_search` | Search cards by keyword |
| `trello_get_labels` | Get board labels |
| `trello_get_members` | Get board members |

## Prerequisites

1. **Trello Power-Up** — register at [trello.com/power-ups/admin](https://trello.com/power-ups/admin)
2. **API Key & Token** — from the Power-Up admin page
3. **Python 3.10+** with Poetry

## Install

```bash
git clone https://github.com/musictechlab/mtl-trello-mcp.git
cd mtl-trello-mcp
cp .env.example .env
# Edit .env with your TRELLO_API_KEY and TRELLO_TOKEN
poetry install
```

## Register with Claude Code

```bash
claude mcp add --scope user --transport stdio mtl-trello -- bash -c "cd /path/to/mtl-trello-mcp && poetry run python -m mtl_trello_mcp"
```

## Usage in Claude Code

```
Show me all my Trello boards
```

```
What cards are on the StreamData Lab board?
```

```
Create a card "Fix ISRC validation" in the BACKLOG list
```

```
Move card abc123 to the DONE list
```

```
Search Trello for "audio fingerprinting"
```

## License

MIT

---

Built by [MusicTech Lab](https://musictechlab.io)
