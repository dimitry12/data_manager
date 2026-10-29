# data-manager

Minimal stdlib-only SQLite store for derivation outputs, including binary and JSON-compatible data.

Install directly from GitHub, for example:

```bash
pip install "data-manager @ git+https://github.com/dimitry12/data_manager.git@v0.4.0"
```

## Model

All records are stored in a single SQLite table named `derived_data`:

- `derivation_type`: logical kind of derivation/output.
- `id`: full SHA-256 hash of canonical JSON `params`.
- `params`: JSON provenance parameters, including inputs.
- `metadata`: JSON value-adjacent data excluded from hashing/provenance.
- `value_type`: distinguishes `binary` from `json` payloads.
- `data`: payload storage.

The primary key is `(derivation_type, id)`, so different derivation types can use identical parameters without colliding.

## Typical cache usage

Configure once at process startup (or use the `.data_manager_path` file described below):

```python
# app_startup.py
import data_manager

data_manager.configure(".data/derivations.db")
```

Then use it inside expensive functions. The derivation type is the function name, and the parameters are the function inputs: args and kwargs. A convenient pattern is to build one dictionary and unpack it into both `get()` and `put()`.

```python
# captions.py
import data_manager


def caption_image(image_path: str, *, model: str = "captioner-v1") -> dict:
    cache_key = {
        "derivation_type": "captions.caption_image",
        "params": {
            "args": [image_path],
            "kwargs": {"model": model},
        },
    }

    try:
        return data_manager.get(**cache_key).data
    except data_manager.NotFoundError:
        pass

    result = run_expensive_captioning(image_path, model=model)
    data_manager.put(**cache_key, data=result)
    return result
```

For binary outputs, pass bytes directly. They are stored verbatim as SQLite BLOBs, so image bytes remain inspectable/renderable by SQLite viewers.

```python
def make_thumbnail(image_path: str, *, size: int = 256) -> bytes:
    cache_key = {
        "derivation_type": "images.make_thumbnail",
        "params": {
            "args": [image_path],
            "kwargs": {"size": size},
        },
    }

    try:
        return data_manager.get(**cache_key).data
    except data_manager.NotFoundError:
        pass

    thumbnail = render_thumbnail_bytes(image_path, size=size)
    data_manager.put(**cache_key, data=thumbnail)
    return thumbnail
```

`get()` returns a `DataRecord` with `.id`, `.data`, `.metadata`, `.params`, `.derivation_type`, and `.value_type`. Values passed as `bytes`, `bytearray`, or `memoryview` are stored verbatim as SQLite BLOBs and returned as `bytes`. Other values are stored as canonical JSON and returned as Python values.

## Metadata context

Use `metadata_context()` to apply metadata to multiple `put()` calls without passing `metadata=` each time.

```python
with data_manager.metadata_context({"experiment": "baseline", "model": "captioner-v1"}):
    caption = caption_image("image.png")
    thumbnail = make_thumbnail("image.png")
```

Nested metadata contexts overwrite while active and restore the previous metadata on exit. Explicit `metadata=` on `put()` wins over context metadata, including `metadata=None`.

## Process-wide configuration

### Default database path

Without explicit configuration, the first `get()`, `put()`, or `get_store()` checks for a file named `.data_manager_path` in the current working directory. Put the database path in this UTF-8 text file, for example:

```text
/absolute/path/to/shared/derivations.db
```

Surrounding whitespace and trailing newlines are stripped. Absolute paths are used directly; relative paths are resolved against the directory containing the file. Only the current directory is checked, not parent directories. An empty or whitespace-only file raises `ValueError`; other file read errors are propagated.

This lets Git worktrees and temporary checkouts reuse one database without copying it. Keep the database outside the checkouts, add `.data_manager_path` to the consuming project's `.gitignore`, and create or copy the small pointer file into each checkout with the same absolute path. Git does not automatically copy ignored files into new worktrees. Cache identity still depends on derivation type and parameters, not the checkout, so include any relevant code/input version in your parameters.

The selected store is reused for the process, even if the working directory or pointer file changes. Calling `configure()` without arguments re-reads the default from the current directory:

```python
data_manager.configure()
```

If `.data_manager_path` is absent, the default is no-op mode: `put()` still returns the deterministic parameter hash, but nothing is persisted and `get()` raises `NotFoundError`.

Explicit `configure(path)` or `configure(store=...)` takes precedence and does not read the pointer file. Direct `DataManager(path)` instances also continue to require an explicit path.

You can install a pre-created store:

```python
store = data_manager.DataManager(".data/derivations.db")
data_manager.configure(store=store)
```

### Cache-only misses

Use cache-only mode when a missing value should not trigger potentially
expensive fallback computation:

```python
data_manager.configure(".data/derivations.db", cache_only=True)

try:
    result = data_manager.get(**cache_key).data
except data_manager.NotFoundDoNotComputeError:
    result = None  # Skip or report the missing derivation; do not compute it.
except data_manager.NotFoundError:
    result = run_expensive_computation()
```

`NotFoundDoNotComputeError` is a subclass of `NotFoundError`, so existing code
that treats all misses alike remains compatible. Code that respects the
cache-only advice must catch the subclass before `NotFoundError`.

Cache-only behavior belongs to the store and is therefore consistent between
the module-level helper, `get_store()`, and direct stores:

```python
store = data_manager.DataManager(".data/derivations.db", cache_only=True)

try:
    result = store.get(**cache_key).data
except data_manager.NotFoundDoNotComputeError:
    result = None
```

Passing a pre-created store with `configure(store=store, cache_only=True)` also
enables cache-only behavior on that store.
