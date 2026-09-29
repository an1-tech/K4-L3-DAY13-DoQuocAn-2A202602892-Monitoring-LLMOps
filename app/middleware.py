from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Mỗi request phải bắt đầu bằng context sạch.
        clear_contextvars()

        incoming_request_id = request.headers.get("x-request-id")
        correlation_id = (
            incoming_request_id.strip()
            if incoming_request_id and incoming_request_id.strip()
            else f"req-{uuid.uuid4().hex[:8]}"
        )

        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        started = time.perf_counter()

        try:
            response = await call_next(request)

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            response.headers["x-request-id"] = correlation_id
            response.headers["x-response-time-ms"] = str(elapsed_ms)

            return response
        finally:
            # Không để context của request hiện tại rò sang request sau.
            clear_contextvars()
