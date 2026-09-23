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

| Method | Path                 | Description                                  |
|--------|----------------------|----------------------------------------------|
| GET    | `/api/health`        | Liveness check                               |
| GET    | `/api/default-top-n` | Default N value                              |
| POST   | `/api/evaluate`      | `multipart/form-data`: `files`, `job_description?`, `top_n` |
