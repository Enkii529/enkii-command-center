import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional

from .. import n8n_client, job_store
from ..ai_actions import _build_n8n_workflow

router = APIRouter(prefix="/n8n", tags=["n8n"])


@router.get("/status")
def n8n_status():
    configured = n8n_client.is_configured()
    healthy = n8n_client.is_healthy() if configured else False
    return {
        "configured": configured,
        "healthy": healthy,
        "message": (
            "n8n connected" if healthy
            else "Set N8N_API_KEY in .env (generate at n8n Settings > API)" if not configured
            else "n8n unreachable"
        ),
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


# ─────────────────────────────────────────────────────────────
#  Async build endpoint — returns a job ID immediately,
#  generation runs in background, frontend polls /build/{id}
# ─────────────────────────────────────────────────────────────

class BuildWorkflowRequest(BaseModel):
    description: str
    model: Optional[str] = "qwen2.5-coder:7b"
    deploy: bool = True


def _condense_description(description: str) -> str:
    """
    If the description is very long (e.g. a requirements doc), extract
    the core intent into a focused paragraph the LLM can work with cleanly.
    Long prompts cause the model to generate incomplete/invalid JSON.
    """
    lines = [l.strip() for l in description.strip().splitlines() if l.strip()]
    # If short enough, use as-is
    if len(description) < 800:
        return description

    # Extract key lines: numbered requirements, source mentions, output format hints
    keywords = ["trigger", "source", "pull", "fetch", "every", "schedule",
                 "reddit", "hacker news", "rss", "youtube", "news", "rank",
                 "save", "output", "normalize", "dedupe", "top", "comment",
                 "google", "notion", "slack", "telegram", "discord"]
    key_lines = []
    for line in lines:
        lower = line.lower()
        if any(k in lower for k in keywords):
            key_lines.append(line.lstrip("0123456789.-) "))
        if len(key_lines) >= 12:
            break

    if key_lines:
        condensed = ". ".join(key_lines[:12])
        return condensed

    # Fallback: first 700 chars
    return description[:700]


def _run_build_job(job_id: str, description: str, model: str, deploy: bool):
    """Background task: generate workflow JSON and optionally deploy to n8n."""
    try:
        job_store.set_running(job_id)

        condensed = _condense_description(description)
        workflow_json = _build_n8n_workflow(condensed, model)

        if not workflow_json:
            job_store.set_failed(job_id, "Could not generate a valid workflow. Try rephrasing your description.")
            return

        name = workflow_json.get("name", "AI-Generated Workflow")
        nodes = workflow_json.get("nodes", [])
        connections = workflow_json.get("connections", {})

        if not nodes:
            job_store.set_failed(job_id, "Generated workflow has no nodes. Try a simpler description.")
            return

        result = {
            "name": name,
            "nodes": nodes,
            "connections": connections,
            "node_count": len(nodes),
            "deployed": False,
            "workflow_id": None,
            "n8n_url": None,
        }

        if deploy and n8n_client.is_configured():
            deployed = n8n_client.create_workflow(name, nodes, connections, active=False)
            wf_id = deployed.get("id", "")
            result["deployed"] = True
            result["workflow_id"] = wf_id
            result["n8n_url"] = f"http://localhost:5678/workflow/{wf_id}"

        job_store.set_done(job_id, result)

    except Exception as exc:
        job_store.set_failed(job_id, str(exc))


@router.post("/build")
def build_workflow(req: BuildWorkflowRequest, background_tasks: BackgroundTasks):
    """
    Start an async workflow build job.
    Returns {job_id} immediately — poll GET /n8n/build/{job_id} for result.
    """
    if not req.description.strip():
        raise HTTPException(status_code=400, detail="description is required")
    if req.deploy and not n8n_client.is_configured():
        raise HTTPException(status_code=503, detail="N8N_API_KEY not configured")

    job_id = str(uuid.uuid4())
    job_store.create_job(job_id, {"description": req.description[:200]})
    background_tasks.add_task(_run_build_job, job_id, req.description, req.model or "qwen2.5-coder:7b", req.deploy)

    return {"job_id": job_id, "status": "pending"}


@router.get("/build/{job_id}")
def get_build_status(job_id: str):
    """Poll this endpoint to check build progress and get the result."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
