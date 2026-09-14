from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_TABLE_NAME = "derived_data"
_METADATA_UNSET = object()
_context_metadata: ContextVar[Any] = ContextVar("data_manager_metadata", default=_METADATA_UNSET)


class NotFoundError(KeyError):
    """Raised when a requested derivation record does not exist."""


class NotFoundDoNotComputeError(NotFoundError):
    """Raised on a cache-only miss to advise against fallback computation."""


def _not_found_error(message: str, *, cache_only: bool) -> NotFoundError:
    if cache_only:
        return NotFoundDoNotComputeError(
            f"{message}; cache-only mode is enabled, so fallback computation should not run"
        )
    return NotFoundError(message)


@dataclass(frozen=True)
class DataRecord:
    """A stored derivation value."""

    derivation_type: str
    id: str
    params: Any
    data: Any
    metadata: Any | None = None
    value_type: str = "json"


def _canonical_json(value: Any) -> str:
    """Serialize JSON-compatible values deterministically."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _parameter_id(params: Any) -> str:
    """Return the full SHA-256 hash of canonical JSON parameters."""

    encoded = _canonical_json(params).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@contextmanager
def metadata_context(metadata: Any):
    """Use metadata for put calls that do not specify metadata explicitly."""

    token = _context_metadata.set(metadata)
    try:
        yield
    finally:
        _context_metadata.reset(token)


def _effective_metadata(metadata: Any) -> Any | None:
    if metadata is not _METADATA_UNSET:
        return metadata
    context_metadata = _context_metadata.get()
    if context_metadata is _METADATA_UNSET:
        return None
    return context_metadata


class NoOpDataManager:
    """Store implementation that computes ids but does not persist anything."""

    def __init__(self, *, cache_only: bool = False) -> None:
        self.cache_only = cache_only

    def put(
        self,
        derivation_type: str,
        params: Any,
        data: Any,
        *,
        metadata: Any = _METADATA_UNSET,
    ) -> str:
        return _parameter_id(params)

    def get(self, derivation_type: str, params: Any) -> DataRecord:
        record_id = _parameter_id(params)
        raise _not_found_error(
            f"No record for derivation_type={derivation_type!r}, id={record_id!r}; store is disabled",
            cache_only=self.cache_only,
        )


class DataManager:
    """SQLite-backed store for derivation outputs."""

    def __init__(self, path: str | Path, *, cache_only: bool = False) -> None:
        self.path = Path(path)
        self.cache_only = cache_only
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def put(
        self,
        derivation_type: str,
        params: Any,
        data: Any,
        *,
        metadata: Any = _METADATA_UNSET,
    ) -> str:
        """Insert or update data and return the record id."""

        record_id = _parameter_id(params)
        value_type, stored_data = self._encode_data(data)
        params_json = _canonical_json(params)
        metadata = _effective_metadata(metadata)
        metadata_json = None if metadata is None else _canonical_json(metadata)

        with closing(self.connect()) as conn:
            conn.execute(
                f"""
                INSERT INTO {_TABLE_NAME}
                    (derivation_type, id, params, metadata, value_type, data)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(derivation_type, id) DO UPDATE SET
                    params = excluded.params,
                    metadata = excluded.metadata,
                    value_type = excluded.value_type,
                    data = excluded.data
                """,
                (derivation_type, record_id, params_json, metadata_json, value_type, stored_data),
            )
            conn.commit()
        return record_id

    def get(self, derivation_type: str, params: Any) -> DataRecord:
        record_id = _parameter_id(params)
        with closing(self.connect()) as conn:
            row = conn.execute(
                f"""
                SELECT params, metadata, value_type, data
                FROM {_TABLE_NAME}
                WHERE derivation_type = ? AND id = ?
                """,
                (derivation_type, record_id),
            ).fetchone()

        if row is None:
            raise _not_found_error(
                f"No record for derivation_type={derivation_type!r}, id={record_id!r}",
                cache_only=self.cache_only,
            )

        params_json, metadata_json, value_type, data = row
        return DataRecord(
            derivation_type=derivation_type,
            id=record_id,
            params=json.loads(params_json),
            metadata=None if metadata_json is None else json.loads(metadata_json),
            data=self._decode_data(value_type, data),
            value_type=value_type,
        )

    def _ensure_table(self) -> None:
        with closing(self.connect()) as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
                    derivation_type TEXT NOT NULL,
                    id TEXT NOT NULL,
                    params TEXT NOT NULL,
                    metadata TEXT,
                    value_type TEXT NOT NULL,
                    data BLOB NOT NULL,
                    PRIMARY KEY (derivation_type, id)
                ) WITHOUT ROWID
                """
            )
            conn.commit()

    @staticmethod
    def _encode_data(data: Any) -> tuple[str, Any]:
        if isinstance(data, bytes | bytearray | memoryview):
            return "binary", sqlite3.Binary(bytes(data))
        return "json", _canonical_json(data)

    @staticmethod
    def _decode_data(value_type: str, data: Any) -> Any:
        if value_type == "binary":
            return bytes(data)
        if value_type == "json":
            return json.loads(data)
        raise ValueError(f"Unknown stored value_type: {value_type!r}")
