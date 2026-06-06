# Changelog

All notable changes to data-manager are documented here.

## Unreleased

## 0.2.0

- Add `metadata_context()` for applying default metadata to cache writes, with nested contexts restoring previous metadata and explicit `put(..., metadata=...)` taking precedence.

## 0.1.0

- Initial release.
- Add minimal SQLite-backed derivation cache with a fixed `derived_data` table.
- Store JSON-compatible values as JSON and binary values verbatim as SQLite BLOBs.
- Add process-wide configuration with no-op mode by default.
