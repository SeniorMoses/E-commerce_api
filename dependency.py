
import jwt

from typing import Annotated

from fastapi import (
    Depends,
    HTTPException,
    status
)

from fastapi.security import OAuth2PasswordBearer

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models import UserModel
from auth import decode_access_token


# ==========================================
# OAUTH2 CONFIGURATION
# ==========================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)


# ==========================================
# DATABASE DEPENDENCY
# ==========================================

DBSession = Annotated[
    AsyncSession,
    Depends(get_db)
]


# ==========================================
# AUTHENTICATION ERROR
# ==========================================

def authentication_error() -> HTTPException:

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )


# ==========================================
# GET CURRENT USER
# ==========================================

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DBSession
) -> UserModel:

    try:
        payload = decode_access_token(token)

        subject = payload.get("sub")

        if not isinstance(subject, str) or not subject:
            raise authentication_error()

    except (
        jwt.InvalidTokenError,
        TypeError,
        ValueError
    ):
        raise authentication_error()

    result = await db.execute(
        select(UserModel).where(
            UserModel.email == subject
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise authentication_error()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated."
        )

    return user


# ==========================================
# GET CURRENT ADMIN
# ==========================================

async def get_current_admin(
    current_user: Annotated[
        UserModel,
        Depends(get_current_user)
    ]
) -> UserModel:

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required."
        )

    return current_user


# ==========================================
# REUSABLE DEPENDENCIES
# ==========================================

CurrentUser = Annotated[
    UserModel,
    Depends(get_current_user)
]

CurrentAdmin = Annotated[
    UserModel,
    Depends(get_current_admin)
]
