# Variables
MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
ENV_FILE := $(MAKEFILE_DIR)/config/.env
REDIS_CONTAINER = book-rec-redis
POSTGRES_CONTAINER = book-rec-postgres
CADDY_CONTAINER = book-rec-caddy
GCP_INSTANCE = book-rec-dev
GCP_ZONE = us-central1-c

# Poetry commands
install:
	poetry install

# always clear the Redis cache before loading
load:
	make redis-clear 
	poetry run load

# Load books into PostgreSQL
load-postgres:
	poetry run load-postgres

# Development server
dev-debug:
	LOG_LEVEL=DEBUG poetry run fastapi dev app/main.py

activate:
	poetry env activate

dev:
	poetry run fastapi dev app/main.py

# Local development (databases + native FastAPI)
# add redis to the mix
dev-local-db:
	docker compose --env-file $(ENV_FILE) -f infra/docker-compose.yml up postgres -d
	@echo "Databases started. Run 'poetry run fastapi dev app/main.py' to start API"

# Development with Caddy proxy
dev-caddy:
	docker compose up caddy app -d
	@echo "Server running at http://localhost"
	@echo "Caddy admin at http://localhost:2019"

# Environment management
activate:
	poetry env activate

clear-pycache:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
	find . -name "*.pyo" -delete
	find . -name "*.pyc" -delete
	
# ---------------
# Caddy commands
#---------------

# Start Caddy service
caddy-start:
	docker compose up caddy -d

# Stop Caddy service  
caddy-stop:
	docker compose stop caddy

# Restart Caddy (reload config)
caddy-reload:
	docker exec $(CADDY_CONTAINER) caddy reload --config /etc/caddy/Caddyfile

# View Caddy logs
caddy-logs:
	docker compose logs caddy -f

# Check Caddy config
caddy-validate:
	docker exec $(CADDY_CONTAINER) caddy validate --config /etc/caddy/Caddyfile

# Caddy admin API status
caddy-status:
	@echo "=== Caddy Status ==="
	@curl -s http://localhost:2019/config/ | head -50
	@echo ""

# Switch to production config
caddy-prod:
	@echo "Switching to production Caddyfile..."
	@cp Caddyfile.prod Caddyfile
	@make caddy-reload

# --------------
# Redis commands
#---------------

# KEYS *
# KEYS chat*
# JSON.GET chat:<chat_id>

# start the redis docker ps
redis-start:
	docker compose up redis -d

# enter redis CLI
redis-cli:
	docker exec -it $(REDIS_CONTAINER) redis-cli

# clear the cache only
redis-clear:
	docker exec -it $(REDIS_CONTAINER) redis-cli FLUSHALL

# clear only session data
redis-clear-sessions:
	@echo "Clearing all sessions (session:* keys)..."
	@docker exec $(REDIS_CONTAINER) redis-cli --scan --pattern "session:*" | xargs -r docker exec -i $(REDIS_CONTAINER) redis-cli DEL
	@echo "Sessions cleared successfully"

# stop and start again (doesn't clear the cache)
redis-restart:
	docker compose restart redis

# get the Redis memory usage
redis-memory:
	@echo "=== Redis Memory Usage ==="
	@docker exec -it $(REDIS_CONTAINER) redis-cli INFO memory | grep -E "(used_memory_human|used_memory_peak_human|used_memory_rss_human|maxmemory_human)"
	@echo ""

# export all sessions to JSON
redis-export-sessions:
	@echo "Exporting all sessions to JSON..."
	poetry run python export.py all

# export specific session ID to JSON (usage: make redis-export-session SESSION_ID=abc12345)
redis-export-session:
	@if [ -z "$(SESSION_ID)" ]; then \
		echo "Error: SESSION_ID is required. Usage: make redis-export-session SESSION_ID=your_session_id"; \
		echo "Available session IDs:"; \
		poetry run python export.py list; \
	else \
		echo "Exporting session ID: $(SESSION_ID)"; \
		poetry run python export.py $(SESSION_ID); \
	fi

# list all available chat IDs
redis-list-chats:
	@echo "Listing all available chat IDs..."
	poetry run python export.py list

# -------------------
# PostgreSQL commands
#--------------------

# start postgres docker container
postgres-start:
	docker compose up postgres -d

# enter postgres CLI
postgres-cli:
	docker exec -it $(POSTGRES_CONTAINER) psql -U postgres -d book_recommender

# check postgres status
postgres-status:
	@echo "=== PostgreSQL Status ==="
	@docker exec $(POSTGRES_CONTAINER) pg_isready -U postgres
	@echo ""

# show postgres database info
postgres-info:
	@echo "=== PostgreSQL Database Info ==="
	@docker exec $(POSTGRES_CONTAINER) psql -U postgres -d book_recommender -c "\l"
	@echo ""
	@docker exec $(POSTGRES_CONTAINER) psql -U postgres -d book_recommender -c "\dt"
	@echo ""

# -----------------
# Docker management
#------------------
docker-reset:
	docker compose down
	docker compose up -d

docker-clean:
	docker compose -f infra/docker-compose.yml down -v

# ---------------------
# Google Cloud Platform
#-----------------------

