from __future__ import annotations

from pathlib import Path
from typing import Any

from .store import _METADATA_UNSET, DataManager, DataRecord, NoOpDataManager, metadata_context

Store = DataManager | NoOpDataManager

_store: Store = NoOpDataManager()


def configure(
    path: str | Path | None = None,
    *,
    store: Store | None = None,
    cache_only: bool = False,
) -> Store:
    """Set the process-wide store and cache-miss behavior.

    Configure once at process startup, then use module-level helpers from any
    other module in the same process. With no configuration, data-manager stays
    in no-op mode. In cache-only mode, the configured store raises
    ``NotFoundDoNotComputeError`` on a miss.
    """

    global _store

    if store is not None:
        if path is not None:
            raise ValueError("store cannot be combined with path")
        store.cache_only = cache_only
        configured_store = store
    elif path is None:
        configured_store = NoOpDataManager(cache_only=cache_only)
    else:
        configured_store = DataManager(path, cache_only=cache_only)

    _store = configured_store
    return _store


def get_store() -> Store:
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
