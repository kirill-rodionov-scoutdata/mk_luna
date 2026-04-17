.PHONY: start stop restart logs clean test migrate lint format

# Copy .env from example if it doesn't exist yet
.env:
	cp .env.example .env

start: .env
	docker compose up --build

stop:
	docker compose down

restart: stop start

logs:
	docker compose logs -f

clean:
	docker compose down -v --remove-orphans

migrate:
	POSTGRES_HOST=localhost uv run alembic upgrade head

test:
	@POSTGRES_HOST=localhost uv run pytest tests/ -v

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests
