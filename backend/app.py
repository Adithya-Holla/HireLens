from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from .config import DEFAULT_TOP_N, PROJECT_ROOT
from .file_readers import read_resume_bytes
from .pipeline import evaluate_candidates

app = FastAPI(title="HireLens API", version="1.0.0")

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


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

    data = await file.read()
    try:
        text = read_resume_bytes(file.filename, data).strip()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read {file.filename}: {e}")

    if not text:
        raise HTTPException(status_code=422, detail=f"No text could be extracted from {file.filename}")

    return {"job_description": text, "file_name": file.filename}


@app.post("/api/evaluate")
async def evaluate(
    files: list[UploadFile] = File(...),
    job_description: str = Form(""),
    top_n: int = Form(DEFAULT_TOP_N),
) -> dict:
    if top_n < 1:
        raise HTTPException(status_code=422, detail="top_n must be a positive integer")

    resumes: list[tuple[str, str]] = []
    rejected: list[str] = []

    for upload in files:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            rejected.append(upload.filename or "unknown")
            continue
        data = await upload.read()
        try:
            resumes.append((upload.filename, read_resume_bytes(upload.filename, data)))
        except Exception as e:
            rejected.append(f"{upload.filename} ({e})")

    if not resumes:
        raise HTTPException(status_code=422, detail="No valid PDF/DOCX resumes uploaded")

    top, all_results, errors = evaluate_candidates(
        resumes=resumes,
        job_description=job_description.strip(),
        top_n=top_n,
    )

    return {
        "top_candidates": top,
        "all_results": all_results,
        "errors": errors + [{"name": name, "error": "Unsupported file format"} for name in rejected],
        "total_evaluated": len(all_results),
    }


# Static frontend must be mounted last so /api routes take precedence.
app.mount("/", StaticFiles(directory=PROJECT_ROOT / "frontend", html=True), name="frontend")
