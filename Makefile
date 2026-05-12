.PHONY: help init venv stream_retina query

export PYTHONDONTWRITEBYTECODE=1

RETINA_STREAM_ENDPINT ?= https://iprl.dioptra.io/api/v1/stream
BATCH_SIZE ?= 1000 
DURATION ?= 60s 
DB ?=
Q ?=

help: ## Display this help menu
	@awk 'BEGIN {FS = ":.*##"; printf "Traceoute Analysis Help Menu\n\n"} /^[a-zA-Z_-]+:.*##/ { printf "  %-16s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

venv: ## Create .venv and install dependencies
	@if [ ! -d ".venv" ]; then \
		echo "Creating .venv..."; \
		python3 -m venv .venv; \
		.venv/bin/pip install dataclasses-json httpx notebook pandas numpy; \
		echo "Done."; \
	fi

init: venv ## Initialize meta.json and data directory
	@./scripts/init.py


stream_retina: init ## Stream live retina data (usage: make stream_retina DURATION=60s BATCH_SIZE=1000 RETINA_STREAM_ENDPINT="")
	@./scripts/stream_retina.py $(DURATION) \
		--url $(RETINA_STREAM_ENDPINT) \
		--batch-size $(BATCH_SIZE) \
		--db data/$(shell date +'%Y%m%d%H%M%S')__stream_retina__$(DURATION).db


query: init ## Run a SQLite query and output CSV (usage: make query DB=data/foo.db Q="SELECT * FROM fies")
	@./scripts/query.py $(DB) "$(Q)"
