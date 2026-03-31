import json
import re
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from .ollama import generate, list_models, chat, is_healthy

SYSTEM_PROMPT = """You are the Command Center AI assistant. You help the user manage their projects, tasks, documents, and content through natural language.

When the user asks you to DO something (create, list, summarize, etc.), respond with a JSON block wrapped in ```json ... ``` containing the action to execute.

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

If the user is just chatting or asking a question that doesn't need an action, respond normally without JSON. Be friendly, concise, and helpful. When you execute an action, briefly explain what you're doing."""


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
        healthy = is_healthy()
        return {"success": True, "message": f"Ollama: {'online' if healthy else 'offline'}", "data": {"ollama": healthy}}

    elif action == "draft_content":
        topic = params.get("topic", "")
        platform = params.get("platform", "twitter")
        tone = params.get("tone", "professional")
        system_msg = f"Draft a {platform} post about the following topic. Tone: {tone}. Keep it concise and engaging. For Twitter, stay under 280 characters."
        draft = generate(model, topic, system=system_msg)
        return {"success": True, "message": f"Drafted {platform} content", "data": {"draft": draft, "platform": platform}}

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
