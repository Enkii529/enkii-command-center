from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ..ollama import list_models, get_default_model, generate, chat, embed

router = APIRouter(prefix="/ai", tags=["AI"])


class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: list[dict]


class GenerateRequest(BaseModel):
    model: Optional[str] = None
    prompt: str
    system: Optional[str] = None


class SummarizeRequest(BaseModel):
    model: Optional[str] = None
    text: str


class EmbedRequest(BaseModel):
    model: Optional[str] = None
    text: str


@router.get("/models")
def get_models():
    return {"models": list_models(), "default": get_default_model()}


@router.post("/chat")
def ai_chat(req: ChatRequest):
    model = req.model or get_default_model()
    response = chat(model, req.messages)
    return {"model": model, "response": response}


@router.post("/generate")
def ai_generate(req: GenerateRequest):
    model = req.model or get_default_model()
    response = generate(model, req.prompt, system=req.system)
    return {"model": model, "response": response}


@router.post("/summarize")
def ai_summarize(req: SummarizeRequest):
    model = req.model or get_default_model()
    system = "You are a helpful assistant. Summarize the following text concisely in 2-3 sentences. Be direct and factual."
    response = generate(model, req.text, system=system)
    return {"model": model, "summary": response}


@router.post("/embed")
def ai_embed(req: EmbedRequest):
    model = req.model or "nomic-embed-text:latest"
    embedding = embed(model, req.text)
    return {"model": model, "embedding": embedding, "dimensions": len(embedding)}
