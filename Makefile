.PHONY: dev build up down logs

dev:
	docker-compose up --build

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

backend-shell:
	docker-compose exec backend sh

frontend-shell:
	docker-compose exec frontend sh
