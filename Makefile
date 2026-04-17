.PHONY: start stop restart logs clean

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
