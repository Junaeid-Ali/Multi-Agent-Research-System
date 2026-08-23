"""
FastAPI backend for the multi-agent research system.

Wraps the same building blocks used in pipeline.py (build_search_agent,
build_reader_agent, writer_chain, critic_chain) but:
  1. Exposes a simple REST endpoint (/api/research) for a plain
     request/response call.
  2. Exposes a Server-Sent Events endpoint (/api/research/stream) that
     streams progress events as each agent finishes its stage, so the UI
     can show a live timeline instead of a blank spinner for the whole run.
  3. Exposes a WebSocket endpoint (/ws/research) for local/non-serverless
     deployments. NOTE: this will NOT work on Vercel — serverless functions
     there are request/response only, no persistent connections. Use the
     SSE endpoint instead when deployed on Vercel (the frontend already
     does this, see frontend/app.jsx).

Run locally with (from the PROJECT ROOT, not inside backend/):
    uvicorn backend.main:app --reload --port 8000

This is a package-relative import (see the `.agents` import below), which
is what lets this exact same app object be imported as `backend.main:app`
both locally and by api/index.py on Vercel, without the import path
depending on which directory the process happens to be started from.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agents import build_search_agent, build_reader_agent, critic_chain, writer_chain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("research-api")

app = FastAPI(title="Multi-Agent Research System API")

# Dev-friendly CORS. If you deploy the frontend on a different origin than
# the backend, set ALLOWED_ORIGINS to a comma-separated list of exact
# origins (e.g. "https://your-frontend.onrender.com") instead of "*".
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allowed_origins == "*" else allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    topic: str


# ---------------------------------------------------------------------------
# Stage functions — same logic as pipeline.run_research_pipeline, split up
# so we can emit a progress event between each one.
# ---------------------------------------------------------------------------

def _run_search(topic: str) -> str:
    search_agent = build_search_agent()
    result = search_agent.invoke(
        {"messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]}
    )
    return result["messages"][-1].content


def _run_reader(topic: str, search_result: str) -> str:
    reader_agent = build_reader_agent()
    result = reader_agent.invoke(
        {
            "messages": [
                (
                    "user",
                    f"Based on the following search results about '{topic}', "
                    f"pick the most relevant URL and scrape it for deeper content.\n\n"
                    f"Search Results:\n{search_result[:800]}",
                )
            ]
        }
    )
    return result["messages"][-1].content


def _run_writer(topic: str, research_combined: str):
    return writer_chain.invoke({"topic": topic, "research": research_combined})


def _run_critic(report):
    return critic_chain.invoke({"report": report})


def run_full_pipeline_sync(topic: str) -> dict:
    """Blocking, no progress events — used by the plain REST endpoint."""
    state = {}
    state["search_result"] = _run_search(topic)
    state["scraped_result"] = _run_reader(topic, state["search_result"])
    research_combined = (
        f"Search Result: {state['search_result']}\n\n"
        f"Detailed Explained Content: {state['scraped_result']}"
    )
    state["report"] = _run_writer(topic, research_combined)
    state["feedback"] = _run_critic(state["report"])
    return state


# ---------------------------------------------------------------------------
# REST endpoint (fallback / simple integration)
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/research")
async def research_endpoint(req: ResearchRequest):
    topic = req.topic.strip()
    if not topic:
        return {"error": "Topic is required."}
    # Run the sync/blocking langchain calls in a worker thread so we don't
    # block the event loop.
    state = await asyncio.to_thread(run_full_pipeline_sync, topic)
    return state


# ---------------------------------------------------------------------------
# SSE endpoint (live progress) — used on Vercel and anywhere else that
# supports streaming HTTP responses but not persistent WebSockets.
# ---------------------------------------------------------------------------

@app.get("/api/research/stream")
async def research_stream(topic: str):
    """
    Event shape matches the /ws/research WebSocket: {"type": "stage", ...}
    then a final {"type": "complete", "data": {...}} or {"type": "error", ...}.
    """
    topic = topic.strip()

    async def run_with_heartbeat(fn, *args, interval: float = 15.0):
        """Runs a blocking stage in a thread; yields ('heartbeat', None) every
        `interval` seconds while waiting, so Vercel's connection doesn't sit
        silent long enough to be reaped, then ('result', value) at the end."""
        task = asyncio.create_task(asyncio.to_thread(fn, *args))
        while True:
            done, _ = await asyncio.wait({task}, timeout=interval)
            if task in done:
                yield ("result", task.result())
                return
            yield ("heartbeat", None)

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    async def event_generator():
        if not topic:
            yield sse({"type": "error", "message": "Topic is required."})
            return

        state = {}
        try:
            # Search
            yield sse({"type": "stage", "stage": "search", "status": "start"})
            async for kind, value in run_with_heartbeat(_run_search, topic):
                if kind == "heartbeat":
                    yield ": keep-alive\n\n"
                else:
                    state["search_result"] = value
                    yield sse({"type": "stage", "stage": "search", "status": "done", "data": str(value)[:400]})

            # Reader
            yield sse({"type": "stage", "stage": "reader", "status": "start"})
            async for kind, value in run_with_heartbeat(_run_reader, topic, state["search_result"]):
                if kind == "heartbeat":
                    yield ": keep-alive\n\n"
                else:
                    state["scraped_result"] = value
                    yield sse({"type": "stage", "stage": "reader", "status": "done", "data": str(value)[:400]})

            # Writer
            research_combined = (
                f"Search Result: {state['search_result']}\n\n"
                f"Detailed Explained Content: {state['scraped_result']}"
            )
            yield sse({"type": "stage", "stage": "writer", "status": "start"})
            async for kind, value in run_with_heartbeat(_run_writer, topic, research_combined):
                if kind == "heartbeat":
                    yield ": keep-alive\n\n"
                else:
                    state["report"] = value
                    yield sse({"type": "stage", "stage": "writer", "status": "done"})

            # Critic
            yield sse({"type": "stage", "stage": "critic", "status": "start"})
            async for kind, value in run_with_heartbeat(_run_critic, state["report"]):
                if kind == "heartbeat":
                    yield ": keep-alive\n\n"
                else:
                    state["feedback"] = value
                    yield sse({"type": "stage", "stage": "critic", "status": "done"})

            yield sse({"type": "complete", "data": state})

        except Exception as exc:  # noqa: BLE001
            logger.exception("Pipeline failed (SSE)")
            yield sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable any proxy buffering so events flush immediately
        },
    )


# ---------------------------------------------------------------------------
# WebSocket endpoint — local / non-serverless deployments only.
# Does NOT work on Vercel (see module docstring). Frontend uses the SSE
# endpoint above instead.
# ---------------------------------------------------------------------------

@app.websocket("/ws/research")
async def research_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        raw = await websocket.receive_text()
        payload = json.loads(raw)
        topic = (payload.get("topic") or "").strip()

        if not topic:
            await websocket.send_json({"type": "error", "message": "Topic is required."})
            await websocket.close()
            return

        state = {}

        async def send_stage(stage: str, status: str, data=None):
            msg = {"type": "stage", "stage": stage, "status": status}
            if data is not None:
                msg["data"] = data
            await websocket.send_json(msg)

        # 1. Search agent
        await send_stage("search", "start")
        state["search_result"] = await asyncio.to_thread(_run_search, topic)
        await send_stage("search", "done", str(state["search_result"])[:400])

        # 2. Reader agent
        await send_stage("reader", "start")
        state["scraped_result"] = await asyncio.to_thread(
            _run_reader, topic, state["search_result"]
        )
        await send_stage("reader", "done", str(state["scraped_result"])[:400])

        # 3. Writer chain
        research_combined = (
            f"Search Result: {state['search_result']}\n\n"
            f"Detailed Explained Content: {state['scraped_result']}"
        )
        await send_stage("writer", "start")
        state["report"] = await asyncio.to_thread(_run_writer, topic, research_combined)
        await send_stage("writer", "done")

        # 4. Critic chain
        await send_stage("critic", "start")
        state["feedback"] = await asyncio.to_thread(_run_critic, state["report"])
        await send_stage("critic", "done")

        await websocket.send_json({"type": "complete", "data": state})

    except WebSocketDisconnect:
        logger.info("Client disconnected from /ws/research")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed")
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Serve the frontend for local single-process runs (e.g. `uvicorn main:app`
# from backend/ with no separate static host). On Vercel, vercel.json's
# rewrites serve frontend/ directly as static files instead, so this mount
# mostly matters for local dev / non-Vercel single-deploy setups.
# ---------------------------------------------------------------------------
_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
