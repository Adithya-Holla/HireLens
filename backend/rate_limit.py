"""In-memory sliding-window rate limiting, per client IP."""

import os
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

# path -> (max requests, window seconds), overridable via environment variables.
LIMITS: dict[str, tuple[int, int]] = {
    "/api/evaluate": (
        int(os.getenv("RATE_LIMIT_EVALUATE_PER_HOUR", "10")),
        3600,
    ),
    "/api/job-description": (
        int(os.getenv("RATE_LIMIT_JD_PER_HOUR", "30")),
        3600,
    ),
}
DEFAULT_LIMIT = (int(os.getenv("RATE_LIMIT_DEFAULT_PER_MINUTE", "60")), 60)


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Record a hit for key. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        hits = self._hits[key]

        while hits and hits[0] <= now - window:
            hits.popleft()

        if len(hits) >= limit:
            retry_after = max(1, int(hits[0] + window - now) + 1)
            return False, retry_after

        hits.append(now)
        return True, 0

    def prune_stale_keys(self) -> None:
        """Drop keys with no recent hits so memory stays bounded."""
        now = time.monotonic()
        stale = [
            key
            for key, hits in self._hits.items()
            if not hits or hits[-1] <= now - 3600
        ]
        for key in stale:
            del self._hits[key]


limiter = SlidingWindowLimiter()


def client_key(request: Request) -> str:
    """Identify the client, correctly behind a reverse proxy.

    The client controls X-Forwarded-For and can prepend fake IPs, but the proxy
    APPENDS the real source address — so the last entry is the trustworthy one.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        last = forwarded.split(",")[-1].strip()
        if last:
            return last
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path

    if not path.startswith("/api/"):
        return await call_next(request)

    limit, window = LIMITS.get(path, DEFAULT_LIMIT)
    allowed, retry_after = limiter.check(
        f"{path}:{client_key(request)}", limit, window
    )

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "detail": f"Rate limit exceeded. Try again in {retry_after} seconds."
            },
            headers={"Retry-After": str(retry_after)},
        )

    # Amortized cleanup so the hit log never grows without bound.
    if len(limiter._hits) > 10_000:
        limiter.prune_stale_keys()

    return await call_next(request)
