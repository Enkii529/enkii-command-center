import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..ollama import is_healthy as ollama_healthy

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _check_service(url: str, timeout: float = 3.0) -> bool:
    try:
        resp = httpx.get(url, timeout=timeout)
        return resp.status_code < 500
    except Exception:
        return False


@router.get("/status")
def service_status():
    return {
        "services": [
            {"name": "API", "url": "http://localhost:8080", "status": "online", "port": 8080},
            {"name": "Ollama", "url": "http://localhost:11434", "status": "online" if ollama_healthy() else "offline", "port": 11434},
            {"name": "Appsmith", "url": "http://localhost:8081", "status": "online" if _check_service("http://appsmith:80") else "offline", "port": 8081},
            {"name": "Metabase", "url": "http://localhost:3000", "status": "online" if _check_service("http://metabase:3000") else "offline", "port": 3000},
            {"name": "Grafana", "url": "http://localhost:3001", "status": "online" if _check_service("http://grafana:3000") else "offline", "port": 3001},
            {"name": "n8n", "url": "http://localhost:5678", "status": "online" if _check_service("http://n8n:5678") else "offline", "port": 5678},
            {"name": "Prometheus", "url": "http://localhost:9090", "status": "online" if _check_service("http://prometheus:9090") else "offline", "port": 9090},
        ]
    }


@router.get("/activity")
def activity_feed(limit: int = 20, db: Session = Depends(get_db)):
    items = []

    tasks = db.execute(
        text("SELECT id, title, status, priority, created_at, 'task' as item_type FROM tasks ORDER BY created_at DESC LIMIT :lim"),
        {"lim": limit}
    ).mappings().all()
    items.extend([dict(t) for t in tasks])

    docs = db.execute(
        text("SELECT id, title, status, source_type, created_at, 'document' as item_type FROM documents ORDER BY created_at DESC LIMIT :lim"),
        {"lim": limit}
    ).mappings().all()
    items.extend([dict(d) for d in docs])

    content = db.execute(
        text("SELECT id, title, stage, platform, created_at, 'content' as item_type FROM content_items ORDER BY created_at DESC LIMIT :lim"),
        {"lim": limit}
    ).mappings().all()
    items.extend([dict(c) for c in content])

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"items": items[:limit]}
