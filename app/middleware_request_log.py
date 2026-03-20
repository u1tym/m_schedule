import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        client = request.client.host if request.client else "-"
        query = request.url.query or "-"
        log.info(
            "request_in method=%s path=%s query=%s client=%s",
            request.method,
            request.url.path,
            query,
            client,
        )
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            log.exception(
                "request_error method=%s path=%s query=%s client=%s elapsed_ms=%.2f",
                request.method,
                request.url.path,
                query,
                client,
                elapsed_ms,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        log.info(
            "request_out method=%s path=%s status=%s elapsed_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        if response.status_code >= 500:
            log.error(
                "response_5xx method=%s path=%s status=%s client=%s elapsed_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                client,
                elapsed_ms,
            )
        elif response.status_code >= 400:
            log.warning(
                "response_4xx method=%s path=%s status=%s client=%s elapsed_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                client,
                elapsed_ms,
            )
        return response
