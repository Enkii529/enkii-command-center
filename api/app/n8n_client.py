import uuid
import re
import httpx
from .config import settings


def _get_client() -> httpx.Client:
    return httpx.Client(
        base_url=settings.n8n_base_url,
        headers={"X-N8N-API-KEY": settings.n8n_api_key},
        timeout=30.0,
    )


def _raise_with_body(resp: httpx.Response):
    """Raise an exception that includes the n8n response body for debugging."""
    if resp.is_error:
        try:
            body = resp.json()
            msg = body.get("message", str(body))
        except Exception:
            msg = resp.text[:400]
        raise ValueError(f"n8n {resp.status_code}: {msg}")


# ─────────────────────────────────────────────────────────────
#  Workflow sanitizer — fixes common LLM output mistakes
#  before sending to n8n so we get fewer 400 errors
# ─────────────────────────────────────────────────────────────
_VALID_TYPES = {
    "n8n-nodes-base.scheduleTrigger",
    "n8n-nodes-base.manualTrigger",
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.set",
    "n8n-nodes-base.if",
    "n8n-nodes-base.code",
    "n8n-nodes-base.dateTime",
    "n8n-nodes-base.merge",
    "n8n-nodes-base.splitInBatches",
    "n8n-nodes-base.itemLists",
    "n8n-nodes-base.function",
    "n8n-nodes-base.noOp",
    "n8n-nodes-base.respondToWebhook",
}

_TYPE_VERSIONS = {
    "n8n-nodes-base.scheduleTrigger": 1.2,
    "n8n-nodes-base.manualTrigger": 1,
    "n8n-nodes-base.webhook": 2,
    "n8n-nodes-base.httpRequest": 4.2,
    "n8n-nodes-base.set": 3.4,
    "n8n-nodes-base.if": 2.2,
    "n8n-nodes-base.code": 2,
    "n8n-nodes-base.dateTime": 2,
    "n8n-nodes-base.merge": 3,
    "n8n-nodes-base.splitInBatches": 3,
    "n8n-nodes-base.itemLists": 3,
    "n8n-nodes-base.function": 2,
    "n8n-nodes-base.noOp": 1,
    "n8n-nodes-base.respondToWebhook": 1.1,
}


def _sanitize_node(node: dict) -> dict:
    """Fix individual node to pass n8n validation."""
    node = dict(node)

    # Ensure unique id
    if not node.get("id"):
        node["id"] = str(uuid.uuid4())

    # Ensure position is [x, y] integers
    pos = node.get("position", [250, 300])
    if not isinstance(pos, list) or len(pos) < 2:
        pos = [250, 300]
    node["position"] = [int(pos[0]), int(pos[1])]

    # Fix deprecated/invalid node types
    type_map = {
        "n8n-nodes-base.start": "n8n-nodes-base.manualTrigger",
        "n8n-nodes-base.itemListFilter": "n8n-nodes-base.itemLists",
        "n8n-nodes-base.itemListSort": "n8n-nodes-base.itemLists",
        "n8n-nodes-base.functionItem": "n8n-nodes-base.code",
        "n8n-nodes-base.moveBinaryData": "n8n-nodes-base.set",
        "n8n-nodes-base.spreadsheetFile": "n8n-nodes-base.itemLists",
    }
    node_type = node.get("type", "")
    if node_type in type_map:
        node["type"] = type_map[node_type]
        node_type = node["type"]

    # If type is completely unknown, replace with noOp so the workflow still imports
    if node_type not in _VALID_TYPES:
        node["type"] = "n8n-nodes-base.noOp"
        node["typeVersion"] = 1
        node["parameters"] = {}
        return node

    # Fix typeVersion
    expected_ver = _TYPE_VERSIONS.get(node.get("type", ""))
    if expected_ver and node.get("typeVersion") != expected_ver:
        node["typeVersion"] = expected_ver

    # Ensure parameters exists
    if "parameters" not in node or not isinstance(node["parameters"], dict):
        node["parameters"] = {}

    params = node["parameters"]

    # Fix set node: LLM sometimes generates a flat list instead of nested object
    if node.get("type") == "n8n-nodes-base.set":
        raw = params.get("assignments", {})
        if isinstance(raw, list):
            # Flat list → wrap in correct structure
            fixed = []
            for i, item in enumerate(raw):
                if isinstance(item, dict):
                    fixed.append({
                        "id": item.get("id", str(i + 1)),
                        "name": item.get("name", f"field{i}"),
                        "value": item.get("value", ""),
                        "type": item.get("type", "string"),
                    })
            params["assignments"] = {"assignments": fixed}
        elif isinstance(raw, dict) and "assignments" not in raw:
            # Dict but missing inner list
            params["assignments"] = {"assignments": []}

    # Fix httpRequest: ensure method is uppercase
    if node.get("type") == "n8n-nodes-base.httpRequest":
        if "method" in params:
            params["method"] = str(params["method"]).upper()
        # jsonBody must be a string, not a dict
        if "jsonBody" in params and isinstance(params["jsonBody"], dict):
            import json as _json
            params["jsonBody"] = _json.dumps(params["jsonBody"])

    # Fix code node: jsCode must be a string
    if node.get("type") == "n8n-nodes-base.code":
        if "jsCode" not in params or not isinstance(params.get("jsCode"), str):
            params["jsCode"] = "// Auto-generated placeholder\nreturn items;"

    return node


