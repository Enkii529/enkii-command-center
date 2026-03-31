# Command Center Starter - Full Step-by-Step Setup Guide

This guide turns the starter bundle into a working local command center.

It covers:
- prerequisites
- first boot
- what to configure in each service
- how to make the portal actually useful
- how to move from "stack is running" to "system is functional"

---

## 1. What this build already gives you

The starter already includes:
- PostgreSQL with pgvector
- Redis
- FastAPI backend
- Appsmith
- Metabase
- Grafana
- Prometheus
- n8n
- Ollama
- seed data for ventures, projects, and tasks

The stack is **not fully functional out of the box** in the sense of:
- no Appsmith pages are pre-built yet
- no n8n workflows are pre-built yet
- no external APIs are connected yet
- no auth reverse proxy or HTTPS is added yet

So "fully functional" means you will configure those pieces after first boot.

---

## 2. Prerequisites

### On Windows
Install:
1. Docker Desktop
2. Git
3. A code editor such as VS Code
4. Optional but recommended: WSL2 enabled in Docker Desktop

### Confirm Docker works
Open PowerShell in the project folder and run:

```powershell
docker --version

docker compose version
```

If both return versions, you're good.

---

## 3. Extract and open the project

1. Extract `command-center-starter.zip`
2. Open a terminal in the extracted folder
3. Confirm you see these files:

```text
.env.example
README.md
docker-compose.yml
api/
db/
docs/
grafana/
prometheus/
```

---

## 4. Create and edit the environment file

### Step 1
Copy the example env file:

```powershell
copy .env.example .env
```

If you're in Git Bash:

```bash
cp .env.example .env
```

### Step 2
Open `.env` and change these values:

```env
POSTGRES_DB=command_center
POSTGRES_USER=cc_admin
POSTGRES_PASSWORD=your_strong_postgres_password

REDIS_PASSWORD=your_strong_redis_password

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_strong_grafana_password

N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your_strong_n8n_password
N8N_ENCRYPTION_KEY=make_this_a_long_random_string_32_chars_or_more

METABASE_DB_FILE=/metabase-data/metabase.db

OLLAMA_HOST=0.0.0.0
API_PORT=8080
```

### What matters most
Do **not** leave these as defaults:
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `GRAFANA_ADMIN_PASSWORD`
- `N8N_BASIC_AUTH_PASSWORD`
- `N8N_ENCRYPTION_KEY`

---

## 5. Start the stack

From the project folder run:

```powershell
docker compose up -d --build
```

### What this does
- builds the FastAPI service from `api/`
- starts all containers
- initializes the database from `db/init/*.sql`
- creates Docker volumes for persistence

### Check status
Run:

```powershell
docker compose ps
```

You want to see these services up:
- postgres
- redis
- api
- appsmith
- metabase
- prometheus
- grafana
- n8n
- ollama

If something fails, inspect logs:

```powershell
docker compose logs api

docker compose logs postgres

docker compose logs appsmith

docker compose logs n8n
```

---

## 6. Verify the base services

Open these URLs in your browser:

- API docs: `http://localhost:8080/docs`
- Appsmith: `http://localhost:8081`
- Metabase: `http://localhost:3000`
- Grafana: `http://localhost:3001`
- n8n: `http://localhost:5678`
- Prometheus: `http://localhost:9090`
- Ollama API root test from terminal:

```powershell
curl http://localhost:11434/api/tags
```

### API checks
Open:
- `http://localhost:8080/health`
- `http://localhost:8080/summary`
- `http://localhost:8080/ventures`
- `http://localhost:8080/tasks`

If those return JSON, your API and database are working.

---

## 7. What the database already contains

The schema creates starter data automatically.

You should already have:
- ventures:
  - APlusCrypto
  - BizHeroes
  - Cosmic Chords Music
- one starter project:
  - Command Center Buildout
- a few starter tasks

That means Appsmith and Metabase will have real data to show immediately.

---

## 8. Configure Appsmith

This is the main portal UI. This is where your command center actually becomes usable.

### Step 1 - First login
1. Open `http://localhost:8081`
2. Complete the Appsmith admin signup
3. Create a workspace named something like:
   - `Command Center`

### Step 2 - Create datasources
You need **two** datasources.

