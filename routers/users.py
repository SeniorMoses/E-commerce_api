
from datetime import datetime, timezone

import jwt

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from fastapi.security import OAuth2PasswordRequestForm

from pydantic import BaseModel, Field

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db

from models import (
    UserModel,
    RefreshTokenModel,
)

from schemas import (
    UserCreate,
    UserResponse,
    UserUpdate,
    Token,
    RefreshTokenRequest,
)

from auth import (
    hash_password,
    verify_password,
    create_token_pair,
    decode_refresh_token,
    hash_refresh_token,
)

from dependency import (
    CurrentUser,
    CurrentAdmin,
)


# ==========================================
# ROUTER CONFIGURATION
# ==========================================

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

DBSession = Annotated[
    AsyncSession,
    Depends(get_db)
]


# ==========================================
# BIO SCHEMA
# ==========================================

class BioUpdate(BaseModel):
    bio: str = Field(
        min_length=1,
        max_length=500
    )


# ==========================================
# HELPERS
# ==========================================

def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def save_refresh_token(
    db: AsyncSession,
    user: UserModel,
    token: str,
    payload: dict,
) -> None:

    db.add(
        RefreshTokenModel(
            user_id=user.id,
            jti=payload["jti"],
            token_hash=hash_refresh_token(token),
            expires_at=datetime.fromtimestamp(
                payload["exp"],
                tz=timezone.utc,
            ),
        )
    )


# ==========================================
# REGISTER
# ==========================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    data: UserCreate,
    db: DBSession,
):

    result = await db.execute(
        select(UserModel).where(
            (UserModel.email == data.email)
            | (UserModel.phone_number == data.phone_number)
        )
    )

    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Email or phone number already exists.",
        )

    user = UserModel(
        email=data.email,
        full_name=data.full_name,
        phone_number=data.phone_number,
        hashed_password=await hash_password(data.password),
        role="customer",
        is_active=True,
    )

    db.add(user)

    try:
        await db.commit()
        await db.refresh(user)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email or phone number already exists.",
        )

    return user


# ==========================================
# LOGIN
# ==========================================

@router.post(
    "/login",
    response_model=Token,
)
async def login_user(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DBSession,
):

    result = await db.execute(
        select(UserModel).where(
            UserModel.email == form.username
        )
    )

    user = result.scalar_one_or_none()

    if user is None or not await verify_password(
        form.password,
        user.hashed_password,
    ):
        raise unauthorized()

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account has been deactivated.",
        )

    tokens = create_token_pair(
        subject=user.email,
        role=user.role,
    )

    payload = decode_refresh_token(
        tokens["refresh_token"]
    )

    try:
        await save_refresh_token(
            db,
            user,
            tokens["refresh_token"],
            payload,
        )

        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return tokens


# ==========================================
# REFRESH TOKEN ROTATION
# ==========================================

@router.post(
    "/refresh",
    response_model=Token,
)
async def refresh_tokens(
    data: RefreshTokenRequest,
    db: DBSession,
):

    try:
        payload = decode_refresh_token(data.refresh_token)

    except jwt.InvalidTokenError:
        raise unauthorized()

    jti = payload.get("jti")
    subject = payload.get("sub")

    if not isinstance(jti, str) or not isinstance(subject, str):
        raise unauthorized()

    result = await db.execute(
        select(RefreshTokenModel)
        .where(RefreshTokenModel.jti == jti)
        .with_for_update()
    )

    stored = result.scalar_one_or_none()

    if stored is None or stored.revoked:
        raise unauthorized()

    if stored.token_hash != hash_refresh_token(data.refresh_token):
        raise unauthorized()

    if stored.expires_at <= datetime.now(timezone.utc):
        raise unauthorized()

    user_result = await db.execute(
        select(UserModel).where(
            UserModel.id == stored.user_id
        )
    )

    user = user_result.scalar_one_or_none()

    if (
        user is None
        or not user.is_active
        or user.email != subject
    ):
        raise unauthorized()

    new_tokens = create_token_pair(
        subject=user.email,
        role=user.role,
    )

    new_payload = decode_refresh_token(
        new_tokens["refresh_token"]
    )

    stored.revoked = True
    stored.replaced_by_jti = new_payload["jti"]

    try:
        await save_refresh_token(
            db,
            user,
            new_tokens["refresh_token"],
            new_payload,
        )

        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return new_tokens


# ==========================================
# LOGOUT
# ==========================================

@router.post("/logout")
async def logout_user(
    data: RefreshTokenRequest,
    db: DBSession,
):

    try:
        payload = decode_refresh_token(data.refresh_token)

    except jwt.InvalidTokenError:
        raise unauthorized()

    result = await db.execute(
        select(RefreshTokenModel)
        .where(RefreshTokenModel.jti == payload["jti"])
        .with_for_update()
    )

    stored = result.scalar_one_or_none()

    if (
        stored is None
        or stored.revoked
        or stored.token_hash != hash_refresh_token(data.refresh_token)
    ):
        raise unauthorized()

    stored.revoked = True

    await db.commit()

    return {"message": "Successfully logged out."}


# ==========================================
# GET CURRENT PROFILE
# ==========================================

@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_profile(
    current_user: CurrentUser,
):
    return current_user


# ==========================================
# UPDATE PROFILE
# ==========================================

@router.patch(
    "/me",
    response_model=UserResponse,
)
async def update_profile(
    data: UserUpdate,
    current_user: CurrentUser,
    db: DBSession,
):

    updates = data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(current_user, field, value)

    try:
        await db.commit()
        await db.refresh(current_user)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The email or phone number is already in use.",
        )

    return current_user


# ==========================================
# GET USER BIO
# ==========================================

@router.get("/me/bio")
async def get_bio(
    current_user: CurrentUser,
):
    return {"bio": current_user.bio}


# ==========================================
# UPDATE USER BIO
# ==========================================

@router.put("/me/bio")
async def update_bio(
    data: BioUpdate,
    current_user: CurrentUser,
    db: DBSession,
):

    current_user.bio = data.bio.strip()

    await db.commit()
    await db.refresh(current_user)

    return {"message": "Bio updated successfully."}


# ==========================================
# ADMIN: LIST USERS
# ==========================================

@router.get(
    "/",
    response_model=list[UserResponse],
)
async def list_users(
    admin: CurrentAdmin,
    db: DBSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):

    result = await db.execute(
        select(UserModel)
        .order_by(UserModel.id.desc())
        .offset(skip)
        .limit(limit)
    )

    return result.scalars().all()


# ==========================================
# ADMIN: GET USER
# ==========================================

@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
async def get_user(
    user_id: int,
    admin: CurrentAdmin,
    db: DBSession,
):

    result = await db.execute(
        select(UserModel).where(
            UserModel.id == user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    return user


# ==========================================
# ADMIN: CHANGE ACCOUNT STATUS
# ==========================================

@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    admin: CurrentAdmin,
    db: DBSession,
):

    result = await db.execute(
        select(UserModel).where(
            UserModel.id == user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    user.is_active = is_active

    await db.commit()

    return {
        "message": "Account status updated.",
        "user_id": user.id,
        "is_active": user.is_active,
    }
