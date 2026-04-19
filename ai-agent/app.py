"""
app.py — FastAPI entry-point for the LangGraph Text2SQL microservice.

Endpoints:
  POST /api/chat/ask     — sync JSON response
  POST /api/chat/stream  — SSE streaming (thinking phases + result)
  GET  /health           — liveness probe
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from agents import DB_OK, GROQ_KEY, USE_LLM
from graph import agent_graph
from state import AgentState

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("datapulse.app")

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI setup
# ──────────────────────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="DataPulse Text2SQL API", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:4201"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# Request / response models
# ──────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message:  str
    role:     str           = "INDIVIDUAL"   # INDIVIDUAL | CORPORATE | ADMIN
    user_id:  Optional[int] = None
    store_id: Optional[int] = None


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_state(req: ChatRequest) -> AgentState:
    return {
        "question":          req.message,
        "role":              req.role,
        "user_id":           req.user_id,
        "store_id":          req.store_id,
        "is_in_scope":       False,
        "is_greeting":       False,
        "sql_query":         None,
        "query_result":      None,
        "error":             None,
        "error_message":     None,
        "final_answer":      None,
        "needs_viz":         False,
        "visualization_code": None,
        "iteration_count":   0,
        "intent":            None,
    }


def _serialize_final(final: AgentState) -> dict:
    return {
        "answer":   final.get("final_answer") or "Yanıt üretilemedi.",
        "sql":      final.get("sql_query"),
        "plotData": final.get("visualization_code"),
        "intent":   final.get("intent"),
        "role":     final.get("role"),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/api/chat/ask")
@limiter.limit("30/minute")
def chat_ask(request: Request, req: ChatRequest):
    """Synchronous endpoint — returns full result after graph completes."""
    try:
        final = agent_graph.invoke(_make_state(req))
    except Exception as ex:
        logger.error(f"Graph error: {ex}")
        return {"answer": "Beklenmedik bir hata oluştu.", "sql": None, "plotData": None}
    return _serialize_final(final)


THINKING_PHASES = [
    "Sorgunuz analiz ediliyor...",
    "Kapsam doğrulanıyor...",
    "SQL sorgusu oluşturuluyor...",
    "Veritabanı sorgulanıyor...",
    "Sonuçlar yorumlanıyor...",
    "Grafik hazırlanıyor...",
]


async def _event_stream(req: ChatRequest) -> AsyncGenerator[str, None]:
    def sse(ev: str, data: dict) -> str:
        return f"event: {ev}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    loop  = asyncio.get_event_loop()
    task  = loop.run_in_executor(None, agent_graph.invoke, _make_state(req))

    for phase in THINKING_PHASES:
        if task.done():
            break
        yield sse("thinking", {"text": phase})
        await asyncio.sleep(0.55)

    try:
        final = await task
    except Exception as ex:
        yield sse("error", {"message": str(ex)})
        return

    yield sse("result", _serialize_final(final))
    yield sse("done", {})


@app.post("/api/chat/stream")
@limiter.limit("30/minute")
async def chat_stream(request: Request, req: ChatRequest):
    """SSE streaming endpoint — emits thinking phases then result."""
    return StreamingResponse(
        _event_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "llm": USE_LLM, "llm_provider": "groq" if USE_LLM else "none", "db": DB_OK}


# ──────────────────────────────────────────────────────────────────────────────
# Entry-point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
