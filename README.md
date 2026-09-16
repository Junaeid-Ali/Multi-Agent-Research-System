# Research Wire — Multi-Agent Research System

## 🎯 Problem Statement
Automate multi-agent research workflows with coordinated information gathering from multiple sources and deploy on serverless platforms.

## 🛠️ Technologies & Models
- **LLM Orchestration**: LangChain
- **Backend**: FastAPI (REST + SSE + WebSocket)
- **Frontend**: React
- **Deployment**: Vercel
- **Tools**: Web search & URL scraping agents

---

## Structure

```
research-wire/
├── api/
│   └── index.py          # Vercel entrypoint
├── backend/
│   ├── main.py           # FastAPI app
│   ├── agents.py         # LangChain agents
│   ├── tools.py          # web_search, scrape_url
│   └── pipeline.py       # CLI pipeline
├── frontend/
│   ├── index.html
│   ├── app.jsx           # React
│   └── style.css
├── vercel.json
├── requirements.txt
└── .env.example
```

## What was fixed vs. the original project

1. **`vercel.json` routing** - Added rewrites for `/api/*` and `/ws/*`
2. **`tools.py` web_search** - Moved return statement outside loop (now returns 5 results)
3. **Import paths** - Moved to proper package structure with relative imports
4. **`.env` file** - Added `.env.example` template instead

## Known limitation

**WebSocket doesn't work on Vercel** - Uses Server-Sent Events (SSE) instead for streaming.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload --port 8000
```

## Deploying to Vercel

1. Push to GitHub
2. Import repo in Vercel
3. Set env vars: `OPENAI_API_KEY`, `TAVILY_API_KEY`
4. Deploy
