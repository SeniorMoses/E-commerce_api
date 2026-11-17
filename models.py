
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    ForeignKey,
    Numeric,
    DateTime,
    CheckConstraint,
    UniqueConstraint,
    func,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from db import Base


# ==========================================
# USER MODEL
# ==========================================

class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    bio: Mapped[str | None] = mapped_column(
    String(500),
    nullable=True
    )
    phone_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default="customer",
        server_default="customer",
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships

    cart_items: Mapped[list["CartItemModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    orders: Mapped[list["OrderModel"]] = relationship(
        back_populates="user"
    )


# ==========================================
# PRODUCT MODEL
# ==========================================

class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "price > 0",
            name="check_product_price"
        ),
        CheckConstraint(
            "stock >= 0",
            name="check_product_stock"
        ),
    )

    # Relationships

    cart_items: Mapped[list["CartItemModel"]] = relationship(
        back_populates="product"
    )

    order_items: Mapped[list["OrderItemModel"]] = relationship(
        back_populates="product"
    )


# ==========================================
# CART ITEM MODEL
# ==========================================

class CartItemModel(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "product_id",
            name="unique_user_cart_product"
        ),
        CheckConstraint(
            "quantity > 0",
            name="check_cart_quantity"
        ),
    )

    # Relationships

    user: Mapped["UserModel"] = relationship(
        back_populates="cart_items"
    )

    product: Mapped["ProductModel"] = relationship(
        back_populates="cart_items"
    )


# ==========================================
# ORDER MODEL
# ==========================================

class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="Pending",
        server_default="Pending",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "total_price >= 0",
            name="check_order_total"
        ),
    )

    # Relationships

    user: Mapped["UserModel"] = relationship(
        back_populates="orders"
    )

    items: Mapped[list["OrderItemModel"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan"
    )


# ==========================================
# ORDER ITEM MODEL
# ==========================================

class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    product_title: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="check_order_item_quantity"
        ),
        CheckConstraint(
            "price > 0",
            name="check_order_item_price"
        ),
    )

    # Relationships

    order: Mapped["OrderModel"] = relationship(
        back_populates="items"
    )

    product: Mapped["ProductModel | None"] = relationship(
        back_populates="order_items"
    )


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    jti: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    replaced_by_jti: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True
    )
