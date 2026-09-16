# Research Wire

<<<<<<< HEAD
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
# Research Wire

## 1. Problem Solved

Research often requires switching between search, reading, writing, and
reviewing. Research Wire automates this workflow with multiple AI agents and
shows progress as the report is created.

## 2. Frameworks and Important Details

- **FastAPI + Uvicorn:** Python backend with REST and Server-Sent Events (SSE)
  for live progress updates.
- **LangChain + OpenAI:** Coordinates the search, reader, writer, and critic
  agents using `gpt-4o-mini`.
- **Tavily:** Provides web search results for the research agent.
- **React + Babel Standalone:** Lightweight frontend with no build step.
- **Requests + BeautifulSoup:** Extracts readable content from selected URLs.
- **Vercel:** Optional deployment for the frontend and API function.

## 3. How It Helps

It reduces manual research time, keeps the workflow organized, combines web
sources into a structured report, and provides critic feedback before the
result is used.

## 4. Setup

From the project root:

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
copy .env.example .env
```

Add `OPENAI_API_KEY` and `TAVILY_API_KEY` to `.env`, then run:

```bash
uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000 in a browser.
It reduces manual research time, keeps the workflow organized, combines web
