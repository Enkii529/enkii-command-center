from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from .. import n8n_client

router = APIRouter(prefix="/n8n", tags=["n8n"])


@router.get("/status")
def n8n_status():
    configured = n8n_client.is_configured()
    healthy = n8n_client.is_healthy() if configured else False
    return {
        "configured": configured,
        "healthy": healthy,
        "message": "n8n connected" if healthy else "Set N8N_API_KEY in .env (generate at n8n Settings > API)" if not configured else "n8n unreachable",
    }


@router.get("/workflows")
def get_workflows():
    if not n8n_client.is_configured():
        raise HTTPException(status_code=503, detail="N8N_API_KEY not configured")
    return {"workflows": n8n_client.list_workflows()}


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    if not n8n_client.is_configured():
        raise HTTPException(status_code=503, detail="N8N_API_KEY not configured")
    return n8n_client.get_workflow(workflow_id)


class CreateWorkflowRequest(BaseModel):
    name: str
    nodes: list[dict]
    connections: dict
    active: bool = False


@router.post("/workflows")
def create_workflow(req: CreateWorkflowRequest):
    if not n8n_client.is_configured():
        raise HTTPException(status_code=503, detail="N8N_API_KEY not configured")
    return n8n_client.create_workflow(req.name, req.nodes, req.connections, req.active)


@router.patch("/workflows/{workflow_id}/activate")
def activate_workflow(workflow_id: str):
    if not n8n_client.is_configured():
        raise HTTPException(status_code=503, detail="N8N_API_KEY not configured")
    return n8n_client.activate_workflow(workflow_id)


@router.patch("/workflows/{workflow_id}/deactivate")
def deactivate_workflow(workflow_id: str):
    if not n8n_client.is_configured():
        raise HTTPException(status_code=503, detail="N8N_API_KEY not configured")
    return n8n_client.deactivate_workflow(workflow_id)


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: str):
    if not n8n_client.is_configured():
        raise HTTPException(status_code=503, detail="N8N_API_KEY not configured")
    success = n8n_client.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"deleted": True}


@router.get("/executions")
def get_executions(workflow_id: Optional[str] = None, limit: int = 10):
    if not n8n_client.is_configured():
        raise HTTPException(status_code=503, detail="N8N_API_KEY not configured")
    return {"executions": n8n_client.list_executions(workflow_id, limit)}
