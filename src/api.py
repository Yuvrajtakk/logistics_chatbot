# Thin HTTP wrapper around the existing orchestrate() / synthesize_answer()
# pipeline. Does not duplicate any pipeline logic — just exposes it over
# HTTP so the website can call it. In-memory session store is intentional
# (single-user demo scale) — do not add Redis/DB-backed sessions unless
# that's ever genuinely needed (YAGNI).

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.orchestrator import orchestrate
from src.answer_synth import synthesize_answer
from src.memory import ConversationMemory
import src.llm_client

app = FastAPI()
_allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: dict[str, ConversationMemory] = {}


@app.get("/health")
def health():
    """Small unauthenticated probe used by the hosting platform."""
    return {"status": "ok"}

class ChatRequest(BaseModel):
    question: str
    provider: str = "groq"
    session_id: str = "default"

@app.post("/api/chat")
def chat(req: ChatRequest):
    memory = _sessions.setdefault(req.session_id, ConversationMemory())
    provider = "groq" if os.getenv("RAILWAY_ENVIRONMENT") else req.provider

    result = orchestrate(req.question, memory=memory, provider=provider)
    answer = synthesize_answer(req.question, result, provider=provider)
    memory.add_turn(question=req.question, tool=result.get("route", "unknown"), answer=answer)

    return {
        "answer": answer,
        "route": result.get("route"),
        "sql": result.get("sql"),  # None unless route touched sql
    }

@app.get("/api/providers")
def providers():
    # Gemini is intentionally reported unavailable — see Section 6.
    is_production = bool(os.getenv("RAILWAY_ENVIRONMENT"))
    return {
        "groq": True,
        "ollama": not is_production,
        "gemini": False,
        "provider_mode": "groq-only" if is_production else "selectable",
    }
