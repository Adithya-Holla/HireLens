import time

from .config import REQUEST_DELAY_SECONDS
from .evaluator import final_score
from .job_description import JOB_DESCRIPTION
from .job_parser import parse_job_description
from .models import JobD
from .reporting import top_candidates
from .resume_parser import parse_resume


def evaluate_candidates(
    resumes: list[tuple[str, str]],
    job_description: str,
    top_n: int,
    progress: callable = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Score every resume against the job description.

    resumes: list of (display_name, resume_text) tuples.
    An empty job_description falls back to the built-in default JD.
    Returns (top_n_candidates, all_ranked_results, errors).
    """
    job: JobD = parse_job_description(job_description or JOB_DESCRIPTION)

    all_results: list[dict] = []
    errors: list[dict] = []

    for index, (name, resume_text) in enumerate(resumes, start=1):
        if progress:
            progress(index, len(resumes), name)
        try:
            parsed_resume = parse_resume(resume_text)
            time.sleep(REQUEST_DELAY_SECONDS)

            result = final_score(job, parsed_resume)
            time.sleep(REQUEST_DELAY_SECONDS)

            all_results.append({
                "name": parsed_resume.name,
                "score": result.score,
                "details": result.details,
            })
        except Exception as e:
            errors.append({"name": name, "error": str(e)})

    all_results.sort(key=lambda x: x["score"], reverse=True)
    return top_candidates(all_results, top_n), all_results, errors
