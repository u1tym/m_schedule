import logging
import time

import jwt
from jwt.exceptions import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings

log = logging.getLogger("app.request")
auth_log = logging.getLogger("app.auth")


def _log_incoming_auth_cookie(request: Request) -> None:
    settings = get_settings()
    name = settings.cookie_name
    raw = request.cookies.get(name)
    if raw is None:
        auth_log.info("auth_cookie name=%s present=no", name)
        return
    auth_log.info("auth_cookie name=%s present=yes token_chars=%s", name, len(raw))
    if not settings.auth_log_jwt_claims:
        return
    try:
        if settings.jwt_secret_key:
            payload = jwt.decode(
                raw,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            auth_log.info(
                "jwt_claims_verified sub=%s username=%s iat=%s exp=%s",
                payload.get("sub"),
                payload.get("username"),
                payload.get("iat"),
                payload.get("exp"),
            )
        else:
            payload = jwt.decode(raw, options={"verify_signature": False})
            auth_log.warning(
                "jwt_claims_unverified sub=%s username=%s iat=%s exp=%s "
                "(no JWT_SECRET_KEY/SECRET_KEY; signature not checked)",
                payload.get("sub"),
                payload.get("username"),
                payload.get("iat"),
                payload.get("exp"),
            )
    except InvalidTokenError as exc:
        auth_log.warning("jwt_decode_failed error=%s", exc)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        client = request.client.host if request.client else "-"
        query = request.url.query or "-"
        _log_incoming_auth_cookie(request)
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
