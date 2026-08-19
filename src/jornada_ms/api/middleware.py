"""HTTP middleware shared by all API routes."""

import re
from uuid import uuid4

from starlette.types import ASGIApp, Receive, Scope, Send

_SAFE_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class CorrelationIdMiddleware:
    """Attach a safe correlation identifier to request state and responses."""

    def __init__(self, app: ASGIApp, header_name: str = "X-Correlation-ID") -> None:
        self.app = app
        self.header_name = header_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        requested = headers.get(self.header_name.lower().encode())
        value = requested.decode("latin-1") if requested else ""
        correlation_id = value if _SAFE_CORRELATION_ID.fullmatch(value) else str(uuid4())
        scope.setdefault("state", {})["correlation_id"] = correlation_id

        async def send_with_correlation(message) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.append(
                    (self.header_name.lower().encode(), correlation_id.encode())
                )
                message = {**message, "headers": response_headers}
            await send(message)

        await self.app(scope, receive, send_with_correlation)