#### A. PostgreSQL datasource
Use these values:
- Host: `postgres`
- Port: `5432`
- Database name: value of `POSTGRES_DB`
- Username: value of `POSTGRES_USER`
- Password: value of `POSTGRES_PASSWORD`
- SSL: off for local use

Why `postgres` and not `localhost`?
Because Appsmith runs in Docker and connects over the Docker network.

#### B. REST API datasource
Use:
- Base URL: `http://api:8080`

### Step 3 - Build the pages
Create these Appsmith pages:
1. Home
2. Inbox
3. Tasks
4. CryptoHQ
5. ContentPipeline
6. AILab
7. Ops

### Step 4 - Configure the Home page
Use a mix of cards and tables.

Create REST queries:
- `getSummary` -> `GET /summary`
- `getTasks` -> `GET /tasks`
- `getContentItems` -> `GET /content-items`
- `getDocuments` -> `GET /documents`
- `getTrades` -> `GET /trades`

#### Widgets to add on Home
1. Summary cards:
   - ventures_total
   - projects_active
   - tasks_open
   - tasks_due_today
   - content_in_pipeline
   - new_documents
   - trades_total
2. Table: high priority open tasks
3. Table: tasks due today
4. Table: content items not published
5. Table: new documents
6. Table: recent trades

### Step 5 - Configure the Tasks page
Create queries:
- `getTasks` -> `GET /tasks`
- `createTask` -> `POST /tasks`
- `updateTask` -> `PATCH /tasks/{{TasksTable.selectedRow.id}}`

#### Suggested layout
- top filter row
- main tasks table
- button: `New Task`
- modal form for create/edit

#### Create task body example
```json
{
  "venture_id": {{SelectVenture.selectedOptionValue || null}},
  "project_id": {{SelectProject.selectedOptionValue || null}},
  "title": {{InputTitle.text}},
  "description": {{InputDescription.text}},
  "status": {{SelectStatus.selectedOptionValue}},
  "priority": {{SelectPriority.selectedOptionValue}},
  "due_date": {{DateDue.selectedDate || null}},
  "assigned_to": {{InputAssignedTo.text || null}}
}
```

#### Update task body example
```json
{
  "title": {{EditTitle.text}},
  "description": {{EditDescription.text}},
  "status": {{EditStatus.selectedOptionValue}},
  "priority": {{EditPriority.selectedOptionValue}},
  "due_date": {{EditDue.selectedDate || null}},
  "assigned_to": {{EditAssignedTo.text || null}}
}
```

### Step 6 - Configure the Inbox page
Queries:
- `getDocuments` -> `GET /documents`
- `createDocument` -> `POST /documents`

Add:
- document queue table
- side panel or modal showing selected document text
- button to add document manually

#### Create document body example
```json
{
  "title": {{DocTitle.text}},
  "source_type": {{DocSourceType.selectedOptionValue}},
  "source_url": {{DocSourceUrl.text || null}},
  "raw_text": {{DocRawText.text || null}},
  "status": "new"
}
```

### Step 7 - Configure the Content Pipeline page
Queries:
- `getContentItems` -> `GET /content-items`
- `createContentItem` -> `POST /content-items`

Add:
- table or kanban-style columns by stage
- quick add form
- filters by platform and venture

#### Create content item body example
```json
{
  "venture_id": {{ContentVenture.selectedOptionValue || null}},
  "project_id": {{ContentProject.selectedOptionValue || null}},
  "title": {{ContentTitle.text}},
  "platform": {{ContentPlatform.selectedOptionValue || null}},
  "stage": {{ContentStage.selectedOptionValue}},
  "content_type": {{ContentType.selectedOptionValue || null}},
  "hook": {{ContentHook.text || null}},
  "cta": {{ContentCTA.text || null}}
}
```

### Step 8 - Configure the CryptoHQ page
Queries:
- `getTrades` -> `GET /trades`
- `createTrade` -> `POST /trades`

Add:
- recent trades table
- manual trade entry form
- placeholder sections for positions and signals

#### Create trade body example
```json
{
  "account_id": {{TradeAccount.selectedOptionValue || null}},
  "symbol": {{TradeSymbol.text}},
  "side": {{TradeSide.selectedOptionValue}},
  "quantity": {{Number(TradeQty.text)}},
  "price": {{Number(TradePrice.text)}},
  "rationale": {{TradeRationale.text || null}},
  "strategy_tag": {{TradeStrategy.text || null}}
}
```

