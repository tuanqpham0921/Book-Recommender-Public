# Variables
MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
ENV_FILE := $(MAKEFILE_DIR)/config/.env
DOCKER_COMPOSE_FILE := $(MAKEFILE_DIR)/docker-compose.yml

# -------------------
# General commands
# -------------------

# Poetry commands
install:
	poetry install

# Local development (native FastAPI)
dev:
	poetry run fastapi dev app/main.py

# run the ingestion script
ingestion:
	poetry run python ingestion/loader.py


# -------------------
# PostgreSQL commands
# -------------------

# Local development (databases + native FastAPI)
postgres-start:
	docker compose --env-file $(ENV_FILE) -f $(DOCKER_COMPOSE_FILE) up postgres -d
	@echo "Databases started. Run 'make dev' to start API"

# stop the postgres container
postgres-stop:
	docker compose -f $(DOCKER_COMPOSE_FILE) down postgres
	@echo "PostgreSQL container stopped (does not remove volumes)"

# enter postgres CLI
postgres-cli:
	docker exec -it $(POSTGRES_CONTAINER) psql -U postgres -d book_recommender

# clean the docker containers
docker-clean:
	docker compose -f $(DOCKER_COMPOSE_FILE) down -v

# -------------------
.PHONY: dev ingestion postgres-start postgres-stop postgres-cli docker-clean