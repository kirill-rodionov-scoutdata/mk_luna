.PHONY: start test lint migrate

# Copy .env from example if it doesn't exist yet
.env:
	cp .env.example .env

start: .env
	docker compose up --build

test:
	@POSTGRES_HOST=localhost RABBITMQ_HOST=localhost uv run pytest tests/ -v

lint:
	uv run ruff format src tests
	uv run ruff check --fix src tests

migrate:
	docker compose run --rm --no-deps \
		-v $(shell pwd)/migrations:/app/migrations \
		api alembic revision --autogenerate -m "new migration"
