# Changelog

All notable user-visible changes to Elixis will be documented in this file.

This project follows the intent of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added

- Started the project changelog so product, CLI, API, and synthesis-engine changes have a durable release history.

### Fixed

- Streaming identity synthesis now finishes the game in the `resolution` phase and records the output, like the non-streaming path.
- Calling `declare_themes()` again without new input on a game in progress is refused instead of keeping stale threads and duplicating tensions.
- A backup that fails while writing no longer leaves a partial archive behind for `list_backups()` and restore to pick up.
