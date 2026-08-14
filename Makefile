DOCKER_COMPOSE := $(shell command -v docker-compose >/dev/null 2>&1 && echo docker-compose || echo docker compose)
COMPOSE_DEV    := $(DOCKER_COMPOSE) -p data-loaders-dev -f docker-compose.yaml
# Matches the project name Compose already assigned (directory-derived default) to the
# running prod containers — pinning it explicitly avoids orphaning them under a new label.
COMPOSE_PROD   := $(DOCKER_COMPOSE) -p data-loaders -f docker-compose.prod.yaml

ENV ?= dev
ifeq ($(ENV),prod)
  COMPOSE := $(COMPOSE_PROD)
else
  COMPOSE := $(COMPOSE_DEV)
endif

# SERVICE -> Python module, one entry per docker-compose profile/loader.
MODULE_weather-history := loaders.weather_loader.history.main
MODULE_weather-daily    := loaders.weather_loader.daily.main
MODULE_business         := loaders.business_data_loader.src.main
MODULE_stock            := loaders.stock_data_loader.src.main
MODULE_pc               := loaders.pc_loader.main
MODULE_metabarcoding    := loaders.sharepoint_loader.metabarcoding_loader.main
MODULE_sales-pipeline   := loaders.sharepoint_loader.sales_pipeline_loader.main
MODULE_sample-results   := loaders.sharepoint_loader.sample_results_loader.main

# Every service is gated behind a docker-compose profile (so `up`/`build` never
# touch all loaders by accident) — this activates them all for `make build-*`.
empty :=
space := $(empty) $(empty)
comma := ,
ALL_PROFILES := $(subst $(space),$(comma),weather-history weather-daily business stock pc metabarcoding sales-pipeline sample-results)

# Tables/columns raw-SQL loaders assume exist; rest of the history is in migrations/archive/.
MIGRATIONS_DEV := migrations/001_metag_tables.sql \
	migrations/002a_add_is_pathogen.sql \
	migrations/004_stage_changes_table.sql \
	migrations/008_metag_read_archives.sql \
	migrations/009_rename_audit_columns.sql \
	migrations/010_drop_dna_concentration.sql \
	migrations/011_replace_sample_date.sql \
	migrations/012_physico_chimique_eav.sql

PYTHON_PROD := venv/bin/python -c
DOTENV_PROD := from dotenv import load_dotenv; load_dotenv('.env.prod');

.PHONY: help build-dev build-prod up \
	init-dev-db init-prod-db \
	run-prod-metabarcoding run-prod-crm-stages \
	export-donnees-source export-reporting-mensuel \
	down clean clean-all

help:
	@echo 'Usage: make [target]'
	@echo 'Targets:'
	@echo '  build-dev                - Build dev image'
	@echo '  build-prod               - Build prod image'
	@echo '  init-dev-db              - Apply bootstrap SQL migrations (dev)'
	@echo '  init-prod-db             - Apply bootstrap SQL migrations (prod)'
	@echo '  up                       - Run a loader: make up SERVICE=<name> [ENV=dev|prod] [PC_PROVIDER=aurea|bdd_pc|esdac]'
	@echo '                             Services: weather-history weather-daily business stock pc metabarcoding sales-pipeline sample-results'
	@echo '                             Example:  make up SERVICE=pc ENV=prod PC_PROVIDER=aurea'
	@echo '  run-prod-metabarcoding   - Run metabarcoding-loader in prod (Python direct)'
	@echo '  run-prod-crm-stages      - Run CRM stage changes loader (Python direct)'
	@echo '  export-donnees-source    - Export donnees-source to SharePoint (Python direct)'
	@echo '  export-reporting-mensuel - Export reporting mensuel to SharePoint (Python direct)'
	@echo '  down                     - Stop all containers'
	@echo '  clean                    - Stop containers and remove images/volumes (destructive)'
	@echo '  clean-all                - Alias for clean'

build-dev:
	COMPOSE_PROFILES=$(ALL_PROFILES) $(COMPOSE_DEV) build

build-prod:
	COMPOSE_PROFILES=$(ALL_PROFILES) $(COMPOSE_PROD) build

up:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Usage: make up SERVICE=<name> [ENV=dev|prod] [PC_PROVIDER=aurea|bdd_pc|esdac]"; \
		echo "Services: weather-history weather-daily business stock pc metabarcoding sales-pipeline sample-results"; \
		exit 1; \
	fi
	@if [ -z "$(MODULE_$(SERVICE))" ]; then \
		echo "Unknown SERVICE '$(SERVICE)'. Services: weather-history weather-daily business stock pc metabarcoding sales-pipeline sample-results"; \
		exit 1; \
	fi
	PC_PROVIDER=$(PC_PROVIDER) $(COMPOSE) --profile $(SERVICE) up -d
	$(COMPOSE) exec $(SERVICE)-loader python -m $(MODULE_$(SERVICE))

init-dev-db:
	@for f in $(MIGRATIONS_DEV); do \
		echo "Applying $$f..."; \
		$(COMPOSE_DEV) exec -T db psql -U myuser -d db -f /dev/stdin < $$f || exit 1; \
	done

init-prod-db:
	@eval $$(grep -E '^DB_(USER|PASSWORD|HOST|PORT|NAME)=' .env.prod | sed 's/ *= */=/g' | sed 's/^/export /') && \
	for f in $(MIGRATIONS_DEV); do \
		psql "postgresql://$$DB_USER:$$DB_PASSWORD@$$DB_HOST:$$DB_PORT/$$DB_NAME" -f $$f || exit 1; \
	done

run-prod-metabarcoding:
	$(PYTHON_PROD) "$(DOTENV_PROD) import runpy; runpy.run_module('loaders.sharepoint_loader.metabarcoding_loader.main', run_name='__main__')"

export-donnees-source:
	$(PYTHON_PROD) "$(DOTENV_PROD) from loaders.export.main import main; main()" --mode donnees-source

export-reporting-mensuel:
	$(PYTHON_PROD) "$(DOTENV_PROD) from loaders.export.main import main; main()" --mode reporting-mensuel

run-prod-crm-stages:
	@echo " Setting up SSH tunnel to Odoo.sh..."
	@fuser -k 5433/tcp 2>/dev/null || true
	@test -n "$$ODOO_SSH_HOST" || (echo "ODOO_SSH_HOST is required" && exit 1)
	@ssh -i "$${ODOO_SSH_KEY:-$$HOME/.ssh/id_rsa}" -f -N -L 5433:192.168.1.1:5432 "$$ODOO_SSH_HOST"
	@PGPASSWORD=$$(ssh -i "$${ODOO_SSH_KEY:-$$HOME/.ssh/id_rsa}" "$$ODOO_SSH_HOST" 'echo $$PGPASSWORD') && \
	 sed -i "s/^PGPASSWORD=.*/PGPASSWORD=$$PGPASSWORD/" .env.prod
	$(PYTHON_PROD) "$(DOTENV_PROD) from loaders.crm_stage_loader.src.main import main; main()" $(if $(SINCE),--since $(SINCE),)

down:
	$(COMPOSE_DEV) down
	$(COMPOSE_PROD) down || true

clean:
	$(COMPOSE_DEV) down --rmi all --volumes --remove-orphans
	$(COMPOSE_PROD) down --rmi all --volumes --remove-orphans || true

clean-all: clean
