# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup
- `trello_list_boards` — list all boards
- `trello_get_board` — get board with all lists and cards
- `trello_get_lists` — get lists in a board
- `trello_create_list` — create a new list
- `trello_get_card` — get full card details
- `trello_create_card` — create a new card
- `trello_update_card` — update card name, description, due date
- `trello_move_card` — move card to a different list
- `trello_archive_card` — archive a card
- `trello_search` — search cards by keyword
- `trello_get_labels` — get board labels
- `trello_create_label` — create a new label on a board
- `trello_update_label` — rename or recolor an existing label
- `trello_add_label_to_card` — attach a single label to a card (preserves other labels)
- `trello_remove_label_from_card` — detach a single label from a card
- `trello_get_members` — get board members
- `trello_get_comments` — read comments on a card, newest first

### Changed
- `trello_update_card` now accepts `label_ids` (comma-separated) to replace a card's full label set
