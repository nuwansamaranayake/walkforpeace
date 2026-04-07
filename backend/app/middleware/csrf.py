"""CSRF protection — validates Origin/Referer on state-changing requests.

Uses pure ASGI middleware (not BaseHTTPMiddleware) to avoid event loop conflicts
with async SQLAlchemy. BaseHTTPMiddleware wraps call_next in a separate task
group, which causes 'Future attached to a different loop' errors.
"""
import json
import logging
from urllib.parse import urlparse

from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings

logger = logging.getLogger(__name__)

SAFE_METHODS = {b"GET", b"HEAD", b"OPTIONS"}


class CSRFMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").encode() if isinstance(scope.get("method"), str) else scope.get("method", b"GET")
        if method in SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        # Extract headers
        headers = dict(scope.get("headers", []))
        origin = headers.get(b"origin", b"").decode()
        referer = headers.get(b"referer", b"").decode()

        source = origin or referer
        if not source:
            # Allow requests without Origin/Referer (same-origin forms, curl, etc.)
            await self.app(scope, receive, send)
            return

        # Parse and validate
        parsed = urlparse(source)
        allowed_hosts = {"walkforpeacelk.org", "www.walkforpeacelk.org"}
        if settings.ENVIRONMENT == "development":
            allowed_hosts.update({"localhost", "127.0.0.1", "test"})

        if parsed.hostname not in allowed_hosts:
            logger.warning(f"CSRF blocked: {scope.get('method')} {scope.get('path')} from {source}")
            body = json.dumps({"detail": "Cross-origin request blocked"}).encode()
            await send({
                "type": "http.response.start",
                "status": 403,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body)).encode()],
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
            })
            return

        await self.app(scope, receive, send)
