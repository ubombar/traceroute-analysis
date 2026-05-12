.PHONY: help init venv fetch_retina

export PYTHONDONTWRITEBYTECODE=1

RETINA_URL ?= https://iprl.dioptra.io/api/v1/stream
BATCH_SIZE ?= 1000 

# Fetch duration
FD ?= 60s 

help: ## Display this help menu
	@awk 'BEGIN {FS = ":.*##"; printf "Traceoute Analysis Help Menu\n\n"} /^[a-zA-Z_-]+:.*##/ { printf "  %-12s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

venv: ## Create .venv and install dependencies
	@if [ ! -d ".venv" ]; then \
		echo "Creating .venv..."; \
		python3 -m venv .venv; \
		.venv/bin/pip install dataclasses-json httpx; \
		echo "Done."; \
	fi

init: venv ## Initialize meta.json and data directory
	@./scripts/init.py


fetch_retina: init ## Fetch retina data (usage: make fetch_retina FD=60s BATCH_SIZE=1000 RETINA_URL="")
	@./scripts/fetch_retina_data.py $(FD) \
		--url $(RETINA_URL) \
		--batch-size $(BATCH_SIZE) \
		--db data/$(shell date +'%Y%m%d__%H%M%S')__$(FD).db
