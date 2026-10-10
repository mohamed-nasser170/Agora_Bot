# Agora · Αγορά

> *Where ideas gather.* A conversational AI assistant with live weather, session memory and first-class Arabic + English support — served as a real web app.

Built with **LangGraph + LangChain + Groq + FastAPI**. The front-end is plain HTML/CSS/JS (no build step) and streams answers token-by-token over Server-Sent Events.

## Features

- **LangGraph state machine** — `router → weather | general | clarify → memory`
- **Live streaming** answers (SSE) with a Stop button
- **Weather tool** — OpenWeatherMap with automatic wttr.in fallback, 10-min cache, rendered as a weather card in the chat
- **Dual-layer memory** — rolling short-term window + long-term user facts (name, interests), isolated per browser session
- **Bilingual** — auto RTL for Arabic, Egyptian-Arabic friendly, Arabic city names understood
- **Live-demo ready** — per-IP rate limiting, per-session memory, health endpoint, Dockerfile, Render blueprint
- Light / dark themes, mobile layout, Markdown + code blocks with copy buttons

## Project structure

```
agora/
├── server.py              FastAPI app: UI + /api/chat (SSE) + /api/health + /api/clear
├── main.py                optional terminal chat
├── bootstrap.py           builds chain + flow (shared by server and CLI)
├── chains/chat_chain.py   ChatGroq wrapper, system prompt, streaming
├── graph/flow.py          LangGraph state machine (+ live event stream)
├── memory/memory.py       short-term + long-term memory, SessionStore
├── tools/weather_tool.py  OpenWeatherMap / wttr.in
├── utils/helpers.py       intent detection, city extraction (EN/AR), sanitising
├── static/                index.html · style.css · app.js
└── tests/test_agora.py    offline tests (fake LLM — no key needed)
```

```
User ─► [router] ─┬─ weather ─► [weather tool → LLM] ─┐
                  ├─ general ─► [LLM] ────────────────┼─► [memory] ─► END
                  └─ clarify ─► [ask a follow-up] ────┘
```

## Run it locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # Windows: copy .env.example .env
# edit .env → set GROQ_API_KEY=gsk_...

uvicorn server:app --reload
```

Open **http://localhost:8000**. (Terminal version: `python main.py`.)

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `GROQ_API_KEY` | yes | — | free at console.groq.com |
| `GROQ_MODEL` | no | `openai/gpt-oss-20b` | Groq retires models often — see console.groq.com/docs/deprecations |
| `GROQ_REASONING_EFFORT` | no | `low` | only used for `gpt-oss` models; empty = off |
| `OPENWEATHER_API_KEY` | no | — | wttr.in is used when empty |
| `MAX_HISTORY` | no | `20` | turns kept in short-term memory |
| `MAX_TOKENS` / `TEMPERATURE` | no | `1500` / `0.6` | generation settings |
| `RATE_LIMIT_PER_MIN` | no | `20` | per-IP, protects your Groq quota |

## Put it online (live demo)

**Render (free tier)** — push the repo to GitHub → *New → Blueprint* → pick the repo (`render.yaml` is included) → add `GROQ_API_KEY` in the dashboard. You get a public `https://….onrender.com` link. Free instances sleep when idle, so the first request can take ~30 s.

**Docker / Hugging Face Spaces**
```bash
docker build -t agora .
docker run -p 7860:7860 -e GROQ_API_KEY=gsk_... agora
```

**Instant public link from your laptop** (handy for a presentation):
```bash
uvicorn server:app --port 8000
cloudflared tunnel --url http://localhost:8000     # or: ngrok http 8000
```

Never commit `.env`; on a host, set the key as an environment variable.

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | body `{message, session_id}` → SSE events `meta`, `tool`, `token`, `done`, `error` |
| `POST` | `/api/clear` | body `{session_id}` → wipes that session's memory |
| `GET`  | `/api/health` | status; `?deep=1` also pings the LLM |

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## License

MIT
