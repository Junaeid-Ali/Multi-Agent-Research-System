# Research Wire

## Problem Solved

Research Wire automates the research process using AI agents for web search,
source reading, report writing, and quality review.

## Frameworks Used

- **FastAPI + Uvicorn:** Backend API and streaming responses.
- **LangChain + OpenAI:** Coordinates the research agents using `gpt-4o-mini`.
- **Tavily:** Searches the web for relevant sources.
- **React + Babel Standalone:** Frontend without a build process.
- **Requests + BeautifulSoup:** Extracts content from web pages.
- **Render + Vercel:** Render hosts the backend; Vercel hosts the frontend.

## How It Helps

It saves research time, organizes information from multiple sources, creates
structured reports, and provides critic feedback.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Add these keys to `.env`:

```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Run locally:

```bash
uvicorn backend.main:app --reload --port 8000
```

Open `http://localhost:8000`.

The deployed frontend uses the Render backend:

```text
https://multi-agent-research-system-1-mrbt.onrender.com
```
