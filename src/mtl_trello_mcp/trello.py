"""Trello API client — boards, lists, cards, labels, members, search."""

import os
import sys

import httpx

BASE_URL = "https://api.trello.com/1"


def _auth_params() -> dict:
    """Get Trello API key and token from environment."""
    api_key = os.getenv("TRELLO_API_KEY")
    token = os.getenv("TRELLO_TOKEN")
    if not api_key or not token:
        print(
            "ERROR: TRELLO_API_KEY and TRELLO_TOKEN must be set.\n"
            "Get them from: https://trello.com/power-ups/admin",
            file=sys.stderr,
        )
        raise ValueError("TRELLO_API_KEY and TRELLO_TOKEN are required")
    return {"key": api_key, "token": token}


def _request(method: str, endpoint: str, params: dict | None = None) -> dict | list:
    """Make authenticated request to Trello API."""
    url = f"{BASE_URL}{endpoint}"
    all_params = {**(params or {}), **_auth_params()}
    resp = httpx.request(method, url, params=all_params, timeout=15)
    resp.raise_for_status()
    return resp.json()


# --- Boards ---


def get_boards() -> list[dict]:
    """Get all boards for the authenticated user."""
    return _request("GET", "/members/me/boards", {"fields": "name,url,closed"})


def get_board(board_id: str) -> dict:
    """Get a specific board."""
    return _request("GET", f"/boards/{board_id}")


# --- Lists ---


def get_lists(board_id: str) -> list[dict]:
    """Get all open lists in a board."""
    return _request("GET", f"/boards/{board_id}/lists", {"filter": "open"})


def create_list(board_id: str, name: str) -> dict:
    """Create a new list in a board."""
    return _request("POST", "/lists", {"name": name, "idBoard": board_id})


# --- Cards ---


def get_cards(list_id: str) -> list[dict]:
    """Get all cards in a list."""
    return _request("GET", f"/lists/{list_id}/cards")


def get_card(card_id: str) -> dict:
    """Get a specific card with full details."""
    return _request(
        "GET",
        f"/cards/{card_id}",
        {
            "fields": "name,desc,url,due,closed,idList,labels",
            "members": "true",
            "member_fields": "fullName,username",
        },
    )


def create_card(
    list_id: str,
    name: str,
    desc: str | None = None,
    due: str | None = None,
    label_ids: str | None = None,
    member_ids: str | None = None,
) -> dict:
    """Create a new card."""
    params: dict = {"name": name, "idList": list_id}
    if desc:
        params["desc"] = desc
    if due:
        params["due"] = due
    if label_ids:
        params["idLabels"] = label_ids
    if member_ids:
        params["idMembers"] = member_ids
    return _request("POST", "/cards", params)


def update_card(
    card_id: str,
    name: str | None = None,
    desc: str | None = None,
    list_id: str | None = None,
    due: str | None = None,
    closed: bool | None = None,
) -> dict:
    """Update a card."""
    params: dict = {}
    if name:
        params["name"] = name
    if desc:
        params["desc"] = desc
    if list_id:
        params["idList"] = list_id
    if due:
        params["due"] = due
    if closed is not None:
        params["closed"] = str(closed).lower()
    return _request("PUT", f"/cards/{card_id}", params)


def move_card(card_id: str, list_id: str) -> dict:
    """Move a card to a different list."""
    return update_card(card_id, list_id=list_id)


def archive_card(card_id: str) -> dict:
    """Archive a card."""
    return update_card(card_id, closed=True)


def delete_card(card_id: str) -> dict:
    """Delete a card permanently."""
    return _request("DELETE", f"/cards/{card_id}")


# --- Labels ---


def get_labels(board_id: str) -> list[dict]:
    """Get all labels for a board."""
    return _request("GET", f"/boards/{board_id}/labels")


# --- Members ---


def get_board_members(board_id: str) -> list[dict]:
    """Get all members of a board."""
    return _request(
        "GET", f"/boards/{board_id}/members", {"fields": "fullName,username"}
    )


def get_me() -> dict:
    """Get current authenticated user info."""
    return _request("GET", "/members/me")


# --- Search ---


def search_cards(
    query: str, board_id: str | None = None, max_results: int = 10
) -> list[dict]:
    """Search for cards across boards."""
    params: dict = {"query": query, "modelTypes": "cards", "cards_limit": max_results}
    if board_id:
        params["idBoards"] = board_id
    result = _request("GET", "/search", params)
    return result.get("cards", [])
