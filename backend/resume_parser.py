from .llm import chat_json
from .models import Resume

resume_schema = Resume.model_json_schema()


def parse_resume(resume_text: str) -> Resume:
    system_prompt = f"""
    You are an expert resume parser. You will receive a resume text and you will return a JSON object that matches the following schema:
    {resume_schema}
    Important: You must return a valid JSON object that matches the schema. Do not include any additional text or explanations. Only return the JSON object.
    """

    user_prompt = f"""
    Analyze the following resume text: {resume_text}
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    resume_data = chat_json(messages)
    return Resume(**resume_data)
