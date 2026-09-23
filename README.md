# HireLens

**AI-assisted shortlisting for hiring teams.**

HireLens turns a stack of resumes and one job description into a ranked shortlist.
Add a job description as text or file, drop in up to 20 resumes, and HireLens parses,
scores, and ranks each candidate from 0–100 — with matching skills, gaps, and a
plain-English verdict for every result.

---

## Features

- **Job description ingestion** — paste as text or upload a PDF/DOCX; HireLens extracts
  the role, required/preferred skills, education, and responsibilities.
- **Batch resume parsing** — PDF and DOCX resumes are read and structured
  automatically (name, contact, experience, skills, education, projects, certifications).
- **HR-style evaluation** — each candidate is compared against the job description and
  returned with a match score, matched skills, missing skills, and a short verdict.
- **Adjustable shortlist** — you choose how many top candidates to surface.
- **Shared, server-side AI key** — visitors never see or supply credentials; all model
  calls happen on the server.
- **Rate-limited by design** — per-IP sliding-window limits are enforced *before* any
  model call, so abuse never costs credits.
- **Resilient by default** — bounded upload sizes, request caps, non-blocking
  evaluation, and fault-tolerant JSON parsing from the model.
- **Two interfaces** — the web application, and a CLI for terminal workflows.

## Tech stack

| Layer    | Technology                                              |
|----------|---------------------------------------------------------|
| Frontend | Vanilla HTML / CSS / JS (static, no build step)         |
| Backend  | FastAPI, Starlette, Uvicorn                             |
| AI       | [Groq](https://groq.com) (`openai/gpt-oss-120b`)        |
| Parsing  | pypdf, python-docx                                      |
| Models   | Pydantic v2                                             |

## Architecture

```
Browser ──static──▶ FastAPI ──▶ /api/evaluate
                                     │
                    ┌────────────────┴───────────────────┐
                    │  pipeline (worker thread)          │
                    │  JD parse ─▶ resume parse ─▶ score │  ◀─ Groq API
                    └────────────────────────────────────┘
                                     │
                              ranked top-N results
```

The frontend is served by the same FastAPI process, so the whole product deploys as a
single service with no CORS or build tooling.

## Project structure

```
.
├── backend/
│   ├── app.py             # FastAPI application, routes, request limits
│   ├── cli.py             # Command-line interface
│   ├── config.py          # Environment, client setup, tunables
│   ├── evaluator.py       # Candidate scoring against the job description
│   ├── file_readers.py    # PDF/DOCX text extraction (paths and uploads)
│   ├── job_description.py # Built-in default job description
│   ├── job_parser.py      # Job description → structured model
│   ├── llm.py             # Groq client call + resilient JSON decoding
│   ├── models.py          # Pydantic schemas (JobD, Resume, MatchResult)
│   ├── pipeline.py        # End-to-end evaluation pipeline + JD cache
│   ├── rate_limit.py      # Per-IP sliding-window middleware
│   ├── reporting.py       # Ranking helpers (CLI output)
│   └── resume_parser.py   # Resume text → structured model
├── frontend/
│   ├── index.html         # Application UI
│   ├── styles.css         # Design system
│   ├── app.js             # Client logic
│   ├── favicon.svg        # Brand favicon
│   └── favicon.ico
├── resumes/               # Resume drop folder (CLI mode)
├── main.py                # Web server entry point
└── requirements.txt
```

## Getting started

### Prerequisites

- Python 3.10+
- A [Groq API key](https://console.groq.com)

### Installation

```bash
git clone https://github.com/Adithya-Holla/HireLens.git
cd HireLens

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_...
```

All other settings have safe defaults and can be overridden via environment variables
(see [Configuration](#configuration)).

> The API key is read exclusively by the server. It is never sent to the browser, and
> `.env` is gitignored — do not commit it.

### Usage

**Web application**

```bash
python main.py
```

Open http://127.0.0.1:8000, add a job description, upload resumes, choose how many top
candidates you want, and select **Evaluate candidates**.

**Command line**

```bash
python -m backend.cli
```

Reads every PDF/DOCX in `resumes/` and prints the top N candidates.

## API

The API is REST and returns JSON. Authentication with Groq is handled server-side;
clients call the endpoints without credentials.

| Method | Path                   | Description                                                        |
|--------|------------------------|--------------------------------------------------------------------|
| GET    | `/api/health`          | Liveness probe                                                     |
| GET    | `/api/default-top-n`   | Default shortlist size                                             |
| POST   | `/api/evaluate`        | Score and rank resumes — `files`, `job_description?`, `top_n`      |
| POST   | `/api/job-description` | Extract text from a PDF/DOCX job description file                  |

**Example**

```bash
curl -X POST https://<your-host>/api/evaluate \
  -F "files=@resume.pdf" \
  -F "top_n=5" \
  -F "job_description=We are hiring a backend engineer..."
```

**Response shape**

```json
{
  "top_candidates": [
    {
      "name": "Jane Doe",
      "score": 91.5,
      "details": {
        "candidate_name": "Jane Doe",
        "matching_skills": ["Python", "FastAPI"],
        "missing_important_skills": ["Rust"],
        "experience_requirement_met": true,
        "verdict": "Strong match; systems-language gap."
      }
    }
  ],
  "all_results": [],
  "errors": [],
  "total_evaluated": 4
}
```

Schema endpoints (`/docs`, `/redoc`, `/openapi.json`) are disabled in production;
this README is the authoritative API reference.

## Configuration

| Variable                       | Default           | Purpose                                  |
|--------------------------------|-------------------|------------------------------------------|
| `GROQ_API_KEY`                 | — (required)      | Groq API credential                       |
| `RATE_LIMIT_EVALUATE_PER_HOUR` | `10`              | Evaluate calls per IP per hour            |
| `RATE_LIMIT_JD_PER_HOUR`       | `30`              | JD-upload calls per IP per hour           |
| `RATE_LIMIT_DEFAULT_PER_MINUTE`| `60`              | Other API calls per IP per minute         |
| `MAX_UPLOAD_MB`                | `10`              | Max size per uploaded file                |
| `REQUEST_DELAY_SECONDS`        | `2`               | Politeness delay between model calls      |

## Security & limits

- **Rate limiting** — sliding-window, per client IP, enforced before any model call.
  Exceeding a limit returns `429` with a `Retry-After` header. Client identity comes
  from the last (proxy-appended) `X-Forwarded-For` entry, so it cannot be spoofed.
- **Request bounds** — max 20 files per evaluation, 10 MB per file, 20,000 characters
  of job description; violations are rejected with `413`/`422` before processing.
- **Non-blocking evaluation** — model calls run in a worker threadpool, so one slow
  evaluation never degrades service for other visitors.
- **Fault-tolerant parsing** — model output is validated against Pydantic schemas and
  tolerated markdown/JSON inconsistencies; per-candidate failures are reported without
  failing the batch.
- **Rate-limit resilience** — Groq's tokens-per-minute (429) responses are retried with
  a 5s/15s/30s backoff, sized to the rolling per-minute window; if the limit persists,
  only that candidate is marked failed and the batch continues.

*Counters are in-memory and reset on restart. If you scale to multiple instances,
back the limiter with a shared store such as Redis.*

## Roadmap

- Job-description template library
- Export shortlist as CSV/PDF
- Shared-store rate limiting for multi-instance deployments

## License

All rights reserved unless otherwise stated by the author.
