import pytest

import data_manager
from data_manager import DataManager, NotFoundError


@pytest.fixture(autouse=True)
def reset_data_manager_configuration():
    data_manager.configure()
    yield
    data_manager.configure()


def test_configure_once_then_use_module_level_functions(tmp_path):
    data_manager.configure(tmp_path / "cache.db")
    params = {"input": "x"}

    record_id = data_manager.put("demo", params, {"value": 42})
    record = data_manager.get("demo", params)

    assert len(record_id) == 64
    assert record.id == record_id
    assert record.data == {"value": 42}


def test_get_returns_id_metadata_and_data(tmp_path):
    data_manager.configure(tmp_path / "cache.db")
    params = {"input": "x"}

    record_id = data_manager.put("demo", params, "value", metadata={"note": "debug"})
    record = data_manager.get("demo", params)

    assert record.id == record_id
    assert record.metadata == {"note": "debug"}
    assert record.data == "value"


def test_configure_can_install_precreated_store(tmp_path):
    store = DataManager(tmp_path / "cache.db")

    data_manager.configure(store=store)
    data_manager.put("demo", {"x": 1}, "value")

    assert data_manager.get_store() is store
    assert data_manager.get("demo", {"x": 1}).data == "value"


def test_default_store_is_noop():
    with pytest.raises(NotFoundError):
        data_manager.get("demo", {"x": 1})


def test_configure_without_path_returns_to_noop(tmp_path):
    data_manager.configure(tmp_path / "cache.db")
    data_manager.configure()

    with pytest.raises(NotFoundError):
        data_manager.get("demo", {"x": 1})


def test_noop_store_computes_ids_but_never_persists():
    params = {"x": 1}

    record_id = data_manager.put("demo", params, b"value")

    assert len(record_id) == 64
    with pytest.raises(NotFoundError):
        data_manager.get("demo", params)


def test_configure_rejects_path_and_store_together(tmp_path):
    with pytest.raises(ValueError):
        data_manager.configure(tmp_path / "cache.db", store=DataManager(tmp_path / "other.db"))
