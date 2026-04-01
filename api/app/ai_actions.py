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

N8N_WORKFLOW_PROMPT = """You are an n8n workflow builder. Generate a valid n8n workflow JSON based on the user's description.

IMPORTANT RULES:
- Return ONLY valid JSON with keys: "name", "nodes", "connections"
- Every workflow MUST have exactly one trigger node as the first node
- Use real n8n node types (e.g. "n8n-nodes-base.scheduleTrigger", "n8n-nodes-base.httpRequest", "n8n-nodes-base.set", "n8n-nodes-base.if", "n8n-nodes-base.code", "n8n-nodes-base.webhook")
- Each node needs: "name", "type", "typeVersion", "position" (array of [x, y]), "parameters"
- Connections format: {"NodeName": {"main": [[{"node": "NextNodeName", "type": "main", "index": 0}]]}}
- Position nodes left-to-right, starting at [250, 300], increment x by 250
- The Command Center API is at http://api:8080 (inside Docker network)

Common n8n node types:
- n8n-nodes-base.scheduleTrigger — runs on a cron schedule (parameters: {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}})
- n8n-nodes-base.webhook — HTTP webhook trigger (parameters: {"path": "my-hook", "httpMethod": "POST"})
- n8n-nodes-base.manualTrigger — manual run button (parameters: {})
- n8n-nodes-base.httpRequest — make HTTP calls (parameters: {"url": "...", "method": "GET|POST", "sendBody": true, "bodyParameters": {"parameters": [{"name": "...", "value": "..."}]}})
- n8n-nodes-base.set — set/transform data (parameters: {"assignments": {"assignments": [{"name": "...", "value": "...", "type": "string"}]}})
- n8n-nodes-base.if — conditional branch (parameters: {"conditions": {"options": {"version": 2}, "combinator": "and", "conditions": [{"leftValue": "...", "rightValue": "...", "operator": {"type": "string", "operation": "equals"}}]}})
- n8n-nodes-base.code — run JavaScript (parameters: {"jsCode": "return items;"})

Example — workflow that checks for new documents every hour and sends them to Ollama for summarization:
{
  "name": "Auto-Summarize New Documents",
  "nodes": [
    {"name": "Every Hour", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [250, 300], "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}}},
    {"name": "Get New Docs", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [500, 300], "parameters": {"url": "http://api:8080/documents", "method": "GET"}},
    {"name": "Filter New", "type": "n8n-nodes-base.if", "typeVersion": 2.2, "position": [750, 300], "parameters": {"conditions": {"options": {"version": 2}, "combinator": "and", "conditions": [{"leftValue": "={{ $json.status }}", "rightValue": "new", "operator": {"type": "string", "operation": "equals"}}]}}},
    {"name": "Summarize", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [1000, 300], "parameters": {"url": "http://api:8080/ai/summarize", "method": "POST", "sendBody": true, "specifyBody": "json", "jsonBody": "={{ JSON.stringify({text: $json.raw_text}) }}"}}
  ],
  "connections": {"Every Hour": {"main": [[{"node": "Get New Docs", "type": "main", "index": 0}]]}, "Get New Docs": {"main": [[{"node": "Filter New", "type": "main", "index": 0}]]}, "Filter New": {"main": [[{"node": "Summarize", "type": "main", "index": 0}]]}}
}

Now generate a workflow for the following description. Return ONLY the JSON, no markdown, no explanation:
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


def process_user_message(message: str, model: str, db: Session, history: list[dict] | None = None) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    ai_response = chat(model, messages)

    action_data = _extract_json(ai_response)
    if action_data and "action" in action_data:
        result = _execute_action(action_data, model, db)
        # Strip the JSON from the display message
        clean_response = re.sub(r"```json\s*\{.*?\}\s*```", "", ai_response, flags=re.DOTALL).strip()
        if not clean_response:
            clean_response = result["message"]
        return {
            "response": clean_response,
            "action_executed": action_data["action"],
            "result": result,
        }

    return {"response": ai_response, "action_executed": None, "result": None}
