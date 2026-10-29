from __future__ import annotations

from pathlib import Path
from typing import Any

from .store import _METADATA_UNSET, DataManager, DataRecord, NoOpDataManager, metadata_context

Store = DataManager | NoOpDataManager

_store: Store | None = None


def _default_database_path() -> Path | None:
    path_file = Path.cwd() / ".data_manager_path"
    try:
        path = path_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not path:
        raise ValueError(f"{path_file} must contain a database path")
    return path_file.parent / path


def configure(
    path: str | Path | None = None,
    *,
    store: Store | None = None,
    cache_only: bool = False,
) -> Store:
    """Set the process-wide store and cache-miss behavior.

    An explicit path or store takes precedence. Otherwise, read the database
    path from .data_manager_path in the current working directory, falling back
    to no-op mode if the file is absent. In cache-only mode, the configured
    store raises ``NotFoundDoNotComputeError`` on a miss.
    """

    global _store

    if store is not None:
        if path is not None:
            raise ValueError("store cannot be combined with path")
        store.cache_only = cache_only
        configured_store = store
    else:
        if path is None:
            path = _default_database_path()
        if path is None:
            configured_store = NoOpDataManager(cache_only=cache_only)
        else:
            configured_store = DataManager(path, cache_only=cache_only)

    _store = configured_store
    return _store


def get_store() -> Store:
    if _store is None:
        return configure()
    return _store


def put(
    derivation_type: str,
    params: Any,
    data: Any,
    *,
    metadata: Any = _METADATA_UNSET,
) -> str:
    return get_store().put(derivation_type, params, data, metadata=metadata)


def get(derivation_type: str, params: Any) -> DataRecord:
    return get_store().get(derivation_type, params)
