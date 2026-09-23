import json
import logging
import re
import time

from groq import RateLimitError

from .config import MODEL, client

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$", re.MULTILINE)

# Groq enforces a tokens-per-minute limit backed by a rolling 60s window, so a
# rejected call needs real seconds for older tokens to age out. The SDK's own
# retries (~0.5s/1.5s) are too short for that — hence our own, longer backoff.
_RATE_RETRY_DELAYS = (5, 15, 30)  # seconds, one per retry attempt


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
    """Send messages to the LLM and return the parsed JSON response.

    Retries Groq TPM (429) rate limits with a backoff long enough for the
    rolling per-minute window to free up tokens.
    """
    attempts = len(_RATE_RETRY_DELAYS) + 1
    for attempt in range(attempts):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                response_format={"type": "json_object"},
            )
        except RateLimitError:
            if attempt >= len(_RATE_RETRY_DELAYS):
                raise
            delay = _RATE_RETRY_DELAYS[attempt]
            logger.warning(
                "Groq tokens-per-minute limit hit; retrying in %ds (attempt %d/%d)",
                delay, attempt + 1, attempts,
            )
            time.sleep(delay)
            continue

        answer = response.choices[0].message.content
        return _load_json(answer)

    raise AssertionError("unreachable")
