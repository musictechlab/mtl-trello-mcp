"""Unit tests for the attachment helpers in trello.py."""

from unittest.mock import MagicMock, patch

import pytest

from mtl_trello_mcp import server, trello


@patch.dict("os.environ", {"TRELLO_API_KEY": "test-key", "TRELLO_TOKEN": "test-token"})
@patch("mtl_trello_mcp.trello.httpx.post")
def test_add_attachment_multipart(mock_post, tmp_path):
    """add_attachment uploads the file via multipart with auth params."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"name": "shot.png", "url": "https://trello/att/1"}
    mock_post.return_value = mock_resp

    img = tmp_path / "shot.png"
    img.write_bytes(b"\x89PNG\r\n")

    result = trello.add_attachment("card123", str(img), name="Mockup 1")

    assert result["url"] == "https://trello/att/1"
    args, kwargs = mock_post.call_args
    # Posts to the card's attachments endpoint
    assert args[0].endswith("/cards/card123/attachments")
    # Auth params + the explicit name are sent as query params
    assert kwargs["params"]["key"] == "test-key"
    assert kwargs["params"]["token"] == "test-token"
    assert kwargs["params"]["name"] == "Mockup 1"
    # The file is sent as multipart form-data under "file"
    assert "file" in kwargs["files"]
    mock_resp.raise_for_status.assert_called_once()


@patch("mtl_trello_mcp.trello._request")
def test_attach_link(mock_request):
    """attach_link POSTs the URL to the attachments endpoint."""
    mock_request.return_value = {"name": "Loom", "url": "https://loom/x"}

    trello.attach_link("card123", "https://loom/x", name="Loom")

    mock_request.assert_called_once_with(
        "POST",
        "/cards/card123/attachments",
        {"url": "https://loom/x", "name": "Loom"},
    )


def test_resolve_upload_path_allows_file_in_root(tmp_path, monkeypatch):
    """A regular file inside the allowed root resolves to its real path."""
    monkeypatch.setenv("TRELLO_UPLOAD_DIR", str(tmp_path))
    f = tmp_path / "shot.png"
    f.write_bytes(b"\x89PNG\r\n")

    assert server._resolve_upload_path(str(f)) == str(f.resolve())


def test_resolve_upload_path_rejects_outside_root(tmp_path, monkeypatch):
    """A path that escapes the allowed root is rejected."""
    monkeypatch.setenv("TRELLO_UPLOAD_DIR", str(tmp_path / "staging"))
    (tmp_path / "staging").mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("token")

    with pytest.raises(ValueError, match="must be within"):
        server._resolve_upload_path(str(secret))


def test_resolve_upload_path_rejects_non_file(tmp_path, monkeypatch):
    """A directory (or missing path) inside the root is rejected."""
    monkeypatch.setenv("TRELLO_UPLOAD_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="not a regular file"):
        server._resolve_upload_path(str(tmp_path))


def test_resolve_upload_path_rejects_hidden_component(tmp_path, monkeypatch):
    """A file inside a dotdir (e.g. ~/.ssh/id_rsa) is rejected by default."""
    monkeypatch.setenv("TRELLO_UPLOAD_DIR", str(tmp_path))
    monkeypatch.delenv("TRELLO_ALLOW_HIDDEN", raising=False)
    ssh = tmp_path / ".ssh"
    ssh.mkdir()
    key = ssh / "config_note.txt"  # ordinary name; the .ssh component is the trigger
    key.write_text("data")

    with pytest.raises(ValueError, match="hidden path component"):
        server._resolve_upload_path(str(key))


def test_resolve_upload_path_allows_hidden_when_opted_in(tmp_path, monkeypatch):
    """TRELLO_ALLOW_HIDDEN=1 lifts the hidden-component restriction."""
    monkeypatch.setenv("TRELLO_UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("TRELLO_ALLOW_HIDDEN", "1")
    hidden_dir = tmp_path / ".config"
    hidden_dir.mkdir()
    f = hidden_dir / "note.txt"
    f.write_text("data")

    assert server._resolve_upload_path(str(f)) == str(f.resolve())


def test_resolve_upload_path_rejects_sensitive_name(tmp_path, monkeypatch):
    """A sensitive filename pattern is rejected even when not hidden."""
    monkeypatch.setenv("TRELLO_UPLOAD_DIR", str(tmp_path))
    cert = tmp_path / "server.pem"
    cert.write_text("-----BEGIN CERTIFICATE-----")

    with pytest.raises(ValueError, match="sensitive file"):
        server._resolve_upload_path(str(cert))


def test_resolve_upload_path_rejects_oversized(tmp_path, monkeypatch):
    """A file above the size cap is rejected."""
    monkeypatch.setenv("TRELLO_UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("TRELLO_MAX_UPLOAD_MB", "1")
    big = tmp_path / "big.png"
    big.write_bytes(b"\x00" * (2 * 1024 * 1024))

    with pytest.raises(ValueError, match="too large"):
        server._resolve_upload_path(str(big))


@patch("mtl_trello_mcp.trello._request")
def test_add_comment(mock_request):
    """add_comment POSTs the text to the card's comment-actions endpoint."""
    mock_request.return_value = {"id": "act1", "data": {"text": "hello"}}

    trello.add_comment("card123", "hello")

    mock_request.assert_called_once_with(
        "POST",
        "/cards/card123/actions/comments",
        {"text": "hello"},
    )
