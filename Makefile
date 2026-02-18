.PHONY: help install test smoke full clean docker-build docker-test start-opa stop-opa

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies and package
	pip install -r requirements.txt
	pip install -e .

test: ## Run all tests
	pytest tests/ -v

smoke: ## Run smoke tests against local OPA
	@echo "Running smoke tests..."
	OPA_URL=http://localhost:8181 opa-test --mode smoke --config config.example.yaml

full: ## Run full test suite against local OPA
	@echo "Running full test suite..."
	OPA_URL=http://localhost:8181 opa-test --mode full --config config.example.yaml

clean: ## Clean up generated files
	rm -rf build/ dist/ *.egg-info
	rm -rf test-results/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

docker-build: ## Build Docker image
	docker build -t opa-test-framework:latest .

docker-test: ## Run tests in Docker
	docker-compose up --abort-on-container-exit test-runner

start-opa: ## Start OPA using docker-compose
	@echo "Starting OPA..."
	docker-compose up -d opa
	@echo "Waiting for OPA to be ready..."
	@timeout 30 bash -c 'until curl -f http://localhost:8181/health 2>/dev/null; do sleep 2; done' || (echo "OPA failed to start" && exit 1)
	@echo "Loading policies..."
	@for policy in examples/policies/*.rego; do \
		if [[ ! "$$policy" =~ _test\.rego$$ ]]; then \
			policy_name=$$(basename "$$policy" .rego); \
			echo "  Loading: $$policy_name"; \
			curl -s -X PUT --data-binary @"$$policy" http://localhost:8181/v1/policies/"$$policy_name" > /dev/null; \
		fi \
	done
	@echo "✓ OPA is ready at http://localhost:8181"

stop-opa: ## Stop OPA
	docker-compose down

quick-start: start-opa smoke ## Quick start: start OPA and run smoke tests

ci-test: ## Run tests in CI mode
	OPA_URL=http://localhost:8181 opa-test --ci --mode smoke --report-format junit --output test-results/smoke-results.xml
	OPA_URL=http://localhost:8181 opa-test --ci --mode full --report-format junit --output test-results/full-results.xml

format: ## Format code with black
	black src/ tests/

lint: ## Lint code with flake8
	flake8 src/ tests/

type-check: ## Type check with mypy
	mypy src/

dev-setup: install start-opa ## Setup development environment
	@echo "✓ Development environment ready!"
	@echo "  Run 'make smoke' to test"
