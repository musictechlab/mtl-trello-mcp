# mtl-trello-mcp

MCP server for Trello project management.

## Tech Stack

- **Language**: Python 3.10+
- **Package manager**: Poetry
- **MCP framework**: FastMCP (`mcp[cli]`)
- **Linter**: Ruff
- **Test framework**: Pytest

## Commands

| Action | Command |
|--------|---------|
| Install | `poetry install` |
| Test | `poetry run pytest` |
| Lint | `poetry run ruff check .` |
| Format | `poetry run ruff format .` |
| Run | `poetry run python -m mtl_trello_mcp` |

## Architecture

- `src/mtl_trello_mcp/server.py` — MCP server with all tool definitions
- `src/mtl_trello_mcp/__main__.py` — Entry point
- Trello API access via `TRELLO_API_KEY` and `TRELLO_TOKEN` env vars

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `TRELLO_API_KEY` | Trello Power-Up API key | Yes |
| `TRELLO_TOKEN` | Trello API token | Yes |
| `TRELLO_UPLOAD_DIR` | Allowed root for attachment uploads (defaults to `~`) | No |
