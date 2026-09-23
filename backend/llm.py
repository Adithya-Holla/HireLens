import json

from .config import MODEL, client


def chat_json(messages: list[dict]) -> dict:
    """Send messages to the LLM and return the parsed JSON response."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        response_format={"type": "json_object"},
    )

    answer = response.choices[0].message.content
    return json.loads(answer)
