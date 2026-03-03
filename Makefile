PYTHON ?= .venv/bin/python

.PHONY: help fetch-spec spec-diff validate-sdk update-api test lint

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

fetch-spec: ## Download the latest OpenAPI spec from OX documentation
	$(PYTHON) scripts/fetch_spec.py

spec-diff: ## Show changes between committed and current spec
	$(PYTHON) scripts/spec_diff.py

validate-sdk: ## Validate SDK coverage against the current spec
	$(PYTHON) scripts/validate_coverage.py

update-api: fetch-spec spec-diff validate-sdk ## Fetch spec, show diff, validate coverage
	@echo ""
	@echo "Done. Review the diff and coverage report above."
	@echo "If there are new endpoints or fields, update the SDK accordingly."

test: ## Run tests
	$(PYTHON) -m pytest -v

lint: ## Run ruff linter and formatter check
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
