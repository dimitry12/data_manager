# Developer commands for data-manager.
# These commands are for maintaining the package, not for end-user runtime use.

.PHONY: test build clean

# Run the test suite in parallel. Dependencies are pinned and installed by uv.
test:
	uv run --with pytest==8.4.2 --with pytest-xdist==3.8.0 --python=3.13 python -m pytest -n auto

# Build source and wheel distributions. Build dependency is pinned in pyproject.toml.
build:
	uv build

# Remove local generated artifacts.
clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