### Step 9 - Configure the Ops page
You can start simple.

Add buttons or links to:
- Grafana
- Prometheus
- API docs
- n8n

Then add iframe/embed widgets if you want an in-app ops page.

---

## 9. Configure Metabase

Use Metabase for analytics, not CRUD.

### Step 1 - First login
1. Open `http://localhost:3000`
2. Create the admin user
3. Skip sample data if prompted

### Step 2 - Connect the database
Choose PostgreSQL and use:
- Host: `postgres`
- Port: `5432`
- Database: value of `POSTGRES_DB`
- Username: value of `POSTGRES_USER`
- Password: value of `POSTGRES_PASSWORD`

### Step 3 - Add starter SQL questions
Use the SQL in:
- `docs/metabase-starter-queries.md`

Create these questions first:
1. Open tasks by priority
2. Tasks due today or overdue
3. Content pipeline by stage
4. New documents by day
5. Trades by symbol
6. Venture workload

### Step 4 - Create a dashboard named `Command Center Analytics`
Add the saved questions to one dashboard.

Recommended layout:
- Row 1: open tasks by priority, tasks due today or overdue
- Row 2: content pipeline by stage, new documents by day
- Row 3: trades by symbol, venture workload

---

## 10. Configure Grafana

Use Grafana for ops monitoring.

### Step 1 - First login
Open `http://localhost:3001`

Login with:
- username: value of `GRAFANA_ADMIN_USER`
- password: value of `GRAFANA_ADMIN_PASSWORD`

### Step 2 - Confirm Prometheus datasource exists
The starter is set up to provision Prometheus automatically.

Go to:
- Connections
- Data Sources

You should see Prometheus already present.

### Step 3 - Open the starter dashboard
The file exists here:
- `grafana/dashboards/command-center-overview.json`

If it did not auto-load, import it manually.

### Step 4 - What to monitor first
Track these first:
- API uptime
- API request count
- API latency
- container restarts
- host CPU
- host RAM
- disk space

Note: the current starter mainly exposes FastAPI metrics. For full Docker/host monitoring, add node-exporter and cAdvisor later.

---

## 11. Configure Prometheus

Prometheus should already start with the included config.

Open:
- `http://localhost:9090`

Run test queries like:
- `up`
- `http_requests_total`

If those work, Prometheus is scraping at least the API metrics endpoint.

---

## 12. Configure Ollama

Ollama is the local model runtime.

### Step 1 - Check available models
Run:

```powershell
curl http://localhost:11434/api/tags
```

If no models are installed yet, the list may be empty.

### Step 2 - Pull a model
From PowerShell:

```powershell
docker exec -it cc-ollama ollama pull llama3.2
```

Or another model you want to use.

### Step 3 - Test a generation
```powershell
docker exec -it cc-ollama ollama run llama3.2 "Give me a one sentence summary of what a command center dashboard does."
```

### Step 4 - How you will use Ollama in this stack
Primary use cases:
- summarize incoming documents
- classify notes or research items
- draft first-pass content notes
- support n8n automations

Do not let it write directly to production tables without either:
- validation logic, or
- an approval step

---

## 13. Configure n8n

Use n8n to automate ingestion and workflows.

### Step 1 - First login
Open `http://localhost:5678`

Login with:
- username: value of `N8N_BASIC_AUTH_USER`
- password: value of `N8N_BASIC_AUTH_PASSWORD`

Complete the owner setup.

### Step 2 - Create your first credentials
At minimum, create:
- HTTP credential for local API if needed
- later: Notion
- later: exchange APIs
- later: email/webhooks

### Step 3 - Build the first three workflows

#### Workflow 1 - Manual document intake
Purpose: push research or article text into the inbox.

Nodes:
1. Manual Trigger
2. Set node
   - title
   - source_type
   - source_url
   - raw_text
3. HTTP Request
   - POST `http://api:8080/documents`
   - send JSON body
4. Success notification or log

#### Workflow 2 - Trade journal intake
Purpose: create trade records quickly.

