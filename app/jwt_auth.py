"""Cookie JWT の検証とクレーム取得（API_LOGIN_SPEC.md の access_token / username 等）。"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from jwt.exceptions import InvalidTokenError

from app.config import Settings, get_settings


def _raw_cookie_token(request: Request, settings: Settings) -> str | None:
    return request.cookies.get(settings.cookie_name)


def try_decode_verified_payload(token: str, settings: Settings) -> dict | None:
    """署名検証済みペイロードを返す。検証不能・失敗時は None。"""
    if not settings.jwt_secret_key:
        return None
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError:
        return None


def jwt_username_for_access_log(request: Request, settings: Settings) -> str:
    """アクセスログ用。検証済み username が取れなければ "-"。"""

    raw = _raw_cookie_token(request, settings)
    if raw is None:
        return "-"
    payload = try_decode_verified_payload(raw, settings)
    if payload is None:
        return "-"
    username = payload.get("username")
    if isinstance(username, str) and username.strip():
        return username.strip()
    return "-"


def decode_verified_token(token: str, settings: Settings) -> dict:
    if not settings.jwt_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT verification is not configured (set JWT_SECRET_KEY or SECRET_KEY).",
        )
    payload = try_decode_verified_payload(token, settings)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    return payload


def get_jwt_claims(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    token = _raw_cookie_token(request, settings)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    return decode_verified_token(token, settings)


def get_jwt_username(
    claims: Annotated[dict, Depends(get_jwt_claims)],
) -> str:
    username = claims.get("username")
    if not isinstance(username, str) or not username.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has no username claim.",
        )
    return username
