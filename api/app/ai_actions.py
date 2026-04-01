import json
import re
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from .ollama import generate, list_models, chat, is_healthy
from . import n8n_client

SYSTEM_PROMPT = """You are the Command Center AI assistant. You help the user manage their projects, tasks, documents, content, and automations through natural language.

When the user asks you to DO something (create, list, summarize, build, etc.), respond with a JSON block wrapped in ```json ... ``` containing the action to execute.

Available actions:

1. create_task - Create a new task
   {"action": "create_task", "params": {"title": "...", "priority": "high|medium|low", "status": "todo", "description": "..."}}

2. list_tasks - List tasks, optionally filtered
   {"action": "list_tasks", "params": {"status": "todo|in_progress|done", "limit": 10}}

3. create_document - Add a document to the inbox
   {"action": "create_document", "params": {"title": "...", "raw_text": "...", "source_type": "manual"}}

4. list_documents - List recent documents
   {"action": "list_documents", "params": {"limit": 10}}

5. summarize_text - Summarize provided text
   {"action": "summarize_text", "params": {"text": "..."}}

6. list_models - List available AI models
   {"action": "list_models", "params": {}}

7. system_status - Check system health
   {"action": "system_status", "params": {}}

8. draft_content - Draft content for a platform
   {"action": "draft_content", "params": {"topic": "...", "platform": "twitter|linkedin|blog", "tone": "professional|casual|bold"}}

9. list_workflows - List all n8n automation workflows
   {"action": "list_workflows", "params": {}}

10. create_workflow - Build and deploy an n8n automation workflow. Describe what the workflow should do.
    {"action": "create_workflow", "params": {"description": "detailed description of what the workflow should do"}}

11. activate_workflow - Turn on an n8n workflow by ID
    {"action": "activate_workflow", "params": {"workflow_id": "..."}}

12. deactivate_workflow - Turn off an n8n workflow by ID
    {"action": "deactivate_workflow", "params": {"workflow_id": "..."}}

13. list_executions - Show recent n8n workflow runs
    {"action": "list_executions", "params": {"workflow_id": "optional", "limit": 10}}

If the user is just chatting or asking a question that doesn't need an action, respond normally without JSON. Be friendly, concise, and helpful. When you execute an action, briefly explain what you're doing."""

N8N_WORKFLOW_PROMPT = """You are an expert n8n workflow builder. Generate a complete, valid n8n workflow JSON.

OUTPUT FORMAT: Return ONLY a raw JSON object. No markdown, no code fences, no explanation. Just the JSON.

REQUIRED JSON KEYS: "name" (string), "nodes" (array), "connections" (object)

NODE STRUCTURE — every node must have ALL of these fields:
{
  "name": "Unique Node Name",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.2,
  "position": [250, 300],
  "parameters": {}
}

VALID NODE TYPES (use ONLY these exact type strings):
- "n8n-nodes-base.scheduleTrigger"  typeVersion: 1.2  — runs on schedule
  parameters: {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}}
- "n8n-nodes-base.manualTrigger"    typeVersion: 1    — manual run button
  parameters: {}
- "n8n-nodes-base.webhook"          typeVersion: 2    — HTTP webhook
  parameters: {"path": "my-hook", "httpMethod": "POST", "responseMode": "onReceived"}
- "n8n-nodes-base.httpRequest"      typeVersion: 4.2  — call any HTTP API
  parameters: {"url": "https://...", "method": "GET"}
- "n8n-nodes-base.set"              typeVersion: 3.4  — set/transform fields
  parameters: {"assignments": {"assignments": [{"id": "1", "name": "field", "value": "val", "type": "string"}]}}
- "n8n-nodes-base.if"               typeVersion: 2.2  — conditional branch
  parameters: {"conditions": {"options": {"caseSensitive": true, "leftValue": "", "typeValidation": "strict", "version": 2}, "combinator": "and", "conditions": [{"leftValue": "={{ $json.status }}", "rightValue": "active", "operator": {"type": "string", "operation": "equals"}}]}}
- "n8n-nodes-base.code"             typeVersion: 2    — run JavaScript
  parameters: {"jsCode": "return items.map(item => ({ json: item.json }));"}
- "n8n-nodes-base.dateTime"         typeVersion: 2    — date/time operations
  parameters: {"operation": "getCurrentDate", "includeTime": true, "outputFieldName": "currentDate"}

CONNECTIONS FORMAT — CRITICAL, must be exactly this structure:
{
  "TriggerNodeName": {"main": [[{"node": "NextNodeName", "type": "main", "index": 0}]]},
  "NextNodeName": {"main": [[{"node": "FinalNodeName", "type": "main", "index": 0}]]}
}
The last node has NO entry in connections. For if-node: true branch is index 0, false branch is index 1.

POSITIONING: Start at [250, 300], increment x by 250 for each node. Keep y at 300.

INTERNAL URLS (inside Docker): Command Center API = http://api:8080

REAL EXAMPLE — Pull crypto news every 6 hours:
{"name":"Crypto News Monitor","nodes":[{"name":"Every 6 Hours","type":"n8n-nodes-base.scheduleTrigger","typeVersion":1.2,"position":[250,300],"parameters":{"rule":{"interval":[{"field":"hours","hoursInterval":6}]}}},{"name":"Fetch Crypto News","type":"n8n-nodes-base.httpRequest","typeVersion":4.2,"position":[500,300],"parameters":{"url":"https://api.coingecko.com/api/v3/news","method":"GET"}},{"name":"Save to Command Center","type":"n8n-nodes-base.httpRequest","typeVersion":4.2,"position":[750,300],"parameters":{"url":"http://api:8080/documents","method":"POST","sendBody":true,"specifyBody":"json","jsonBody":"={{ JSON.stringify({title: $json.title, raw_text: $json.description || $json.title, source_type: \\\"crypto_news\\\"}) }}"}}],"connections":{"Every 6 Hours":{"main":[[{"node":"Fetch Crypto News","type":"main","index":0}]]},"Fetch Crypto News":{"main":[[{"node":"Save to Command Center","type":"main","index":0}]]}}}

Now generate a workflow for this description. Return ONLY the JSON object, nothing else:
"""