# SSH into GCP instance
ssh-gcp:
	gcloud compute ssh $(GCP_INSTANCE) \
		--zone=$(GCP_ZONE)

# Stop GCP instance
stop-gcp:
	gcloud compute instances stop $(GCP_INSTANCE) \
		--zone=$(GCP_ZONE)

# List all GCP compute instances
gcp-instances-list:
	gcloud compute instances list

# Create GCP instance directly (without template)
# TODO: Need to make a new service account for book recommender (no Admin)
gcp-create-instance:
	@echo "Creating GCP instance $(GCP_INSTANCE)..."
	@echo "Using Secret Manager for sensitive data..."
	@SCRIPT_PATH=$$(pwd)/infra/scripts/startup.sh; \
	gcloud compute instances create $(GCP_INSTANCE) \
		--zone=$(GCP_ZONE) \
		--machine-type=e2-medium \
		--image-family=ubuntu-2204-lts \
		--image-project=ubuntu-os-cloud \
		--boot-disk-size=10GB \
		--tags=http-server,https-server,web-server \
		--metadata=enable-oslogin=TRUE,ENV_SECRET_NAME="OPENAI_API_KEY" \
		--metadata-from-file=startup-script=$$SCRIPT_PATH \
		--scopes="https://www.googleapis.com/auth/cloud-platform"
	@echo "✓ Instance created successfully!"
	@echo "Waiting for instance to be fully ready..."
	@while [ "$$(gcloud compute instances describe $(GCP_INSTANCE) --zone=$(GCP_ZONE) --format='value(status)' 2>/dev/null)" != "RUNNING" ]; do \
		echo "  Instance status: $$(gcloud compute instances describe $(GCP_INSTANCE) --zone=$(GCP_ZONE) --format='value(status)' 2>/dev/null || echo 'CREATING')"; \
		sleep 5; \
	done
	@echo "✓ Instance is now RUNNING!"
	@VM_IP=$$(gcloud compute instances describe $(GCP_INSTANCE) --zone=$(GCP_ZONE) --format="get(networkInterfaces[0].accessConfigs[0].natIP)"); \
	echo ""; \
	echo "=== Instance Ready ==="; \
	echo "Name: $(GCP_INSTANCE)"; \
	echo "Zone: $(GCP_ZONE)"; \
	echo "External IP: $$VM_IP"; \
	echo ""; \
	echo "Waiting for startup script to complete..."; \
	echo "(This may take 2-5 minutes for Docker setup)"; \
	for i in {1..60}; do \
		if curl -s http://$$VM_IP:8000/health > /dev/null 2>&1; then \
			echo "✓ Application is ready at http://$$VM_IP:8000"; \
			echo "✓ Health check: http://$$VM_IP:8000/health"; \
			echo "✓ Through Caddy: http://$$VM_IP"; \
			break; \
		else \
			printf "."; \
			sleep 5; \
		fi; \
		if [ $$i -eq 60 ]; then \
			echo ""; \
			echo "⚠️  Startup script still running. Check logs with:"; \
			echo "   gcloud compute instances get-serial-port-output $(GCP_INSTANCE) --zone=$(GCP_ZONE)"; \
		fi; \
	done
	@echo ""; \
	echo "Next steps:"; \
	echo "1. Set environment variables: make gcp-set-env"; \
	echo "2. SSH into instance: make ssh-gcp"

# Add environment variables to instance
gcp-set-env:
	@echo "Setting environment variables for $(GCP_INSTANCE)..."
	@read -p "Enter OpenAI API Key: " OPENAI_KEY; \
	VM_IP=$$(gcloud compute instances describe $(GCP_INSTANCE) --zone=$(GCP_ZONE) --format="get(networkInterfaces[0].accessConfigs[0].natIP)"); \
	gcloud compute instances add-metadata $(GCP_INSTANCE) \
		--metadata=OPENAI_API_KEY="$$OPENAI_KEY",POSTGRES_PASSWORD="1234",ENVIRONMENT="development",DEBUG="true",CORS_ORIGINS="http://$$VM_IP:3000,http://$$VM_IP,https://$$VM_IP" \
		--zone=$(GCP_ZONE)

# export OPENAI_API_KEY=""
# curl -v http://localhost:8000/ready
ping-openai:
	curl -w "time_total: %{time_total}\n" -o /dev/null -s https://api.openai.com/v1/models

# Testing commands
test:
	poetry run pytest tests/ -v

test-verbose:
	poetry run pytest tests/ -v

test-unit:
	poetry run pytest tests/unit/ -v

test-utils:
	poetry run pytest tests/unit/test_common_utils.py -v

test-coverage:
	poetry run pytest tests/ --cov=app --cov-report=html --cov-report=term

.PHONY: install load load-postgres dev activate redis-start redis-cli redis-clear redis-clear-chats redis-restart redis-memory redis-export-chats redis-export-chat redis-list-chats postgres-start postgres-cli postgres-status postgres-info docker-reset docker-clean ssh-gcp stop-gcp gcp-instances-list gcp-create-instance gcp-set-env ping-openai test test-verbose test-unit test-utils test-coverage

# NOTE: adding to poetry
# poetry add --group dev pytest pytest-asyncio pytest-cov

prototype: prototype/db_query.py
	./prototype/db_query.py