.PHONY: dev api health demo docker-build docker-run docker-stop

PORT ?= 8001
SCHEMA ?= examples/schema_ps.json
TEXT ?= Generate a SQL query to list active employees hired in the last 90 days

dev: api

api:
	python -m uvicorn src.api:app --host 0.0.0.0 --port $(PORT)

health:
	curl -s http://127.0.0.1:$(PORT)/health && echo

demo:
	curl -s -X POST "http://127.0.0.1:$(PORT)/plan" \
	  -H "Content-Type: application/json" \
	  -d '{"text":"$(TEXT)","schema_path":"$(SCHEMA)","audit":false}' && echo

docker-build:
	docker build -t enterprise-ai-ops .

docker-run:
	docker run --rm -p $(PORT):8000 enterprise-ai-ops

docker-stop:
	@docker ps --filter "ancestor=enterprise-ai-ops" --format "{{.ID}}" | xargs -r docker stop