# data-manager

Minimal stdlib-only SQLite store for derivation outputs, including binary and JSON-compatible data.

Install directly from GitHub, for example:

```bash
pip install "data-manager @ git+https://github.com/dimitry12/data_manager.git@v0.1.0"
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

Configure once at process startup:

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

## Process-wide configuration

If you never call `configure()`, module-level helpers use no-op mode by default. In no-op mode, `put()` still returns the deterministic parameter hash, but nothing is persisted and `get()` raises `NotFoundError`.

You can also return to no-op mode explicitly:

```python
data_manager.configure()
```

You can also install a pre-created store:

```python
store = data_manager.DataManager(".data/derivations.db")
data_manager.configure(store=store)
```
