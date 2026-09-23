from .job_description import JOB_DESCRIPTION
from .llm import chat_json
from .models import JobD


def parse_job_description(job_description: str = JOB_DESCRIPTION) -> JobD:
    job_schema = JobD.model_json_schema()

    system_prompt = f"""
    You are an expert job description parser. You will receive a job description and you will return a JSON object that matches the following schema:
    {job_schema}
    Important: You must return a valid JSON object that matches the schema. Do not include any additional text or explanations. Only return the JSON object.
    """

    user_prompt = f"""
    Analyze the following job description: {job_description}
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    job_data = chat_json(messages)
    return JobD(**job_data)