def _sanitize_connections(connections: dict, node_names: set) -> dict:
    """
    Fix connections structure. n8n expects:
    {"NodeName": {"main": [[{"node": "OtherNode", "type": "main", "index": 0}]]}}
    """
    if not isinstance(connections, dict):
        return {}

    cleaned = {}
    for source, outputs in connections.items():
        if source not in node_names:
            continue
        if not isinstance(outputs, dict):
            continue

        fixed_outputs = {}
        for output_key, branches in outputs.items():
            if not isinstance(branches, list):
                continue
            fixed_branches = []
            for branch in branches:
                if isinstance(branch, list):
                    fixed_items = []
                    for conn in branch:
                        if isinstance(conn, dict) and conn.get("node") in node_names:
                            fixed_items.append({
                                "node": conn["node"],
                                "type": conn.get("type", "main"),
                                "index": int(conn.get("index", 0)),
                            })
                    fixed_branches.append(fixed_items)
                elif isinstance(branch, dict) and branch.get("node") in node_names:
                    # LLM sometimes omits the outer list wrapper
                    fixed_branches.append([{
                        "node": branch["node"],
                        "type": branch.get("type", "main"),
                        "index": int(branch.get("index", 0)),
                    }])
            if fixed_branches:
                fixed_outputs[output_key] = fixed_branches

        if fixed_outputs:
            cleaned[source] = fixed_outputs

    return cleaned


def sanitize_workflow(name: str, nodes: list[dict], connections: dict) -> tuple[str, list[dict], dict]:
    """Full sanitize pass — returns (name, clean_nodes, clean_connections)."""
    clean_nodes = [_sanitize_node(n) for n in nodes]
    node_names = {n["name"] for n in clean_nodes}
    clean_connections = _sanitize_connections(connections, node_names)
    # Ensure name is a non-empty string
    clean_name = str(name).strip() or "AI-Generated Workflow"
    return clean_name, clean_nodes, clean_connections


# ─────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────

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
        _raise_with_body(resp)
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
        _raise_with_body(resp)
        return resp.json()


def create_workflow(name: str, nodes: list[dict], connections: dict, active: bool = False) -> dict:
    # Sanitize before sending
    clean_name, clean_nodes, clean_connections = sanitize_workflow(name, nodes, connections)
    # Note: n8n API v1 treats `active` as read-only on creation.
    # Workflows always start inactive; use activate_workflow() after creation.
    payload = {
        "name": clean_name,
        "nodes": clean_nodes,
        "connections": clean_connections,
        "settings": {"executionOrder": "v1"},
    }
    with _get_client() as client:
        resp = client.post("/api/v1/workflows", json=payload)
        _raise_with_body(resp)
        result = resp.json()
        # Activate after creation if requested
        if active and result.get("id"):
            activate_workflow(result["id"])
        return result


def activate_workflow(workflow_id: str) -> dict:
    with _get_client() as client:
        resp = client.patch(f"/api/v1/workflows/{workflow_id}", json={"active": True})
        _raise_with_body(resp)
        return resp.json()


def deactivate_workflow(workflow_id: str) -> dict:
    with _get_client() as client:
        resp = client.patch(f"/api/v1/workflows/{workflow_id}", json={"active": False})
        _raise_with_body(resp)
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
        _raise_with_body(resp)
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
