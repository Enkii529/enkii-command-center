from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from .. import n8n_client
from ..ai_actions import _build_n8n_workflow

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


class BuildWorkflowRequest(BaseModel):
    description: str
    model: Optional[str] = "qwen2.5-coder:7b"
    deploy: bool = True


@router.post("/build")
def build_workflow(req: BuildWorkflowRequest):
    """
    Direct endpoint: describe a workflow in plain English, get it built
    and optionally deployed to n8n immediately. Bypasses the chat AI entirely.
    """
    if not req.description.strip():
        raise HTTPException(status_code=400, detail="description is required")

    # Generate workflow JSON via coding model
    workflow_json = _build_n8n_workflow(req.description, req.model)
    if not workflow_json:
        raise HTTPException(
            status_code=422,
            detail="Could not generate a valid workflow. Try rephrasing your description."
        )

    name = workflow_json.get("name", "AI-Generated Workflow")
    nodes = workflow_json.get("nodes", [])
    connections = workflow_json.get("connections", {})

    if not nodes:
        raise HTTPException(status_code=422, detail="Generated workflow has no nodes.")

    result = {
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "node_count": len(nodes),
        "deployed": False,
        "workflow_id": None,
        "n8n_url": None,
    }

    if req.deploy:
        if not n8n_client.is_configured():
            raise HTTPException(status_code=503, detail="N8N_API_KEY not configured")
        deployed = n8n_client.create_workflow(name, nodes, connections, active=False)
        wf_id = deployed.get("id", "")
        result["deployed"] = True
        result["workflow_id"] = wf_id
        result["n8n_url"] = f"http://localhost:5678/workflow/{wf_id}"

    return result
