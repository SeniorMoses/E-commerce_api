
from decimal import Decimal
from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
)


# ==========================================
# COMMON TYPES
# ==========================================

PhoneNumber = Annotated[
    str,
    StringConstraints(
        min_length=7,
        max_length=20,
        pattern=r"^\+?[0-9]+$"
    )
]


# ==========================================
# ENUMS
# ==========================================

class UserRole(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"


class OrderStatus(str, Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"


# ==========================================
# BASE SCHEMA
# ==========================================

class ORMBaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )


# ==========================================
# USER SCHEMAS
# ==========================================

class UserCreate(BaseModel):
    email: EmailStr

    full_name: str = Field(
        min_length=2,
        max_length=100
    )

    phone_number: PhoneNumber

    password: str = Field(
        min_length=8,
        max_length=128
    )


class UserResponse(ORMBaseSchema):
    id: int
    email: EmailStr
    full_name: str
    phone_number: str
    role: UserRole
    is_active: bool
    bio : str | None=None

class UserUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    phone_number: PhoneNumber | None = None
    bio : str | None=None 

# ==========================================
# AUTHENTICATION SCHEMAS
# ==========================================

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

 u
class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    sub: EmailStr
    role: UserRole


class LoginRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128
    )


# ==========================================
# PRODUCT SCHEMAS
# ==========================================

class ProductCreate(BaseModel):
    title: str = Field(
        min_length=2,
        max_length=100
    )

    description: str | None = Field(
        default=None,
        max_length=1000
    )

    price: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2
    )

    stock: int = Field(
        default=0,
        ge=0
    )


class ProductUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    description: str | None = Field(
        default=None,
        max_length=1000
    )

    price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2
    )

    stock: int | None = Field(
        default=None,
        ge=0
    )


class ProductResponse(ORMBaseSchema):
    id: int
    title: str
    description: str | None
    price: Decimal
    stock: int


# ==========================================
# CART SCHEMAS
# ==========================================

class CartItemCreate(BaseModel):
    product_id: int

    quantity: int = Field(
        default=1,
        gt=0
    )


class CartItemUpdate(BaseModel):
    quantity: int = Field(
        gt=0
    )


class CartItemResponse(ORMBaseSchema):
    id: int
    quantity: int
    product: ProductResponse


class CartSummaryResponse(BaseModel):
    items: list[CartItemResponse]
    total_price: Decimal


# ==========================================
# ORDER SCHEMAS
# ==========================================

class OrderItemResponse(ORMBaseSchema):
    product_id: int | None
    product_title: str
    quantity: int
    price: Decimal


class OrderResponse(ORMBaseSchema):
    id: int
    total_price: Decimal
    status: OrderStatus
    items: list[OrderItemResponse]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# ==========================================
# PAGINATION SCHEMAS
# ==========================================

class PaginationParams(BaseModel):
    skip: int = Field(
        default=0,
        ge=0
    )

    limit: int = Field(
        default=20,
        ge=1,
        le=100
    )
