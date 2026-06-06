from __future__ import annotations

from pathlib import Path
from typing import Any

from .store import _METADATA_UNSET, DataManager, DataRecord, NoOpDataManager, metadata_context

Store = DataManager | NoOpDataManager

_store: Store = NoOpDataManager()


def configure(path: str | Path | None = None, *, store: Store | None = None) -> Store:
    """Set the process-wide store.

    Configure once at process startup, then use module-level helpers from any
    other module in the same process. With no configuration, data-manager stays
    in no-op mode.
    """

    global _store

    if store is not None:
        if path is not None:
            raise ValueError("store cannot be combined with path")
        _store = store
    elif path is None:
        _store = NoOpDataManager()
    else:
        _store = DataManager(path)

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
