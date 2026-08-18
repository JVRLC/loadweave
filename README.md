# LoadWeave

> Lightweight Python ETL pipelines for turning scattered business data into reliable, repeatable workflows.

LoadWeave is a dependency-free ETL runner for data jobs that do not need the complexity of a full data platform.

```text
Source → Transform → Transform → Destination
```

## Business problem

Many workflows still rely on manually exporting, cleaning, and reshaping data. LoadWeave turns those repeated steps into explicit, reusable JSON pipelines.

## What it delivers

- Streaming ETL without loading entire datasets into memory
- Reusable sources, transformations, and destinations
- JSON configuration and environment-variable support
- Custom Python plugins and pre-run validation
- Built-in CSV, JSONL, and Odoo XML-RPC processing
- Local, scheduled, or containerized execution

## Quick demo

Requires Python 3.10+.

```bash
git clone https://github.com/JVRLC/loadweave.git
cd loadweave
python -m venv .venv
source .venv/bin/activate
pip install -e .
loadweave components
loadweave check examples/csv-to-jsonl/pipeline.json
loadweave run examples/csv-to-jsonl/pipeline.json
```

```text
CSV → field selection → field rename → JSONL
```

## Odoo integration demo

```bash
docker compose up -d
cp .env.example .env
# Add the local Odoo credentials, then:
loadweave run examples/odoo-to-jsonl/pipeline.json
```

## Extensibility

Custom sources are ordinary Python classes referenced as `package.module:Class`. The same extension model applies to transformations and destinations.

## Engineering quality

- pytest with a 90%+ branch-coverage target
- strict mypy and Ruff validation
- typed package, Docker support, and semantic versioning

## Technologies

**Python · ETL · Data Engineering · CLI · Docker · JSON · CSV · Odoo · XML-RPC · pytest · mypy · Ruff**

## Typical use cases

CSV/Excel automation, SaaS and ERP extraction, recurring reporting, BI preparation, migrations, synchronization, and custom ETL jobs.

## About

This portfolio project demonstrates how I build small, maintainable data systems for ETL, API integration, and business-process automation.

Licensed under the [MIT License](LICENSE).
