# Show available recipes
default:
    @just --list --unsorted

# Run all available recipes
all: lint typecheck test coverage build docs-build

# Sync development dependencies (may update uv.lock if pyproject.toml changed)
sync *ARGS:
    uv sync {{ARGS}} --group dev

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
    uv run pytest --cov=sing_box_config --cov=plugins --cov-report=term-missing tests/

# Build distribution packages
build:
    uv build

# Serve documentation locally
docs-serve:
    uv run mkdocs serve

# Build documentation
docs-build:
    NO_MKDOCS_2_WARNING=1 uv run mkdocs build --strict

# Install project-local Ansible collection
ansible-collection-install:
    mkdir -p .ansible/collections
    ansible-galaxy collection install --force --collections-path .ansible/collections .
    ansible-galaxy collection install --force --collections-path .ansible/collections ../ansible-collection-general

# Build project-local Ansible collection
ansible-collection-build:
    mkdir -p .ansible/dist/
    ansible-galaxy collection build --force --output-path .ansible/dist/ .

# Remove build artifacts
clean:
    rm -rf dist/ site/ .ansible/ .cache/ .ruff_cache/ .pytest_cache/ htmlcov/ .coverage ansible-navigator.log
    find src/ tests/ -type f -name "*.pyc" -delete
    find src/ tests/ -type d -name "__pycache__" -delete
