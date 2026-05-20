.PHONY: help init venv stream_retina query ls reconcile reconcile_f add

export PYTHONDONTWRITEBYTECODE=1

RETINA_STREAM_ENDPINT ?= https://iprl.dioptra.io/api/v1/stream
BATCH_SIZE ?= 1000
DURATION ?= 60s
DB ?=
Q ?=
F ?= ""
PLATFORM ?=
FROM_DATE ?=
TO_DATE ?=

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

stream_retina: init venv ## Stream live retina data (usage: make stream_retina DURATION=60s BATCH_SIZE=1000 RETINA_STREAM_ENDPINT="")
	@./scripts/stream_retina.py $(DURATION) \
		--url $(RETINA_STREAM_ENDPINT) \
		--batch-size $(BATCH_SIZE) \
		--filter $(F) \
		--db data/$(shell date +'%Y%m%d%H%M%S')__stream_retina2__$(DURATION).db

query: init ## Run a SQLite query and output CSV (usage: make query DB=data/foo.db Q="SELECT * FROM fies")
	@./scripts/query.py $(DB) "$(Q)"

ls: init ## List existing experiments
	@./scripts/meta.py ls

reconcile: init ## Reconcile untracked databases (usage: make reconcile)
	@./scripts/meta.py reconcile

reconcile_f: init ## Force reconcile, clears and re-adds all (usage: make reconcile_f)
	@./scripts/meta.py reconcile --force

add: init ## Add a new experiment (usage: make add DB=data/foo.db PLATFORM=retina)
	@./scripts/meta.py add $(DB) \
		$(if $(PLATFORM),--platform $(PLATFORM),) \
		$(if $(FROM_DATE),--from-date $(FROM_DATE),) \
		$(if $(TO_DATE),--to-date $(TO_DATE),)
