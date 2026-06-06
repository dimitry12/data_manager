import sqlite3

import data_manager
from data_manager import DataManager


def test_put_get_binary_roundtrip(tmp_path):
    store = DataManager(tmp_path / "data.db")
    params = {"input": "image.png", "threshold": 0.8}
    data = b"\x00\x01caption\xff"

    record_id = store.put("caption", params, data, metadata={"model": "demo"})
    record = store.get("caption", params)

    assert len(record_id) == 64
    assert record.id == record_id
    assert record.derivation_type == "caption"
    assert record.params == params
    assert record.metadata == {"model": "demo"}
    assert record.value_type == "binary"
    assert record.data == data

    with sqlite3.connect(tmp_path / "data.db") as conn:
        storage_type, stored_data = conn.execute("SELECT typeof(data), data FROM derived_data").fetchone()
    assert storage_type == "blob"
    assert stored_data == data


def test_put_get_json_roundtrip_without_manual_encoding(tmp_path):
    store = DataManager(tmp_path / "data.db")
    params = {"source": "numbers"}
    value = {"caption": "hello", "scores": [1, 2.5], "accepted": True, "nothing": None}

    store.put("analysis", params, value, metadata={"debug": "not hashed"})
    record = store.get("analysis", params)

    assert record.data == value
    assert record.value_type == "json"
    assert record.metadata == {"debug": "not hashed"}


def test_put_get_string_roundtrip_without_manual_encoding(tmp_path):
    store = DataManager(tmp_path / "data.db")

    store.put("caption", {"image": "x.png"}, "plain caption")

    assert store.get("caption", {"image": "x.png"}).data == "plain caption"


def test_metadata_context_applies_when_metadata_is_omitted(tmp_path):
    store = DataManager(tmp_path / "data.db")

    with data_manager.metadata_context({"run": "demo"}):
        store.put("demo", {"x": 1}, "value")

    assert store.get("demo", {"x": 1}).metadata == {"run": "demo"}


def test_nested_metadata_context_overwrites_then_restores(tmp_path):
    store = DataManager(tmp_path / "data.db")

    with data_manager.metadata_context({"scope": "outer"}):
        store.put("demo", {"x": 1}, "outer")
        with data_manager.metadata_context({"scope": "inner"}):
            store.put("demo", {"x": 2}, "inner")
        store.put("demo", {"x": 3}, "outer-again")

    assert store.get("demo", {"x": 1}).metadata == {"scope": "outer"}
    assert store.get("demo", {"x": 2}).metadata == {"scope": "inner"}
    assert store.get("demo", {"x": 3}).metadata == {"scope": "outer"}


def test_explicit_metadata_overrides_context_metadata(tmp_path):
    store = DataManager(tmp_path / "data.db")

    with data_manager.metadata_context({"scope": "context"}):
        store.put("demo", {"x": 1}, "explicit", metadata={"scope": "explicit"})
        store.put("demo", {"x": 2}, "none", metadata=None)

    assert store.get("demo", {"x": 1}).metadata == {"scope": "explicit"}
    assert store.get("demo", {"x": 2}).metadata is None


def test_hash_uses_canonical_params_but_not_metadata(tmp_path):
    store = DataManager(tmp_path / "data.db")
    params_a = {"b": 2, "a": 1}
    params_b = {"a": 1, "b": 2}

    id_a = store.put("demo", params_a, "first", metadata={"note": "one"})
    id_b = store.put("demo", params_b, "second", metadata={"note": "two"})

    assert id_a == id_b
    assert store.get("demo", params_a).data == "second"
    assert store.get("demo", params_a).metadata == {"note": "two"}


def test_derivation_type_namespaces_ids(tmp_path):
    store = DataManager(tmp_path / "data.db")
    params = {"x": 1}

    first_id = store.put("first", params, b"a")
    second_id = store.put("second", params, b"b")

    assert first_id == second_id
    assert store.get("first", params).data == b"a"
    assert store.get("second", params).data == b"b"


def test_none_is_valid_params_value(tmp_path):
    store = DataManager(tmp_path / "data.db")

    record_id = store.put("demo", None, b"none")

    assert len(record_id) == 64
    assert store.get("demo", None).data == b"none"


def test_values_are_parameterized(tmp_path):
    store = DataManager(tmp_path / "data.db")
    malicious = "x'; DROP TABLE derived_data; --"
    store.put(malicious, {"id": malicious}, b"safe")

    with sqlite3.connect(tmp_path / "data.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM derived_data").fetchone()[0] == 1

    assert store.get(malicious, {"id": malicious}).data == b"safe"
