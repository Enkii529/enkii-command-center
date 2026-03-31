# Command Center Starter Build

This is a working starter scaffold based on your uploaded dashboard blueprint. It gives you a single local stack with:

- PostgreSQL + `pgvector` as the system of record
- Redis for queue/cache use cases
- FastAPI backend for CRUD + dashboard summary endpoints
- Appsmith for the main portal UI
- Metabase for analytics
- Grafana + Prometheus for observability
- n8n for automation
- Ollama for local model serving

## What this starter is

This is the **first buildable foundation**, not the final polished product.

It is meant to get you from blueprint -> running stack -> real data model -> first dashboards.

## Folder layout

```text
command-center-starter/
├─ api/                     # FastAPI backend
├─ db/init/                 # DB extension + schema + seed data
├─ docs/                    # Build notes and next steps
├─ grafana/                 # Datasource + dashboard provisioning
├─ prometheus/              # Prometheus config
├─ n8n/workflows/           # Placeholder workflow export directory
├─ scripts/                 # Helper scripts
├─ .env.example             # Environment template
└─ docker-compose.yml       # Main stack
```

## Quick start

1. Copy the environment file.

```bash
cp .env.example .env
```

2. Edit `.env` and set strong passwords.

3. Start the stack.

```bash
docker compose up -d --build
```

4. Wait for containers to settle, then open:

- API: `http://localhost:8080/docs`
- Appsmith: `http://localhost:8081`
- Metabase: `http://localhost:3000`
- Grafana: `http://localhost:3001`
- n8n: `http://localhost:5678`
- Prometheus: `http://localhost:9090`

## First login notes

### Appsmith
- Complete initial admin setup
- Add a PostgreSQL datasource pointing to `postgres:5432`
- Build the first page from the widgets in `docs/portal-page-map.md`

### Metabase
- Complete initial setup
- Connect to Postgres using the values in `.env`
- Start with the SQL questions in `docs/metabase-starter-queries.md`

### Grafana
- Login with the values in `.env`
- Prometheus datasource is provisioned automatically
- Import or extend the starter dashboard in `grafana/dashboards/command-center-overview.json`

### n8n
- Finish the owner setup
- Create credentials for Notion, exchange APIs, email, or webhooks as needed
- Store workflow exports under `n8n/workflows/`

## Recommended build order

1. Boot the stack
2. Verify API + database
3. Create the **Home** page in Appsmith
4. Create the **Inbox/Triage** page in Appsmith
5. Connect Metabase to Postgres
6. Add the first ingestion flow in n8n
7. Add local LLM calls through Ollama
8. Only then add agent orchestration

## Core API endpoints included

- `GET /health`
- `GET /summary`
- `GET /ventures`
- `POST /ventures`
- `GET /projects`
- `POST /projects`
- `GET /tasks`
- `POST /tasks`
- `PATCH /tasks/{id}`
- `GET /content-items`
- `POST /content-items`
- `GET /documents`
- `POST /documents`
- `GET /trades`
- `POST /trades`

## What to build next

Read:

- `docs/implementation-roadmap.md`
- `docs/portal-page-map.md`
- `docs/metabase-starter-queries.md`
- `docs/appsmith-build-notes.md`

## Notes

- This starter keeps the final UI low-code-first so you can move faster.
- The API is intentionally thin. It is there to stabilize your data model and give Appsmith/automations a clean layer to hit.
- The schema follows the uploaded blueprint closely and is designed so you can expand without rebuilding the whole thing.
