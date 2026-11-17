
from typing import Annotated
from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db

from models import (
    CartItemModel,
    ProductModel,
    OrderModel,
    OrderItemModel,
)

from schemas import (
    OrderResponse,
    OrderStatusUpdate,
    OrderStatus,
)

from dependency import (
    CurrentUser,
    CurrentAdmin,
)


# ==========================================
# ROUTER CONFIGURATION
# ==========================================

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

DBSession = Annotated[
    AsyncSession,
    Depends(get_db)
]


# ==========================================
# CHECKOUT
# ==========================================

@router.post(
    "/checkout",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def checkout(
    current_user: CurrentUser,
    db: DBSession,
):

    try:
        # Lock the customer's cart rows.
        cart_result = await db.execute(
            select(CartItemModel)
            .where(
                CartItemModel.user_id == current_user.id
            )
            .order_by(CartItemModel.product_id)
            .with_for_update()
        )

        cart_items = cart_result.scalars().all()

        if not cart_items:
            raise HTTPException(
                status_code=400,
                detail="Your cart is empty.",
            )

        product_ids = [
            item.product_id for item in cart_items
        ]

        # Lock products to prevent concurrent stock changes.
        product_result = await db.execute(
            select(ProductModel)
            .where(ProductModel.id.in_(product_ids))
            .order_by(ProductModel.id)
            .with_for_update()
        )

        products = {
            product.id: product
            for product in product_result.scalars().all()
        }

        total_price = Decimal("0.00")
        order_items = []

        # Validate inventory and calculate order total.
        for cart_item in cart_items:

            product = products.get(cart_item.product_id)

            if product is None:
                raise HTTPException(
                    status_code=409,
                    detail="A product in your cart is no longer available.",
                )

            if product.stock < cart_item.quantity:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Insufficient stock for {product.title}. "
                        f"Available: {product.stock}."
                    ),
                )

            item_total = (
                product.price * cart_item.quantity
            )

            total_price += item_total

            order_items.append(
                {
                    "product": product,
                    "quantity": cart_item.quantity,
                    "price": product.price,
                    "title": product.title,
                }
            )

        # Create order.
        order = OrderModel(
            user_id=current_user.id,
            total_price=total_price,
            status=OrderStatus.Pending.value,
        )

        db.add(order)

        await db.flush()

        # Create order items and update inventory.
        for item in order_items:

            product = item["product"]

            product.stock -= item["quantity"]

            db.add(
                OrderItemModel(
                    order_id=order.id,
                    product_id=product.id,
                    product_title=item["title"],
                    quantity=item["quantity"],
                    price=item["price"],
                )
            )

        # Clear the customer's cart.
        for cart_item in cart_items:
            await db.delete(cart_item)

        await db.commit()

        # Reload the order with its items.
        result = await db.execute(
            select(OrderModel)
            .options(selectinload(OrderModel.items))
            .where(OrderModel.id == order.id)
        )

        return result.scalar_one()

    except HTTPException:
        await db.rollback()
        raise

    except Exception:
        await db.rollback()
        raise


# ==========================================
# GET MY ORDERS
# ==========================================

@router.get(
    "/",
    response_model=list[OrderResponse],
)
async def get_my_orders(
    current_user: CurrentUser,
    db: DBSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):

    result = await db.execute(
        select(OrderModel)
        .options(selectinload(OrderModel.items))
        .where(
            OrderModel.user_id == current_user.id
        )
        .order_by(OrderModel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return result.scalars().all()


# ==========================================
# GET SINGLE ORDER
# ==========================================

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
async def get_order(
    order_id: int,
    current_user: CurrentUser,
    db: DBSession,
):

    result = await db.execute(
        select(OrderModel)
        .options(selectinload(OrderModel.items))
        .where(
            OrderModel.id == order_id,
            OrderModel.user_id == current_user.id,
        )
    )

    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    return order


# ==========================================
# ADMIN: GET ALL ORDERS
# ==========================================

@router.get(
    "/admin/all",
    response_model=list[OrderResponse],
)
async def get_all_orders(
    admin: CurrentAdmin,
    db: DBSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):

    result = await db.execute(
        select(OrderModel)
        .options(selectinload(OrderModel.items))
        .order_by(OrderModel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return result.scalars().all()


# ==========================================
# ADMIN: UPDATE ORDER STATUS
# ==========================================

@router.patch(
    "/admin/{order_id}/status",
    response_model=OrderResponse,
)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    admin: CurrentAdmin,
    db: DBSession,
):

    result = await db.execute(
        select(OrderModel)
        .options(selectinload(OrderModel.items))
        .where(OrderModel.id == order_id)
        .with_for_update()
    )

    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    order.status = data.status.value

    await db.commit()

    await db.refresh(order)

    result = await db.execute(
        select(OrderModel)
        .options(selectinload(OrderModel.items))
        .where(OrderModel.id == order_id)
    )

    return result.scalar_one()
