"""
Rate-limit middleware for API requests.
"""

from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Minimal rate-limit middleware placeholder."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """
        Pass through the request without enforcing limits yet.

        Args:
            request: Incoming request.
            call_next: Downstream handler.

        Returns:
            Response from the downstream handler.
        """
        return await call_next(request)