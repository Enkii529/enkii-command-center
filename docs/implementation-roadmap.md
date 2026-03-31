# Implementation Roadmap

## Phase 1 - Foundation

Goal: get one durable local stack online.

Deliverables:
- Docker stack boots cleanly
- Postgres schema loads
- API health check passes
- Appsmith, Metabase, Grafana, n8n, and Ollama are reachable

Definition of done:
- `docker compose ps` shows all core services healthy or running
- `GET /summary` returns counts
- you can log into each UI once

## Phase 2 - Portal MVP

Goal: one practical home page.

Build these pages in Appsmith:
1. Home
2. Inbox / Triage
3. Tasks
4. Crypto HQ
5. Content Pipeline

Definition of done:
- Home page shows summary counts from `/summary`
- Tasks page can list, create, and update tasks
- Content page can create and view content pipeline records
- Documents page can create and review inbox items

## Phase 3 - Analytics

Goal: move from CRUD to visibility.

Use Metabase for:
- overdue tasks
- content pipeline by stage
- trade history by symbol
- documents added over time
- venture activity split

Use Grafana for:
- container uptime
- API latency
- resource usage
- future queue depth

## Phase 4 - Ingestion

Goal: make the inbox fill itself.

Start with deterministic sources:
- RSS/news
- Notion sync
- exchange API snapshots
- manual webhooks from your own projects

Rules:
- raw payload first
- normalize second
- enrich third
- never let dashboards read directly from raw payloads

## Phase 5 - AI Operators

Goal: AI becomes useful, not messy.

Recommended first operators:
- Triage Operator
- Research Operator
- Builder Operator
- Ops Operator

Requirements before shipping operators:
- every action must hit a real tool or API route
- every action must leave an audit trail in `agent_runs` and `tool_calls`
- write actions should support approval gates

## Phase 6 - Hardening

- reverse proxy and TLS
- external auth / SSO
- secrets management
- backups
- restore drills
- alerting
- pin image versions after first stable run
