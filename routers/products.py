
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models import ProductModel
from schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)
from dependency import CurrentAdmin


# ==========================================
# ROUTER CONFIGURATION
# ==========================================

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)

DBSession = Annotated[
    AsyncSession,
    Depends(get_db)
]


# ==========================================
# CREATE PRODUCT
# ==========================================

@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    data: ProductCreate,
    admin: CurrentAdmin,
    db: DBSession,
):

    product = ProductModel(
        title=data.title,
        description=data.description,
        price=data.price,
        stock=data.stock,
    )

    db.add(product)

    await db.commit()
    await db.refresh(product)

    return product


# ==========================================
# LIST PRODUCTS
# ==========================================

@router.get(
    "/",
    response_model=list[ProductResponse],
)
async def list_products(
    db: DBSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
):

    if (
        min_price is not None
        and max_price is not None
        and min_price > max_price
    ):
        raise HTTPException(
            status_code=422,
            detail="Minimum price cannot exceed maximum price.",
        )

    statement = select(ProductModel)

    if search:
        statement = statement.where(
            or_(
                ProductModel.title.ilike(f"%{search}%"),
                ProductModel.description.ilike(f"%{search}%"),
            )
        )

    if min_price is not None:
        statement = statement.where(
            ProductModel.price >= min_price
        )

    if max_price is not None:
        statement = statement.where(
            ProductModel.price <= max_price
        )

    statement = (
        statement
        .order_by(ProductModel.id.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(statement)

    return result.scalars().all()


# ==========================================
# GET SINGLE PRODUCT
# ==========================================

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
async def get_product(
    product_id: int,
    db: DBSession,
):

    result = await db.execute(
        select(ProductModel).where(
            ProductModel.id == product_id
        )
    )

    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    return product


# ==========================================
# UPDATE PRODUCT
# ==========================================

@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    admin: CurrentAdmin,
    db: DBSession,
):

    result = await db.execute(
        select(ProductModel).where(
            ProductModel.id == product_id
        )
    )

    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    updates = data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    return product


# ==========================================
# DELETE PRODUCT
# ==========================================

@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_product(
    product_id: int,
    admin: CurrentAdmin,
    db: DBSession,
):

    result = await db.execute(
        select(ProductModel).where(
            ProductModel.id == product_id
        )
    )

    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    await db.delete(product)
    await db.commit()

    return None
