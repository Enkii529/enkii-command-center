import httpx
from .config import settings

_client = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(base_url=settings.ollama_base_url, timeout=120.0)
    return _client


def list_models() -> list[dict]:
    resp = _get_client().get("/api/tags")
    resp.raise_for_status()
    data = resp.json()
    models = data.get("models", [])
    return [
        {
            "name": m["name"],
            "size": m.get("size", 0),
            "family": m.get("details", {}).get("family", "unknown"),
            "parameter_size": m.get("details", {}).get("parameter_size", ""),
            "quantization": m.get("details", {}).get("quantization_level", ""),
        }
        for m in models
    ]


def get_default_model() -> str:
    models = list_models()
    if not models:
        return "mistral:7b"
    # Prefer larger chat models first
    preferred = [
        "nvidia-nemotron-nano", "qwen3:8b", "mistral:7b",
        "deepseek-r1:8b", "hermes3:8b", "llama3.1:8b",
    ]
    for pref in preferred:
        for m in models:
            if pref in m["name"]:
                return m["name"]
    return models[0]["name"]


def generate(model: str, prompt: str, system: str | None = None, stream: bool = False) -> str:
    body: dict = {"model": model, "prompt": prompt, "stream": stream}
    if system:
        body["system"] = system
    resp = _get_client().post("/api/generate", json=body, timeout=180.0)
    resp.raise_for_status()
    return resp.json().get("response", "")


def chat(model: str, messages: list[dict], stream: bool = False) -> str:
    body = {"model": model, "messages": messages, "stream": stream}
    resp = _get_client().post("/api/chat", json=body, timeout=180.0)
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "")


def embed(model: str, text: str) -> list[float]:
    body = {"model": model, "input": text}
    resp = _get_client().post("/api/embed", json=body, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()
    embeddings = data.get("embeddings", [])
    return embeddings[0] if embeddings else []


def is_healthy() -> bool:
    try:
        resp = _get_client().get("/api/tags", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False
