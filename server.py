"""
server.py
════════════════════════════════════════════════════════════════
Agora — FastAPI web server (the live demo).

  GET  /                 the chat UI (static/index.html)
  POST /api/chat         streams the answer as Server-Sent Events
  POST /api/clear        wipe a session's memory
  GET  /api/health       status (add ?deep=1 to ping the LLM)

Run locally:   uvicorn server:app --reload
Production:    uvicorn server:app --host 0.0.0.0 --port $PORT
════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from bootstrap import ConfigError, build_flow
from memory.memory import SessionStore
from tools.weather_tool import is_configured as weather_configured
from utils.helpers import get_logger, is_meaningful, sanitise_input

logger = get_logger("agora.server")
ROOT = Path(__file__).parent
SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


# ─── Tiny per-IP rate limiter (protects your Groq quota on a public demo) ─────

class RateLimiter:
    def __init__(self, limit: int, window: int = 60):
        self.limit, self.window = limit, window
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        if len(self._hits) > 5000:  # keep memory bounded
            for k in [k for k, v in self._hits.items() if not v or now - v[-1] > self.window]:
                self._hits.pop(k, None)
        return True


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str


class ClearRequest(BaseModel):
    session_id: str


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─── App factory ──────────────────────────────────────────────────────────────

def create_app(flow_factory: Callable = build_flow) -> FastAPI:
    sessions = SessionStore()
    limiter = RateLimiter(int(os.getenv("RATE_LIMIT_PER_MIN", "20")))
    state: dict = {"flow": None, "error": None, "deep": (0.0, None)}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            state["flow"] = flow_factory()
        except ConfigError as exc:
            state["error"] = str(exc)
            logger.error("Agora started without a model: %s", exc)
        except Exception as exc:  # pragma: no cover
            state["error"] = f"{type(exc).__name__}: {exc}"
            logger.exception("startup failed")
        yield

    app = FastAPI(title="Agora", version="2.0.0", lifespan=lifespan)

    def session_id(raw: str) -> str:
        if not SESSION_RE.match(raw or ""):
            raise HTTPException(400, "Invalid session id.")
        return raw

    @app.get("/api/health")
    def health(deep: int = 0):
        flow = state["flow"]
        info = {
            "ok": flow is not None,
            "model": flow.chain.model_name if flow else None,
            "weather": "OpenWeatherMap" if weather_configured() else "wttr.in",
            "error": state["error"],
        }
        if deep and flow:
            ts, cached = state["deep"]
            if time.time() - ts > 120:
                ok, detail = flow.chain.ping()
                cached = {"llm_ok": ok, "detail": detail}
                state["deep"] = (time.time(), cached)
            info.update(cached)
        return info

    @app.post("/api/chat")
    def chat(req: ChatRequest, request: Request):
        flow = state["flow"]
        if flow is None:
            raise HTTPException(503, state["error"] or "Agora is not ready yet.")
        sid = session_id(req.session_id)
        if not limiter.allow(client_ip(request)):
            raise HTTPException(429, "You're sending messages too fast — give it a few seconds.")

        text = sanitise_input(req.message)
        if not text or not is_meaningful(text):
            raise HTTPException(400, "Please type a message.")

        memory = sessions.get(sid)

        def events():
            for event, data in flow.stream(text, memory):
                yield sse(event, data)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/clear")
    def clear(req: ClearRequest):
        sessions.drop(session_id(req.session_id))
        return {"ok": True}

    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.get("/")
    def index():
        return FileResponse(ROOT / "static" / "index.html")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))
