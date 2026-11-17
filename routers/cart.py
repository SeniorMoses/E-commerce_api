
from typing import Annotated
from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db

from models import (
    CartItemModel,
    ProductModel,
)

from schemas import (
    CartItemCreate,
    CartItemUpdate,
    CartItemResponse,
    CartSummaryResponse,
)

from dependency import CurrentUser


# ==========================================
# ROUTER CONFIGURATION
# ==========================================

router = APIRouter(
    prefix="/cart",
    tags=["Shopping Cart"],
)

DBSession = Annotated[
    AsyncSession,
    Depends(get_db)
]


# ==========================================
# ADD PRODUCT TO CART
# ==========================================

@router.post(
    "/",
    response_model=CartItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_cart(
    data: CartItemCreate,
    current_user: CurrentUser,
    db: DBSession,
):

    product_result = await db.execute(
        select(ProductModel).where(
            ProductModel.id == data.product_id
        )
    )

    product = product_result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    if product.stock < data.quantity:
        raise HTTPException(
            status_code=400,
            detail="Insufficient product stock.",
        )

    cart_result = await db.execute(
        select(CartItemModel).where(
            CartItemModel.user_id == current_user.id,
            CartItemModel.product_id == data.product_id,
        )
    )

    cart_item = cart_result.scalar_one_or_none()

    if cart_item:
        new_quantity = cart_item.quantity + data.quantity

        if new_quantity > product.stock:
            raise HTTPException(
                status_code=400,
                detail="Requested quantity exceeds available stock.",
            )

        cart_item.quantity = new_quantity

    else:
        cart_item = CartItemModel(
            user_id=current_user.id,
            product_id=data.product_id,
            quantity=data.quantity,
        )

        db.add(cart_item)

    await db.commit()

    result = await db.execute(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(CartItemModel.id == cart_item.id)
    )

    return result.scalar_one()


# ==========================================
# VIEW CART
# ==========================================

@router.get(
    "/",
    response_model=list[CartItemResponse],
)
async def view_cart(
    current_user: CurrentUser,
    db: DBSession,
):

    result = await db.execute(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(
            CartItemModel.user_id == current_user.id
        )
        .order_by(CartItemModel.id.desc())
    )

    return result.scalars().all()


# ==========================================
# CART SUMMARY
# ==========================================

@router.get(
    "/summary",
    response_model=CartSummaryResponse,
)
async def cart_summary(
    current_user: CurrentUser,
    db: DBSession,
):

    result = await db.execute(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(
            CartItemModel.user_id == current_user.id
        )
    )

    items = result.scalars().all()

    total_items = sum(
        item.quantity for item in items
    )

    total_price = sum(
        (
            item.product.price * item.quantity
            for item in items
        ),
        Decimal("0.00"),
    )

    return {
        "total_items": total_items,
        "total_price": total_price,
        "items": items,
    }


# ==========================================
# UPDATE CART ITEM QUANTITY
# ==========================================

@router.patch(
    "/{item_id}",
    response_model=CartItemResponse,
)
async def update_cart_item(
    item_id: int,
    data: CartItemUpdate,
    current_user: CurrentUser,
    db: DBSession,
):

    result = await db.execute(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(
            CartItemModel.id == item_id,
            CartItemModel.user_id == current_user.id,
        )
    )

    cart_item = result.scalar_one_or_none()

    if cart_item is None:
        raise HTTPException(
            status_code=404,
            detail="Cart item not found.",
        )

    if data.quantity > cart_item.product.stock:
        raise HTTPException(
            status_code=400,
            detail="Requested quantity exceeds available stock.",
        )

    cart_item.quantity = data.quantity

    await db.commit()

    result = await db.execute(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(CartItemModel.id == item_id)
    )

    return result.scalar_one()


# ==========================================
# REMOVE CART ITEM
# ==========================================

@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_cart_item(
    item_id: int,
    current_user: CurrentUser,
    db: DBSession,
):

    result = await db.execute(
        select(CartItemModel).where(
            CartItemModel.id == item_id,
            CartItemModel.user_id == current_user.id,
        )
    )

    cart_item = result.scalar_one_or_none()

    if cart_item is None:
        raise HTTPException(
            status_code=404,
            detail="Cart item not found.",
        )

    await db.delete(cart_item)
    await db.commit()

    return None


# ==========================================
# CLEAR CART
# ==========================================

@router.delete(
    "/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_cart(
    current_user: CurrentUser,
    db: DBSession,
):

    result = await db.execute(
        select(CartItemModel).where(
            CartItemModel.user_id == current_user.id
        )
    )

    items = result.scalars().all()

    for item in items:
        await db.delete(item)

    await db.commit()

    return None
