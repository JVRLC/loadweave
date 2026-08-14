````markdown
# Business Data Loader

A Python-based ETL pipeline that extracts data from Odoo CRM, automatically resolves relational fields, and loads it into a PostgreSQL data warehouse using Docker and SQLAlchemy.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Requirements](#requirements)
- [Setup](#setup)
- [Usage](#usage)
- [Database Schema](#database-schema)
- [Architecture](#architecture)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Project Overview

This project automates the end-to-end ETL process for migrating Odoo CRM data into a PostgreSQL data warehouse. It extracts opportunities, contacts, and clients from Odoo, automatically resolves relational fields (many2one, many2many) into human-readable values, and uses UPSERT logic to maintain data consistency.

---

## Features

**Automatic Data Extraction**

- Extracts all fields from Odoo models (`crm.lead`, `res.partner`)
- No manual field specification needed

**Smart Relational Field Resolution**

- Automatically converts `[51, 'John Doe']` → `'John Doe'`
- Converts many2many lists `[1, 2, 3]` → `'1,2,3'`
- Uses Odoo's `fields_get` API to detect field types

**UPSERT Logic**

- Keeps existing records in the database
- Adds only new records
- Updates modified records
- Prevents duplicate IDs

**Robust Database Connection**

- Retry logic (5 attempts with 3s delay)
- Automatic schema creation (`raw` schema)
- Primary key enforcement on `id` column

**Docker-Ready**

- Fully containerized with Docker Compose
- Development and production profiles
- Health checks for PostgreSQL
- Persistent logs

**Data Segregation**

- **Opportunities**: All CRM leads from `crm.lead`
- **Contacts**: Partners with `customer_rank = 0`
- **Clients**: Partners with `customer_rank > 0`

---

## Requirements

- Docker & Docker Compose
- Python 3.10+
- PostgreSQL 15+
- Odoo instance with XML-RPC API access

Python packages (installed automatically in Docker):

- `sqlalchemy`
- `psycopg2-binary`
- `python-dotenv`

---

## Setup

### 1. Clone the Repository

```bash
git clone git@github.com:YOUR_USERNAME/loadweave.git
cd business-data-loader
```

### 2. Create Environment File

Create a `.env` file in the root directory:

```env
# Odoo Connection
ODOO_URL=https://your-odoo-instance.odoo.com
ODOO_DB=your-database-name
ODOO_USER=admin
ODOO_PASSWORD=your_password

# PostgreSQL Connection
DB_USER=myuser
DB_PASSWORD=mypassword
DB_NAME=db
DB_HOST=db
DB_PORT=5432
```

### 3. Make Helper Script Executable

```bash
chmod +x wait-for-postgres.sh
```

### 4. Start Docker Containers

**Development:**

```bash
make up-dev
# or
docker-compose --profile dev -f docker-compose.yaml up -d
```

**Production:**

```bash
make up-prod
# or
docker-compose --profile prod -f docker-compose.prod.yaml up -d
```

---

## Usage

### Run the ETL Pipeline

**Using Make:**

```bash
make up-dev
```

**Manual Execution:**

```bash
# Start containers
docker-compose --profile dev up -d

# Run ETL
docker-compose exec cron_job python -m src.main
```

### Check Logs

```bash
docker-compose logs -f cron_job
```

### Connect to PostgreSQL

```bash
docker-compose exec db psql -U myuser -d db
```

**Query the data:**

```sql
-- List tables in raw schema
\dt raw.*

-- View opportunities
SELECT * FROM raw.opportunities LIMIT 10;

-- View contacts
SELECT * FROM raw.contacts LIMIT 10;

-- View clients
SELECT * FROM raw.clients LIMIT 10;

-- Count records
SELECT
  (SELECT COUNT(*) FROM raw.opportunities) as opportunities,
  (SELECT COUNT(*) FROM raw.contacts) as contacts,
  (SELECT COUNT(*) FROM raw.clients) as clients;
```

---

## Database Schema

All tables are created dynamically under the `raw` schema:

### `raw.opportunities`

- Source: `crm.lead` model in Odoo
- Contains all CRM opportunities/leads
- All fields from Odoo are included

### `raw.contacts`

- Source: `res.partner` model in Odoo
- Filter: `customer_rank = 0` (non-customers)
- Contains prospects and contacts

### `raw.clients`

- Source: `res.partner` model in Odoo
- Filter: `customer_rank > 0` (active customers)
- Contains paying clients

### Table Structure

- **Primary Key**: `id` (String) - Odoo record ID
- **All other fields**: String (nullable) - Dynamically created based on Odoo fields
- **Relational fields**: Resolved to human-readable names or comma-separated IDs

---

## Architecture

```
┌─────────────────┐
│   Odoo CRM      │
│  (XML-RPC API)  │
└────────┬────────┘
         │
         │ 1. Extract data via search_read
         │ 2. Resolve relational fields
         │
┌────────▼────────┐
│  Python ETL     │
│  (src/mig.py)   │
│                 │
│  - Extract      │
│  - Transform    │
│  - Load (UPSERT)│
└────────┬────────┘
         │
         │ 3. UPSERT into PostgreSQL
         │
┌────────▼────────┐
│  PostgreSQL     │
│  Data Warehouse │
│                 │
│  Schema: raw    │
│  - opportunities│
│  - contacts     │
│  - clients      │
└─────────────────┘
```

---

## Environment Variables

### Required Variables

| Variable        | Description         | Example                      |
| --------------- | ------------------- | ---------------------------- |
| `ODOO_URL`      | Odoo instance URL   | `https://mycompany.odoo.com` |
| `ODOO_DB`       | Odoo database name  | `mycompany-production`       |
| `ODOO_USER`     | Odoo username       | `admin`                      |
| `ODOO_PASSWORD` | Odoo password       | `securepassword123`          |
| `DB_USER`       | PostgreSQL username | `myuser`                     |
| `DB_PASSWORD`   | PostgreSQL password | `mypassword`                 |
| `DB_NAME`       | PostgreSQL database | `data_warehouse`             |
| `DB_HOST`       | PostgreSQL host     | `db` (Docker) or `localhost` |
| `DB_PORT`       | PostgreSQL port     | `5432`                       |

---
````
