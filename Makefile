.PHONY: install lint typecheck test check demo

install:
	uv venv --allow-existing && uv pip install -e ".[dev]"

lint:
	uv run ruff format --check src tests && uv run ruff check src tests

format:
	uv run ruff format src tests && uv run ruff check --fix src tests

typecheck:
	uv run mypy

test:
	uv run pytest

check: lint typecheck test

demo:
	uv run investment-os brief
	uv run investment-os analyze BBCA
	uv run investment-os analyze ANTM
