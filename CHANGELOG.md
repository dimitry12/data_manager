# Changelog

All notable changes to data-manager are documented here.

## Unreleased

## 0.4.0

- Discover the default SQLite path from `.data_manager_path` in the current
  working directory, allowing worktrees and temporary checkouts to share a
  database. Explicit configuration takes precedence; a missing file keeps
  no-op mode.

## 0.3.0

- Add advisory cache-only mode. Cache misses raise
  `NotFoundDoNotComputeError`, a subclass of `NotFoundError`, when a store is
  configured with `cache_only=True`.

## 0.2.0

- Add `metadata_context()` for applying default metadata to cache writes, with nested contexts restoring previous metadata and explicit `put(..., metadata=...)` taking precedence.

## 0.1.0

- Initial release.
- Add minimal SQLite-backed derivation cache with a fixed `derived_data` table.
- Store JSON-compatible values as JSON and binary values verbatim as SQLite BLOBs.
- Add process-wide configuration with no-op mode by default.
