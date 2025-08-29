install:
	poetry install

run:
	poetry run python src/main.py

lint:
	poetry run black src/*
	poetry run isort src/*

test:
	poetry run python tests/test_function.py