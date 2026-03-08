.PHONY: lint install run-bot run-observer migrate upgrade compile test docker-up docker-down

lint:
	ruff check axiomai_proxy --fix
	mypy axiomai_proxy

install:
	python -m pip install --upgrade pip
	pip install -e .

run-bot:
	python -m axiomai_proxy.tgbot

run-observer:
	python -m axiomai_proxy.observer

migrate:
	alembic revision -m "$(m)"

upgrade:
	alembic upgrade head

compile:
	python -m compileall axiomai_proxy

test:
	pytest -q

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
