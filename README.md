# HireLens

AI-powered resume parser and evaluator. Upload resumes, and HireLens ranks the top N
candidates against a job description using Groq's LLM API.

## Project structure

```
.
├── backend/
│   ├── app.py            # FastAPI web API + static file serving
│   ├── cli.py            # Command-line interface
│   ├── config.py         # Env loading, Groq client, constants
│   ├── evaluator.py      # final_score(): resume vs. JD scoring
│   ├── file_readers.py   # PDF/DOCX text extraction
│   ├── job_description.py# Default job description text
│   ├── job_parser.py     # parse_job_description()
│   ├── llm.py            # chat_json(): shared Groq call
│   ├── models.py         # Pydantic models (JobD, Resume, MatchResult, ...)
│   ├── pipeline.py       # evaluate_candidates(): end-to-end scoring pipeline
│   ├── reporting.py      # Ranking/print helpers
│   └── resume_parser.py  # parse_resume()
├── frontend/
│   ├── index.html        # Upload UI
│   ├── styles.css
│   └── app.js            # Calls /api/evaluate and renders results
├── resumes/              # Drop PDF/DOCX resumes here (CLI mode)
├── main.py               # Entry point: starts the web server
└── requirements.txt
```

## Setup

```bash
python -m venv myenv
myenv\Scripts\activate        # Windows (use `source myenv/bin/activate` on macOS/Linux)
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

> **Note:** The API key lives only on the server. The browser talks to `/api/*` endpoints
> and never sees or sends a key, so every user of the site shares the one server-side key.

## Run

### Web app (default)

```bash
python main.py
```

Open http://127.0.0.1:8000, paste a job description (or use the built-in default),
drop in PDF/DOCX resumes, choose N, and click **Evaluate**.

### CLI

```bash
python -m backend.cli
```

Reads every PDF/DOCX in `resumes/` and prints the top N candidates.

## API

Rate-limited (see below); auth with Groq happens server-side only.

| Method | Path                 | Description                                  |
|--------|----------------------|----------------------------------------------|
| GET    | `/api/health`        | Liveness check                               |
| GET    | `/api/default-top-n` | Default N value                              |
| POST   | `/api/evaluate`      | `multipart/form-data`: `files` (≤20, ≤10 MB each), `job_description?` (≤20k chars), `top_n` |
| POST   | `/api/job-description` | `multipart/form-data`: `file` (PDF/DOCX ≤10 MB) → extracted text |

## Rate limiting

Requests are limited per client IP with a sliding window (`backend/rate_limit.py`):

| Endpoint               | Default limit                | Env var override            |
|------------------------|------------------------------|-----------------------------|
| `/api/evaluate`        | 10 requests / hour           | `RATE_LIMIT_EVALUATE_PER_HOUR` |
| `/api/job-description` | 30 requests / hour           | `RATE_LIMIT_JD_PER_HOUR`    |
| other `/api/*`         | 60 requests / minute         | `RATE_LIMIT_DEFAULT_PER_MINUTE` |

Exceeding a limit returns HTTP 429 with a `Retry-After` header. The client IP is taken
from the **last** entry of `X-Forwarded-For` — the one appended by your reverse proxy —
so clients cannot spoof fake IPs to bypass the limits. Limits are counted **before** any
LLM call, so rejected requests cost nothing. Note the counter is in memory — it resets on
restart and is per-process (if you later scale to multiple workers/instances, use a
shared store like Redis).

## Request limits

| Limit                         | Default              | Env var override     |
|-------------------------------|----------------------|----------------------|
| Upload size per file          | 10 MB                | `MAX_UPLOAD_MB`      |
| Files per evaluate request    | 20                   | —                    |
| Job description length        | 20,000 chars         | —                    |
| Delay between Groq calls      | 2 s                  | `REQUEST_DELAY_SECONDS` |

All violations return a clear 413/422 before any LLM work happens. The FastAPI schema
endpoints (`/docs`, `/redoc`, `/openapi.json`) are disabled — the public API is
documented in this README only.

Evaluation runs in a threadpool, so one slow run never blocks other visitors.

## Deploying

The site is designed for many HR users to share **your** key:

1. Set `GROQ_API_KEY` as an environment variable on your host (Render, Railway, a VPS, etc.).
   Do **not** commit `.env` — it is gitignored and must stay off the repo.
2. Start the server: `uvicorn backend.app:app --host 0.0.0.0 --port 8000`
3. Share the URL. Visitors only interact with the web page; all Groq calls are made by the
   server with the key from its environment, and the key is never sent to the browser.

For example, on a Linux host:

```bash
export GROQ_API_KEY=gsk_...
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```
