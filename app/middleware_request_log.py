import logging
import time

import jwt
from jwt.exceptions import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import Settings, get_settings
from app.jwt_auth import jwt_username_for_access_log

# ファイル出力は configure_logging が付与する「app」配下へ伝播させる。
# auth も同一ロガーに出し、request_in と必ず同じ運命になるようにする（別名ロガーだけだと設定次第で見えないことがある）。
log = logging.getLogger("app.request")


def _log_incoming_auth_cookie(request: Request, settings: Settings) -> None:
    name = settings.cookie_name
    raw = request.cookies.get(name)
    if raw is None:
        log.info("auth_cookie name=%s present=no", name)
        return
    log.info("auth_cookie name=%s present=yes token_chars=%s", name, len(raw))
    if not settings.auth_log_jwt_claims:
        return
    try:
        if settings.jwt_secret_key:
            payload = jwt.decode(
                raw,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            log.info(
                "jwt_claims_verified sub=%s username=%s iat=%s exp=%s",
                payload.get("sub"),
                payload.get("username"),
                payload.get("iat"),
                payload.get("exp"),
            )
        else:
            payload = jwt.decode(raw, options={"verify_signature": False})
            log.warning(
                "jwt_claims_unverified sub=%s username=%s iat=%s exp=%s "
                "(no JWT_SECRET_KEY/SECRET_KEY; signature not checked)",
                payload.get("sub"),
                payload.get("username"),
                payload.get("iat"),
                payload.get("exp"),
            )
    except InvalidTokenError as exc:
        log.warning("jwt_decode_failed error=%s", exc)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        settings = get_settings()
        jwt_username = jwt_username_for_access_log(request, settings)
        client = request.client.host if request.client else "-"
        query = request.url.query or "-"
        _log_incoming_auth_cookie(request, settings)
        log.info(
            "request_in method=%s path=%s query=%s client=%s jwt_username=%s",
            request.method,
            request.url.path,
            query,
            client,
            jwt_username,
        )
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            log.exception(
                "request_error method=%s path=%s query=%s client=%s jwt_username=%s elapsed_ms=%.2f",
                request.method,
                request.url.path,
                query,
                client,
                jwt_username,
                elapsed_ms,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        log.info(
            "request_out method=%s path=%s status=%s jwt_username=%s elapsed_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            jwt_username,
            elapsed_ms,
        )
        if response.status_code >= 500:
            log.error(
                "response_5xx method=%s path=%s status=%s client=%s jwt_username=%s elapsed_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                client,
                jwt_username,
                elapsed_ms,
            )
        elif response.status_code >= 400:
            log.warning(
                "response_4xx method=%s path=%s status=%s client=%s jwt_username=%s elapsed_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                client,
                jwt_username,
                elapsed_ms,
            )
        return response
