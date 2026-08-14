#!/bin/sh
# Generic loader entrypoint
# Expects env var LOADER_MODULE (e.g. loaders.sharepoint_loader.result_physico_chimique.main)
# Usage from docker-compose: set LOADER_MODULE per service and mount /wait-for-postgres.sh

set -e

# Default to provided module or the result_physico_chimique loader
LOADER_MODULE=${LOADER_MODULE:-loaders.sharepoint_loader.result_physico_chimique.main}

# Wait for postgres (if script present) then run the python module
if [ -x /wait-for-postgres.sh ] || [ -f /wait-for-postgres.sh ]; then
  # call wait-for-postgres.sh and pass the python command to run
  sh /wait-for-postgres.sh python -m "$LOADER_MODULE" "$@"
else
  # fallback: directly run python module
  python -m "$LOADER_MODULE" "$@"
fi
