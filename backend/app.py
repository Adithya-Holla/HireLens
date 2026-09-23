from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .config import (
    DEFAULT_TOP_N,
    MAX_FILES_PER_REQUEST,
    MAX_JD_CHARS,
    MAX_UPLOAD_BYTES,
    PROJECT_ROOT,
)
from .file_readers import read_resume_bytes
from .pipeline import evaluate_candidates
from .rate_limit import rate_limit_middleware

app = FastAPI(
    title="HireLens API",
    version="1.0.0",
    # The public API is documented in README.md; keep schema/docs off the public site.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.middleware("http")(rate_limit_middleware)

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def _too_large(file_name: str) -> HTTPException:
    limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
    return HTTPException(
        status_code=413,
        detail=f"{file_name} is larger than the {limit_mb} MB limit",
    )


async def _read_upload(upload: UploadFile) -> bytes:
    """Read an upload while enforcing the size cap (never buffer unbounded data)."""
    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise _too_large(upload.filename or "file")
    return data


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/default-top-n")
def default_top_n() -> dict:
    return {"top_n": DEFAULT_TOP_N}


@app.post("/api/job-description")
async def upload_job_description(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=422, detail="Only PDF and DOCX job descriptions are supported")

    data = await _read_upload(file)
    try:
        text = read_resume_bytes(file.filename, data).strip()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read {file.filename}: {e}")

    if not text:
        raise HTTPException(status_code=422, detail=f"No text could be extracted from {file.filename}")

    if len(text) > MAX_JD_CHARS:
        text = text[:MAX_JD_CHARS]

    return {"job_description": text, "file_name": file.filename}


@app.post("/api/evaluate")
async def evaluate(
    files: list[UploadFile] = File(...),
    job_description: str = Form(""),
    top_n: int = Form(DEFAULT_TOP_N),
) -> dict:
    if top_n < 1:
        raise HTTPException(status_code=422, detail="top_n must be a positive integer")

    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=422,
            detail=f"Too many files: send at most {MAX_FILES_PER_REQUEST} per request",
        )

    job_description = job_description.strip()
    if len(job_description) > MAX_JD_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"Job description is too long (max {MAX_JD_CHARS} characters)",
        )

    resumes: list[tuple[str, str]] = []
    upload_errors: list[dict] = []

    for upload in files:
        name = upload.filename or "unknown"
        suffix = Path(name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            upload_errors.append({
                "name": name,
                "error": "Unsupported file format — PDF or DOCX only",
            })
            continue
        try:
            data = await _read_upload(upload)
            text = read_resume_bytes(name, data)
        except HTTPException as e:
            upload_errors.append({"name": name, "error": str(e.detail)})
            continue
        except Exception as e:
            upload_errors.append({"name": name, "error": f"Could not read file: {e}"})
            continue
        if not text.strip():
            upload_errors.append({
                "name": name,
                "error": "No extractable text — the PDF is likely a scanned image",
            })
            continue
        resumes.append((name, text))

    if not resumes:
        # Nothing readable: return 200 with per-file reasons so the UI can
        # show exactly why each upload failed.
        return {
            "top_candidates": [],
            "all_results": [],
            "errors": upload_errors,
            "total_evaluated": 0,
        }

    # LLM calls + rate-limit sleeps are blocking; run them off the event loop so
    # one slow evaluation can't freeze the site for everyone else.
    top, all_results, errors = await run_in_threadpool(
        evaluate_candidates,
        resumes=resumes,
        job_description=job_description,
        top_n=top_n,
    )

    return {
        "top_candidates": top,
        "all_results": all_results,
        "errors": errors + upload_errors,
        "total_evaluated": len(all_results),
    }


# Static frontend must be mounted last so /api routes take precedence.
app.mount("/", StaticFiles(directory=PROJECT_ROOT / "frontend", html=True), name="frontend")
