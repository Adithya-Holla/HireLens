from .llm import chat_json
from .models import JobD, MatchResult, Resume


def final_score(job: JobD, resume: Resume) -> MatchResult:
    match_schema = MatchResult.model_json_schema()

    prompt = f"""
    You are an HR recruiter.
    Compare the candidate's resume with the job description.

    JOB DESCRIPTION:
    {job.model_dump_json(indent=2)}

    CANDIDATE RESUME:
    {resume.model_dump_json(indent=2)}

    Return a valid JSON object matching this schema:
    {match_schema}

    Ensure the JSON object contains:
    - "score": A float between 0 and 100 representing the overall match percentage.
    - "details": A JSON dictionary containing:
        1. candidate_name
        2. matching_skills
        3. missing_important_skills
        4. experience_requirement_met (boolean/string)
        5. verdict (concise short summary)

    Important: Output only valid JSON. Do not include markdown code fences or conversational text outside the JSON.
    """

    messages = [{"role": "user", "content": prompt}]

    match_data = chat_json(messages)
    return MatchResult(**match_data)
