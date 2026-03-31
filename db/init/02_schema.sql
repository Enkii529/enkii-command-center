CREATE TABLE IF NOT EXISTS ventures (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS projects (
    id BIGSERIAL PRIMARY KEY,
    venture_id BIGINT REFERENCES ventures(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    priority TEXT NOT NULL DEFAULT 'medium',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasks (
    id BIGSERIAL PRIMARY KEY,
    venture_id BIGINT REFERENCES ventures(id) ON DELETE SET NULL,
    project_id BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'todo',
    priority TEXT NOT NULL DEFAULT 'medium',
    due_date DATE,
    assigned_to TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS work_sessions (
    id BIGSERIAL PRIMARY KEY,
    venture_id BIGINT REFERENCES ventures(id) ON DELETE SET NULL,
    project_id BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    task_id BIGINT REFERENCES tasks(id) ON DELETE SET NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS content_items (
    id BIGSERIAL PRIMARY KEY,
    venture_id BIGINT REFERENCES ventures(id) ON DELETE SET NULL,
    project_id BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    platform TEXT,
    stage TEXT NOT NULL DEFAULT 'idea',
    content_type TEXT,
    hook TEXT,
    cta TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assets (
    id BIGSERIAL PRIMARY KEY,
    content_item_id BIGINT REFERENCES content_items(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL,
    file_url TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS publishes (
    id BIGSERIAL PRIMARY KEY,
    content_item_id BIGINT REFERENCES content_items(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    url TEXT,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS exchanges (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS accounts (
    id BIGSERIAL PRIMARY KEY,
    exchange_id BIGINT REFERENCES exchanges(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    bucket_type TEXT NOT NULL DEFAULT 'general',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS positions (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT REFERENCES accounts(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    quantity NUMERIC(28, 10) NOT NULL,
    avg_entry NUMERIC(28, 10),
    current_price NUMERIC(28, 10),
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT REFERENCES accounts(id) ON DELETE SET NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity NUMERIC(28, 10) NOT NULL,
    price NUMERIC(28, 10) NOT NULL,
    rationale TEXT,
    strategy_tag TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id BIGSERIAL PRIMARY KEY,
    trade_id BIGINT REFERENCES trades(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    body TEXT,
    phase_tag TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT,
    signal_name TEXT NOT NULL,
    signal_value TEXT,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'manual',
    source_url TEXT,
    raw_text TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notes (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES documents(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    body TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS embeddings (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES documents(id) ON DELETE CASCADE,
    note_id BIGINT REFERENCES notes(id) ON DELETE CASCADE,
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (document_id IS NOT NULL OR note_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS entities (
    id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    name TEXT NOT NULL,
    slug TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS entity_links (
    id BIGSERIAL PRIMARY KEY,
    from_entity_id BIGINT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    to_entity_id BIGINT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS integrations (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    integration_type TEXT NOT NULL,
    config_ref TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jobs (
    id BIGSERIAL PRIMARY KEY,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    scheduled_for TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id BIGSERIAL PRIMARY KEY,
    operator_name TEXT NOT NULL,
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_payload JSONB,
    status TEXT NOT NULL DEFAULT 'pending',
    approval_required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id BIGSERIAL PRIMARY KEY,
    agent_run_id BIGINT REFERENCES agent_runs(id) ON DELETE SET NULL,
    tool_name TEXT NOT NULL,
    request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_payload JSONB,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_content_items_stage ON content_items(stage);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

INSERT INTO ventures (name, slug, description)
VALUES
    ('APlusCrypto', 'apluscrypto', 'Crypto research, education, and trading operation'),
    ('BizHeroes', 'bizheroes', 'Marketing and digital business operations'),
    ('Cosmic Chords Music', 'cosmic-chords-music', 'Music creation and publishing pipeline')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO projects (venture_id, name, description, status, priority)
SELECT id, 'Command Center Buildout', 'Initial command center stack and workflows', 'active', 'high'
FROM ventures WHERE slug = 'bizheroes'
ON CONFLICT DO NOTHING;

INSERT INTO tasks (venture_id, title, description, status, priority, due_date)
SELECT id, 'Stand up Docker stack', 'Boot Postgres, API, Appsmith, Metabase, Grafana, n8n, and Ollama', 'todo', 'high', CURRENT_DATE
FROM ventures WHERE slug = 'bizheroes'
UNION ALL
SELECT id, 'Connect Appsmith to Postgres/API', 'Build first Home dashboard widgets', 'todo', 'high', CURRENT_DATE + 1
FROM ventures WHERE slug = 'bizheroes'
UNION ALL
SELECT id, 'Create crypto journal workflow', 'Wire n8n to insert journal entries and trade snapshots', 'todo', 'medium', CURRENT_DATE + 3
FROM ventures WHERE slug = 'apluscrypto';
