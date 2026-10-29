import pytest

import data_manager
from data_manager import DataManager, NotFoundDoNotComputeError, NotFoundError, runtime


@pytest.fixture(autouse=True)
def reset_data_manager_configuration(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runtime, "_store", None)


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


def test_default_store_is_noop(tmp_path):
    with pytest.raises(NotFoundError):
        data_manager.get("demo", {"x": 1})

    assert list(tmp_path.iterdir()) == []


def test_default_store_uses_relative_path_file_without_configure(tmp_path):
    (tmp_path / ".data_manager_path").write_text("  .data/cache.db\n", encoding="utf-8")

    data_manager.put("demo", {"x": 1}, "value")

    assert data_manager.get("demo", {"x": 1}).data == "value"
    assert data_manager.get_store().path == tmp_path / ".data" / "cache.db"
    assert (tmp_path / ".data" / "cache.db").is_file()


def test_configure_uses_absolute_path_file(tmp_path):
    database_path = tmp_path / "données" / "cache with spaces.db"
    (tmp_path / ".data_manager_path").write_text(f"{database_path}\n", encoding="utf-8")

    store = data_manager.configure()
    store.put("demo", {"x": 1}, "value")

    assert store.path == database_path
    assert store.get("demo", {"x": 1}).data == "value"


def test_checkouts_share_database_via_absolute_path_files(tmp_path, monkeypatch):
    database_path = tmp_path / "shared" / "derivations.db"
    first_checkout = tmp_path / "worktree-a"
    second_checkout = tmp_path / "worktree-b"
    for checkout in (first_checkout, second_checkout):
        checkout.mkdir()
        (checkout / ".data_manager_path").write_text(f"{database_path}\n", encoding="utf-8")

    monkeypatch.chdir(first_checkout)
    data_manager.put("demo", {"x": 1}, "from first checkout")

    monkeypatch.chdir(second_checkout)
    data_manager.configure()

    assert data_manager.get("demo", {"x": 1}).data == "from first checkout"
    data_manager.put("demo", {"x": 2}, "from second checkout")

    monkeypatch.chdir(first_checkout)
    data_manager.configure()

    assert data_manager.get("demo", {"x": 2}).data == "from second checkout"
    assert list(first_checkout.iterdir()) == [first_checkout / ".data_manager_path"]
    assert list(second_checkout.iterdir()) == [second_checkout / ".data_manager_path"]


def test_configure_rediscovers_path_file(tmp_path):
    path_file = tmp_path / ".data_manager_path"
    path_file.write_text("first.db", encoding="utf-8")
    first_store = data_manager.get_store()
    path_file.write_text("second.db", encoding="utf-8")

    assert data_manager.get_store() is first_store

    second_store = data_manager.configure()

    assert second_store is not first_store
    assert second_store.path == tmp_path / "second.db"


@pytest.mark.parametrize("contents", ["from-file.db\n", " \n\t"])
def test_explicit_path_takes_precedence_over_path_file(tmp_path, contents):
    (tmp_path / ".data_manager_path").write_text(contents, encoding="utf-8")
    explicit_path = tmp_path / "explicit.db"

    store = data_manager.configure(explicit_path)

    assert store.path == explicit_path
    assert not (tmp_path / "from-file.db").exists()


@pytest.mark.parametrize("contents", ["from-file.db\n", " \n\t"])
def test_explicit_store_takes_precedence_over_path_file(tmp_path, contents):
    (tmp_path / ".data_manager_path").write_text(contents, encoding="utf-8")
    store = DataManager(tmp_path / "explicit.db")

    assert data_manager.configure(store=store) is store
    assert not (tmp_path / "from-file.db").exists()


@pytest.mark.parametrize("contents", ["", " \n\t"])
@pytest.mark.parametrize("initialize", [data_manager.get_store, data_manager.configure])
def test_empty_path_file_is_rejected(tmp_path, contents, initialize):
    (tmp_path / ".data_manager_path").write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match=r"\.data_manager_path.*database path"):
        initialize()


def test_path_file_read_errors_are_not_silently_ignored(tmp_path):
    (tmp_path / ".data_manager_path").mkdir()

    with pytest.raises(OSError):
        data_manager.get_store()


def test_default_does_not_search_parent_directories(tmp_path, monkeypatch):
    (tmp_path / ".data_manager_path").write_text("cache.db", encoding="utf-8")
    child = tmp_path / "child"
    child.mkdir()
    monkeypatch.chdir(child)

    with pytest.raises(NotFoundError):
        data_manager.get("demo", {"x": 1})

    assert not (tmp_path / "cache.db").exists()
    assert list(child.iterdir()) == []


def test_discovered_relative_path_stays_anchored_after_chdir(tmp_path, monkeypatch):
    (tmp_path / ".data_manager_path").write_text("cache.db", encoding="utf-8")
    store = data_manager.get_store()
    child = tmp_path / "child"
    child.mkdir()
    monkeypatch.chdir(child)

    data_manager.put("demo", {"x": 1}, "value")

    assert data_manager.get_store() is store
    assert data_manager.get("demo", {"x": 1}).data == "value"
    assert not (child / "cache.db").exists()


def test_cache_only_mode_uses_path_file(tmp_path):
    (tmp_path / ".data_manager_path").write_text("cache.db", encoding="utf-8")

    store = data_manager.configure(cache_only=True)

    assert store.path == tmp_path / "cache.db"
    with pytest.raises(NotFoundDoNotComputeError):
        data_manager.get("demo", {"x": 1})
    data_manager.put("demo", {"x": 1}, "value")
    assert data_manager.get("demo", {"x": 1}).data == "value"


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


def test_cache_only_miss_advises_against_fallback_computation(tmp_path):
    data_manager.configure(tmp_path / "cache.db", cache_only=True)

    with pytest.raises(NotFoundDoNotComputeError, match="fallback computation should not run"):
        data_manager.get("demo", {"x": 1})


def test_noop_cache_only_miss_has_the_same_behavior():
    data_manager.configure(cache_only=True)

    with pytest.raises(NotFoundDoNotComputeError):
        data_manager.get("demo", {"x": 1})


def test_cache_only_advisory_is_a_not_found_error():
    assert issubclass(NotFoundDoNotComputeError, NotFoundError)


def test_cache_only_mode_returns_existing_records(tmp_path):
    data_manager.configure(tmp_path / "cache.db", cache_only=True)
    data_manager.put("demo", {"x": 1}, "value")

    assert data_manager.get("demo", {"x": 1}).data == "value"


def test_direct_store_honors_cache_only_mode(tmp_path):
    store = DataManager(tmp_path / "cache.db", cache_only=True)

    with pytest.raises(NotFoundDoNotComputeError):
        store.get("demo", {"x": 1})


def test_configure_applies_cache_only_mode_to_precreated_store(tmp_path):
    store = DataManager(tmp_path / "cache.db")
    data_manager.configure(store=store, cache_only=True)

    with pytest.raises(NotFoundDoNotComputeError):
        store.get("demo", {"x": 1})

    with pytest.raises(NotFoundDoNotComputeError):
        data_manager.get_store().get("demo", {"x": 1})


def test_configure_resets_cache_only_mode(tmp_path):
    data_manager.configure(tmp_path / "cache.db", cache_only=True)
    data_manager.configure(tmp_path / "other.db")

    with pytest.raises(NotFoundError) as error:
        data_manager.get("demo", {"x": 1})

    assert type(error.value) is NotFoundError
