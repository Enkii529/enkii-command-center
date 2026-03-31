from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from . import schemas
from .routers import ai, dashboard
from .ai_actions import process_user_message
from .ollama import get_default_model

app = FastAPI(title="Command Center API", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Routers
app.include_router(ai.router)
app.include_router(dashboard.router)


def rows_to_dicts(result):
    return [dict(row._mapping) for row in result]


# ── AI Action endpoint ──────────────────────────────────────────

class AIActionRequest(BaseModel):
    message: str
    model: Optional[str] = None
    history: Optional[list[dict]] = None


@app.post("/dashboard/ai-action")
def ai_action(req: AIActionRequest, db: Session = Depends(get_db)):
    model = req.model or get_default_model()
    result = process_user_message(req.message, model, db, history=req.history)
    return result


# ── Core endpoints ──────────────────────────────────────────────

@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/summary", response_model=schemas.SummaryResponse)
def summary(db: Session = Depends(get_db)):
    queries = {
        "ventures_total": "SELECT COUNT(*) FROM ventures",
        "projects_active": "SELECT COUNT(*) FROM projects WHERE status = 'active'",
        "tasks_open": "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done', 'archived')",
        "tasks_due_today": "SELECT COUNT(*) FROM tasks WHERE due_date = CURRENT_DATE AND status NOT IN ('done', 'archived')",
        "content_in_pipeline": "SELECT COUNT(*) FROM content_items WHERE stage NOT IN ('published', 'archived')",
        "new_documents": "SELECT COUNT(*) FROM documents WHERE status = 'new'",
        "trades_total": "SELECT COUNT(*) FROM trades",
    }
    output = {}
    for key, query in queries.items():
        output[key] = db.execute(text(query)).scalar_one()
    return output


# ── Ventures ────────────────────────────────────────────────────

@app.get("/ventures", response_model=list[schemas.VentureRead])
def get_ventures(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT * FROM ventures ORDER BY id DESC"))
    return rows_to_dicts(result)


@app.post("/ventures", response_model=schemas.VentureRead)
def create_venture(payload: schemas.VentureCreate, db: Session = Depends(get_db)):
    query = text("""
        INSERT INTO ventures (name, slug, description, status)
        VALUES (:name, :slug, :description, :status)
        RETURNING *
    """)
    row = db.execute(query, payload.model_dump()).mappings().first()
    db.commit()
    return dict(row)


# ── Projects ────────────────────────────────────────────────────

@app.get("/projects", response_model=list[schemas.ProjectRead])
def get_projects(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT * FROM projects ORDER BY id DESC"))
    return rows_to_dicts(result)


@app.post("/projects", response_model=schemas.ProjectRead)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    query = text("""
        INSERT INTO projects (venture_id, name, description, status, priority)
        VALUES (:venture_id, :name, :description, :status, :priority)
        RETURNING *
    """)
    row = db.execute(query, payload.model_dump()).mappings().first()
    db.commit()
    return dict(row)


# ── Tasks ───────────────────────────────────────────────────────

@app.get("/tasks", response_model=list[schemas.TaskRead])
def get_tasks(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT * FROM tasks ORDER BY id DESC"))
    return rows_to_dicts(result)


@app.post("/tasks", response_model=schemas.TaskRead)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    query = text("""
        INSERT INTO tasks (venture_id, project_id, title, description, status, priority, due_date, assigned_to)
        VALUES (:venture_id, :project_id, :title, :description, :status, :priority, :due_date, :assigned_to)
        RETURNING *
    """)
    row = db.execute(query, payload.model_dump()).mappings().first()
    db.commit()
    return dict(row)


@app.patch("/tasks/{task_id}", response_model=schemas.TaskRead)
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    existing = db.execute(text("SELECT * FROM tasks WHERE id = :id"), {"id": task_id}).mappings().first()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    values = {**dict(existing), **{k: v for k, v in payload.model_dump().items() if v is not None}}
    query = text("""
        UPDATE tasks
        SET title = :title, description = :description, status = :status,
            priority = :priority, due_date = :due_date, assigned_to = :assigned_to,
            updated_at = NOW()
        WHERE id = :id
        RETURNING *
    """)
    row = db.execute(query, {
        "id": task_id, "title": values["title"], "description": values["description"],
        "status": values["status"], "priority": values["priority"],
        "due_date": values["due_date"], "assigned_to": values["assigned_to"],
    }).mappings().first()
    db.commit()
    return dict(row)


# ── Content Items ───────────────────────────────────────────────

@app.get("/content-items", response_model=list[schemas.ContentItemRead])
def get_content_items(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT * FROM content_items ORDER BY id DESC"))
    return rows_to_dicts(result)


@app.post("/content-items", response_model=schemas.ContentItemRead)
def create_content_item(payload: schemas.ContentItemCreate, db: Session = Depends(get_db)):
    query = text("""
        INSERT INTO content_items (venture_id, project_id, title, platform, stage, content_type, hook, cta)
        VALUES (:venture_id, :project_id, :title, :platform, :stage, :content_type, :hook, :cta)
        RETURNING *
    """)
    row = db.execute(query, payload.model_dump()).mappings().first()
    db.commit()
    return dict(row)


# ── Documents ───────────────────────────────────────────────────

@app.get("/documents", response_model=list[schemas.DocumentRead])
def get_documents(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT * FROM documents ORDER BY id DESC"))
    return rows_to_dicts(result)


@app.post("/documents", response_model=schemas.DocumentRead)
def create_document(payload: schemas.DocumentCreate, db: Session = Depends(get_db)):
    query = text("""
        INSERT INTO documents (title, source_type, source_url, raw_text, status)
        VALUES (:title, :source_type, :source_url, :raw_text, :status)
        RETURNING *
    """)
    row = db.execute(query, payload.model_dump()).mappings().first()
    db.commit()
    return dict(row)


# ── Trades ──────────────────────────────────────────────────────

@app.get("/trades", response_model=list[schemas.TradeRead])
def get_trades(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT * FROM trades ORDER BY id DESC"))
    return rows_to_dicts(result)


@app.post("/trades", response_model=schemas.TradeRead)
def create_trade(payload: schemas.TradeCreate, db: Session = Depends(get_db)):
    query = text("""
        INSERT INTO trades (account_id, symbol, side, quantity, price, rationale, strategy_tag)
        VALUES (:account_id, :symbol, :side, :quantity, :price, :rationale, :strategy_tag)
        RETURNING *
    """)
    row = db.execute(query, payload.model_dump()).mappings().first()
    db.commit()
    return dict(row)


@app.get("/")
def root():
    return {
        "name": "Command Center API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "dashboard": "http://localhost:5629",
        "today": str(date.today()),
    }