Nodes:
1. Webhook or Manual Trigger
2. Set node
   - symbol
   - side
   - quantity
   - price
   - rationale
   - strategy_tag
3. HTTP Request
   - POST `http://api:8080/trades`

#### Workflow 3 - AI document triage
Purpose: summarize a document and route it.

Nodes:
1. Schedule Trigger
2. HTTP Request
   - GET `http://api:8080/documents`
3. Filter for `status = new`
4. HTTP Request or Code node to send text to Ollama
5. Parse summary/classification
6. Optional: write note or create task

### Step 4 - Export workflows
Save exports into:
- `n8n/workflows/`

That keeps your automations versionable.

---

## 14. Make the system actually useful fast

If your goal is "fully functional as soon as possible," do this exact order:

### Day 1 - Working base
1. Boot the stack
2. Confirm `/summary` works
3. Configure Appsmith datasources
4. Build Home page cards
5. Build Tasks page list and create form

### Day 2 - Real usage
6. Build Documents page
7. Build Content page
8. Build Trade entry form
9. Create Metabase dashboard

### Day 3 - First automation
10. Add n8n manual document intake workflow
11. Add n8n trade entry workflow
12. Pull one Ollama model
13. Add a basic summarize-via-Ollama test flow

Once that is done, it stops being a shell and becomes a real working control center.

---

## 15. Minimum definition of "fully functional"

For this starter, I would call it fully functional when all of these are true:

### Core platform
- all Docker containers start cleanly
- data persists across restarts
- `/summary` returns real counts

### Portal
- Home page shows live summary cards
- Tasks page can create and update tasks
- Documents page can create inbox items
- Content page can create content items
- Crypto page can create trade entries

### Analytics
- Metabase dashboard is connected and populated
- Grafana shows API metrics

### Automation
- n8n can push a document into the API
- n8n can push a trade into the API
- Ollama can summarize text locally

### Operational sanity
- you can restart the stack without losing data
- passwords are changed from defaults
- backups or export habits are defined

---

## 16. Strong next upgrades after MVP

After the MVP works, add these next:

1. **Node Exporter + cAdvisor**
   - better host and container monitoring in Grafana
2. **Reverse proxy + HTTPS**
   - Caddy or Nginx if exposed outside localhost
3. **SSO/Auth layer**
   - Keycloak or another auth provider
4. **Backups**
   - Postgres dump schedule
   - Appsmith backup/export habit
   - n8n workflow exports
5. **More API routes**
   - positions
   - signals
   - notes
   - agent_runs
   - tool_calls
6. **Approval flow for AI actions**
   - especially before writes to tasks, trades, or content records

---

## 17. Common mistakes to avoid

1. Using `localhost` inside Appsmith or Metabase datasource settings
   - use Docker service names like `postgres` and `api`
2. Leaving default passwords in `.env`
3. Building too much logic inside Appsmith widgets
   - keep logic in API or database
4. Letting raw external data power dashboards directly
   - normalize it first
5. Letting AI write directly into core tables without review
6. Forgetting to export n8n workflows

---

## 18. Useful commands

### Start
```powershell
docker compose up -d --build
```

### Stop
```powershell
docker compose down
```

### Stop without deleting volumes
```powershell
docker compose stop
```

### View running services
```powershell
docker compose ps
```

### Tail logs for one service
```powershell
docker compose logs -f api
```

### Restart one service
```powershell
docker compose restart api
```

### Check the API directly
```powershell
curl http://localhost:8080/health
curl http://localhost:8080/summary
```

### See Docker volumes
```powershell
docker volume ls
```

---

## 19. Best first expansion path

If you want the highest payoff with the least wasted work, do this next:

1. finish Appsmith pages
2. finish Metabase dashboard
3. add 2 or 3 n8n workflows
4. add Ollama summarization
5. add more API routes for notes, signals, positions, and agent logs
6. then add multi-agent logic

That order prevents the project from turning into agent chaos before the data model is stable.

---

## 20. Final blunt truth

Right now the starter is a **strong skeleton**.
It is not a complete finished command center yet.

To make it fully functional, the highest-value manual work is:
- build the Appsmith pages
- connect Metabase
- create the first n8n workflows
- pull a local Ollama model
- add the next API endpoints you know you'll actually use

Once those are done, the system becomes real fast.
