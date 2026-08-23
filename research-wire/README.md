# Research Wire — Multi-Agent Research System

## Structure

```
research-wire/
├── api/
│   └── index.py          # Vercel entrypoint — re-exports backend.main:app
├── backend/
│   ├── __init__.py
│   ├── main.py            # FastAPI app (REST + SSE + WebSocket)
│   ├── agents.py           # LangChain agents / chains
│   ├── tools.py             # web_search, scrape_url tools
│   └── pipeline.py           # standalone CLI pipeline (optional, for local testing)
├── frontend/
│   ├── index.html
│   ├── app.jsx             # React (loaded via Babel Standalone, no build step)
│   └── style.css
├── vercel.json
├── pyproject.toml
├── requirements.txt
├── .env.example
└── .gitignore
```

## What was fixed vs. the original project

1. **`vercel.json` had no `rewrites`.** Vercel's router didn't know to send
   `/`, `/api/*`, or `/ws/*` anywhere, so everything 404'd. Fixed: `/api/*`
   and `/ws/*` route to the Python function; everything else is served as
   a static file from `frontend/`.
2. **`tools.py` `web_search`** had its `return` statement indented inside
   the `for` loop, so it only ever returned 1 search result instead of 5.
   Moved the `return` outside the loop.
3. **Import paths were inconsistent.** `agents.py`, `tools.py`, and
   `pipeline.py` used to live at the project root while `backend/main.py`
   imported them with bare `from agents import ...` — that only resolved
   if you happened to run the process with `backend/` as the working
   directory. They've been moved into `backend/` as a proper package
   (`backend/__init__.py` added) with relative imports (`from .agents
   import ...`), so `backend.main:app` resolves identically whether it's
   imported from `api/index.py` on Vercel or run locally.
4. **`.env` was not included** — a `.env.example` template is provided
   instead. Never commit real API keys; set them in Vercel's dashboard for
   deployment.

## Known platform limitation

**`/ws/research` (WebSocket) does not work on Vercel.** Vercel serverless
functions are request/response only — no persistent connections. The
frontend already uses `/api/research/stream` (Server-Sent Events) instead,
which works within Vercel's streaming response support. The WebSocket
route is left in `backend/main.py` for local development or if you deploy
the backend elsewhere (Render, Railway, a VM, etc.) where persistent
connections are supported.

## Local development

```bash
# from the project root
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # fill in OPENAI_API_KEY and TAVILY_API_KEY

uvicorn backend.main:app --reload --port 8000
```

Then open http://localhost:8000 — `backend/main.py` mounts `frontend/` as
static files for local single-process runs.

## Deploying to Vercel

1. Push this folder to a GitHub repo.
2. Import the repo in Vercel.
3. Set `OPENAI_API_KEY` and `TAVILY_API_KEY` as Environment Variables in
   Vercel project settings (do not commit `.env`).
4. Deploy. `vercel.json` handles routing `/api/*` to the Python function
   and everything else to the static frontend.
