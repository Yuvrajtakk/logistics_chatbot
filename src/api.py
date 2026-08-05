# Thin HTTP wrapper around the existing orchestrate() / synthesize_answer()
# pipeline. Does not duplicate any pipeline logic — just exposes it over
# HTTP so the website can call it. In-memory session store is intentional
# (single-user demo scale) — do not add Redis/DB-backed sessions unless
# that's ever genuinely needed (YAGNI).

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.orchestrator import orchestrate
from src.answer_synth import synthesize_answer
from src.memory import ConversationMemory
import src.llm_client

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # web/ dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: dict[str, ConversationMemory] = {}

class ChatRequest(BaseModel):
    question: str
    provider: str = "groq"
    session_id: str = "default"

@app.post("/api/chat")
def chat(req: ChatRequest):
    src.llm_client.DEFAULT_PROVIDER = req.provider
    memory = _sessions.setdefault(req.session_id, ConversationMemory())

    result = orchestrate(req.question, memory=memory)
    answer = synthesize_answer(req.question, result)
    memory.add_turn(question=req.question, tool=result.get("route", "unknown"), answer=answer)

    return {
        "answer": answer,
        "route": result.get("route"),
        "sql": result.get("sql"),  # None unless route touched sql
    }

@app.get("/api/providers")
def providers():
    # Gemini is intentionally reported unavailable — see Section 6.
    return {"groq": True, "ollama": True, "gemini": False}
