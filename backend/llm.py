import json
import re

from .config import MODEL, client

_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$", re.MULTILINE)


def _load_json(text: str) -> dict:
    """Parse JSON even if the model wrapped it in markdown fences or prose."""
    candidates = [text.strip()]

    unfenced = _FENCE_RE.sub("", candidates[0]).strip()
    if unfenced != candidates[0]:
        candidates.append(unfenced)

    # Last resort: take the outermost {...} block.
    start, end = unfenced.find("{"), unfenced.rfind("}")
    if start != -1 and end > start:
        candidates.append(unfenced[start : end + 1])

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data

    raise ValueError(f"Model did not return valid JSON: {text[:200]!r}")


def chat_json(messages: list[dict]) -> dict:
    """Send messages to the LLM and return the parsed JSON response."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        response_format={"type": "json_object"},
    )

    answer = response.choices[0].message.content
    return _load_json(answer)
