from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.jwt_auth import get_jwt_username
from app.models import Account


def get_current_account_id(
    username: Annotated[str, Depends(get_jwt_username)],
    db: Session = Depends(get_db),
) -> int:
    """JWT の username に対応する accounts.id。存在しない・削除済みは 403。"""
    account = db.scalar(
        select(Account).where(Account.username == username, Account.is_deleted.is_(False))
    )
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not found for this user.",
        )
    return account.id
