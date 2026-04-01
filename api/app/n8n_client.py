import httpx
from .config import settings


def _get_client() -> httpx.Client:
    return httpx.Client(
        base_url=settings.n8n_base_url,
        headers={"X-N8N-API-KEY": settings.n8n_api_key},
        timeout=30.0,
    )


def is_configured() -> bool:
    return bool(settings.n8n_api_key)


def is_healthy() -> bool:
    if not is_configured():
        return False
    try:
        with _get_client() as client:
            resp = client.get("/api/v1/workflows?limit=1")
            return resp.status_code == 200
    except Exception:
        return False


def list_workflows() -> list[dict]:
    with _get_client() as client:
        resp = client.get("/api/v1/workflows")
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "id": w["id"],
                "name": w["name"],
                "active": w["active"],
                "createdAt": w.get("createdAt", ""),
                "updatedAt": w.get("updatedAt", ""),
                "nodes": len(w.get("nodes", [])),
            }
            for w in data.get("data", [])
        ]


def get_workflow(workflow_id: str) -> dict:
    with _get_client() as client:
        resp = client.get(f"/api/v1/workflows/{workflow_id}")
        resp.raise_for_status()
        return resp.json()


def create_workflow(name: str, nodes: list[dict], connections: dict, active: bool = False) -> dict:
    payload = {
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "active": active,
        "settings": {
            "executionOrder": "v1",
        },
    }
    with _get_client() as client:
        resp = client.post("/api/v1/workflows", json=payload)
        resp.raise_for_status()
        return resp.json()


def activate_workflow(workflow_id: str) -> dict:
    with _get_client() as client:
        resp = client.patch(f"/api/v1/workflows/{workflow_id}", json={"active": True})
        resp.raise_for_status()
        return resp.json()


def deactivate_workflow(workflow_id: str) -> dict:
    with _get_client() as client:
        resp = client.patch(f"/api/v1/workflows/{workflow_id}", json={"active": False})
        resp.raise_for_status()
        return resp.json()


def delete_workflow(workflow_id: str) -> bool:
    with _get_client() as client:
        resp = client.delete(f"/api/v1/workflows/{workflow_id}")
        return resp.status_code == 200


def list_executions(workflow_id: str = None, limit: int = 10) -> list[dict]:
    params = {"limit": limit}
    if workflow_id:
        params["workflowId"] = workflow_id
    with _get_client() as client:
        resp = client.get("/api/v1/executions", params=params)
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "id": e["id"],
                "workflowId": e.get("workflowId", ""),
                "status": e.get("status", ""),
                "startedAt": e.get("startedAt", ""),
                "stoppedAt": e.get("stoppedAt", ""),
            }
            for e in data.get("data", [])
        ]
