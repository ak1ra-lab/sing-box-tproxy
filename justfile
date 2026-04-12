# Show available recipes
default:
    @just --list --unsorted

# Sync development dependencies (may update uv.lock if pyproject.toml changed)
sync *ARGS:
    uv sync --group dev {{ARGS}}

# Lint and format source code
lint:
    uv run ruff check --fix src/ tests/
    uv run ruff format src/ tests/

# Run static type checks with Astral ty
typecheck:
    uv run ty check src/

# Run tests
test *ARGS:
    uv run pytest -v {{ARGS}} tests/

# Run tests with coverage report
coverage:
    uv run pytest --cov=sing-box-config --cov-report=term-missing tests/

# Build distribution packages
build:
    uv build -v

# Serve documentation locally
docs-serve:
    uv run mkdocs serve

# Build documentation
docs-build:
    uv run mkdocs build --strict

# Remove build artifacts
clean:
    rm -rf dist/ site/ .pytest_cache/ htmlcov/ .coverage
    find src/ tests/ -type f -name "*.pyc" -delete
    find src/ tests/ -type d -name "__pycache__" -delete
