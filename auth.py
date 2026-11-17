
import os
import secrets
import hashlib

from datetime import datetime, timedelta, timezone

import jwt

from pwdlib import PasswordHash
from fastapi.concurrency import run_in_threadpool


# ==========================================
# CONFIGURATION
# ==========================================

ACCESS_TOKEN_SECRET = os.getenv("SECRET_KEY")
REFRESH_TOKEN_SECRET = os.getenv("REFRESH_SECRET_KEY")

if not ACCESS_TOKEN_SECRET:
    raise RuntimeError("SECRET_KEY environment variable is not configured.")

if not REFRESH_TOKEN_SECRET:
    raise RuntimeError("REFRESH_SECRET_KEY environment variable is not configured.")

ALGORITHM = "HS256"
ISSUER = "senior-hive-api"

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ==========================================
# PASSWORD HASHING
# ==========================================

password_hash = PasswordHash.recommended()


def hash_password_sync(password: str) -> str:
    return password_hash.hash(password)


def verify_password_sync(
    password: str,
    hashed_password: str
) -> bool:
    return password_hash.verify(password, hashed_password)


async def hash_password(password: str) -> str:
    return await run_in_threadpool(
        hash_password_sync,
        password
    )


async def verify_password(
    password: str,
    hashed_password: str
) -> bool:
    return await run_in_threadpool(
        verify_password_sync,
        password,
        hashed_password
    )


# ==========================================
# TOKEN GENERATION
# ==========================================

def create_access_token(
    subject: str,
    role: str
) -> str:

    now = datetime.now(timezone.utc)

    payload = {
        "sub": subject,
        "role": role,
        "jti": secrets.token_urlsafe(32),
        "iat": now,
        "exp": now + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
        "iss": ISSUER,
        "type": "access"
    }

    return jwt.encode(
        payload,
        ACCESS_TOKEN_SECRET,
        algorithm=ALGORITHM
    )


def create_refresh_token(
    subject: str,
    role: str
) -> str:

    now = datetime.now(timezone.utc)

    payload = {
        "sub": subject,
        "role": role,
        "jti": secrets.token_urlsafe(32),
        "iat": now,
        "exp": now + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        ),
        "iss": ISSUER,
        "type": "refresh"
    }

    return jwt.encode(
        payload,
        REFRESH_TOKEN_SECRET,
        algorithm=ALGORITHM
    )


# ==========================================
# TOKEN PAIR
# ==========================================

def create_token_pair(
    subject: str,
    role: str
) -> dict:

    return {
        "access_token": create_access_token(
            subject,
            role
        ),
        "refresh_token": create_refresh_token(
            subject,
            role
        ),
        "token_type": "bearer"
    }


# ==========================================
# TOKEN VALIDATION
# ==========================================

def decode_access_token(token: str) -> dict:

    payload = jwt.decode(
        token,
        ACCESS_TOKEN_SECRET,
        algorithms=[ALGORITHM],
        issuer=ISSUER,
        options={
            "require": [
                "sub",
                "role",
                "jti",
                "iat",
                "exp",
                "iss",
                "type"
            ]
        }
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError(
            "Invalid access token type."
        )

    return payload


def decode_refresh_token(token: str) -> dict:

    payload = jwt.decode(
        token,
        REFRESH_TOKEN_SECRET,
        algorithms=[ALGORITHM],
        issuer=ISSUER,
        options={
            "require": [
                "sub",
                "role",
                "jti",
                "iat",
                "exp",
                "iss",
                "type"
            ]
        }
    )

    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError(
            "Invalid refresh token type."
        )

    return payload


# ==========================================
# REFRESH TOKEN STORAGE SUPPORT
# ==========================================

def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token before storing it
    in the database.
    """

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()