def _extract_json(text_resp: str) -> dict | None:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text_resp, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try raw JSON
    try:
        start = text_resp.index("{")
        end = text_resp.rindex("}") + 1
        return json.loads(text_resp[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


def _build_n8n_workflow(description: str, model: str) -> dict:
    """Use Ollama (preferably a coding model) to generate an n8n workflow."""
    # Prefer coding model if available
    models = list_models()
    code_model = model
    for m in models:
        if "coder" in m["name"].lower():
            code_model = m["name"]
            break

    prompt = N8N_WORKFLOW_PROMPT + description
    response = generate(code_model, prompt, stream=False)

    workflow = _extract_json(response)
    if not workflow:
        return None
    return workflow


def _execute_action(action_data: dict, model: str, db: Session) -> dict:
    action = action_data.get("action", "")
    params = action_data.get("params", {})

    if action == "create_task":
        title = params.get("title", "Untitled Task")
        priority = params.get("priority", "medium")
        status = params.get("status", "todo")
        description = params.get("description", "")
        row = db.execute(
            text("""
                INSERT INTO tasks (title, priority, status, description)
                VALUES (:title, :priority, :status, :description)
                RETURNING id, title, priority, status
            """),
            {"title": title, "priority": priority, "status": status, "description": description}
        ).mappings().first()
        db.commit()
        return {"success": True, "message": f"Created task #{row['id']}: {row['title']} [{row['priority']}]", "data": dict(row)}

    elif action == "list_tasks":
        status_filter = params.get("status")
        limit = params.get("limit", 10)
        if status_filter:
            rows = db.execute(
                text("SELECT id, title, status, priority, due_date FROM tasks WHERE status = :s ORDER BY created_at DESC LIMIT :lim"),
                {"s": status_filter, "lim": limit}
            ).mappings().all()
        else:
            rows = db.execute(
                text("SELECT id, title, status, priority, due_date FROM tasks ORDER BY created_at DESC LIMIT :lim"),
                {"lim": limit}
            ).mappings().all()
        tasks = [dict(r) for r in rows]
        return {"success": True, "message": f"Found {len(tasks)} tasks", "data": tasks}

    elif action == "create_document":
        title = params.get("title", "Untitled Document")
        raw_text = params.get("raw_text", "")
        source_type = params.get("source_type", "manual")
        row = db.execute(
            text("""
                INSERT INTO documents (title, raw_text, source_type, status)
                VALUES (:title, :raw_text, :source_type, 'new')
                RETURNING id, title
            """),
            {"title": title, "raw_text": raw_text, "source_type": source_type}
        ).mappings().first()
        db.commit()
        return {"success": True, "message": f"Created document #{row['id']}: {row['title']}", "data": dict(row)}

    elif action == "list_documents":
        limit = params.get("limit", 10)
        rows = db.execute(
            text("SELECT id, title, status, source_type, created_at FROM documents ORDER BY created_at DESC LIMIT :lim"),
            {"lim": limit}
        ).mappings().all()
        return {"success": True, "message": f"Found {len(rows)} documents", "data": [dict(r) for r in rows]}

    elif action == "summarize_text":
        text_to_summarize = params.get("text", "")
        summary = generate(
            model, text_to_summarize,
            system="Summarize the following text concisely in 2-3 sentences. Be direct and factual."
        )
        return {"success": True, "message": "Summary generated", "data": {"summary": summary}}

    elif action == "list_models":
        models = list_models()
        return {"success": True, "message": f"Found {len(models)} models", "data": models}

    elif action == "system_status":
        ollama_ok = is_healthy()
        n8n_ok = n8n_client.is_healthy()
        return {
            "success": True,
            "message": f"Ollama: {'online' if ollama_ok else 'offline'} | n8n: {'online' if n8n_ok else 'offline (set N8N_API_KEY)'}",
            "data": {"ollama": ollama_ok, "n8n": n8n_ok},
        }

    elif action == "draft_content":
        topic = params.get("topic", "")
        platform = params.get("platform", "twitter")
        tone = params.get("tone", "professional")
        system_msg = f"Draft a {platform} post about the following topic. Tone: {tone}. Keep it concise and engaging. For Twitter, stay under 280 characters."
        draft = generate(model, topic, system=system_msg)
        return {"success": True, "message": f"Drafted {platform} content", "data": {"draft": draft, "platform": platform}}

    # ── n8n actions ─────────────────────────────────────

    elif action == "list_workflows":
        if not n8n_client.is_configured():
            return {"success": False, "message": "n8n not configured. Set N8N_API_KEY in your .env file. Generate one at n8n Settings > API.", "data": None}
        workflows = n8n_client.list_workflows()
        return {"success": True, "message": f"Found {len(workflows)} workflows", "data": workflows}

    elif action == "create_workflow":
        if not n8n_client.is_configured():
            return {"success": False, "message": "n8n not configured. Set N8N_API_KEY in your .env file. Generate one at n8n Settings > API.", "data": None}
        description = params.get("description", "")
        if not description:
            return {"success": False, "message": "Please describe what the workflow should do.", "data": None}

        workflow_json = _build_n8n_workflow(description, model)
        if not workflow_json:
            return {"success": False, "message": "Could not generate a valid workflow. Try describing it differently.", "data": None}

        name = workflow_json.get("name", "AI-Generated Workflow")
        nodes = workflow_json.get("nodes", [])
        connections = workflow_json.get("connections", {})

        result = n8n_client.create_workflow(name, nodes, connections)
        wf_id = result.get("id", "")
        return {
            "success": True,
            "message": f"Created n8n workflow '{name}' (ID: {wf_id}). Open n8n to review and activate it.",
            "data": {"id": wf_id, "name": name, "nodes": len(nodes)},
        }

    elif action == "activate_workflow":
        if not n8n_client.is_configured():
            return {"success": False, "message": "n8n not configured. Set N8N_API_KEY.", "data": None}
        wf_id = params.get("workflow_id", "")
        result = n8n_client.activate_workflow(wf_id)
        return {"success": True, "message": f"Activated workflow {wf_id}", "data": result}

    elif action == "deactivate_workflow":
        if not n8n_client.is_configured():
            return {"success": False, "message": "n8n not configured. Set N8N_API_KEY.", "data": None}
        wf_id = params.get("workflow_id", "")
        result = n8n_client.deactivate_workflow(wf_id)
        return {"success": True, "message": f"Deactivated workflow {wf_id}", "data": result}

    elif action == "list_executions":
        if not n8n_client.is_configured():
            return {"success": False, "message": "n8n not configured. Set N8N_API_KEY.", "data": None}
        wf_id = params.get("workflow_id")
        limit = params.get("limit", 10)
        execs = n8n_client.list_executions(wf_id, limit)
        return {"success": True, "message": f"Found {len(execs)} executions", "data": execs}

    else:
        return {"success": False, "message": f"Unknown action: {action}", "data": None}


_WORKFLOW_KEYWORDS = [
    "create workflow", "build workflow", "make workflow", "new workflow",
    "create automation", "build automation", "make automation", "set up automation",
    "create an n8n", "build an n8n", "make an n8n", "create n8n",
    "automate", "schedule a task", "set up a schedule",
    "pull from", "fetch from", "monitor and", "check every",
]


def _detect_workflow_intent(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in _WORKFLOW_KEYWORDS)


def process_user_message(message: str, model: str, db: Session, history: list[dict] | None = None) -> dict:
    # Fast-path: keyword-detected workflow intent — skip chat model, go direct
    if _detect_workflow_intent(message):
        action_data = {"action": "create_workflow", "params": {"description": message}}
        result = _execute_action(action_data, model, db)
        return {
            "response": result["message"],
            "action_executed": "create_workflow",
            "result": result,
        }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    ai_response = chat(model, messages)

    action_data = _extract_json(ai_response)
    if action_data and "action" in action_data:
        result = _execute_action(action_data, model, db)
        clean_response = re.sub(r"```json\s*\{.*?\}\s*```", "", ai_response, flags=re.DOTALL).strip()
        if not clean_response:
            clean_response = result["message"]
        return {
            "response": clean_response,
            "action_executed": action_data["action"],
            "result": result,
        }

    return {"response": ai_response, "action_executed": None, "result": None}
